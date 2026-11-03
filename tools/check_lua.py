"""Syntax-check the Lua Portal ships: the companion mod and the per-town spawn
picture patch. Needs luaparser (pip install luaparser).

    .venv\\Scripts\\python tools\\check_lua.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from luaparser import ast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "portal" / "engine"))
import finish  # noqa: E402


def main() -> None:
    for path in sorted((ROOT / "companion").rglob("*.lua")):
        ast.parse(path.read_text(encoding="utf-8"))
        print("ok", path.relative_to(ROOT))
    ast.parse(finish.SPAWN_PICTURE_LUA.format(title="T", map_dir=finish._lua_str('A "b", C'),
                                              max_x=1, max_y=2))
    print("ok spawn picture patch")


if __name__ == "__main__":
    main()
