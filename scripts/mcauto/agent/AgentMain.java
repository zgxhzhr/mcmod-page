package mcauto;

import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * mcauto agent —— 进世界后自动触发导出，不需要按键、不需要 GUI、不需要作弊。
 *
 * 跨加载器兼容策略
 * ----------------
 * 各加载器运行时的成员名完全不同：
 *   NeoForge 1.21  mojmap   player / level / sendCommand
 *   Forge    1.20  SRG      f_91074_ / f_91073_ / m_45729_
 *   Fabric   1.20  intermediary  field_1724 / field_1687 / method_45729
 * 硬编码任何一种都会在另两种上失效，所以这里**一律按类型/签名找成员**，不看名字：
 *   - Minecraft 实例：返回类型是 Minecraft 的无参静态方法
 *   - level / player / connection：按字段类型（ClientLevel / LocalPlayer / ClientPacketListener，
 *     含 intermediary 的 class_638 / class_746 / class_634）
 *   - execute(Runnable)：只有一个 Runnable 参数的方法
 *   - sendCommand(String)：connection 上只有一个 String 参数的方法（优先名字含 command 的）
 *
 * 用法：
 *   -javaagent:mcauto-agent.jar=mode=lms,timeout=600,gameDir=D:\run
 *
 * mode:
 *   lms    → com.xkball...ItemDataExporterScreen#runExportMcMod()   （LMS/NeoForge）
 *   lmsent → com.xkball...McAutoBridge#exportEntities(modid)        （我们 fork 的 LMS）
 *   iconr  → 派发命令 exporticons <modid>                            （IconRenderer Forge）
 *   irr    → com.xkball...ExportMain#DoExport()（IRR 走这条也行）
 *
 * 完成后在 user.dir 写 _mcauto_done（成功）或 _mcauto_error.txt（失败）。
 */
public final class AgentMain {

    private static final long POLL_MS = 500;
    private static Instrumentation INST;

    // 各加载器下同一概念的类型名
    private static final String[] LEVEL_TYPES = {
            "net.minecraft.client.multiplayer.ClientLevel",
            "net.minecraft.class_638",
    };
    private static final String[] PLAYER_TYPES = {
            "net.minecraft.client.player.LocalPlayer",
            "net.minecraft.client.entity.player.ClientPlayerEntity",
            "net.minecraft.class_746",
    };
    private static final String[] CONNECTION_TYPES = {
            "net.minecraft.client.multiplayer.ClientPacketListener",
            "net.minecraft.client.network.ClientPlayNetworkHandler",
            "net.minecraft.class_634",
    };

    public static void premain(String args, Instrumentation inst) {
        INST = inst;
        final Map<String, String> cfg = parse(args);
        final long timeoutMs = Long.parseLong(cfg.getOrDefault("timeout", "600")) * 1000L;
        final String mode = cfg.getOrDefault("mode", "lms");
        final Path gameDir = Path.of(System.getProperty("user.dir"));
        log("premain mode=" + mode + " timeout=" + timeoutMs + "ms cwd=" + gameDir);

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

        // 第一阶段：**零反射**，只看类是否已加载。
        // 教训：在 Forge 模组加载期对 Minecraft 调 getDeclaredMethods()，会触发事件总线的
        // 类转换，而它那时还加载不了 org...ScreenEvent，结果抛错并把游戏卡成未响应。
        // 所以先等「世界类已加载」，说明客户端已经跑起来、Forge 转换器也初始化完了。
        while (System.currentTimeMillis() - start < timeoutMs) {
            mcClass = findClassAny("net.minecraft.client.Minecraft",
                    "net.minecraft.client.MinecraftClient",
                    "net.minecraft.class_310");
            boolean worldReady = findClassAny(LEVEL_TYPES) != null;
            boolean forgeReady = findClass("net.minecraftforge.client.event.ScreenEvent") != null
                    || findClass("net.minecraftforge.common.MinecraftForge") != null;
            if (mcClass != null && worldReady && (forgeReady || findClass("net.minecraftforge.eventbus.EventBus") == null)) {
                break;
            }
            Thread.sleep(POLL_MS);
        }
        if (mcClass == null) {
            writeError(gameDir, "等不到 Minecraft 类");
            return;
        }
        log("类已就绪，开始反射（探测世界状态）");

        // 第二阶段：反射，失败就重试 —— 加载期早一秒都可能炸
        while (System.currentTimeMillis() - start < timeoutMs) {
            {
                Object mc = null;
                try {
                    mc = mcInstance(mcClass);
                } catch (Throwable e) {
                    log("反射暂不可用（" + e.getClass().getSimpleName() + "），1 秒后重试");
                    Thread.sleep(1000);
                    continue;
                }
                if (mc != null) {
                    Object level = fieldByType(mc, LEVEL_TYPES);
                    Object player = fieldByType(mc, PLAYER_TYPES);
                    if (level != null && player != null) {
                        log("已进世界，3 秒后开始导出");
                        Thread.sleep(3000);
                        final Object mcF = mc;
                        Thread rm = new Thread(() -> releaseMouseLoop(mcF), "mcauto-release-mouse");
                        rm.setDaemon(true);
                        rm.start();
                        runExportOnMainThread(mcClass, mc, mode);
                        releaseMouse(mc);
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
        // 只认「把任务排进队列」的那个方法，**绝不盲试**。
        // 教训：BlockableEventLoop 里有 8 个单 Runnable 参数的方法，其中 submit 系
        // 会在**当前线程同步执行**；把渲染任务投进去 = 在 agent 线程调 OpenGL，
        // JVM 直接 fatal（"No context is current"），进程当场死，不可恢复。
        // 各映射下的名字：
        //   mojmap        execute
        //   Forge SRG     m_18707_
        //   intermediary  method_18856
        String[] queueMethodNames = {"execute", "m_18707_", "method_18856", "func_213187_a"};
        Method queue = null;
        for (String want : queueMethodNames) {
            Class<?> k = mc.getClass();
            while (k != null && k != Object.class && queue == null) {
                for (Method m : k.getDeclaredMethods()) {
                    Class<?>[] ps = m.getParameterTypes();
                    if (ps.length == 1 && ps[0] == Runnable.class && m.getName().equals(want)) {
                        queue = m;
                        break;
                    }
                }
                k = k.getSuperclass();
            }
            if (queue != null) {
                log("任务投递方法 " + queue.getName() + "（映射名 " + want + "）");
                break;
            }
        }
        if (queue == null) {
            throw new IllegalStateException(
                    "找不到 execute(Runnable)：候选名都没命中，不敢盲试（会崩 JVM）");
        }
        queue.setAccessible(true);

        final Throwable[] err = new Throwable[1];
        final Object lock = new Object();
        final boolean[] done = new boolean[1];

        Runnable task = () -> {
            log("任务开始 mode=" + mode + " 线程=" + Thread.currentThread().getName());
            try {
                switch (mode) {
                    case "lms":
                        lmsExport(System.getProperty("mcauto.modid", ""));
                        break;
                    case "lmsent":
                        bridgeCall("com.xkball.let_me_see_see.mcauto.McAutoBridge",
                                "com.xkball.let_me_see_see.LetMeSeeSee",
                                System.getProperty("mcauto.modid", ""));
                        break;
                    case "iconr":
                        commandExport(mc, "exporticons " + System.getProperty("mcauto.modid", "ALL"));
                        waitForProducts(Path.of(System.getProperty("user.dir"), "IconRendererOutput"),
                                600_000L);
                        break;
                    case "irr":
                        irrExport();
                        break;
                    default:
                        throw new IllegalArgumentException("未知 mode=" + mode);
                }
            } catch (Throwable ex) {
                err[0] = ex;
            } finally {
                synchronized (lock) {
                    done[0] = true;
                    lock.notifyAll();
                }
            }
        };

        queue.invoke(mc, task);

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

    // ── 导出实现 ──────────────────────────────────────────────

    private static void lmsExport(String modid) throws Exception {
        Class<?> screen = findClass("com.xkball.let_me_see_see.client.gui.screen.ItemDataExporterScreen");
        if (screen == null) {
            throw new IllegalStateException("找不到 ItemDataExporterScreen，LMS 没装或版本不符");
        }
        Object inst = screen.getDeclaredConstructor().newInstance();
        if (modid != null && !modid.isEmpty()) {
            try {
                screen.getMethod("setNamespaceFilterValue", String.class).invoke(inst, modid);
                log("已限定命名空间: " + modid);
            } catch (Throwable e) {
                log("设置命名空间失败: " + e);
            }
        }
        Method m = screen.getMethod("runExportMcMod");
        log("调用 runExportMcMod()");
        m.invoke(inst);
    }

    private static void bridgeCall(String bridgeName, String anchor, String modid) throws Exception {
        Class<?> bridge = findOrLoad(bridgeName, anchor);
        if (bridge == null) {
            throw new IllegalStateException("找不到 " + bridgeName + " —— 装的不是我们 fork 的版本");
        }
        Method m = bridge.getMethod("exportEntities", String.class);
        log("调用 " + bridge.getSimpleName() + "#exportEntities(" + modid + ")");
        Object ret = m.invoke(null, modid);
        log("返回: " + ret);
    }

    private static void commandExport(Object mc, String cmd) throws Exception {
        Object player = fieldByType(mc, PLAYER_TYPES);
        Object connection = fieldByType(player, CONNECTION_TYPES);
        if (connection == null) {
            throw new IllegalStateException("找不到 player.connection");
        }

        // Forge：客户端命令不在 connection 的调度器里（那是服务端同步下来的），
        // 必须走 net.minecraftforge.client.ClientCommandHandler.runCommand(String)。
        String bare = cmd.startsWith("/") ? cmd.substring(1) : cmd;
        Class<?> cch = findClass("net.minecraftforge.client.ClientCommandHandler");
        if (cch != null) {
            try {
                Method run = null;
                for (Method m : cch.getMethods()) {
                    if (m.getName().equals("runCommand") && m.getParameterCount() == 1
                            && m.getParameterTypes()[0] == String.class) {
                        run = m;
                        break;
                    }
                }
                if (run != null) {
                    log("ClientCommandHandler.runCommand(" + bare + ")");
                    Object r = run.invoke(null, bare);
                    log("  返回: " + r);
                    if (Boolean.TRUE.equals(r)) {
                        return;
                    }
                }
            } catch (Throwable e) {
                log("  ClientCommandHandler 调用失败: " + e);
            }
        }

        // 优先走 Brigadier 调度器：connection.getCommands() 返回 CommandDispatcher，
        // player.createCommandSourceStack() 给出 source，然后 dispatcher.execute(cmd, source)。
        // 这样不依赖 sendCommand/sendChat 这种一改映射就变的方法名 ——
        // 之前按「参数是 String」猜方法，猜到了 sendChat，命令被当聊天发出去。
        Object dispatcher = methodReturningType(connection,
                "com.mojang.brigadier.CommandDispatcher");
        Object source = methodReturningType(player,
                "net.minecraft.commands.CommandSourceStack");
        if (dispatcher != null && source != null) {
            for (Method m : dispatcher.getClass().getMethods()) {
                if (!m.getName().equals("execute") || m.getParameterCount() != 2) {
                    continue;
                }
                Class<?>[] ps = m.getParameterTypes();
                if (ps[0] != String.class) {
                    continue;
                }
                if (!ps[1].isInstance(source)) {
                    continue;
                }
                log("用调度器执行 /" + bare);
                m.invoke(dispatcher, bare, source);
                return;
            }
            log("调度器 execute(String, source) 没找到，退回 sendCommand");
        } else {
            log("拿不到 CommandDispatcher 或 CommandSourceStack，退回 sendCommand");
        }

        // 兜底：优先名字里带 command 的（mojmap/intermediary 都是 sendCommand）
        Method send = null;
        for (Method m : connection.getClass().getMethods()) {
            Class<?>[] ps = m.getParameterTypes();
            if (ps.length == 1 && ps[0] == String.class
                    && m.getName().toLowerCase().contains("command")) {
                send = m;
                break;
            }
        }
        if (send == null) {
            throw new IllegalStateException("找不到可用的命令发送方法");
        }
        send.setAccessible(true);
        log("派发命令 /" + cmd + "（方法 " + send.getName() + "）");
        send.invoke(connection, cmd.startsWith("/") ? cmd.substring(1) : cmd);
    }

    /** 找无参、返回类型为指定类（或其子类）的方法，用来拿 dispatcher / source */
    private static Object methodReturningType(Object obj, String returnTypeName) {
        Class<?> k = obj.getClass();
        while (k != null && k != Object.class) {
            for (Method m : k.getDeclaredMethods()) {
                if (m.getParameterCount() != 0) {
                    continue;
                }
                Class<?> rt = m.getReturnType();
                if (!rt.getName().equals(returnTypeName) && !returnTypeName.equals(rt.getName())) {
                    // 允许返回子类
                    boolean assignable = false;
                    for (Class<?> sup = rt; sup != null; sup = sup.getSuperclass()) {
                        if (sup.getName().equals(returnTypeName)) {
                            assignable = true;
                            break;
                        }
                    }
                    if (!assignable) {
                        continue;
                    }
                }
                try {
                    m.setAccessible(true);
                    Object v = m.invoke(obj);
                    if (v != null) {
                        return v;
                    }
                } catch (Throwable ignored) {
                }
            }
            k = k.getSuperclass();
        }
        return null;
    }

    /**
     * 等目录里出现 json 产物并稳定 5 秒。
     * 命令式触发（Forge 的 /exporticons）是异步导出，必须等落盘。
     */
    private static void waitForProducts(Path dir, long timeoutMs) {
        long start = System.currentTimeMillis();
        long lastSig = -1;
        long lastChange = start;
        while (System.currentTimeMillis() - start < timeoutMs) {
            long sig = 0;
            int files = 0;
            if (Files.isDirectory(dir)) {
                try (var stream = Files.walk(dir, 4)) {
                    for (Path f : (Iterable<Path>) stream::iterator) {
                        if (Files.isRegularFile(f) && f.toString().endsWith(".json")) {
                            files++;
                            sig += Files.size(f) + f.getFileName().toString().hashCode();
                        }
                    }
                } catch (Throwable ignored) {
                }
            }
            if (files > 0) {
                if (sig != lastSig) {
                    lastSig = sig;
                    lastChange = System.currentTimeMillis();
                    log("产物写入中… " + files + " 个 json");
                } else if (System.currentTimeMillis() - lastChange > 5000) {
                    log("产物稳定（" + files + " 个 json）");
                    return;
                }
            }
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                return;
            }
        }
        log("等产物超时");
    }

    private static void irrExport() throws Exception {
        Class<?> em = findClass("cn.mcmod.item_render.export.ExportMain");
        if (em == null) {
            throw new IllegalStateException("找不到 ExportMain，IRR 没装或版本不符");
        }
        Object inst = staticInvokeNoArg(em);
        Method m = em.getMethod("DoExport");
        log("调用 ExportMain#DoExport()");
        m.invoke(inst);
    }

    // ── 鼠标 ──────────────────────────────────────────────────

    private static void releaseMouse(Object mc) {
        try {
            Object mh = fieldByType(mc, new String[]{
                    "net.minecraft.client.MouseHandler", "net.minecraft.class_312"});
            if (mh == null) {
                return;
            }
            for (Method m : mh.getClass().getMethods()) {
                if (m.getParameterCount() == 0 && m.getName().toLowerCase().contains("release")) {
                    m.invoke(mh);
                    return;
                }
            }
        } catch (Throwable ignored) {
        }
    }

    private static void releaseMouseLoop(Object mc) {
        for (int i = 0; i < 240; i++) {
            releaseMouse(mc);
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                return;
            }
        }
    }

    // ── 反射工具：按类型/签名找，不按名字 ────────────────────────

    private static Class<?> findClass(String name) {
        for (Class<?> c : INST.getAllLoadedClasses()) {
            if (c.getName().equals(name)) {
                return c;
            }
        }
        return null;
    }

    private static Class<?> findClassAny(String... names) {
        for (String n : names) {
            Class<?> c = findClass(n);
            if (c != null) {
                return c;
            }
        }
        return null;
    }

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
                log("加载 " + name + " 失败: " + e);
            }
        }
        return null;
    }

    /** 返回类型是 mcClass 的无参静态方法 = getInstance() */
    private static Object mcInstance(Class<?> mcClass) {
        for (Method m : mcClass.getDeclaredMethods()) {
            if (!Modifier.isStatic(m.getModifiers()) || m.getParameterCount() != 0) {
                continue;
            }
            if (m.getReturnType() != mcClass) {
                continue;
            }
            try {
                m.setAccessible(true);
                return m.invoke(null);
            } catch (Throwable ignored) {
            }
        }
        return null;
    }

    /** 按字段类型名匹配（支持继承链），不看字段名 */
    private static Object fieldByType(Object obj, String[] typeNames) {
        if (obj == null) {
            return null;
        }
        Class<?> c = obj.getClass();
        while (c != null && c != Object.class) {
            for (Field f : c.getDeclaredFields()) {
                if (Modifier.isStatic(f.getModifiers())) {
                    continue;
                }
                String tn = f.getType().getName();
                for (String want : typeNames) {
                    if (tn.equals(want)) {
                        try {
                            f.setAccessible(true);
                            Object v = f.get(obj);
                            if (v != null) {
                                return v;
                            }
                        } catch (Throwable ignored) {
                        }
                    }
                }
            }
            c = c.getSuperclass();
        }
        return null;
    }

    /** 唯一参数为该类型的方法 */
    private static Method methodWithParams(Class<?> c, Class<?>... params) {
        Class<?> k = c;
        while (k != null && k != Object.class) {
            for (Method m : k.getDeclaredMethods()) {
                Class<?>[] ps = m.getParameterTypes();
                if (ps.length != params.length) {
                    continue;
                }
                boolean okAll = true;
                for (int i = 0; i < ps.length; i++) {
                    if (ps[i] != params[i]) {
                        okAll = false;
                        break;
                    }
                }
                if (okAll) {
                    return m;
                }
            }
            k = k.getSuperclass();
        }
        return null;
    }

    private static Object staticInvokeNoArg(Class<?> c) {
        for (Method m : c.getDeclaredMethods()) {
            if (Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 0
                    && m.getReturnType() == c) {
                try {
                    m.setAccessible(true);
                    return m.invoke(null);
                } catch (Throwable ignored) {
                }
            }
        }
        return null;
    }

    // ── 状态文件 ─────────────────────────────────────────────

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
            Files.writeString(gameDir.resolve("_mcauto_done"), "ok " + System.currentTimeMillis());
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
