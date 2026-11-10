#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TubeStuff（classId 646）23 个页面的批量编辑 JSON。

页面：10 存储方块 + 12 功能方块 + 1 物品，全部为补全正文。

数据来源：
- 方块名：assets/tubestuff/lang/en_US.lang（模组只有 en_US，无中文）
- 功能说明：Modrinth 项目正文（immibis 自己写的英文介绍）
- 纹理：assets/tubestuff/textures/blocks/*.png
  注意 retrievulator 与 mct2 没有独立纹理（作者的说明里也写了「World texture is temporary」），
  这两处分别用 buffer 与 act-top 的纹理近似。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "ts/assets/tubestuff/textures"
OUT = BASE / "ts-编辑-646.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def b64(rel: str) -> str:
    p = TEX / rel
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.LANCZOS if img.width > 32 else Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# id, 中文名, 英文名, 纹理相对路径, 正文
PAGES = [
    ("926635", "缓冲器", "Buffer", "blocks/buffer.png",
     "<p>缓冲器是 TubeStuff 添加的物品中转方块，用于在管道与管道之间搬运物品。</p>"
     "<p><strong>填充方式</strong>：可用管道、管或直接手动放入，界面行为与箱子相同。</p>"
     "<p><strong>自动输出</strong>：旁边接上木质管道、金质管道或基础物流管道后，它会每隔数秒向管道输出一组物品。"
     "间隔随空槽数量变化——全空时约 5 秒一次，接近满时缩短至 0.5 秒。</p>"
     "<p><strong>配合过滤器</strong>：旁边放一个输入端朝向缓冲器的过滤器，会以相同频率向其发送红石脉冲。</p>"
     "<p><strong>减少卡顿</strong>：管道系统中散落的小堆物品会增加计算量，缓冲器会把它们合并成整组后再输出。</p>"),

    ("926636", "MkII型自动合成台", "Automatic Crafting Table MkII", "blocks/act-top.png",
     "<p>MkII 型自动合成台是 TubeStuff 添加的自动合成设备。</p>"
     "<p><strong>界面布局</strong>：上方为 9×5 的输入区，下方为玩家背包，左侧 3×3 配方区，右侧单格输出槽。</p>"
     "<p><strong>使用流程</strong>：先在配方区设置配方（此时输出槽为空属正常现象），再通过任意一面接入管道将材料送入输入区，"
     "每一面连同底面各对应输入区的一行。上方放一个朝下的过滤器或传送器，施加红石信号即可取走成品，"
     "材料充足时下一件几乎立刻合成完毕。</p>"
     "<p><strong>容器物品</strong>：配方产生容器时（例如以水桶参与合成），容器会落入输入区最后一行红色标记的区域，可从底面抽出。"
     "该行达到容量上限后容器将被销毁。</p>"
     "<p><strong>界面按钮</strong>：1 与 64 之间切换输出策略，设为 1 时输出槽非空即停止合成，设为 64 时持续合成至输出槽满载；"
     "C 清空配方；OD 开启矿物词典支持，配方材料会在所有可用类型之间闪烁，例如任意九种铜锭都能用于制作铜块。</p>"
     "<p><strong>旋转</strong>：可用 RedPower 螺丝刀、BuildCraft 兼容扳手（含新月锤与 Omn扳手）、IC2 扳手或石锄。</p>"),

    ("926637", "黑洞箱子", "Black Hole Chest", "blocks/bhc.png",
     "<p>黑洞箱子是 TubeStuff 添加的无限容量存储方块。</p>"
     "<p><strong>容量</strong>：可存入无限数量的物品。翻页仅能翻至已满载的页，不会出现空白页。"
     "卸载时内容会自动压缩，中间不留空槽。</p>"
     "<p><strong>默认关闭</strong>：因强度过高，合成默认被禁用，需在配置文件中开启。"
     "即便配置未开启，也能通过创造模式或 /give 获得。</p>"
     "<p><strong>性能</strong>：图形卡顿时可在客户端配置中关闭动画与黑色粒子。</p>"),

    ("926638", "焚化炉", "Incinerator", "blocks/incinerator-top.png",
     "<p>焚化炉是 TubeStuff 添加的物品销毁方块。</p>"
     "<p><strong>作用</strong>：连接管道或管后，永久销毁进入其中的任何物品。</p>"
     "<p><strong>相对岩浆池的优势</strong>：使用更简便，且没有自燃或意外烧毁周边方块的风险。</p>"),

    ("926639", "复制机", "Duplicator", "blocks/duplicator.png",
     "<p>复制机是 TubeStuff 添加的无限物品源方块，性质上相当于一个始终装着某种物品的箱子。</p>"
     "<p><strong>用法</strong>：用木质管道或传送器可持续抽出指定物品，每次抽取数量由界面设定决定。"
     "木质管道与传送器本身仍只单次抽取一个。</p>"
     "<p><strong>权限</strong>：没有正当获取途径，多人游戏中仅管理员可放置与打开界面。"
     "设计用途是搭建永不缺货的副本奖励箱。</p>"),

    ("926640", "自动型猎犬寻回机", "Retrievulator", "blocks/buffer.png",
     "<p>自动型猎犬寻回机（Retrievulator）是 TubeStuff 添加的库存维持设备。</p>"
     "<p><strong>安装</strong>：需贴着 RedPower 抽取器的输出面安装。缺口较大的一侧为输入端，较小的一侧为输出端，"
     "后者接目标容器（箱子或自动合成台）。也可用过滤器替代抽取器，但实用性较低。"
     "抽取器必须处于非滑动模式。</p>"
     "<p><strong>界面</strong>：分 R 区（抽取器侧）、T 区（目标侧）与右侧临时中转槽。"
     "T 区放置希望目标容器保持的物品与数量，R 区放置与 T 区同布局的实物样本。</p>"
     "<p><strong>工作方式</strong>：在 R 区与抽取器之间搬运物品，并向抽取器发送红石脉冲，将目标容器维持在设定数量。"
     "目标容器已满足要求时，它会生成一个抽取器干扰器放入抽取器内，阻止其继续接收物品。</p>"
     "<p><strong>虚拟物品</strong>：T 区使用虚拟物品，与物流管道类似。右键加一，左键减一，按住 Shift 每次增减十，"
     "单槽最高可设 127 个，不可堆叠的物品也支持。</p>"
     "<p><strong>停机条件</strong>：若 R 区与抽取器在同一格内都有物品，或两者都没有而 T 区有，机器将停止工作。</p>"
     "<p><strong>旋转</strong>：可用 RedPower 螺丝刀、BuildCraft 兼容扳手、IC2 扳手或石锄。</p>"),

    ("926641", "挖掘架", "Block Breaker", "blocks/breaker-frame.png",
     "<p>挖掘架（Block Breaker）是 TubeStuff 添加的自动破坏方块。</p>"
     "<p><strong>用法</strong>：放入工具后，破坏正前方的方块。</p>"
     "<p><strong>特性</strong>：行为与玩家挖掘一致，需要时间，并消耗工具的耐久度。</p>"),

    ("926642", "液体清除机", "Liquid Disposer", "blocks/incinerator-side.png",
     "<p>液体清除机（Liquid Disposer）是 TubeStuff 添加的液体销毁设备，为焚化炉的液体版本。</p>"
     "<p><strong>作用</strong>：接入管道后永久销毁流入的液体。</p>"),

    ("926643", "液体复制机", "Liquid Duplicator", "blocks/duplicator.png",
     "<p>液体复制机（Liquid Duplicator）是 TubeStuff 添加的液体无限源，为复制机的液体版本。</p>"
     "<p><strong>用法</strong>：把装有液体的容器放入槽位（例如装满的桶或 IC2 电池），"
     "之后即可从该设备无限抽取对应液体。</p>"),

    ("926644", "玩家在线感应器", "Online Player Detector", "blocks/detector-on.png",
     "<p>玩家在线感应器（Online Player Detector）是 TubeStuff 添加的红石信号方块。</p>"
     "<p><strong>作用</strong>：放置者在线时变为绿色并输出红石信号。</p>"
     "<p><strong>用途</strong>：适用于服务器要求玩家离线时关闭机器的场合，可与其他方块联动实现自动停机。</p>"),

    ("926645", "MkII型手动合成台", "Manual Crafting Table MkII", "blocks/act-top.png",
     "<p>MkII 型手动合成台是 TubeStuff 添加的合成设备，是自动合成台 MkII 的手动版本。</p>"
     "<p><strong>与自动版的区别</strong>：不依赖红石信号驱动，由玩家手动操作完成合成。</p>"
     "<p><strong>旋转</strong>：与其他 MkII 系列方块相同，可用扳手类工具调整朝向。</p>"),

    ("926646", "放置机", "Deployer", "blocks/dep-top.png",
     "<p>放置机（Deployer）是 TubeStuff 添加的执行端方块。</p>"
     "<p><strong>作用</strong>：朝指定方向放置方块或使用物品，用于把自动化流程的最后一环补齐。</p>"),

    # ── 存储方块 10 ──
    ("926647", "银块", "Silver Block", "blocks/silver.png",
     "<p>银块是 TubeStuff 添加的金属存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把银锭压缩成方块存储，节省空间。</p>"),
    ("926648", "锡块", "Tin Block", "blocks/tin.png",
     "<p>锡块是 TubeStuff 添加的金属存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把锡锭压缩成方块存储，节省空间。</p>"),
    ("926649", "铜块", "Copper Block", "blocks/copper.png",
     "<p>铜块是 TubeStuff 添加的金属存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把铜锭压缩成方块存储，节省空间。</p>"),
    ("926650", "蓝石块", "Nikolite Block", "blocks/nikolite.png",
     "<p>蓝石块（Nikolite Block）是 TubeStuff 添加的尼科莱特存储方块。</p>"
     "<p><strong>放置限制</strong>：必须放在其他方块上方，下方无支撑时会掉落。</p>"),
    ("926651", "煤块", "Coal Brick Block", "blocks/coal.png",
     "<p>煤块（Coal Brick Block）是 TubeStuff 添加的煤存储方块，由原版煤块与石砖合成而成。</p>"
     "<p><strong>说明</strong>：外观为煤砖样式，与木炭块相同。</p>"),
    ("926652", "红石块", "Powdered Redstone Block", "blocks/redstone.png",
     "<p>红石块（Powdered Redstone Block）是 TubeStuff 添加的红石存储方块。</p>"
     "<p><strong>合成</strong>：由原版红石块与沙合成。</p>"
     "<p><strong>功能</strong>：会向相邻方块供能，相当于一个常亮的红石电源。</p>"
     "<p><strong>放置限制</strong>：必须放在其他方块上方，下方无支撑时会掉落。</p>"),
    ("926653", "蓝石合金块", "Blue Alloy Block", "blocks/bluealloy.png",
     "<p>蓝石合金块是 TubeStuff 添加的蓝石合金存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把蓝石合金锭压缩成方块存储。</p>"),
    ("926654", "红石合金块", "Red Alloy Block", "blocks/redalloy.png",
     "<p>红石合金块是 TubeStuff 添加的红石合金存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把红石合金锭压缩成方块存储。</p>"),
    ("926655", "黄铜块", "Brass Block", "blocks/brass.png",
     "<p>黄铜块是 TubeStuff 添加的黄铜存储方块，行为与原版金属块相同。</p>"
     "<p><strong>用途</strong>：把黄铜锭压缩成方块存储。</p>"),
    ("926656", "木炭块", "Charcoal Block", "blocks/charcoal.png",
     "<p>木炭块是 TubeStuff 添加的木炭存储方块。</p>"
     "<p><strong>说明</strong>：外观与煤块完全相同，仅原料不同。</p>"
     "<p><strong>配置</strong>：可在配置中单独关闭。</p>"),

    # ── 物品 1 ──
    ("926657", "猎犬寻回机干扰器", "Retriever Jammer", "items/jammer.png",
     "<p>猎犬寻回机干扰器（Retriever Jammer）是 TubeStuff 添加的物品，由自动型猎犬寻回机自动生成。</p>"
     "<p><strong>来源</strong>：当目标容器已满足设定数量时，自动型猎犬寻回机会生成一个干扰器放入抽取器内。</p>"
     "<p><strong>作用</strong>：阻止抽取器继续接收物品。除此之外没有其他用途，也无法人工获取。</p>"
     "<p><strong>销毁</strong>：玩家走过干扰器时会将其踩碎，而非拾取。</p>"),
]


def main() -> int:
    rows = []
    for rid, zh, en, tex, html in PAGES:
        rows.append({
            "id": rid,
            "name": zh,
            "ename": en,
            "editRemark": (
                "补全正文：功能说明依据 Modrinth 项目页的作者介绍，"
                "方块名取自 lang/en_US.lang（模组无中文语言文件）。"
                f"{tail()}"
            ),
            "editNote": f"补全正文：{en} 的作用、用法与限制。",
            "html": html,
            "icon32": b64(tex),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon}" if noicon else " ✓"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
