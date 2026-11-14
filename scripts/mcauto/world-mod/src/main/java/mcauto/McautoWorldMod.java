package mcauto;

import com.mojang.datafixers.util.Function4;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screen.ConnectingScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.resources.IResourceManager;
import net.minecraft.util.datafix.codec.DatapackCodec;
import net.minecraft.util.registry.DynamicRegistries;
import net.minecraft.world.storage.IServerConfiguration;
import net.minecraft.world.storage.SaveFormat;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.function.Function;

/**
 * 1.16.5 进世界 + 触发 IRR 导出（自动化用）。
 *
 * 为什么要编译期依赖 MC：loadWorld 的第 3/4 参是
 *   Function<SaveFormat$LevelSave, DatapackCodec>
 *   Function4<SaveFormat$LevelSave, DynamicRegistries$Impl, IResourceManager,
 *             DatapackCodec, IServerConfiguration>
 * 这两个是函数式接口，javaagent 里没法给出合法实现；在 mod 里写 lambda 是自然的。
 *
 * 注意：第 6 参类型是**私有嵌套枚举** Minecraft.WorldSelectionType，
 * 编译期无法引用，所以整个调用走反射，枚举值从已加载类里按名找。
 */
@Mod("mcautoworld")
public class McautoWorldMod {

    private boolean worldRequested = false;
    private int ticks = 0;
    private boolean exported = false;

    public McautoWorldMod() {
        MinecraftForge.EVENT_BUS.register(this);
        System.out.println("[mcautoworld] constructed");
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
        Minecraft mc = Minecraft.getInstance();
        if (mc == null) {
            return;
        }
        try {
            if (!worldRequested) {
                worldRequested = true;
                // 1.16.5 的连接界面是 ConnectingScreen(Screen, Minecraft, String host, int port)，
                // 直接用它，不需要 ServerData，也不需要反射。
                String connect = System.getProperty("mcauto.connect", "127.0.0.1:25566");
                int colon = connect.lastIndexOf(':');
                String host = colon > 0 ? connect.substring(0, colon) : connect;
                int port = colon > 0 ? Integer.parseInt(connect.substring(colon + 1)) : 25565;
                System.out.println("[mcautoworld] 打开连接界面 " + host + ":" + port);
                mc.setScreen(new ConnectingScreen(null, mc, host, port));
                return;
            }
            if (mc.level == null || mc.player == null) {
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

    /**
     * 构造「连接服务器」界面。
     * 不硬编码类名：MC 各版本里这个界面分别叫 ConnectScreen / ConnectingScreen / GuiConnecting，
     * 所以直接从 Minecraft 所在的 jar 里找带 Connect 字样的 class 条目。
     */
    private static Object buildConnectScreen(Minecraft mc, String ip) throws Exception {
        String entryName = null;
        try {
            java.security.CodeSource cs = Minecraft.class.getProtectionDomain().getCodeSource();
            if (cs != null && cs.getLocation() != null) {
                Path jar = Paths.get(cs.getLocation().toURI());
                if (jar.toString().endsWith(".jar")) {
                    try (java.util.zip.ZipFile z = new java.util.zip.ZipFile(jar.toFile())) {
                        for (java.util.Enumeration<? extends java.util.zip.ZipEntry> e = z.entries(); e.hasMoreElements(); ) {
                            String n = e.nextElement().getName();
                            if (n.endsWith(".class") && n.contains("/gui/screen/")
                                    && n.contains("Connect") && !n.contains("$")) {
                                entryName = n.substring(0, n.length() - 6).replace('/', '.');
                                break;
                            }
                        }
                    }
                }
            }
        } catch (Throwable t) {
            System.out.println("[mcautoworld] 扫 jar 失败: " + t);
        }
        if (entryName == null) {
            System.out.println("[mcautoworld] jar 里没找到 Connect* 界面类");
            return null;
        }
        System.out.println("[mcautoworld] 连接界面类: " + entryName);
        ClassLoader ldr = Minecraft.class.getClassLoader();
        Class<?> connectC = Class.forName(entryName, false, ldr);
        Class<?> screenC = Class.forName("net.minecraft.client.gui.screen.Screen", false, ldr);
        ServerData data = new ServerData("mcauto-local", ip, false);
        for (java.lang.reflect.Constructor<?> ctor : connectC.getConstructors()) {
            Class<?>[] ps = ctor.getParameterTypes();
            if (ps.length == 3 && ps[1].isInstance(mc)) {
                ctor.setAccessible(true);
                return ctor.newInstance(null, mc, data);
            }
        }
        System.out.println("[mcautoworld] 连接界面构造参数不匹配");
        return null;
    }

    private static void loadWorldReflectively(Minecraft mc, String world) throws Exception {
        Class<?> selType = null;
        try {
            selType = Class.forName("net.minecraft.client.Minecraft$WorldSelectionType");
        } catch (Throwable ignored) {
        }
        Object none = null;
        if (selType != null && selType.isEnum()) {
            Object[] consts = selType.getEnumConstants();
            for (Object c : consts == null ? new Object[0] : consts) {
                if (String.valueOf(c).equalsIgnoreCase("NONE")) {
                    none = c;
                    break;
                }
            }
            if (none == null && consts != null && consts.length > 0) {
                none = consts[0];
            }
        }
        Function<SaveFormat.LevelSave, DatapackCodec> codecFn = save -> null;
        Function4<SaveFormat.LevelSave, DynamicRegistries.Impl, IResourceManager,
                DatapackCodec, IServerConfiguration> cfgFn = (save, regs, rm, codec) -> null;

        // 先试 createLevel（新建世界，不需要读 level.dat，参数更简单）
        for (Class<?> k = mc.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            for (Method m : k.getDeclaredMethods()) {
                if (!m.getName().equals("createLevel")) {
                    continue;
                }
                Class<?>[] cps = m.getParameterTypes();
                if (cps.length < 1 || cps[0] != String.class) {
                    continue;
                }
                Object[] cargs = new Object[cps.length];
                for (int i = 0; i < cps.length; i++) {
                    if (i == 0) {
                        cargs[i] = world;
                    } else if (cps[i] == boolean.class) {
                        cargs[i] = Boolean.FALSE;
                    } else if (cps[i] == int.class) {
                        cargs[i] = 0;
                    } else {
                        cargs[i] = null;
                    }
                }
                try {
                    m.setAccessible(true);
                    System.out.println("[mcautoworld] 调用 createLevel(" + cps.length + " 参)");
                    m.invoke(mc, cargs);
                    return;
                } catch (Throwable e) {
                    System.out.println("[mcautoworld] createLevel 失败: " + e);
                }
            }
        }

        // loadWorld 是 private，getMethods() 拿不到，必须遍历 declared methods
        java.util.List<Method> cands = new java.util.ArrayList<>();
        for (Class<?> k = mc.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            for (Method m : k.getDeclaredMethods()) {
                if (m.getName().equals("loadWorld") && m.getParameterCount() == 7) {
                    cands.add(m);
                }
            }
        }
        for (Method m : cands) {
            m.setAccessible(true);
            Class<?>[] ps = m.getParameterTypes();
            Object[] args = new Object[]{
                    world,
                    DynamicRegistries.builtin(),
                    codecFn,
                    cfgFn,
                    Boolean.FALSE,
                    none,
                    Boolean.FALSE,
            };
            System.out.println("[mcautoworld] 调用 loadWorld，枚举=" + none + " 参数表=" + java.util.Arrays.toString(ps));
            m.invoke(mc, args);
            return;
        }
        throw new IllegalStateException("找不到 loadWorld(String,.../7)");
    }

    private static boolean callIrrExport() {
        try {
            Class<?> em = Class.forName("cn.mcmod.item_render.export.ExportMain");
            Object inst = em.getMethod("getInstance").invoke(null);
            em.getMethod("DoExport").invoke(inst);
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
