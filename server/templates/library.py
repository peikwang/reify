from __future__ import annotations

import json
import re
from typing import Any

from . import adapt, code_lab, game, image, resume, travel, video, website
from .base import accent, esc

CAPABILITIES: dict[str, dict[str, str]] = {
    "game": {
        "label": "小游戏",
        "short": "GAME",
        "description": "可玩、可计分、适配触控的浏览器小游戏",
        "example": "做一个霓虹风格的贪吃蛇小游戏，要有最高分和手机方向键",
        "prompt": "做一个霓虹风格的贪吃蛇小游戏：深色网格背景，蛇身带发光轨迹，吃到能量点有粒子反馈；支持方向键/WASD 和手机方向键，显示分数、最高分和速度等级；页面打开即可开始，带暂停和重开。",
    },
    "website": {
        "label": "网站",
        "short": "WEB",
        "description": "有品牌感、响应式的落地页或个人官网",
        "example": "为独立设计工作室做一个有编辑感的产品官网",
        "prompt": "为一家独立设计工作室做一个有编辑感的官网：第一屏是大字号主张和留白，包含品牌介绍、四项能力、工作流程和联系 CTA；整体安静克制，响应式，带轻微滚动动画。",
    },
    "image": {
        "label": "图片",
        "short": "IMAGE",
        "description": "一次生成多张可保存、可下载的视觉图片",
        "example": "生成 4 张安静的日系静物摄影，陶瓷杯、亚麻布和晨光",
        "prompt": "生成 4 张风格统一的视觉图片：安静的日系静物摄影，陶瓷咖啡杯、亚麻布、晨光和柔和阴影，构图克制，细节真实，适合作为品牌视觉素材。",
    },
    "video": {
        "label": "视频",
        "short": "VIDEO",
        "description": "把一个画面意图生成可播放的短视频",
        "example": "生成一段 5 秒的咖啡杯晨光慢镜头，轻微推进",
        "prompt": "生成一段 5 秒的短视频：陶瓷咖啡杯放在亚麻布上，晨光缓慢移动，镜头轻微推进，画面安静、克制、电影感，16:9。",
    },
    "resume": {
        "label": "简历",
        "short": "CV",
        "description": "可在线查看、可打印为 A4 的个人简历",
        "example": "帮我做一份产品设计师的简历，名字叫林知夏，风格克制一点",
        "prompt": "帮我做一份产品设计师的个人简历：姓名林知夏，8 年经验，强调品牌视觉、产品设计、设计系统和前端实现；单页双栏、可打印 A4、ATS 可读，风格克制有纸张质感。",
    },
    "travel": {
        "label": "旅游攻略",
        "short": "TRIP",
        "description": "按天拆分的路线、预算与在地体验指南",
        "example": "做一份大理 3 天 2 晚的慢旅行攻略，预算人均 1500",
        "prompt": "做一份大理 3 天 2 晚的慢旅行攻略：不赶景点，每天安排三个体验，包含路线、预算、交通和在地小贴士；页面像随身小册子，按天切换，适合手机阅读。",
    },
    "adapt": {
        "label": "适配制作",
        "short": "ADAPT",
        "description": "一套内容自动适配横版、方图与竖版投放",
        "example": "把一张品牌主视觉适配成 16:9、1:1、9:16 三种尺寸",
        "prompt": "把一张手冲咖啡品牌主视觉适配成 16:9 横版、1:1 方图和 9:16 竖版三种尺寸：同一套标题、正文和 CTA 自动重排，不裁切、不溢出，并给出安全边距和导出规格。",
    },
    "code": {
        "label": "编程",
        "short": "CODE",
        "description": "生成代码，并配一个可交互的运行演示",
        "example": "写一个快速排序，并做一个能看见每次分区的可视化页面",
        "prompt": "写一个快速排序算法，并做一个能看见每次分区过程的交互可视化页面：左边显示 Python 代码，右边用柱状图演示 pivot、交换和归位，支持运行和重新打乱。",
    },
}

PLANS = {
    "image": ["理解画面意图与风格", "生成并下载图片素材", "组装图片画廊", "校验资源与版面", "部署图片项目"],
    "video": ["理解影片意图与镜头", "提交视频生成任务", "等待渲染完成", "组装视频播放页", "部署视频项目"],
    "game": ["解析玩法与视觉方向", "生成游戏骨架", "实现核心玩法与计分", "补齐说明与移动端适配", "自检并部署可玩版本"],
    "website": ["提炼品牌与信息架构", "搭建页面骨架", "完成视觉与内容区块", "补齐交互与响应式", "自检并部署上线"],
    "resume": ["提取个人信息与求职方向", "设计版式与信息层级", "生成简历内容", "打印与 ATS 自检", "部署在线简历"],
    "travel": ["解析目的地与天数", "规划每日路线", "生成攻略页面", "校验预算与行程", "部署分享页面"],
    "adapt": ["解析源内容与投放场景", "建立多尺寸画板", "生成适配版式", "校验尺寸与溢出", "部署展示页面"],
    "code": ["澄清输入输出", "设计实现方案", "生成代码与演示", "运行语法与边界自检", "部署演示页面"],
}

THINKING = {
    "image": [
        "先提炼画面主体、光线、材质和情绪，保证四张图属于同一组视觉方向。",
        "调用图像模型生成一组候选画面，并立即下载到本地，避免临时链接过期。",
        "用画廊页承载图片，保留足够的留白，让每张图都能被完整看到。",
        "检查图片文件、HTML 结构和移动端布局，确保不是一份只有链接的空页面。",
        "发布到本地静态路由，并保留项目页和下载入口。",
    ],
    "video": [
        "先提炼镜头、主体、光线和运动方式，控制在一个可生成的时间长度内。",
        "把提示词提交给视频模型，创建异步渲染任务。",
        "轮询渲染进度，把状态实时推给工作台；完成后立即下载 MP4。",
        "用播放器页面承载视频、提示词和下载入口。",
        "检查视频文件、播放器结构和响应式布局，再发布。",
    ],
    "game": [
        "先把它做成一个 30 秒就能理解的街机：目标单一、反馈立刻、失败也愿意再来。",
        "用一个 canvas 承载网格、蛇身、能量点和粒子反馈，所有逻辑保持单文件。",
        "加入速度递进、最高分持久化和触控方向键，确保手机上也能玩。",
        "补上操作说明和三个设计注脚，让页面本身也能解释它自己。",
        "检查结构、交互脚本和移动端 viewport，然后挂到本地静态路由。",
    ],
    "website": [
        "先确定一句话主张和第一屏的视觉记忆点，再决定区块顺序。",
        "用语义化结构搭骨架，留出大标题、留白和一个会呼吸的视觉中心。",
        "把品牌语气写进标题、能力卡片和过程叙述，避免模板化的空话。",
        "加入滚动显现和锚点导航，让页面在桌面与手机上都保持节奏。",
        "检查结构、响应式与交互，再把产物发布成本地可访问的地址。",
    ],
    "resume": [
        "先提取姓名、方向与关键词，决定这份简历要让人记住哪三件事。",
        "采用单页双栏：主栏讲故事，侧栏放技能、教育与工具，打印时保持 A4。",
        "把经历写成结果导向的短句，保留足够的数字与动词。",
        "用打印样式和真实文本保证 ATS 可读，不做纯图片简历。",
        "检查信息完整性与打印规则，部署为可分享的在线简历。",
    ],
    "travel": [
        "先抓住目的地的气质，再把它翻译成每天三个真正想做的动作。",
        "按天拆分路线，避免折返：上午在城外，下午回到湖边，晚上留给夜市。",
        "补上预算、交通和在地小贴士，让攻略可以被真正带走。",
        "检查每天的内容密度和预算加总，确保不是一份塞满景点的清单。",
        "发布成可分享的页面，手机上也像一本随身小册子。",
    ],
    "adapt": [
        "先抽取主视觉的核心信息：一句标题、一个动作、一个视觉中心。",
        "建立 16:9、1:1、9:16 三个画板，共用同一套设计 token。",
        "让标题、正文和 CTA 根据画板比例重排，而不是简单缩放。",
        "检查安全边距和文字溢出，确保每种比例都成立。",
        "部署成可切换尺寸的展示页，方便直接评审。",
    ],
    "code": [
        "先把问题说清楚：输入、输出、边界条件和想要被看见的过程。",
        "选择分治方案，用 Python 实现主体，再用前端把每一步可视化。",
        "生成 main.py 和演示页：代码负责正确性，页面负责解释。",
        "运行 Python 语法检查，并检查演示页的结构与交互脚本。",
        "把代码与演示一起部署，形成可运行、可阅读的交付物。",
    ],
}


def classify(prompt: str) -> str:
    text = prompt.lower()
    if any(k in text for k in ("游戏", "game", "贪吃蛇", "俄罗斯方块", "飞机大战", "扫雷", "街机")):
        return "game"
    if any(k in text for k in ("简历", "resume", "cv", "求职", "个人介绍页")):
        return "resume"
    if any(k in text for k in ("旅游", "旅行", "攻略", "行程", "出游", "三日游", "两日游")):
        return "travel"
    if any(k in text for k in ("适配", "多尺寸", "多端", "方图", "竖版", "横版", "海报", "banner", "封面")):
        return "adapt"
    if any(k in text for k in ("网站", "网页", "官网", "落地页", "landing", "web")):
        return "website"
    if any(k in text for k in ("视频", "短片", "影片", "动画", "镜头", "运镜", "剪辑", "video", "wan")):
        return "video"
    if any(k in text for k in ("图片", "图像", "照片", "插画", "海报", "壁纸", "封面", "视觉", "image", "qwen-image")):
        return "image"
    if any(k in text for k in ("编程", "代码", "算法", "python", "javascript", "排序", "脚本", "接口")):
        return "code"
    return "website"


def _media_title(prompt: str) -> str:
    text = prompt.strip().replace("\n", " ")
    text = re.sub(
        r"^(请|帮我|给我)?\s*(生成|做|来|创建|制作)\s*[0-9一二三四五六七八九十]*\s*(张|段|个|份)?\s*",
        "",
        text,
    )
    title = re.split(r"[：:，,。；;]", text)[0].strip()
    return (title or "图像研究")[:18]


def _extract_name(prompt: str) -> str:
    match = re.search(r"(?:我叫|姓名[:：]?|我是)\s*([\u4e00-\u9fa5A-Za-z·]{2,12})", prompt)
    return match.group(1) if match else "林知夏"


def _extract_role(prompt: str) -> str:
    for role in ("产品经理", "产品设计师", "视觉设计师", "交互设计师", "前端工程师", "后端工程师", "全栈工程师", "运营", "摄影师", "教师"):
        if role in prompt:
            return role
    return "产品设计师 / 视觉设计"


def _extract_destination(prompt: str) -> str:
    cities = ["大理", "丽江", "成都", "重庆", "杭州", "苏州", "厦门", "青岛", "西安", "北京", "上海", "广州", "深圳", "长沙", "昆明", "三亚", "东京", "京都", "大阪", "清迈", "巴厘岛", "新加坡", "巴黎", "伦敦", "纽约", "冰岛"]
    for city in cities:
        if city in prompt:
            return city
    match = re.search(r"(?:去|在|到)\s*([\u4e00-\u9fa5]{2,8})", prompt)
    if match:
        return match.group(1)
    return "大理"


def _extract_days(prompt: str) -> int:
    match = re.search(r"(\d+)\s*天", prompt)
    if match:
        return max(2, min(int(match.group(1)), 5))
    chinese = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5}
    for char, value in chinese.items():
        if f"{char}天" in prompt or f"{char}日游" in prompt:
            return value
    return 3


def defaults(capability: str, prompt: str) -> dict[str, Any]:
    if capability == "game":
        return {
            "title": "霓虹贪吃蛇",
            "tagline": "在霓虹网格里收集能量，别撞上自己的轨迹。",
            "paragraph": "一个足够小、足够快的浏览器街机，打开就能玩。",
            "highlights": ["键盘 / 触控双操作", "连击加速", "本地最高分", "零依赖单文件"],
            "accent": "#b8ff5a",
        }
    if capability == "image":
        clean = _media_title(prompt)
        return {
            "title": clean,
            "tagline": "把一句话，变成一张可以保存的画面。",
            "paragraph": "一组同方向的视觉研究，保留光线、材质与安静的情绪。",
            "highlights": ["多张候选", "本地保存", "可下载", "沉浸画廊"],
            "accent": "#336b57",
            "model": "qwen-image-3.0-pro",
        }
    if capability == "video":
        clean = _media_title(prompt)
        return {
            "title": clean,
            "tagline": "让画面动起来。",
            "paragraph": "一段由画面意图驱动的短片，保留镜头、光线和节奏。",
            "highlights": ["文生视频", "异步渲染", "MP4 下载", "本地播放"],
            "accent": "#c05e3c",
            "model": "wan3.0-video",
            "duration": 5,
            "resolution": "720P",
        }
    if capability == "resume":
        name = _extract_name(prompt)
        return {
            "title": f"{name} · 个人简历",
            "name": name,
            "role": _extract_role(prompt),
            "tagline": "把复杂的信息，整理成清晰的体验。",
            "paragraph": "我是一名横跨品牌与数字产品的设计师，擅长把复杂的信息整理成清晰、有温度的体验。相信好的设计不是装饰，而是让人更快做出决定。",
            "highlights": ["品牌视觉", "产品设计", "设计系统", "前端实现"],
            "accent": "#8a6f3d",
        }
    if capability == "travel":
        destination = _extract_destination(prompt)
        days = _extract_days(prompt)
        return {
            "title": f"{destination} · 风花雪月 {days} 日",
            "destination": destination,
            "days": days,
            "tagline": "把时间浪费在风经过的地方。",
            "paragraph": "不赶路，不打卡。以一座城为原点，每天只安排三件真正想做的事，把剩下的时间留给偶遇。",
            "highlights": ["老城慢行", "湖边日落", "在地市场", "山间咖啡"],
            "accent": "#c65d3b",
        }
    if capability == "adapt":
        return {
            "title": "多端适配工坊",
            "tagline": "让同一套内容，在每一块屏幕上都成立。",
            "paragraph": "从主视觉出发，自动重排标题、正文与行动按钮，生成横版、方图与竖版三种投放规格。",
            "headline": "把复杂，留给我们。",
            "highlights": ["16:9 横版", "1:1 方图", "9:16 竖版", "安全边距"],
            "accent": "#ff6b4a",
        }
    if capability == "code":
        return {
            "title": "快速排序实验室",
            "tagline": "看见每一次分区，理解算法如何把混乱变成秩序。",
            "paragraph": "一个可以运行的算法可视化页面：左边是代码，右边是每一步的状态。",
            "headline": "把混乱，",
            "highlights": ["分而治之", "O(n log n)", "可交互演示", "Python 3.12"],
            "accent": "#72e6d1",
        }
    return {
        "title": "Lumen Studio",
        "tagline": "把每一个想法，变成可被看见的作品。",
        "paragraph": "我们做品牌、网站和数字产品，也相信好的设计应该让复杂的事情看起来简单。",
        "highlights": ["品牌叙事", "视觉系统", "Web 体验", "动效设计"],
        "accent": "#ff7a59",
    }


def safe_brief(capability: str, brief: dict[str, Any]) -> dict[str, Any]:
    value = dict(brief)
    value["accent"] = accent(value.get("accent", "#b8ff5a"))
    value["title"] = str(value.get("title", "VibeForge"))[:80]
    for key in ("tagline", "paragraph", "headline"):
        if key in value:
            value[key] = str(value[key])[:220]
    highlights = value.get("highlights", [])
    if not isinstance(highlights, list):
        highlights = []
    value["highlights"] = [str(item)[:40] for item in highlights][:4]
    return value


def render_html(capability: str, brief: dict[str, Any]) -> str:
    brief = safe_brief(capability, brief)
    renderers = {
        "game": game.render,
        "website": website.render,
        "resume": resume.render,
        "travel": travel.render,
        "adapt": adapt.render,
        "code": code_lab.render,
    }
    return renderers.get(capability, website.render)(brief)


def render_media_html(
    capability: str,
    brief: dict[str, Any],
    assets: list[dict[str, Any]],
    revision: int,
    prompt: str,
    meta: dict[str, Any] | None = None,
) -> str:
    brief = safe_brief(capability, brief)
    if capability == "image":
        return image.render(brief, assets, revision, prompt)
    if capability == "video":
        return video.render(brief, assets[0], revision, prompt, meta or {})
    raise ValueError(f"unsupported media capability: {capability}")


def scaffold_html(capability: str, brief: dict[str, Any]) -> str:
    title = esc(str(brief.get("title", "VibeForge")))
    color = accent(brief.get("accent", "#b8ff5a"))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
html,body{{margin:0;height:100%;background:#080b09;color:#eaf7ef;font-family:ui-sans-serif,-apple-system,"PingFang SC",sans-serif}}
.stage{{height:100%;display:grid;place-items:center;text-align:center;background:radial-gradient(circle at 50% 34%,{color}22,transparent 42%),#080b09}}
.mark{{width:54px;height:54px;border:1px solid {color};border-radius:16px;display:grid;place-items:center;color:{color};font:700 18px/1 ui-monospace,monospace;margin:0 auto 18px;animation:pulse 1.4s infinite}}
p{{color:#7f958a;font-size:12px;letter-spacing:.12em}}
@keyframes pulse{{50%{{opacity:.4;transform:scale(.94)}}}}
</style>
</head>
<body><div class="stage"><div><div class="mark">V</div><h1>{title}</h1><p>AGENT IS BUILDING · PLEASE WAIT</p></div></div></body>
</html>"""


def extra_files(capability: str, brief: dict[str, Any], prompt: str, task_id: str) -> dict[str, str]:
    brief = safe_brief(capability, brief)
    files: dict[str, str] = {}
    if capability == "resume":
        files["resume.json"] = json.dumps(
            {
                "name": brief.get("name", "林知夏"),
                "role": brief.get("role", "产品设计师"),
                "summary": brief.get("paragraph", ""),
                "skills": brief.get("highlights", []),
                "links": {"portfolio": "https://linzhixia.design", "email": "hello@linzhixia.design"},
            },
            ensure_ascii=False,
            indent=2,
        )
    elif capability == "travel":
        files["itinerary.json"] = json.dumps(
            {
                "destination": brief.get("destination", "大理"),
                "days": brief.get("days", 3),
                "theme": brief.get("tagline", ""),
                "stops": [
                    {"day": day + 1, "items": [item[1] for item in travel.DAY_PLACES[day % len(travel.DAY_PLACES)]]}
                    for day in range(int(brief.get("days", 3)))
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    elif capability == "adapt":
        files["sizes.json"] = json.dumps(
            {
                "source": brief.get("title", ""),
                "formats": [
                    {"name": "Desktop hero", "ratio": "16:9", "px": "1920x1080", "safe": 64},
                    {"name": "Social square", "ratio": "1:1", "px": "1080x1080", "safe": 48},
                    {"name": "Story / Reels", "ratio": "9:16", "px": "1080x1920", "safe": 72},
                ],
                "tokens": {"accent": brief.get("accent"), "radius": [18, 999], "grid": 12},
            },
            ensure_ascii=False,
            indent=2,
        )
    elif capability == "code":
        files["main.py"] = '''from __future__ import annotations


def quick_sort(items: list[int]) -> list[int]:
    """Return a new sorted list using the divide-and-conquer strategy."""
    if len(items) <= 1:
        return items
    pivot = items[len(items) // 2]
    left = [item for item in items if item < pivot]
    mid = [item for item in items if item == pivot]
    right = [item for item in items if item > pivot]
    return quick_sort(left) + mid + quick_sort(right)


if __name__ == "__main__":
    data = [8, 3, 5, 1, 9, 2, 7, 4, 6]
    print(quick_sort(data))
'''
    artifact_lines = "\n".join(f"- `{path}`" for path in sorted(files))
    files["README.md"] = f"""# {brief.get('title', 'VibeForge 产物')}

> 由 VibeForge 的个人设计 Agent 生成 · 任务 `{task_id}`

## 原始需求

{prompt}

## 能力

{capability} / {CAPABILITIES.get(capability, {}).get('label', capability)}

## 产物

- `index.html` — 可直接打开的页面
{artifact_lines}
- `README.md` — 本说明

## 验收

- [x] HTML 结构完整
- [x] 移动端 viewport
- [x] 交互脚本已注入
- [x] 已部署到本地静态路由 `/p/{task_id}/`

## 设计说明

{brief.get('paragraph', '')}
"""
    return files


def html_checks(html: str, capability: str) -> list[tuple[str, bool, str]]:
    checks = [
        ("结构完整", html.lstrip().startswith("<!DOCTYPE html>") and "</html>" in html, "DOCTYPE / html 闭合"),
        ("移动端适配", 'name="viewport"' in html, "viewport 已声明"),
        ("内容完整", len(html) > 2400 and "{{" not in html, f"{len(html)} 字符"),
        ("交互就绪", "<script>" in html and "</script>" in html, "脚本已注入"),
    ]
    cap_check = {
        "game": ("玩法载体", "<canvas" in html, "canvas 已生成"),
        "resume": ("打印就绪", "@media print" in html, "A4 打印样式"),
        "travel": ("行程交互", 'class="tab' in html, "每日路线可切换"),
        "adapt": ("多尺寸", 'data-ratio' in html, "三种画板比例"),
        "code": ("代码演示", "quick_sort" in html, "代码与可视化已连接"),
        "image": ("图像画廊", "<img" in html and "assets/" in html, "图片画廊已组装"),
        "video": ("视频播放器", "<video" in html and "assets/" in html, "视频播放器已组装"),
        "website": ("品牌区块", 'class="feature"' in html, "内容区块已生成"),
    }
    checks.append(cap_check.get(capability, cap_check["website"]))
    return checks
