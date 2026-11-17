package itemrender.client.export;

import java.io.File;
import java.io.FileInputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 1.7.10 实体导出（站改扩展，对齐 1.12.2 IRR 的 <modid>_entity.json 产物）。
 *
 * 编译方式与 mcauto-world1710 相同：**纯反射、零 compile 依赖**——
 * 1.7.10 没有可用的 deobf 编译环境，但运行时一切类都在：
 *   javac MobExport.java  →  塞进 IRR_V1.1.0_MC1.7.10.jar 的 itemrender/client/export/。
 *
 * 渲染复用 IRR 自己的 Renderer.renderEntity + FBOHelper（128），
 * 语言切换序列与 ExportUtils.exportMods 完全一致（同版本反编译照抄，SRG 名可信）。
 *
 * 触发：mcauto-world 进世界后 exportMods() 之后 Class.forName 调用 run()。
 * 产出：export/<modid>_entity.json（JSONL：name/Englishname/mod/registerName/Icon，
 *       Icon=128 PNG base64，与 1.12.2 版本字段一致）。
 */
public class MobExport {

    public static String run() {
        try {
            return doRun();
        } catch (Throwable t) {
            StringBuilder sb = new StringBuilder("MobExport failed: " + t);
            for (StackTraceElement e : t.getStackTrace()) {
                sb.append("\n  at ").append(e);
                if (sb.length() > 3000) break;
            }
            System.out.println("[irr-mob] " + sb);
            return sb.toString();
        }
    }

    private static String doRun() throws Exception {
        ClassLoader cl = MobExport.class.getClassLoader();
        Object mc = clientInstance();
        if (mc == null) return "no client";
        Object world = field(mc, "field_71441_e");
        if (world == null) return "no world";
        File mcDir = (File) field(mc, "field_71412_D");
        String wantMod = System.getProperty("mcauto.modid", "");

        // ── EntityList 的 名称→类 Map（先按 SRG 字段名拿，拿不到扫 static Map 字段） ──
        Class<?> entityList = Class.forName("net.minecraft.entity.EntityList", true, cl);
        Class<?> livingBase = Class.forName("net.minecraft.entity.EntityLivingBase", true, cl);
        Map<?, ?> nameToClass = null;
        try {
            Field f = entityList.getField("field_75625_b");
            Object v = f.get(null);
            if (v instanceof Map) nameToClass = (Map<?, ?>) v;
        } catch (Throwable ignored) {
        }
        if (nameToClass == null) {
            for (Field f : entityList.getFields()) {
                if (!java.lang.reflect.Modifier.isStatic(f.getModifiers())) continue;
                if (!Map.class.isAssignableFrom(f.getType())) continue;
                Object v = f.get(null);
                if (v instanceof Map && ((Map<?, ?>) v).containsKey("Villager")) {
                    nameToClass = (Map<?, ?>) v;
                    break;
                }
            }
        }
        if (nameToClass == null) return "EntityList map not found";

        // ── 收集目标实体：类所在 jar 含 modid 才算（1.7.10 无统一注册表反查，来源最可靠） ──
        List<Object[]> targets = new ArrayList<Object[]>(); // [name, Class]
        final int[] skip = new int[6]; // 0=notLiving 1=nosrc 2=excluded 3=modMismatch 4=noctor 5=added
        Class<?> worldParam = Class.forName("net.minecraft.world.World", true, cl);
        for (Map.Entry<?, ?> e : nameToClass.entrySet()) {
            String name = String.valueOf(e.getKey());
            Object val = e.getValue();
            if (!(val instanceof Class)) continue;
            Class<?> cls = (Class<?>) val;
            if (!livingBase.isAssignableFrom(cls)) { skip[0]++; continue; }
            // 1.7.10 归属判定：registerGlobalEntityID 注册的实体没有 mod container，
            // lookupModSpawn 拿不到 → 退到「类包名」匹配（mod 实体类必在 mod 自己的包里，
            // 原版类在 net.minecraft.*）。wantMod 与包名比较忽略大小写（rancraftPenguins vs rancraftpenguins）
            String owner = modOwner(cls);
            String fqcn = cls.getName().toLowerCase();
            if (fqcn.startsWith("net.minecraft") || fqcn.startsWith("cpw.") || fqcn.startsWith("net.minecraftforge")
                    || fqcn.startsWith("itemrender") || fqcn.startsWith("mcauto")) { skip[1]++; continue; }
            if (owner == null && wantMod.isEmpty()) { skip[2]++; continue; }
            if (!wantMod.isEmpty() && !fqcn.contains(wantMod.toLowerCase())) { skip[3]++; continue; }
            try {
                cls.getConstructor(worldParam);
            } catch (Throwable missing) {
                skip[4]++;
                System.out.println("[irr-mob] no (World) ctor: " + name + " -> " + missing);
                continue;
            }
            skip[5]++;
            targets.add(new Object[]{name, cls});
        }
        if (targets.isEmpty()) {
            StringBuilder diag = new StringBuilder("no target mobs (wantMod=" + wantMod
                    + ", map=" + nameToClass.size()
                    + ", skip notLiving=" + skip[0] + " nosrc=" + skip[1] + " excluded=" + skip[2]
                    + " mismatch=" + skip[3] + " noctor=" + skip[4] + " added=" + skip[5]);
            int shown = 0;
            for (Map.Entry<?, ?> e : nameToClass.entrySet()) {
                Object val = e.getValue();
                if (!(val instanceof Class)) continue;
                Class<?> c2 = (Class<?>) val;
                if (!livingBase.isAssignableFrom(c2)) continue;
                diag.append(" | ").append(e.getKey()).append(" owner=").append(modOwner(c2));
                if (++shown >= 4) break;
            }
            return diag.append(')').toString();
        }

        // ── 渲染实例（一次即可，Icon 与语言无关） ──
        Class<?> fboCls = Class.forName("itemrender.client.rendering.FBOHelper", true, cl);
        Class<?> rendererCls = Class.forName("itemrender.client.rendering.Renderer", true, cl);
        Object fbo = fboCls.getConstructor(int.class).newInstance(128);
        Method renderEntity = rendererCls.getMethod("renderEntity",
                livingBase, fboCls, String.class, boolean.class);
        File renderedDir = new File(mcDir, "rendered");
        renderedDir.mkdirs();

        Map<String, byte[]> icons = new HashMap<String, byte[]>();
        Map<String, String> mods = new HashMap<String, String>();
        Map<String, String> registers = new HashMap<String, String>();
        for (Object[] pair : targets) {
            String name = (String) pair[0];
            Class<?> cls = (Class<?>) pair[1];
            Object inst;
            try {
                inst = cls.getConstructor(worldParam).newInstance(world);
            } catch (Throwable t) {
                System.out.println("[irr-mob] instantiate fail " + name + ": " + t);
                continue;
            }
            String owner2 = modOwner(cls);
            String modid = owner2 != null && !owner2.isEmpty() ? owner2
                    : (!wantMod.isEmpty() ? wantMod : modidFromClass(cls, name));
            // IRR 的文件名用 EntityList 注册名并做 sanitize（é/- 会被去掉：Adélie→Adlie）
            String safeName = name.replaceAll("[^A-Za-z0-9()\\[\\]]", "");
            File produced = new File(renderedDir, "entity_" + safeName + ".mobexport.png");
            try {
                renderEntity.invoke(null, inst, fbo, ".mobexport", false);
                if (produced.exists()) {
                    byte[] png = Files.readAllBytes(produced.toPath());
                    icons.put(name, png);
                    mods.put(name, modid);
                    registers.put(name, modid + ":" + name);
                } else {
                    System.out.println("[irr-mob] no png for " + name + " (" + produced.getName() + ")");
                }
            } catch (Throwable t) {
                System.out.println("[irr-mob] render fail " + name + ": " + t);
            }
        }

        // ── 名字：不做语言切换（exportMods 的切换对本模组本就失效——它切 zh_CN，
        //    而 1.7.10 时代这个模组只有 zh_TW/zh_HK；且还原语言时 NPE）。
        //    当前客户端语言=en_US，直接取英文显示名；中文名由解析端从 jar 的 zh_TW.lang 补 ──
        Map<String, String> en = new HashMap<String, String>();
        {
            Class<?> i18n = Class.forName("net.minecraft.client.resources.I18n", true, cl);
            Method tr = null;
            for (Method m : i18n.getMethods()) {
                Class<?>[] ps = m.getParameterTypes();
                if (m.getReturnType() == String.class && ps.length == 2
                        && ps[0] == String.class && ps[1] == Object[].class) { tr = m; break; }
            }
            if (tr != null) {
                for (Object[] pair : targets) {
                    String name = (String) pair[0];
                    String key = "entity." + name + ".name";
                    try {
                        String v = (String) tr.invoke(null, key, new Object[0]);
                        if (v != null && !v.equals(key)) en.put(name, v);
                    } catch (Throwable ignored) {
                    }
                }
            }
        }
        Map<String, String> zh = en;

        // ── 写 <modid>_entity.json（JSONL，字段对齐 1.12.2） ──
        Map<String, List<String>> byMod = new HashMap<String, List<String>>();
        for (Map.Entry<String, byte[]> e : icons.entrySet()) {
            String name = e.getKey();
            String m = mods.get(name);
            StringBuilder sb = new StringBuilder();
            sb.append('{');
            json(sb, "name", zh.containsKey(name) ? zh.get(name) : name);
            sb.append(',');
            json(sb, "Englishname", en.get(name));
            sb.append(',');
            json(sb, "mod", m);
            sb.append(',');
            json(sb, "registerName", registers.get(name));
            sb.append(',');
            sb.append("\"Icon\":\"").append(Base64.getEncoder().encodeToString(e.getValue())).append('"');
            sb.append('}');
            List<String> l = byMod.get(m);
            if (l == null) byMod.put(m, l = new ArrayList<String>());
            l.add(sb.toString());
        }
        File exportDir = new File(mcDir, "export");
        exportDir.mkdirs();
        int files = 0;
        for (Map.Entry<String, List<String>> me : byMod.entrySet()) {
            File f = new File(exportDir, me.getKey() + "_entity.json");
            StringBuilder body = new StringBuilder();
            for (String line : me.getValue()) body.append(line).append('\n');
            Files.write(f.toPath(), body.toString().getBytes(Charset.forName("UTF-8")));
            files++;
            System.out.println("[irr-mob] wrote " + f + " (" + me.getValue().size() + " mobs)");
        }
        return "entity export ok: " + icons.size() + " icons, " + files + " files";
    }

    // ── helpers ────────────────────────────────────────────────────────────

    private static Map<String, String> translateAll(Object langMgr, Object mc, Class<?> langCls,
            Map<?, ?> nameToClass, List<Object[]> targets, String code) throws Exception {
        Object lang = langCls.getConstructor(String.class, String.class, String.class, boolean.class)
                .newInstance(code, code, code, false);
        call1(langMgr, "func_135045_a", langCls, lang);
        Object options = field(mc, "field_71474_y");
        options.getClass().getField("field_74363_ab").set(options, code);
        call(mc, "func_110436_a");
        call(options, "func_74303_b");
        Map<String, String> out = new HashMap<String, String>();
        Class<?> i18n = Class.forName("net.minecraft.client.resources.I18n",
                true, MobExport.class.getClassLoader());
        Method tr = null;
        for (Method m : i18n.getMethods()) {
            Class<?>[] ps = m.getParameterTypes();
            if (m.getReturnType() == String.class && ps.length == 2
                    && ps[0] == String.class && ps[1] == Object[].class) {
                tr = m;
                break;
            }
        }
        if (tr == null) return out;
        for (Object[] pair : targets) {
            String name = (String) pair[0];
            String key = "entity." + name + ".name";
            String v = (String) tr.invoke(null, key, new Object[0]);
            if (v != null && !v.equals(key)) out.put(name, v);
        }
        return out;
    }

    private static String modidFromClass(Class<?> cls, String entityName) {
        String src = classSource(cls);
        // 类所在 jar 文件名猜 modid；兜底用实体名小写
        try {
            int dot = src.lastIndexOf('.');
            String stem = src.substring(src.lastIndexOf('/') + 1, dot > 0 ? dot : src.length());
            String[] seg = stem.split("[-_0-9]");
            String best = "";
            for (String s : seg) if (s.length() > best.length() && !s.equalsIgnoreCase("forge")) best = s;
            if (best.length() > 2) return best.toLowerCase();
        } catch (Throwable ignored) {
        }
        return entityName.toLowerCase();
    }

    /** cpw.mods.fml.common.registry.EntityRegistry.instance().lookupModSpawn(cls).getModId() */
    private static String modOwner(Class<?> entityCls) {
        try {
            ClassLoader cl = MobExport.class.getClassLoader();
            Class<?> er = Class.forName("cpw.mods.fml.common.registry.EntityRegistry", true, cl);
            Object inst = er.getMethod("instance").invoke(null);
            Object container = null;
            for (Method m : er.getMethods()) {
                if (!m.getName().equals("lookupModSpawn")) continue;
                Class<?>[] ps = m.getParameterTypes();
                try {
                    if (ps.length == 1 && ps[0] == Class.class) container = m.invoke(inst, entityCls);
                    else if (ps.length == 2 && ps[0] == Class.class) container = m.invoke(inst, entityCls, Boolean.FALSE);
                } catch (Throwable ignored) { }
                if (container != null) break;
            }
            if (container == null) return null;
            Object id = container.getClass().getMethod("getModId").invoke(container);
            return id == null ? null : String.valueOf(id);
        } catch (Throwable t2) { return null; }
    }

    private static String classSource(Class<?> cls) {
        try {
            java.security.CodeSource cs = cls.getProtectionDomain().getCodeSource();
            if (cs == null || cs.getLocation() == null) return "";
            String s = cs.getLocation().toString();
            return s.startsWith("file:") ? s.substring(5) : s;
        } catch (Throwable t) {
            return "";
        }
    }

    private static Object clientInstance() throws Exception {
        Object handler = Class.forName("cpw.mods.fml.client.FMLClientHandler")
                .getMethod("instance").invoke(null);
        for (Method m : handler.getClass().getMethods()) {
            if (m.getParameterTypes().length == 0 && m.getName().equals("getClient")) {
                return m.invoke(handler);
            }
        }
        return null;
    }

    private static void json(StringBuilder sb, String key, String v) {
        sb.append('"').append(key).append("\":\"");
        if (v == null) v = "";
        for (int i = 0; i < v.length(); i++) {
            char c = v.charAt(i);
            if (c == '"' || c == '\\') sb.append('\\').append(c);
            else if (c == '\n') sb.append("\\n");
            else if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
            else sb.append(c);
        }
        sb.append('"');
    }

    private static Object field(Object o, String name) {
        for (Class<?> k = o.getClass(); k != null && k != Object.class; k = k.getSuperclass()) {
            try {
                Field f = k.getDeclaredField(name);
                f.setAccessible(true);
                return f.get(o);
            } catch (Throwable ignored) {
            }
        }
        try {
            Field f = o.getClass().getField(name);
            return f.get(o);
        } catch (Throwable ignored) {
        }
        return null;
    }

    private static void setStr(Object holder, String fieldName, String nestedName, String v) {
        Object o = holder.getClass() == null ? null : holder;
        try {
            Object inner = o.getClass().getField(fieldName).get(o);
            inner.getClass().getField(nestedName).set(inner, v);
        } catch (Throwable ignored) {
        }
    }

    private static String str(Object o, String getter) {
        try {
            return String.valueOf(call(o, getter));
        } catch (Throwable t) {
            return "en_US";
        }
    }

    private static Object call(Object o, String name) throws Exception {
        for (Method m : o.getClass().getMethods()) {
            if (m.getName().equals(name) && m.getParameterTypes().length == 0) {
                m.setAccessible(true);
                return m.invoke(o);
            }
        }
        throw new NoSuchMethodException(name + " on " + o.getClass());
    }

    private static void call1(Object o, String name, Class<?> paramType, Object arg) {
        try {
            Method m = o.getClass().getMethod(name, paramType);
            m.invoke(o, arg);
        } catch (Throwable t) {
            System.out.println("[irr-mob] " + name + " fail: " + t);
        }
    }
}

