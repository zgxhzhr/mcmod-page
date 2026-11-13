package mcauto;

import java.io.File;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * mcauto agent —— 进世界后自动触发导出，不需要按键、不需要 GUI、不需要作弊。
 *
 * 为什么用 agent 而不是：
 *   - 改 jar      ：要重建工程 / 写 coremod，成本高
 *   - 键盘模拟    ：要窗口焦点，且 GUI 按钮坐标不稳
 *   - 伴侣 mod    ：要 MDK 编译，每个 loader 一套
 * agent 只用 JDK API + 反射，一个 2KB 的 jar，与版本无关。
 *
 * 用法：
 *   -javaagent:mcauto-agent.jar=mode=lms,timeout=600,gameDir=D:\run
 *
 * mode:
 *   lms   → com.xkball.let_me_see_see...ItemDataExporterScreen#runExportMcMod()   （1.21.1 官方工具）
 *   iconr → 派发客户端命令 exporticons ALL                                       （IconRenderer 1.19-1.20.1）
 *   irr   → cn.mcmod.item_render.export.ExportMain#getInstance()#DoExport()      （IRR 1.16.x）
 *
 * 完成后在 gameDir 写 _mcauto_done（成功）或 _mcauto_error.txt（失败）。
 */
public final class AgentMain {

    private static final long POLL_MS = 500;
    private static Instrumentation INST;

    public static void premain(String args, Instrumentation inst) {
        INST = inst;
        final Map<String, String> cfg = parse(args);
        final long timeoutMs = Long.parseLong(cfg.getOrDefault("timeout", "600")) * 1000L;
        final String mode = cfg.getOrDefault("mode", "lms");
        // 不用 -javaagent 参数里的路径：中文路径经命令行传递后可能被错误解码，
        // 写哨兵会静默失败。user.dir 是进程工作目录（我们启动时设的 cwd），由系统提供。
        final Path gameDir = Path.of(System.getProperty("user.dir"));
        log("premain 启动 mode=" + mode + " timeout=" + timeoutMs + "ms gameDir=" + gameDir);

        Thread t = new Thread(() -> {
            try {
                waitWorldThenExport(mode, gameDir, timeoutMs);
            } catch (Throwable e) {
                writeError(gameDir, "agent 异常: " + e);
                log("异常: " + e);
            }
        }, "mcauto-agent");
        t.setDaemon(true);
        t.start();
    }

    private static void waitWorldThenExport(String mode, Path gameDir, long timeoutMs) throws Exception {
        long start = System.currentTimeMillis();
        Class<?> mcClass = null;
        log("等待 Minecraft 类加载…");
        while (System.currentTimeMillis() - start < timeoutMs) {
            if (mcClass == null) {
                mcClass = findClass("net.minecraft.client.Minecraft");
            }
            if (mcClass != null) {
                Object mc = staticInvoke(mcClass, "getInstance");
                if (mc != null) {
                    Object level = field(mc, "level");
                    Object player = field(mc, "player");
                    if (level != null && player != null) {
                        log("已进世界，3 秒后开始导出（等资源加载完）");
                        Thread.sleep(3000);
                        // 先放鼠标：MC 进世界会 GLFW_CURSOR_DISABLED，把系统光标锁在窗口里，
                        // 无人值守时会让人以为电脑卡死。releaseMouse 之后只要没人点窗口就不会再抓。
                        // 放后台线程反复放（若阻塞会拖慢导出 60 秒）
                        final Object mcFinal = mc;
                        final Class<?> mcClsFinal = mcClass;
                        Thread rm = new Thread(() -> releaseMouseLoop(mcClsFinal, mcFinal, 120),
                                "mcauto-release-mouse");
                        rm.setDaemon(true);
                        rm.start();
                        runExportOnMainThread(mcClass, mc, mode);
                        releaseMouse(mcClass, mc);
                        writeDone(gameDir);
                        log("导出完成，已写 _mcauto_done");
                        return;
                    }
                }
            }
            Thread.sleep(POLL_MS);
        }
        writeError(gameDir, "超时 " + timeoutMs + "ms 仍未进入世界");
        log("超时退出");
    }

    /** 在主线程（渲染线程）执行导出，否则 FBO 渲染会炸。 */
    private static void runExportOnMainThread(Class<?> mcClass, Object mc, String mode) throws Exception {
        Method execute = mcClass.getMethod("execute", Runnable.class);
        final Throwable[] err = new Throwable[1];
        final Object lock = new Object();
        final boolean[] done = new boolean[1];
        execute.invoke(mc, (Runnable) () -> {
            try {
                switch (mode) {
                    case "lms":
                        lmsExport();
                        break;
                    case "iconr":
                        commandExport(mcClass, mc, "exporticons ALL");
                        break;
                    case "irr":
                        irrExport();
                        break;
                    case "lmsent":
                        lmsEntityExport(System.getProperty("mcauto.modid", ""));
                        break;
                    default:
                        throw new IllegalArgumentException("未知 mode=" + mode);
                }
            } catch (Throwable t) {
                err[0] = t;
            } finally {
                synchronized (lock) {
                    done[0] = true;
                    lock.notifyAll();
                }
            }
        });
        synchronized (lock) {
            long deadline = System.currentTimeMillis() + 600_000L;
            while (!done[0] && System.currentTimeMillis() < deadline) {
                lock.wait(500);
            }
        }
        if (err[0] != null) {
            throw new RuntimeException("导出失败: " + err[0], err[0]);
        }
    }

    // ── 鼠标释放 ────────────────────────────────────────────────

    /**
     * 调 Minecraft.mouseHandler.releaseMouse()。
     * MC 进世界时用 GLFW_CURSOR_DISABLED 抓鼠标，系统光标被锁在窗口内，
     * 无人值守时用户会以为机器卡死。releaseMouse 把光标还回系统。
     */
    private static void releaseMouse(Class<?> mcClass, Object mc) {
        try {
            Object mh = field(mc, "mouseHandler");
            if (mh == null) {
                return;
            }
            for (Method m : mh.getClass().getMethods()) {
                if (m.getName().equals("releaseMouse") || m.getName().equals("func_198029_a")) {
                    m.invoke(mh);
                    return;
                }
            }
        } catch (Throwable ignored) {
        }
    }

    /** 连续放 N 秒（MC 在窗口获得焦点时可能再次抓取）。 */
    private static void releaseMouseLoop(Class<?> mcClass, Object mc, int seconds) {
        for (int i = 0; i < seconds; i++) {
            releaseMouse(mcClass, mc);
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                return;
            }
        }
    }

    // ── 三种导出实现 ─────────────────────────────────────────────

    /** LMS（mcmod 官方）：new ItemDataExporterScreen().runExportMcMod() */
    private static void lmsExport() throws Exception {
        lmsExport(System.getProperty("mcauto.modid", ""));
    }

    private static void lmsExport(String modid) throws Exception {
        Class<?> screen = findClass("com.xkball.let_me_see_see.client.gui.screen.ItemDataExporterScreen");
        if (screen == null) {
            throw new IllegalStateException("找不到 ItemDataExporterScreen，LMS 没装或版本不符");
        }
        Object inst = screen.getDeclaredConstructor().newInstance();
        // 只导目标模组：runExportMcMod 里 filterItem(itemID) 读 namespaceFilterValue，
        // 不设就等于导全部命名空间（含 1290 个原版物品，编码 PNG 极慢）
        if (modid != null && !modid.isEmpty()) {
            try {
                screen.getMethod("setNamespaceFilterValue", String.class).invoke(inst, modid);
                log("已限定命名空间: " + modid);
            } catch (Throwable e) {
                log("设置命名空间失败（将导出全部）: " + e);
            }
        } else {
            log("未指定 modid，导出全部命名空间（慢）");
        }
        Method m = screen.getMethod("runExportMcMod");
        log("调用 " + screen.getSimpleName() + "#runExportMcMod()");
        m.invoke(inst);
        log("导出方法返回");
    }

    /** IconRenderer：客户端命令 exporticons ALL */
    private static void commandExport(Class<?> mcClass, Object mc, String cmd) throws Exception {
        Object player = field(mc, "player");
        Object connection = field(player, "connection");
        // 1.20+ ClientPacketListener.sendCommand
        Method send = null;
        for (Method m : connection.getClass().getMethods()) {
            if (m.getName().equals("sendCommand") || m.getName().equals("sendUnsignedCommand")) {
                send = m;
                break;
            }
        }
        if (send == null) {
            throw new IllegalStateException("找不到 sendCommand");
        }
        log("派发命令 /" + cmd);
        send.invoke(connection, cmd);
    }

    /**
     * 我们 fork 过的 LMS：直接调 McAutoBridge.exportEntities(modid)。
     * 原版 LMS 没有实体导出，这是 fork 里新增的类。
     */
    private static void lmsEntityExport(String modid) throws Exception {
        Class<?> bridge = findOrLoad("com.xkball.let_me_see_see.mcauto.McAutoBridge",
                "com.xkball.let_me_see_see.LetMeSeeSee");
        if (bridge == null) {
            throw new IllegalStateException("找不到 McAutoBridge —— 装的不是我们 fork 的 LMS");
        }
        Method m = bridge.getMethod("exportEntities", String.class);
        log("调用 McAutoBridge#exportEntities(" + modid + ")");
        Object ret = m.invoke(null, modid);
        log("实体导出返回: " + ret);
    }

    /** IRR 1.16.x：ExportMain.getInstance().DoExport() */    private static void irrExport() throws Exception {
        Class<?> em = findClass("cn.mcmod.item_render.export.ExportMain");
        if (em == null) {
            throw new IllegalStateException("找不到 ExportMain，IRR 没装或版本不符");
        }
        Object inst = staticInvoke(em, "getInstance");
        Method m = em.getMethod("DoExport");
        log("调用 ExportMain#DoExport()");
        m.invoke(inst);
    }

    // ── 反射工具 ────────────────────────────────────────────────

    /**
     * 通过 Instrumentation 找已加载的类。
     * 不能用 Class.forName：MC / mod 类由 TransformationServices 的类加载器加载，
     * agent 自己所在的系统加载器看不到它们。
     */
    private static Class<?> findClass(String name) {
        for (Class<?> c : INST.getAllLoadedClasses()) {
            if (c.getName().equals(name)) {
                return c;
            }
        }
        return null;
    }

    /**
     * 找类；如果还没被加载过，就用 anchor 类（同 mod 里必然已加载的一个）的类加载器去加载。
     *
     * 为什么需要：getAllLoadedClasses 只包含**已加载**的类。我们 fork 加的 McAutoBridge
     * 没有任何其他代码引用它，所以永远不会被自动加载 —— 只扫已加载类会报「找不到」。
     */
    private static Class<?> findOrLoad(String name, String anchor) {
        Class<?> c = findClass(name);
        if (c != null) {
            return c;
        }
        Class<?> a = findClass(anchor);
        if (a != null) {
            try {
                return Class.forName(name, false, a.getClassLoader());
            } catch (Throwable e) {
                log("用 " + anchor + " 的加载器加载 " + name + " 失败: " + e);
            }
        }
        return null;
    }

    private static Object staticInvoke(Class<?> c, String name) {
        try {
            Method m = c.getMethod(name);
            return m.invoke(null);
        } catch (Throwable e) {
            return null;
        }
    }

    private static Object field(Object obj, String name) {
        Class<?> c = obj.getClass();
        while (c != null) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(obj);
            } catch (NoSuchFieldException e) {
                c = c.getSuperclass();
            } catch (Throwable e) {
                return null;
            }
        }
        return null;
    }

    // ── 状态文件与小工具 ─────────────────────────────────────────

    private static Map<String, String> parse(String args) {
        Map<String, String> m = new HashMap<>();
        if (args == null || args.isEmpty()) {
            return m;
        }
        for (String kv : args.split(",")) {
            int i = kv.indexOf('=');
            if (i > 0) {
                m.put(kv.substring(0, i).trim(), kv.substring(i + 1).trim());
            }
        }
        return m;
    }

    private static void writeDone(Path gameDir) {
        try {
            Files.writeString(gameDir.resolve("_mcauto_done"),
                    "ok " + System.currentTimeMillis());
        } catch (Throwable ignored) {
        }
    }

    private static void writeError(Path gameDir, String msg) {
        try {
            Files.writeString(gameDir.resolve("_mcauto_error.txt"), msg);
        } catch (Throwable ignored) {
        }
    }

    private static void log(String s) {
        System.out.println("[mcauto] " + s);
    }

    private AgentMain() {
    }
}
