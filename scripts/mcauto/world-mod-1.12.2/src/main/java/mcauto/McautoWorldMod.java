package mcauto;

import net.minecraft.client.Minecraft;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 1.12.2 进世界 + 触发 IRR 导出（自动化用）。
 *
 * 为什么必须在 mod 里做：1.12.2 运行时类名完全混淆（Minecraft 叫 bib），
 * 外部 javaagent 按名反射拿不到任何东西；而 mod 是编译期依赖 MC 的，
 * 由 ForgeGradle 负责 reobf，代码里可以直接写 mc.launchIntegratedServer(...)。
 */
@Mod(modid = "mcautoworld", name = "mcauto World Loader", version = "1.0.0",
     clientSideOnly = true, acceptableRemoteVersions = "*")
public class McautoWorldMod {

    private boolean worldRequested = false;
    private int ticks = 0;
    private boolean exported = false;

    public McautoWorldMod() {
        MinecraftForge.EVENT_BUS.register(this);
        System.out.println("[mcautoworld] constructed (1.12.2)");
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
        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null) {
            return;
        }
        try {
            if (!worldRequested) {
                worldRequested = true;
                String world = System.getProperty("mcauto.world", "mcauto");
                System.out.println("[mcautoworld] launchIntegratedServer(" + world + ")");
                // 1.12.2 的三参版本：folderName / worldName / WorldSettings
                mc.launchIntegratedServer(world, world, null);
                return;
            }
            if (mc.world == null || mc.player == null) {
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

    /** 1.12.2 的 IRR：itemrender.client.export.ExportUtils.INSTANCE.exportMods() */
    private static boolean callIrrExport() {
        try {
            Class<?> eu = Class.forName("itemrender.client.export.ExportUtils");
            Object inst = null;
            try {
                Field f = eu.getField("INSTANCE");
                inst = f.get(null);
            } catch (Throwable ignored) {
            }
            if (inst == null) {
                inst = eu.getConstructor().newInstance();
            }
            Method m = eu.getMethod("exportMods");
            m.invoke(inst);
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
