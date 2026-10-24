from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GameSpec:
    title: str
    tagline: str
    genre: str
    prompt: str
    core_loop: str
    controls: tuple[str, ...]
    must_have: tuple[str, ...]
    constraints: tuple[str, ...]
    accent: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_spec(brief: dict[str, Any], prompt: str) -> GameSpec:
    clean_prompt = " ".join(str(prompt or "").split())
    core_loop = clean_prompt[:220] or "让玩家在三十秒内理解目标、得分并愿意再来一局。"
    return GameSpec(
        title=str(brief.get("title") or "长尾小游戏"),
        tagline=str(brief.get("tagline") or "把你描述的玩法，做成一个真正能玩的页面。"),
        genre="custom",
        prompt=clean_prompt,
        core_loop=core_loop,
        controls=("键盘（方向键 / WASD / 空格）", "鼠标或触控", "暂停与重新开始"),
        must_have=("开始界面", "实时分数或进度", "失败判定", "重新开始", "暂停"),
        constraints=(
            "单个 HTML 文件，CSS 与 JavaScript 全部内联",
            "使用 <canvas> 渲染玩法并适配手机",
            "不加载外部脚本、字体、图片，不发起任何网络请求",
            "代码必须完整可运行，不使用省略号或占位符",
        ),
        accent=str(brief.get("accent") or "#b8ff5a"),
    )
