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

    public IrrTrigger() {
        MinecraftForge.EVENT_BUS.register(this);
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
    private static Object clientInstance() {
        // 1.16.5 已经删掉 FMLClientHandler，用 LogicalSidedProvider（Forge 自己的类，不混淆）
        try {
            Class<?> lsp = Class.forName("net.minecraftforge.fml.LogicalSidedProvider");
            Class<?> sideCls = Class.forName("net.minecraftforge.fml.LogicalSide");
            Object provider = lsp.getField("INSTANCE").get(null);
            Object clientSide = null;
            for (Object o : sideCls.getEnumConstants()) {
                if ("CLIENT".equalsIgnoreCase(String.valueOf(o))) {
                    clientSide = o;
                    break;
                }
            }
            if (clientSide == null) {
                return null;
            }
            Object opt = lsp.getMethod("get", sideCls).invoke(provider, clientSide);
            if (opt instanceof java.util.Optional) {
                Object v = ((java.util.Optional<?>) opt).orElse(null);
                if (v != null) {
                    return v;
                }
            }
            // 兜底：1.12.2 式的 FMLClientHandler
            Class<?> h = Class.forName("net.minecraftforge.fml.client.FMLClientHandler");
            Object inst = h.getMethod("instance").invoke(null);
            return inst.getClass().getMethod("getClient").invoke(inst);
        } catch (Throwable e) {
            return null;
        }
    }

    /**
     * 让客户端载入本地存档。
     * 不按名字找方法（混淆），而是按签名找：(String, String, *) 三参方法，
     * 1.16.5 里就是 launchIntegratedServer(folder, worldName, WorldSettings)。
     */
    private static boolean requestWorld(Object client, String world) {
        for (Method m : client.getClass().getMethods()) {
            Class<?>[] ps = m.getParameterTypes();
            if (ps.length == 3 && ps[0] == String.class && ps[1] == String.class) {
                try {
                    m.invoke(client, world, world, null);
                    return true;
                } catch (Throwable ignored) {
                }
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
