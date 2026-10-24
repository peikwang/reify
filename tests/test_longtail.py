from __future__ import annotations

import asyncio

import pytest

from server.templates.longtail import (
    build_spec,
    detect_variant,
    render_code_page,
    render_page,
    validate_page_html,
)

BRIEF = {
    "title": "Lumen Cafe",
    "tagline": "A quiet place for loud ideas.",
    "paragraph": "咖啡、烘焙和一个可以坐一下午的角落。",
    "highlights": ["咖啡", "烘焙", "展览", "活动"],
    "accent": "#1e5c40",
}

PAD = "/*" + ("layout-guard " * 400) + "*/"

VALID_PAGE = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lumen Cafe</title><style>{PAD}
@media print {{ body {{ color: #000; }} }}
</style></head>
<body><main>
<section><h1>Lumen Cafe</h1><p>DAY 01 · 咖啡与面包</p><p>DAY 02 · 展览与朋友</p></section>
<section><h2>Menu</h2><p>手冲、可颂、季节限定。</p></section>
<section><h2>Visit</h2><p>每天 09:00 - 19:00。</p></section>
<pre><code>def solve():
    return 42</code></pre>
</main><script>
document.addEventListener('click', function () {{ console.log('ok'); }});
</script></body></html>"""


def test_variant_detection_for_each_capability():
    assert detect_variant("website", "为一家独立设计工作室做官网") == "studio"
    assert detect_variant("website", "做一个街角咖啡店官网") == "custom"
    assert detect_variant("resume", "做一份产品设计师简历") == "classic"
    assert detect_variant("resume", "做一份学术科研简历") == "custom"
    assert detect_variant("travel", "做一份大理三天两晚攻略") == "city"
    assert detect_variant("travel", "做一份海岛露营攻略") == "custom"
    assert detect_variant("code", "写一个快速排序并可视化") == "quicksort"
    assert detect_variant("code", "写一个二分查找并可视化") == "custom"


def test_spec_captures_prompt_and_highlights():
    spec = build_spec("website", BRIEF, "做一个街角咖啡店官网")
    assert spec.capability == "website"
    assert spec.variant == "custom"
    assert spec.title == "Lumen Cafe"
    assert spec.highlights == ("咖啡", "烘焙", "展览", "活动")


def test_base_validator_accepts_complete_page():
    for capability in ("website", "resume", "travel", "code"):
        assert validate_page_html(capability, VALID_PAGE) == [], capability


def test_validator_allows_plain_hyperlinks():
    linked = VALID_PAGE.replace("<h1>", '<a href="https://orcid.org/0000-0000">ORCID</a><h1>')
    assert validate_page_html("resume", linked) == []


def test_validator_rejects_external_network_and_placeholders():
    external = VALID_PAGE.replace("</head>", '<script src="https://cdn.example/x.js"></script></head>')
    assert any("外部资源" in item for item in validate_page_html("website", external))

    network = VALID_PAGE.replace("</body>", "<script>fetch('https://example.test')</script></body>")
    assert any("网络请求" in item for item in validate_page_html("website", network))

    placeholder = VALID_PAGE.replace("<h1>", "<h1>{{TITLE}}")
    assert any("占位符" in item for item in validate_page_html("website", placeholder))


def test_capability_specific_validation():
    resume = VALID_PAGE.replace("@media print", "@media screen")
    assert any("打印" in item for item in validate_page_html("resume", resume))

    travel = VALID_PAGE.replace("DAY 02", "SECOND STOP")
    assert any("两天" in item for item in validate_page_html("travel", travel))

    code = VALID_PAGE.replace("<pre><code>", "<div>").replace("def solve():", "algorithm")
    assert any("代码展示" in item for item in validate_page_html("code", code))


def test_custom_page_renders_and_stamps(monkeypatch):
    async def fake_generate(capability, spec, prompt, feedback=""):
        return VALID_PAGE

    monkeypatch.setattr("server.llm.enabled", lambda: True)
    monkeypatch.setattr("server.llm.generate_longtail_page", fake_generate)
    html = asyncio.run(render_page("website", BRIEF, "做一个街角咖啡店官网"))
    assert html is not None
    assert 'name="reify-longtail" content="website:custom"' in html


def test_custom_page_repairs_once(monkeypatch):
    responses = iter(["<html><body>broken</body></html>", VALID_PAGE])
    calls: list[str] = []

    async def fake_generate(capability, spec, prompt, feedback=""):
        calls.append(feedback)
        return next(responses)

    monkeypatch.setattr("server.llm.enabled", lambda: True)
    monkeypatch.setattr("server.llm.generate_longtail_page", fake_generate)
    html = asyncio.run(render_page("website", BRIEF, "做一个街角咖啡店官网"))
    assert html is not None
    assert len(calls) == 2
    assert "DOCTYPE" in calls[1] or "结构" in calls[1] or "view" in calls[1]


def test_custom_code_renders_python_and_html(monkeypatch):
    async def fake_generate(spec, prompt, feedback=""):
        return {
            "summary": "二分查找",
            "python": "def binary_search(items, target):\n    return -1\n",
            "html": VALID_PAGE,
        }

    monkeypatch.setattr("server.llm.enabled", lambda: True)
    monkeypatch.setattr("server.llm.generate_longtail_code", fake_generate)
    result = asyncio.run(render_code_page(BRIEF, "写一个二分查找并可视化"))
    assert result is not None
    assert "def binary_search" in result["python"]
    assert 'name="reify-longtail" content="code:custom"' in result["html"]


def test_custom_code_rejects_python_syntax_errors(monkeypatch):
    responses = iter(
        [
            {
                "summary": "bad",
                "python": "def broken(:\n",
                "html": VALID_PAGE,
            },
            {
                "summary": "good",
                "python": "def solve():\n    return 1\n",
                "html": VALID_PAGE,
            },
        ]
    )
    calls: list[str] = []

    async def fake_generate(spec, prompt, feedback=""):
        calls.append(feedback)
        return next(responses)

    monkeypatch.setattr("server.llm.enabled", lambda: True)
    monkeypatch.setattr("server.llm.generate_longtail_code", fake_generate)
    result = asyncio.run(render_code_page(BRIEF, "写一个二分查找并可视化"))
    assert result is not None
    assert len(calls) == 2
    assert "Python" in calls[1]


@pytest.mark.parametrize("capability", ["website", "resume", "travel", "code"])
def test_unknown_capabilities_have_builtin_fallbacks(capability: str):
    from server.templates.library import render_html

    assert render_html(capability, BRIEF, "做一个普通页面")
