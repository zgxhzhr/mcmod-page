package mcauto.irr;

import net.minecraftforge.event.TickEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.common.MinecraftForge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * IRR 的自动化触发器（1.16.5 Forge）。
 *
 * 为什么需要它
 * ------------
 * 1.16.5 及更早的 Forge 运行时类名是**混淆**的（Minecraft 叫 dbg/…），
 * 外部 javaagent 按名字反射拿不到任何东西；而且 1.16.5 的 --server 不会自动连，
 * 不自己进世界就没有 Level → IRR 的实体渲染和部分物品图标全错。
 *
 * 所以把「进世界 + 触发导出」放进 mod 里：
 *   · 用 Forge 自己的类（FMLClientHandler / TickEvent，类名不混淆）拿客户端实例
 *   · 用反射按**方法签名**找 launchIntegratedServer（不依赖混淆名）
 *   · 用 SRG 字段名（field_71441_e / field_71439_g）判断是否已进世界
 *   · 在客户端 tick 里直接调用 IRR 的 cn.mcmod.item_render.export.ExportMain#DoExport
 *     —— 本来就在客户端线程，不需要任何线程投递
 *
 * 参数（JVM -D）：
 *   -Dmcauto.modid=xxx     目标命名空间，仅用于写哨兵内容
 *   -Dmcauto.world=mcauto  要载入的存档目录名（默认 mcauto）
 *   -Dmcauto.delay=60      进世界后再等多少 tick 才导出（默认 60 ≈ 3 秒）
 */
@Mod("irrmcauto")
public class IrrTrigger {

    private int ticks = 0;
    private boolean worldRequested = false;
    private boolean exporting = false;
    private boolean done = false;

    static {
        // 类一加载就打印，用来确认 Forge 到底有没有把 jar 加载进来、
        // 以及 -D 参数有没有传到 JVM（排查用）
        System.out.println("[irrmcauto] class loaded; modid="
                + System.getProperty("mcauto.modid", "<null>")
                + " world=" + System.getProperty("mcauto.world", "<null>")
                + " delay=" + System.getProperty("mcauto.delay", "<null>"));
    }

    public IrrTrigger() {
        MinecraftForge.EVENT_BUS.register(this);
        System.out.println("[irrmcauto] constructed, registered to EVENT_BUS");
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || done) {
            return;
        }
        String modid = System.getProperty("mcauto.modid", "");
        if (modid.isEmpty()) {
            return;   // 没指定就什么都不做，当普通模组
        }
        Object client = clientInstance();
        if (client == null) {
            return;
        }
        diagLogged = true;
        try {
            if (!worldRequested) {
                worldRequested = true;
                String world = System.getProperty("mcauto.world", "mcauto");
                boolean ok = requestWorld(client, world);
                log("请求载入存档 " + world + " → " + ok);
                return;
            }
            if (!inWorld(client)) {
                return;
            }
            int delay = Integer.getInteger("mcauto.delay", 60);
            if (++ticks < delay) {
                return;
            }
            if (exporting) {
                return;
            }
            exporting = true;
            log("已进世界，开始调用 IRR 导出");
            boolean ok = callIrrExport();
            write("_mcauto_done", ok ? ("ok " + modid) : "export-returned-false");
            done = true;
            log("导出调用结束，已写 _mcauto_done");
        } catch (Throwable t) {
            write("_mcauto_error.txt", String.valueOf(t));
            log("出错: " + t);
            done = true;
        }
    }

    // ── 拿客户端实例（Forge 类名不混淆）──
    private static boolean diagLogged = false;

    private static void diag(String msg) {
        if (!diagLogged) {
            System.out.println("[irrmcauto] diag: " + msg);
        }
    }

    private static Object clientInstance() {
        // 1.16.5：LogicalSidedProvider.get(CLIENT) 返回的是执行器，不是 Minecraft 实例（踩过）。
        // 正确办法是反射 Minecraft 的静态无参方法 func_71410_x()（SRG 名，返回 Minecraft 自身）。
        try {
            Class<?> mc = Class.forName("net.minecraft.client.Minecraft");
            for (java.lang.reflect.Method m : mc.getDeclaredMethods()) {
                if (java.lang.reflect.Modifier.isStatic(m.getModifiers())
                        && m.getParameterCount() == 0
                        && m.getReturnType() == mc) {
                    m.setAccessible(true);
                    Object got = m.invoke(null);
                    if (got != null) {
                        diag("拿到 Minecraft 实例：" + m.getName());
                        return got;
                    }
                }
            }
            diag("Minecraft 里没找到 静态无参且返回自身 的方法");
        } catch (Throwable e) {
            diag("反射 Minecraft.getInstance 失败: " + e);
        }
        // 兜底：LogicalSidedProvider（某些版本真的返回 client）
        try {
            Class<?> lsp = Class.forName("net.minecraftforge.fml.LogicalSidedProvider");
            Class<?> sideCls = Class.forName("net.minecraftforge.fml.LogicalSide");
            Object provider = lsp.getField("INSTANCE").get(null);
            Object clientSide = null;
            for (Object o : sideCls.getEnumConstants()) {
                if ("CLIENT".equalsIgnoreCase(String.valueOf(o))) { clientSide = o; break; }
            }
            if (clientSide != null) {
                Object got = lsp.getMethod("get", sideCls).invoke(provider, clientSide);
                if (got instanceof java.util.Optional) got = ((java.util.Optional<?>) got).orElse(null);
                if (got != null && got.getClass().getName().contains("Minecraft")) {
                    diag("LogicalSidedProvider 兜底命中");
                    return got;
                }
            }
        } catch (Throwable ignored) { }
        return null;
    }

    /**
     * 让客户端载入本地存档。
     * 不按名字找方法（混淆），而是按签名找：(String, String, *) 三参方法，
     * 1.16.5 里就是 launchIntegratedServer(folder, worldName, WorldSettings)。
     */
    /**
     * 让客户端载入本地存档。
     * 不按名字找方法（混淆），按签名找：前两个参数是 String 的方法。
     * 1.16.5 是 (String, String, DynamicRegistries.Impl, WorldSettings) 四参，
     * 1.12.2 是 (String, String, WorldSettings) 三参 —— 都覆盖到。
     */
    private static boolean requestWorld(Object client, String world) {
        // 1.16.5 的入口是单参：public void func_238191_a_(String worldName) —— 载入已有存档
        //（javap 确认：它内部走 WorldSelectionType.BACKUP）。
        // 早期版本是 (String, String, WorldSettings)，两种都试。
        for (String name : new String[]{"func_238191_a", "loadWorld"}) {
            for (Class<?> k = client.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
                for (java.lang.reflect.Method m : k.getDeclaredMethods()) {
                    if (!m.getName().startsWith(name)) continue;
                    if (m.getParameterCount() != 1) continue;
                    if (m.getParameterTypes()[0] != String.class) continue;
                    try {
                        m.setAccessible(true);
                        log("调用 " + m.getName() + "(String) 载入存档 " + world);
                        m.invoke(client, world);
                        return true;
                    } catch (Throwable e) {
                        log("  " + m.getName() + " 失败: " + e);
                    }
                }
            }
        }
        // 兜底：老签名 (String, String, ...)
        java.util.List<java.lang.reflect.Method> cands = new java.util.ArrayList<>();
        for (Class<?> k = client.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            for (java.lang.reflect.Method m : k.getDeclaredMethods()) {
                Class<?>[] ps = m.getParameterTypes();
                if (ps.length >= 2 && ps[0] == String.class && ps[1] == String.class) cands.add(m);
            }
        }
        for (java.lang.reflect.Method m : cands) {
            Class<?>[] ps = m.getParameterTypes();
            Object[] args = new Object[ps.length];
            args[0] = world; args[1] = world;
            boolean ok = true;
            for (int i = 2; i < ps.length; i++) {
                if (ps[i].isPrimitive()) { ok = false; break; }
                args[i] = null;
            }
            if (!ok) continue;
            try {
                m.setAccessible(true);
                log("调用 " + m.getName() + "（" + ps.length + " 参）载入存档");
                m.invoke(client, args);
                return true;
            } catch (Throwable e) {
                log("  " + m.getName() + " 失败: " + e);
            }
        }
        return false;
    }

    /** 已进世界判断：SRG 字段名 world / player */
    private static boolean inWorld(Object client) {
        return field(client, "field_71441_e") != null && field(client, "field_71439_g") != null;
    }

    private static Object field(Object obj, String name) {
        for (Class<?> k = obj.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            try {
                Field f = k.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(obj);
            } catch (Throwable ignored) {
            }
        }
        return null;
    }

    /** 调 IRR 的导出（IRR 自己的类名不混淆，可以直接按名找） */
    private static boolean callIrrExport() {
        try {
            Class<?> em = Class.forName("cn.mcmod.item_render.export.ExportMain");
            Object inst = em.getMethod("getInstance").invoke(null);
            if (inst == null) {
                return false;
            }
            Method m = em.getMethod("DoExport");
            m.invoke(inst);
            return true;
        } catch (Throwable e) {
            write("_mcauto_error.txt", "irr export failed: " + e);
            return false;
        }
    }

    private static void write(String name, String body) {
        try {
            Path p = Paths.get(System.getProperty("user.dir")).resolve(name);
            Files.write(p, body.getBytes(StandardCharsets.UTF_8));
        } catch (Throwable ignored) {
        }
    }

    private static void log(String msg) {
        System.out.println("[irrmcauto] " + msg);
    }
}
