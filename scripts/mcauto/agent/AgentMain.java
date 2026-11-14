package mcauto;

import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
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

    private static Class<?> mcClass;
    /** premain 解析出来的 -javaagent 参数，供其它方法读 */
    private static final java.util.Map<String, String> PARAMS = new java.util.HashMap<>();
    private static final long[] launchedWorld = new long[1];
    private static final boolean[] connectedOnce = new boolean[1];

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
        final Path gameDir = Paths.get(System.getProperty("user.dir"));
        log("premain mode=" + mode + " timeout=" + timeoutMs + "ms cwd=" + gameDir);
        PARAMS.putAll(cfg);

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

    /** 把「载入存档」也投到渲染线程（launchIntegratedServer 会碰 GL） */
    private static void tryLaunchOnMainThread(Class<?> mcClass, Object mc, String worldName) {
        try {
            Method queue = null;
            for (String want : new String[]{"execute", "m_18707_", "method_18856", "func_213187_a"}) {
                for (Method m : mc.getClass().getMethods()) {
                    if (m.getName().equals(want) && m.getParameterCount() == 1
                            && m.getParameterTypes()[0] == Runnable.class) {
                        queue = m;
                        break;
                    }
                }
                if (queue != null) {
                    break;
                }
            }
            final Object inst = mc;
            final String wn = worldName;
            if (queue == null) {
                log("找不到 execute(Runnable)，直接载入存档");
                launchWorld(inst, wn);
                return;
            }
            final Method q = queue;
            q.invoke(mc, (Runnable) () -> launchWorld(inst, wn));
        } catch (Throwable e) {
            log("载入存档失败: " + e);
        }
    }

    /** 把「自动连接」投到渲染线程（打开界面会碰 GL） */
    private static boolean tryAutoConnect(Class<?> mcClass, Object mc, String addr) {
        try {
            Method queue = null;
            for (String want : new String[]{"execute", "m_18707_", "method_18856", "func_213187_a"}) {
                for (Method m : mc.getClass().getMethods()) {
                    if (m.getName().equals(want) && m.getParameterCount() == 1
                            && m.getParameterTypes()[0] == Runnable.class) {
                        queue = m;
                        break;
                    }
                }
                if (queue != null) {
                    break;
                }
            }
            final Object inst = mc;
            final String addrF = addr;
            if (queue == null) {
                return autoConnect(inst, addrF);
            }
            queue.invoke(mc, (Runnable) () -> autoConnect(inst, addrF));
            return true;
        } catch (Throwable e) {
            log("自动连接投递失败: " + e);
            return false;
        }
    }

    private static void waitWorldThenExport(String mode, Path gameDir, long timeoutMs) throws Exception {
        long start = System.currentTimeMillis();
        Class<?> mcClass = null;
        log("等待 Minecraft 类加载…");
        long lastPhaseLog = 0;

        // 第一阶段：**零反射**，只看类是否已加载。
        // 教训：在 Forge 模组加载期对 Minecraft 调 getDeclaredMethods()，会触发事件总线的
        // 类转换，而它那时还加载不了 org...ScreenEvent，结果抛错并把游戏卡成未响应。
        // 所以先等「世界类已加载」，说明客户端已经跑起来、Forge 转换器也初始化完了。
        while (System.currentTimeMillis() - start < timeoutMs) {
            // 混淆命名版本（1.16.5 及更早 Forge）找不到类名，
            // 但 Forge 的 FMLClientHandler 不混淆，能直接给出实例。
            Object viaFml = mcViaFmlHandler();
            if (viaFml != null) {
                mcClass = viaFml.getClass();
                log("经 FMLClientHandler 拿到客户端类: " + mcClass.getName());
                break;
            }
            mcClass = findClassAny("net.minecraft.client.Minecraft",
                    "net.minecraft.client.MinecraftClient",
                    "net.minecraft.class_310");
            boolean worldReady = findClassAny(LEVEL_TYPES) != null;
            boolean forgeReady = findClass("net.minecraftforge.client.event.ScreenEvent") != null
                    || findClass("net.minecraftforge.common.MinecraftForge") != null;
            // 阶段一只需要「客户端类已出现 + Forge 转换器已就绪」。
            // 之前还要求 worldReady（世界类已加载），但世界类名各版本差异太大，
            // 1.16.5 上永远匹配不到，于是阶段一吃掉了整个超时（踩过）。
            boolean longEnough = System.currentTimeMillis() - start > 8000;
            if (mcClass != null && (forgeReady || worldReady || longEnough)) {
                break;
            }
            if (System.currentTimeMillis() - lastPhaseLog > 5000) {
                lastPhaseLog = System.currentTimeMillis();
                log("阶段一等待中: mcClass=" + (mcClass == null ? "null" : mcClass.getName())
                        + " worldReady=" + worldReady + " forgeReady=" + forgeReady);
            }
            Thread.sleep(POLL_MS);
        }
        if (mcClass == null) {
            // 混淆命名版本：Forge 类名不混淆，借 FMLClientHandler 拿实例再反推类
            Object viaFml = mcViaFmlHandler();
            if (viaFml != null) {
                mcClass = viaFml.getClass();
                log("经 FMLClientHandler 拿到客户端实例，类=" + mcClass.getName());
            }
        }
        AgentMain.mcClass = mcClass;
        if (mcClass == null) {
            writeError(gameDir, "等不到 Minecraft 类");
            return;
        }
        log("类已就绪，开始反射（探测世界状态）");

        // noworld=true：不要求进世界，客户端初始化完就直接导出。
        // 有些工具（IRR）只用物品注册表和渲染器，标题界面也能跑。
        if ("true".equalsIgnoreCase(PARAMS.getOrDefault("noworld",
                System.getProperty("mcauto.noworld", "false")))) {
            log("noworld 模式：不等世界，15 秒后直接导出");
            Thread.sleep(15000);
            for (int i = 0; i < 60; i++) {
                try {
                    Object mcNow = mcInstance(mcClass);
                    if (mcNow != null) {
                        runExportOnMainThread(mcClass, mcNow, mode);
                        writeDone(gameDir);
                        log("导出完成，已写 _mcauto_done");
                        return;
                    }
                } catch (Throwable e) {
                    log("noworld 尝试失败: " + e);
                }
                Thread.sleep(1000);
            }
            writeError(gameDir, "noworld 模式下也拿不到 Minecraft 实例");
            return;
        }

        // 第二阶段：反射，失败就重试 —— 加载期早一秒都可能炸
        while (System.currentTimeMillis() - start < timeoutMs) {
            {
                Object mc = null;
                try {
                    mc = mcInstance(mcClass);
                    // 老版本没有 quickPlay：等几秒还没有世界，就自己载入本地存档
                    String wantConnect = PARAMS.getOrDefault("connect",
                            System.getProperty("mcauto.connect", ""));
                    if (!wantConnect.isEmpty() && !connectedOnce[0]
                            && System.currentTimeMillis() - start > 12000) {
                        connectedOnce[0] = true;
                        boolean ok = tryAutoConnect(mcClass, mc, wantConnect);
                        if (!ok) {
                            log("自动连接失败，回落到本地载入存档");
                            launchWorld(mc, "mcauto");
                        }
                    }
                    String wantWorld = PARAMS.getOrDefault("world",
                            System.getProperty("mcauto.world", ""));
                    if (!wantWorld.isEmpty() && launchedWorld[0] == 0
                            && System.currentTimeMillis() - start > 15000) {
                        launchedWorld[0] = System.currentTimeMillis();
                        tryLaunchOnMainThread(mcClass, mc, wantWorld);
                    }
                } catch (Throwable e) {
                    log("反射暂不可用（" + e.getClass().getSimpleName() + "），1 秒后重试");
                    Thread.sleep(1000);
                    continue;
                }
                if (mc != null) {
                    Object level = fieldByType(mc, LEVEL_TYPES);
                    if (level == null) {
                        level = fieldByNames(mc, new String[]{"field_71441_e", "field_71308_aa", "world", "level"});
                    }
                    Object player = fieldByType(mc, PLAYER_TYPES);
                    if (player == null) {
                        player = fieldByNames(mc, new String[]{"field_71439_g", "field_71438_f", "player"});
                    }
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
                    case "iconrd":
                        // 直接反射调工具自己的导出类，不走命令通道。
                        // Forge 各版本客户端命令入口不一样（1.18.2 没有 getSource），
                        // 而 FileHelper(modid) 构造完就写完了文件，最稳。
                        directExport(System.getProperty("mcauto.modid", ""));
                        break;
                    case "iconr":
                        commandExport(mc, "exporticons " + System.getProperty("mcauto.modid", "ALL"));
                        waitForProducts(Paths.get(System.getProperty("user.dir"), "IconRendererOutput"),
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
        if (cch == null) {
            log("拿不到 ClientCommandHandler，列出 connection 上的单 String 方法：");
            for (Method m : connection.getClass().getMethods()) {
                Class<?>[] ps = m.getParameterTypes();
                if (ps.length == 1 && ps[0] == String.class) {
                    log("   " + m.getDeclaringClass().getSimpleName() + "#" + m.getName()
                            + " -> " + m.getReturnType().getSimpleName());
                }
            }
        }
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
                if (run == null) {
                    log("  ClientCommandHandler 里没有单 String 的 runCommand，列出方法：");
                    for (Method m : cch.getMethods()) {
                        if (m.getName().toLowerCase().contains("command")
                                || m.getName().toLowerCase().contains("dispatch")) {
                            StringBuilder sb = new StringBuilder("     " + m.getName() + "(");
                            for (Class<?> pt : m.getParameterTypes()) {
                                sb.append(pt.getSimpleName()).append(",");
                            }
                            sb.append(") -> ").append(m.getReturnType().getSimpleName());
                            log(sb.toString());
                        }
                    }
                    // 换条路：拿客户端调度器自己执行
                    try {
                        Object cdisp = methodReturningType(cch, "com.mojang.brigadier.CommandDispatcher");
                        // 1.18.2 没有 getSource()，自己 new 一个 ClientCommandSourceStack；
                        // 1.19+ 有 getSource()。两条都试。
                        Method gsrc = null;
                        for (Method m : cch.getMethods()) {
                            if (m.getParameterCount() == 0 && m.getName().toLowerCase().contains("source")) {
                                gsrc = m;
                                break;
                            }
                        }
                        Object csrc = null;
                        if (gsrc != null) {
                            csrc = gsrc.invoke(null);
                        } else {
                            Class<?> srcCls = findClass("net.minecraftforge.client.ClientCommandSourceStack");
                            if (srcCls != null) {
                                for (java.lang.reflect.Constructor<?> ctor : srcCls.getConstructors()) {
                                    Class<?>[] ps = ctor.getParameterTypes();
                                    try {
                                        if (ps.length == 0) {
                                            csrc = ctor.newInstance();
                                        } else if (ps.length == 1 && ps[0].isInstance(mc)) {
                                            csrc = ctor.newInstance(mc);
                                        }
                                        if (csrc != null) {
                                            log("  自己构造了 source: " + ctor);
                                            break;
                                        }
                                    } catch (Throwable ignored) {
                                    }
                                }
                            }
                        }
                        if (cdisp != null && csrc != null) {
                            log("  改用客户端调度器执行（source=" + (csrc == null ? "null" : csrc.getClass().getSimpleName()) + "）");
                            for (Method m : cdisp.getClass().getMethods()) {
                                if (!m.getName().equals("execute") || m.getParameterCount() != 2
                                        || m.getParameterTypes()[0] != String.class) {
                                    continue;
                                }
                                if (csrc == null || m.getParameterTypes()[1].isInstance(csrc)) {
                                    m.invoke(cdisp, bare, csrc);
                                    log("  客户端调度器已执行");
                                    return;
                                }
                            }
                        } else {
                            log("  拿不到客户端调度器或 source");
                        }
                    } catch (Throwable e2) {
                        log("  客户端调度器执行失败: " + e2);
                    }
                } else {
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
                try (java.util.stream.Stream<Path> stream = Files.walk(dir, 4)) {
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

    /**
     * 让客户端自己加载本地单人存档（老版本没有 --quickPlaySingleplayer）。
     *
     * 1.12.2 / 1.7.10 的 Minecraft 都有
     *   launchIntegratedServer(String folder, String worldName, WorldSettings settings)
     * 直接调用就能进世界，比另起一个专用服务端 + --server 简单得多
     * （1.12.2 的 Forge 服务端还要单独装，坑很深）。
     */
    /**
     * 自动连接本地服务端（1.13~1.16 用）。
     *
     * 这些版本没有 --quickPlaySingleplayer，而 --server 只是把地址填进多人界面、
     * 不会自己连。于是直接构造 ConnectScreen 打开：
     *   mc.setScreen(new ConnectScreen(parent, mc, new ServerData(name, "host:port", false)))
     * 1.16.5 是 mojmap 类名（net.minecraft.client.gui.screen.ConnectScreen），可以直接反射。
     */
    private static boolean autoConnect(Object mc, String addr) {
        try {
            int colon = addr.lastIndexOf(':');
            String host = colon > 0 ? addr.substring(0, colon) : addr;
            int port = colon > 0 ? Integer.parseInt(addr.substring(colon + 1)) : 25565;
            String ip = host + ":" + port;

            Class<?> serverDataC = findClass("net.minecraft.client.multiplayer.ServerData");
            if (serverDataC == null) {
                log("找不到 ServerData 类");
                return false;
            }
            Object serverData = serverDataC.getConstructor(String.class, String.class, boolean.class)
                    .newInstance("mcauto-local", ip, false);

            // 关键：用 ServerData 自己的类加载器去加载 ConnectScreen。
            // findClass() 试的那几个加载器在 Forge 的 ModLauncher 下拿不到未加载的类，
            // 而 ServerData 已经加载好了，它的 loader 一定是对的。
            ClassLoader ldr = serverDataC.getClassLoader();
            Class<?> connectC = null;
            for (String cn : new String[]{
                    "net.minecraft.client.gui.screens.ConnectScreen",
                    "net.minecraft.client.gui.screen.ConnectScreen"}) {
                try {
                    connectC = Class.forName(cn, false, ldr);
                    log("ConnectScreen 类找到了: " + cn);
                    break;
                } catch (Throwable ignored) {
                }
            }
            if (connectC == null) {
                // 诊断：把已加载类里名字带 ConnectScreen / ServerData 的都列出来
                int n = 0;
                for (Class<?> c : INST.getAllLoadedClasses()) {
                    String nm = c.getName();
                    if (nm.contains("ConnectScreen") || nm.contains("ServerData")
                            || nm.contains("ServerList")) {
                        log("  候选类: " + nm);
                        if (++n > 8) {
                            break;
                        }
                    }
                }
                if (n == 0) {
                    log("  已加载类里没有任何 ConnectScreen / ServerData / ServerList");
                }
                return false;
            }
            Class<?> screenC = findClass("net.minecraft.client.gui.screen.Screen");
            Object screen = null;
            for (java.lang.reflect.Constructor<?> ctor : connectC.getConstructors()) {
                Class<?>[] ps = ctor.getParameterTypes();
                if (ps.length == 3) {
                    if (ps[0].isAssignableFrom(screenC == null ? Object.class : screenC) || ps[0] == screenC) {
                        screen = ctor.newInstance(null, mc, serverData);
                    } else {
                        screen = ctor.newInstance(null, mc, serverData);
                    }
                    break;
                }
            }
            if (screen == null) {
                log("ConnectScreen 构造失败");
                return false;
            }
            for (Method m : mc.getClass().getMethods()) {
                if (m.getParameterCount() == 1 && m.getName().equals("setScreen")) {
                    m.invoke(mc, screen);
                    log("已打开连接界面 " + ip);
                    return true;
                }
            }
            log("找不到 setScreen");
        } catch (Throwable e) {
            log("自动连接失败: " + e);
        }
        return false;
    }

    private static boolean launchWorld(Object mc, String worldName) {
        // 各版本进世界的方法名/签名都不一样，都试一遍（都是 private 的）：
        //   1.16.5 : loadWorld(String, DynamicRegistries.Impl, Function, Function4,
        //                     boolean, WorldSelectionType, boolean)  7 参
        //   1.12.2 : launchIntegratedServer(String, String, WorldSettings)  3 参
        // 策略：名字里带 loadworld / launchintegratedserver，第一个参数是 String 的都要试。
        java.util.List<Method> cands = new java.util.ArrayList<>();
        for (Class<?> k = mc.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            Method[] ms;
            try {
                ms = k.getDeclaredMethods();
            } catch (Throwable e) {
                continue;
            }
            for (Method m : ms) {
                // 跳过编译器生成的 lambda$xxx / access$xxx，之前就误调到了
                // lambda$loadWorld$25（那是内部回调，调了没有意义）
                if (m.isSynthetic() || m.getName().startsWith("lambda$")) {
                    continue;
                }
                Class<?>[] ps = m.getParameterTypes();
                if (ps.length < 1 || ps[0] != String.class) {
                    continue;
                }
                String n = m.getName().toLowerCase();
                boolean byName = n.contains("loadworld") || n.contains("launchintegratedserver");
                boolean bySig = ps.length >= 2 && ps[1] == String.class;
                if (byName || bySig) {
                    cands.add(m);
                }
            }
        }
        cands.sort((a, b) -> {
            boolean aReal = a.getName().equalsIgnoreCase("loadWorld")
                    || a.getName().equalsIgnoreCase("launchIntegratedServer");
            boolean bReal = b.getName().equalsIgnoreCase("loadWorld")
                    || b.getName().equalsIgnoreCase("launchIntegratedServer");
            return aReal == bReal ? 0 : (aReal ? -1 : 1);
        });
        for (Method m : cands) {
            Class<?>[] ps = m.getParameterTypes();
            Object[] args = new Object[ps.length];
            for (int i = 0; i < ps.length; i++) {
                if (i == 0 || (ps[i] == String.class && i == 1)) {
                    args[i] = worldName;
                } else if (ps[i] == boolean.class) {
                    args[i] = Boolean.FALSE;
                } else if (ps[i] == int.class) {
                    args[i] = 0;
                } else if (ps[i].isPrimitive()) {
                    args[i] = null;
                } else {
                    args[i] = null;
                }
            }
            try {
                m.setAccessible(true);
                log("调用 " + m.getName() + " (" + ps.length + " 参) 载入存档 " + worldName);
                m.invoke(mc, args);
                return true;
            } catch (Throwable e) {
                log("  " + m.getName() + " 失败: " + e);
            }
        }
        if (true) {  // 临时：无条件 dump
            StringBuilder all = new StringBuilder();
            for (Method m : mc.getClass().getMethods()) {
                all.append(m.getName()).append("/").append(m.getParameterCount()).append(" ");
            }
            log("ALLPUBLIC " + all);
        }
        log("没找到可用的载入存档方法（候选 " + cands.size() + " 个）");
        return false;
    }

    /**
     * 直接构造工具的导出类（Forge/Fabric 的包名不同，两个都试）。
     * FileHelper(String modId) 构造函数里就完成 收集 → 渲染 → 写文件 的全流程。
     */
    private static void directExport(String modid) throws Exception {
        String[] classes = {
                "top.gregtao.iconrenderer.utils.FileHelper",   // Forge 移植版
                "top.gregtao.iconr.utils.FileHelper",          // 上游 Fabric 版
        };
        Throwable last = null;
        for (String name : classes) {
            Class<?> cls = findClass(name);
            if (cls == null) {
                continue;
            }
            try {
                Object inst = cls.getConstructor(String.class).newInstance(modid);
                log("直接导出完成：" + name + " 实例=" + (inst != null));
                return;
            } catch (Throwable e) {
                last = e;
                log("  " + name + " 导出失败: " + e);
            }
        }
        throw new IllegalStateException("找不到可用的 FileHelper" + (last == null ? "" : "（最后错误: " + last + "）"));
    }

    /**
     * IRR（Item Render Rebirth）直调导出。
     *
     * 它的导出入口不是命令，是 ExportUtils.INSTANCE.exportMods()：
     *   - 1.12.2 / 1.7.10 都有 public void exportMods()
     *   - 导出前要先 ItemList.updateList() 把物品列表填好
     * 产物：当前目录下 export/<modid>_item.json（一次性导出所有模组，按命名空间分文件）
     */
    private static void irrExport() throws Exception {
        // IRR 有两代 API，类名都是不混淆的（mod 自己的类不受 MC 混淆影响）：
        //   1.x 老版 (1.7.10 / 1.12.2): itemrender.client.export.ExportUtils#exportMods()
        //                               + ItemList.updateList()
        //   2.x 新版 (1.16.x)        : cn.mcmod.item_render.export.ExportMain#getInstance()
        //                               + DoExport()
        boolean done = false;

        // ── 新版 1.16.x ──
        Class<?> em = findClass("cn.mcmod.item_render.export.ExportMain");
        if (em != null) {
            Object inst = null;
            try {
                Method gi = em.getMethod("getInstance");
                inst = gi.invoke(null);
            } catch (Throwable ignored) {
            }
            if (inst == null) {
                try {
                    java.lang.reflect.Constructor<?> c = em.getDeclaredConstructor();
                    c.setAccessible(true);
                    inst = c.newInstance();
                } catch (Throwable ignored) {
                }
            }
            if (inst != null) {
                Method m = em.getMethod("DoExport");
                log("调用 ExportMain#DoExport()");
                try {
                    m.invoke(inst);
                    done = true;
                } catch (java.lang.reflect.InvocationTargetException e) {
                    log("DoExport 抛出: " + e.getCause());
                    done = true;   // 已经执行过了，不再走老 API
                }
            }
        }

        // ── 老版 1.7.10 / 1.12.2 ──
        if (!done) {
            Class<?> listCls = findClass("itemrender.client.export.ItemList");
            if (listCls != null) {
                try {
                    listCls.getMethod("updateList").invoke(null);
                    log("ItemList.updateList() 完成");
                } catch (Throwable e) {
                    log("ItemList.updateList() 失败: " + e);
                }
            }
            Class<?> eu = findClass("itemrender.client.export.ExportUtils");
            if (eu == null) {
                throw new IllegalStateException("找不到 IRR 的导出类（两代 API 都没有）");
            }
            Object inst = null;
            try {
                inst = eu.getField("INSTANCE").get(null);
            } catch (Throwable ignored) {
            }
            if (inst == null) {
                inst = eu.getConstructor().newInstance();
            }
            log("调用 ExportUtils#exportMods()");
            try {
                eu.getMethod("exportMods").invoke(inst);
            } catch (java.lang.reflect.InvocationTargetException e) {
                log("exportMods 抛出: " + e.getCause());
            }
        }
        log("IRR 导出调用结束");
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
        // 没加载过就主动加载：Forge 的 ClientCommandHandler 是懒加载的，
        // 只查已加载类会永远拿不到（1.18.2 上踩过）。
        ClassLoader[] loaders = {
                Thread.currentThread().getContextClassLoader(),
                ClassLoader.getSystemClassLoader(),
                AgentMain.class.getClassLoader(),
                mcClass == null ? null : mcClass.getClassLoader(),
        };
        for (ClassLoader cl : loaders) {
            if (cl == null) {
                continue;
            }
            try {
                return Class.forName(name, false, cl);
            } catch (Throwable ignored) {
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
    /**
     * 通过 Forge 的 FMLClientHandler 拿 Minecraft 实例。
     *
     * 1.16.5 及更早的 Forge 运行时类名是**混淆**的（Minecraft 叫 bib / dbg …），
     * 按 mojmap 名字永远找不到。但 Forge 自己的类名不混淆，而且
     *   net.minecraftforge.fml.client.FMLClientHandler.instance().getClient()
     * 直接返回那个实例，不需要知道它叫什么。
     */
    private static Object mcViaFmlHandler() {
        try {
            Class<?> h = findClass("net.minecraftforge.fml.client.FMLClientHandler");
            if (h == null) {
                return null;
            }
            Object inst = null;
            for (Method m : h.getMethods()) {
                if (m.getParameterCount() == 0 && m.getName().equalsIgnoreCase("instance")) {
                    inst = m.invoke(null);
                    break;
                }
            }
            if (inst == null) {
                return null;
            }
            for (Method m : inst.getClass().getMethods()) {
                if (m.getParameterCount() == 0
                        && m.getName().toLowerCase().contains("getclient")
                        && !m.getReturnType().isPrimitive()) {
                    return m.invoke(inst);
                }
            }
        } catch (Throwable e) {
            log("FMLClientHandler 取 client 失败: " + e);
        }
        return null;
    }

    private static Object mcInstance(Class<?> mcClass) {
        if (mcClass == null) {
            // 混淆命名版本（1.16.5 及更早的 Forge）拿不到类名，走 Forge 的 handler
            return mcViaFmlHandler();
        }
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
    /** 按字段名取（1.16.5 及更早用 SRG 名：world=field_71441_e，player=field_71439_g） */
    private static Object fieldByNames(Object obj, String[] names) {
        if (obj == null) {
            return null;
        }
        Class<?> k = obj.getClass();
        while (k != null && k != Object.class) {
            for (java.lang.reflect.Field f : k.getDeclaredFields()) {
                for (String n : names) {
                    if (f.getName().equals(n)) {
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
            k = k.getSuperclass();
        }
        return null;
    }

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
            Files.write(gameDir.resolve("_mcauto_done"),
                    ("ok " + System.currentTimeMillis()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
        } catch (Throwable ignored) {
        }
    }

    private static void writeError(Path gameDir, String msg) {
        try {
            Files.write(gameDir.resolve("_mcauto_error.txt"),
                    msg.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        } catch (Throwable ignored) {
        }
    }

    private static void log(String s) {
        System.out.println("[mcauto] " + s);
    }

    private AgentMain() {
    }
}
