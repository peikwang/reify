from __future__ import annotations

from server.stacks import detect_source_stack, resolve_stack


def test_non_website_capabilities_stay_static():
    assert resolve_stack("game", "用 React 做一个贪吃蛇", "react") == "static"
    assert resolve_stack("resume", "用 Next.js 做简历", "next") == "static"
    assert resolve_stack("video", "生成一段视频", None) == "static"


def test_website_defaults_to_static():
    assert resolve_stack("website", "为设计工作室做一个官网", None) == "static"
    assert resolve_stack("website", "为 React 开发者做一个官网", None) == "static"


def test_personal_websites_default_to_react():
    assert resolve_stack("website", "帮我做一个个人作品集网站", None) == "react"
    assert resolve_stack("website", "做一个个人主页，展示项目和联系方式", None) == "react"
    assert resolve_stack("website", "做一个摄影作品集", None) == "react"
    assert resolve_stack("website", "做一个个人博客", None) == "react"
    assert resolve_stack("website", "build my personal portfolio website", None) == "react"


def test_company_websites_stay_static():
    assert resolve_stack("website", "做一个公司作品集官网", None) == "static"
    assert resolve_stack("website", "为设计工作室做一个作品集官网", None) == "static"
    assert resolve_stack("website", "做一个产品落地页", None) == "static"
    assert resolve_stack("resume", "做一个个人作品集", None) == "static"


def test_explicit_next_wins_over_personal_default():
    assert resolve_stack("website", "个人网站，用 Next.js 做", None) == "next"
    assert resolve_stack("website", "个人网站，用 React 做", None) == "react"


def test_website_detects_explicit_source_intent():
    assert resolve_stack("website", "用 React 做一个作品集网站", None) == "react"
    assert resolve_stack("website", "用 Vite 做一个官网", None) == "react"
    assert resolve_stack("website", "用 Next.js 做官网，带服务端留言板", None) == "next"
    assert resolve_stack("website", "做一个服务端渲染的官网", None) == "next"


def test_explicit_request_wins():
    assert resolve_stack("website", "做一个官网", "react") == "react"
    assert resolve_stack("website", "用 Next.js 做官网", "static") == "static"


def test_detect_source_stack_is_none_for_plain_prompts():
    assert detect_source_stack("做一个安静的咖啡品牌官网") is None
