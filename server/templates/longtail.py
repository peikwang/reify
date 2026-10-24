from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

LONGTAIL_CAPABILITIES = ("website", "resume", "travel", "code")

_VARIANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "website": {
        "studio": (
            "公司",
            "工作室",
            "团队",
            "品牌",
            "官网",
            "企业",
            "机构",
            "事务所",
            "agency",
            "studio",
            "设计工作室",
        ),
    },
    "resume": {
        "classic": (
            "简历",
            "resume",
            "cv",
            "求职",
            "产品经理",
            "设计师",
            "工程师",
            "运营",
            "教师",
        ),
    },
    "travel": {
        "city": (
            "旅游",
            "旅行",
            "攻略",
            "行程",
            "出游",
            "三日游",
            "两日游",
            "城市",
        ),
    },
    "code": {
        "quicksort": ("快速排序", "快排", "quicksort", "排序"),
    },
}

_CUSTOM_OVERRIDES: dict[str, tuple[str, ...]] = {
    "website": (
        "咖啡",
        "餐厅",
        "民宿",
        "酒店",
        "活动",
        "发布会",
        "婚礼",
        "乐队",
        "播客",
        "公益",
        "招聘",
        "产品发布",
        "展览",
        "课程",
        "健身",
        "诊所",
        "花店",
        "面包店",
        "酒吧",
        "俱乐部",
    ),
    "resume": (
        "学术",
        "科研",
        "博士",
        "论文",
        "医生",
        "护士",
        "律师",
        "演员",
        "歌手",
        "艺术家",
        "建筑师",
        "学生",
        "实习",
        "英文简历",
    ),
    "travel": (
        "自驾",
        "露营",
        "徒步",
        "海岛",
        "美食",
        "亲子",
        "骑行",
        "蜜月",
        "滑雪",
        "冲浪",
        "摄影",
        "背包",
    ),
    "code": (
        "二分",
        "查找",
        "动态规划",
        "最短路径",
        "bfs",
        "dfs",
        "链表",
        "栈",
        "队列",
        "斐波那契",
        "汉诺塔",
        "冒泡",
        "插入排序",
        "归并",
        "堆",
        "图",
        "算法",
    ),
}

_CAPABILITY_BRIEF = {
    "website": (
        "输出一个完整、可直接打开的品牌/空间/活动落地页。需要清晰的标题层级、"
        "至少三个内容区块、一个明确的 CTA，并在手机宽度下成立。"
    ),
    "resume": (
        "输出一份单页、可打印为 A4 的个人简历。需要真实的姓名/方向占位内容、"
        "结果导向的经历短句、技能与联系方式，并带 @media print 打印样式。"
    ),
    "travel": (
        "输出一份按天切换的旅行攻略。需要至少两天的路线、预算、交通和在地贴士，"
        "用按钮或标签切换每日内容，手机上像一本随身小册子。"
    ),
    "code": (
        "输出一个 Python 算法实现和一个可交互的可视化页面。页面要展示代码、"
        "输入/步骤/结果，并让用户能运行或重新生成演示数据。"
    ),
}

_BASE_RULES = (
    "只输出 HTML 文档本身，不要 markdown 代码围栏，不要解释。"
    "所有 CSS 和 JavaScript 必须内联；不加载外部脚本、字体、图片，不发起任何网络请求；"
    "不使用省略号、TODO 或占位代码；适配手机；输出必须完整可运行。"
)


@dataclass(frozen=True)
class PageSpec:
    capability: str
    variant: str
    title: str
    tagline: str
    paragraph: str
    prompt: str
    highlights: tuple[str, ...]
    accent: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_variant(capability: str, prompt: str) -> str:
    if capability not in LONGTAIL_CAPABILITIES:
        return "builtin"
    text = (prompt or "").lower()
    if any(word in text for word in _CUSTOM_OVERRIDES.get(capability, ())):
        return "custom"
    for variant, words in _VARIANTS.get(capability, {}).items():
        if any(word in text for word in words):
            return variant
    return "custom"


def build_spec(capability: str, brief: dict[str, Any], prompt: str) -> PageSpec:
    variant = detect_variant(capability, prompt)
    return PageSpec(
        capability=capability,
        variant=variant,
        title=str(brief.get("title") or "未命名项目"),
        tagline=str(brief.get("tagline") or ""),
        paragraph=str(brief.get("paragraph") or ""),
        prompt=" ".join(str(prompt or "").split())[:600],
        highlights=tuple(str(item) for item in (brief.get("highlights") or [])[:4]),
        accent=str(brief.get("accent") or "#1e5c40"),
    )


def _external_resource(html: str) -> bool:
    return bool(
        re.search(
            r"""(?:src\s*=\s*["']?\s*(?:https?:)?//|url\(\s*["']?https?://|@import\s+["']?https?://|import\s*\(\s*["']https?://|<link[^>]+href\s*=\s*["']?\s*(?:https?:)?//)""",
            html,
            re.IGNORECASE,
        )
    )


def _network_call(html: str) -> bool:
    return bool(
        re.search(
            r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(",
            html,
            re.IGNORECASE,
        )
    )


def validate_page_html(capability: str, html: str) -> list[str]:
    problems: list[str] = []
    lowered = html.lower()
    if not lowered.lstrip().startswith("<!doctype html>"):
        problems.append("必须以 <!DOCTYPE html> 开头")
    if "</html>" not in lowered:
        problems.append("缺少 </html> 闭合标签")
    if "<title" not in lowered:
        problems.append("缺少 <title>")
    if 'name="viewport"' not in lowered:
        problems.append("缺少移动端 viewport")
    if "<style" not in lowered:
        problems.append("缺少内联样式")
    if len(html.encode("utf-8")) < 3600:
        problems.append("文档过短（至少 3600 字节）")
    if re.search(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}", html):
        problems.append("包含未渲染的模板占位符")
    if _external_resource(html):
        problems.append("引用了外部资源")
    if _network_call(html):
        problems.append("包含网络请求调用")

    if capability == "website":
        if "<main" not in lowered and "<section" not in lowered:
            problems.append("缺少主要内容区块（main/section）")
    elif capability == "resume":
        if "@media print" not in lowered:
            problems.append("缺少 @media print 打印样式")
        if "<main" not in lowered and "<article" not in lowered:
            problems.append("缺少简历主体内容")
    elif capability == "travel":
        days = len(re.findall(r"(?:day\s*0?[1-9]|第[一二三四五六七八九十\d]+天)", html, re.IGNORECASE))
        if days < 2:
            problems.append("至少需要两天的行程内容")
        if "addeventlistener" not in lowered and "onclick" not in lowered:
            problems.append("缺少每日内容切换交互")
    elif capability == "code":
        has_code_panel = any(
            token in lowered
            for token in ("<pre", "<code", "<textarea", 'class="code', "class='code", 'id="code', "id='code")
        )
        has_code_text = "def " in lowered and "<script" in lowered
        if not (has_code_panel or has_code_text):
            problems.append("缺少代码展示区")
        if "<script" not in lowered:
            problems.append("缺少交互脚本")
    return problems


def _stamp(html: str, capability: str, variant: str) -> str:
    tag = f'<meta name="reify-longtail" content="{capability}:{variant}">'
    if tag in html:
        return html
    head = re.search(r"<head[^>]*>", html, re.IGNORECASE)
    if head:
        index = head.end()
        return html[:index] + "\n" + tag + html[index:]
    return html


async def render_page(capability: str, brief: dict[str, Any], prompt: str) -> str | None:
    from ..llm import enabled as llm_enabled
    from ..llm import generate_longtail_page

    if capability not in {"website", "resume", "travel"} or not llm_enabled():
        return None
    spec = build_spec(capability, brief, prompt)
    feedback = ""
    for attempt in range(2):
        html = await generate_longtail_page(capability, spec.as_dict(), prompt, feedback)
        if not html:
            feedback = (
                "上一次没有返回完整 HTML 文档。请直接输出从 <!DOCTYPE html> 开始、"
                "以 </html> 结束的完整页面，不要解释。"
            )
            continue
        problems = validate_page_html(capability, html)
        if not problems:
            return _stamp(html, capability, spec.variant)
        feedback = "上一次输出未通过自检，请完整重写并修复：\n" + "\n".join(
            f"- {item}" for item in problems
        )
    return None


async def render_code_page(
    brief: dict[str, Any], prompt: str
) -> dict[str, str] | None:
    from ..llm import enabled as llm_enabled
    from ..llm import generate_longtail_code

    if not llm_enabled():
        return None
    spec = build_spec("code", brief, prompt)
    feedback = ""
    for attempt in range(2):
        result = await generate_longtail_code(spec.as_dict(), prompt, feedback)
        if not result:
            feedback = (
                "上一次没有返回完整 JSON。请输出 {summary, python, html}，"
                "python 必须是完整可编译实现，html 必须是完整单文件页面。"
            )
            continue
        python = str(result.get("python") or "")
        html = str(result.get("html") or "")
        problems = validate_page_html("code", html)
        if python:
            try:
                compile(python, "<generated-main>", "exec")
            except SyntaxError as exc:
                problems.append(f"Python 语法错误：{exc.msg}")
        else:
            problems.append("缺少 Python 代码")
        if not problems:
            return {
                "python": python,
                "html": _stamp(html, "code", spec.variant),
                "summary": str(result.get("summary") or "已生成算法与可视化页面"),
            }
        feedback = "上一次输出未通过自检，请完整重写并修复：\n" + "\n".join(
            f"- {item}" for item in problems
        )
    return None


def system_prompt(capability: str) -> str:
    return (
        "你是 Reify 的单文件交付工程师。"
        + _CAPABILITY_BRIEF.get(capability, "")
        + _BASE_RULES
    )
