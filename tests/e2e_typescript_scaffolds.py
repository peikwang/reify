#!/usr/bin/env python3
"""Phase 5 E2E: materialize both generated scaffolds and run real npm typecheck/build."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.templates.next_app import build_files as next_build_files  # noqa: E402
from server.templates.react_app import build_files as react_build_files  # noqa: E402

BRIEF = {
    "title": "Scaffold Check",
    "tagline": "Build with types",
    "paragraph": "A generated TypeScript scaffold.",
    "highlights": ["structure", "styles", "motion", "build"],
    "accent": "#1e5c40",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def write_tree(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run(root: Path, *command: str) -> None:
    print("  $ " + " ".join(command))
    result = subprocess.run(command, cwd=root, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout[-5000:])
        print(result.stderr[-5000:])
        raise AssertionError(f"command failed: {' '.join(command)}")


def check_react(root: Path) -> None:
    print("1. Vite React TypeScript scaffold")
    files = react_build_files(BRIEF, "a typed react site")
    check("src/App.tsx" in files, "generates src/App.tsx")
    check("src/main.tsx" in files, "generates src/main.tsx")
    check("tsconfig.json" in files, "generates tsconfig.json")
    check("vite.config.ts" in files, "generates vite.config.ts")
    check(not any(path.endswith(".jsx") for path in files), "no JSX files remain")
    check("tsc --noEmit" in files["package.json"], "build runs tsc --noEmit")
    write_tree(root, files)
    run(root, "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund")
    run(root, "npm", "run", "typecheck")
    run(root, "npm", "run", "build")
    check((root / "dist/index.html").is_file(), "dist/index.html exists")
    assets = list((root / "dist/assets").glob("*.js"))
    check(bool(assets), "hashed JS bundle exists")


def check_next(root: Path) -> None:
    print("2. Next.js TypeScript scaffold")
    files = next_build_files(BRIEF, "a typed next app", "scaffold123")
    check("app/page.tsx" in files, "generates app/page.tsx")
    check("app/layout.tsx" in files, "generates app/layout.tsx")
    check("app/NoteBoard.tsx" in files, "generates app/NoteBoard.tsx")
    check("app/api/notes/route.ts" in files, "generates typed route handler")
    check("tsconfig.json" in files, "generates tsconfig.json")
    check("next-env.d.ts" in files, "generates next-env.d.ts")
    check(not any(path.endswith(".jsx") for path in files), "no JSX files remain")
    write_tree(root, files)
    run(root, "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund")
    run(root, "npm", "run", "typecheck")
    run(root, "npm", "run", "build")
    check((root / ".next/BUILD_ID").is_file(), ".next/BUILD_ID exists")
    check((root / ".next/standalone/server.js").is_file(), "standalone server.js exists")


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="vibeforge-ts-scaffolds-"))
    try:
        check_react(work / "react")
        check_next(work / "next")
        print("\nTS SCAFFOLD E2E PASSED")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
