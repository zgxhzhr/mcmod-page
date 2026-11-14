package mcauto;

import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.client.FMLClientHandler;
import cpw.mods.fml.common.FMLCommonHandler;
import net.minecraftforge.common.MinecraftForge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.ArrayList;

/**
 * 1.7.10 进世界 + 触发 IRR 导出。
 *
 * 这个版本**不用 ForgeGradle**：1.7.10 的 ForgeGradle 1.2 依赖的客户端下载地址
 * （s3.amazonaws.com/Minecraft.Download）已经下线，构建链起不来。
 *
 * 但 1.7.10 的 Forge 类名不混淆（cpw.mods.fml.*），而 MC 内部一律走反射 + SRG 名
 * （field_71441_e / field_71439_g / func_71371_a），所以 javac 编一遍就行：
 *
 *   javac -cp forge-1.7.10-...-universal.jar -d classes src/mcauto/*.java
 */
@Mod(modid = "mcautoworld", name = "mcauto World Loader", version = "1.0.0",
     acceptableRemoteVersions = "*")
public class McautoWorldMod {

    private boolean worldRequested = false;
    private int ticks = 0;
    private boolean exported = false;

    public McautoWorldMod() {
        // 1.7.10 有两个事件总线：
        //   MinecraftForge.EVENT_BUS —— Forge 事件（比如 OreDictionary）
        //   FMLCommonHandler.instance().bus() —— FML 事件，**TickEvent 在这里**
        // 只注册 Forge 总线的话，ClientTickEvent 永远不会触发（踩过）。
        MinecraftForge.EVENT_BUS.register(this);
        FMLCommonHandler.instance().bus().register(this);
        System.out.println("[mcautoworld] constructed (1.7.10, javac build); modid="
                + System.getProperty("mcauto.modid", "<null>")
                + " world=" + System.getProperty("mcauto.world", "<null>"));
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || exported) {
            return;
        }
        String modid = System.getProperty("mcauto.modid", "");
        if (modid.isEmpty()) {
            return;
        }
        try {
            Object mc = clientInstance();
            if (mc == null) {
                return;
            }
            if (!worldRequested) {
                worldRequested = true;
                String world = System.getProperty("mcauto.world", "mcauto");
                System.out.println("[mcautoworld] launchIntegratedServer(" + world + ")");
                if (!launchWorld(mc, world)) {
                    System.out.println("[mcautoworld] 没找到 launchIntegratedServer");
                }
                return;
            }
            Object level = field(mc, "field_71441_e");
            Object player = field(mc, "field_71439_g");
            if (level == null || player == null) {
                return;
            }
            int delay = Integer.getInteger("mcauto.delay", 60);
            if (++ticks < delay) {
                return;
            }
            exported = true;
            System.out.println("[mcautoworld] 已进世界，调用 IRR 导出");
            boolean ok = callIrrExport();
            write("_mcauto_done", ok ? ("ok " + modid) : "irr-returned");
        } catch (Throwable t) {
            write("_mcauto_error.txt", String.valueOf(t));
            System.out.println("[mcautoworld] 出错: " + t);
            exported = true;
        }
    }

    /** Forge 的 FMLClientHandler 类名不混淆，能直接拿到客户端实例 */
    private static Object clientInstance() {
        // getClient() 的返回类型是混淆类（编译期没有 MC 类），所以反射调用
        try {
            Object handler = FMLClientHandler.instance();
            for (Method m : handler.getClass().getMethods()) {
                if (m.getParameterCount() == 0 && m.getName().equals("getClient")) {
                    return m.invoke(handler);
                }
            }
        } catch (Throwable ignored) {
        }
        return null;
    }

    /** 进本地存档：按签名找 (String, String, *) 三参方法（1.7.10 是 func_71371_a） */
    private static boolean launchWorld(Object mc, String world) {
        for (Class<?> k = mc.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            for (Method m : k.getDeclaredMethods()) {
                Class<?>[] ps = m.getParameterTypes();
                if (ps.length == 3 && ps[0] == String.class && ps[1] == String.class) {
                    try {
                        m.setAccessible(true);
                        m.invoke(mc, world, world, null);
                        return true;
                    } catch (Throwable ignored) {
                    }
                }
            }
        }
        return false;
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

    /** 1.7.10 的 IRR：itemrender.client.export.ExportUtils.INSTANCE.exportMods() */
    private static boolean callIrrExport() {
        try {
            Class<?> eu = Class.forName("itemrender.client.export.ExportUtils");
            Object inst = null;
            try {
                inst = eu.getField("INSTANCE").get(null);
            } catch (Throwable ignored) {
            }
            if (inst == null) {
                inst = eu.getConstructor().newInstance();
            }
            eu.getMethod("exportMods").invoke(inst);
            return true;
        } catch (Throwable e) {
            write("_mcauto_error.txt", "irr: " + e);
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
}
