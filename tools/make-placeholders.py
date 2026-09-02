#!/usr/bin/env python3
"""Create blank placeholders for assets the loader requires but we do not ship.

public/src/js/assets.js lists ~33 images that upstream references but does
not include -- the yatai_* modifier and gauge sheets, Don-chan's balloon
animation, crown, miss, bg_search. The loader treats any of them 404ing as
fatal, so a clean checkout stalls at 45% with "An error occurred, please
refresh" and the game never starts.

This writes a 1x1 transparent PNG for each missing one, so the game boots
and those elements simply draw nothing. It is run during the image build.
The private overlay image copies real artwork over the top afterwards, so
the placeholders only survive where nothing better exists.

Running it in a working tree will leave untracked files under
public/assets/, which tools/check-no-assets.sh reports -- that is the
check doing its job, not a problem with these files.
"""

import re
import sys
from pathlib import Path

# 1x1 fully transparent PNG.
BLANK_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def listed_images(assets_js: Path) -> list:
    """Pull the "img" array out of assets.js without evaluating any JS."""
    text = assets_js.read_text(encoding="utf-8")
    match = re.search(r'"img"\s*:\s*\[(.*?)\]', text, re.S)
    if not match:
        raise SystemExit(f"no \"img\" array found in {assets_js}")
    return re.findall(r'"([^"]+)"', match.group(1))


def main():
    root = Path(__file__).resolve().parent.parent
    img_dir = root / "public" / "assets" / "img"
    names = listed_images(root / "public" / "src" / "js" / "assets.js")

    created = []
    for name in names:
        target = img_dir / name
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(BLANK_PNG)
        created.append(name)

    print(f"{len(names)} images listed, {len(created)} placeholders created")
    for name in created:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
