#!/usr/bin/env python3
"""Basic deterministic image checks for a TikTok Shop skill output.

Usage: python scripts/validate_assets.py /path/to/商品名 [--market US]
Requires Pillow; not a substitute for visual or seller policy review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: python -m pip install Pillow", file=sys.stderr)
    sys.exit(2)

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--market", default="US")
    parser.add_argument("--min-side", type=int, default=600)
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"ERROR: No such directory: {args.folder}", file=sys.stderr)
        return 2

    results = []
    hashes = {}
    bad = False
    count_gallery = 0
    for foldername in ("主图", "详情图", "SKU图"):
        folder = args.folder / foldername
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            item = {"file": str(path.relative_to(args.folder)), "sha256": sha,
                    "errors": [], "warnings": []}
            try:
                with Image.open(path) as img:
                    item["size"] = list(img.size)
                    item["mode"] = img.mode
                    img.verify()
                w, h = item["size"]
                if foldername in ("主图", "SKU图"):
                    if w < args.min_side or h < args.min_side:
                        item["errors"].append(f"Too small: {w}x{h}")
                    if args.market.upper() == "US" and w != h:
                        item["errors"].append("US product gallery must be square")
                if sha in hashes:
                    item["warnings"].append(f"Exact duplicate of {hashes[sha]}")
                else:
                    hashes[sha] = item["file"]
            except Exception as exc:
                item["errors"].append(f"Cannot read: {exc}")
            if foldername == "主图":
                count_gallery += 1
            if item["errors"]:
                bad = True
            results.append(item)

    if args.market.upper() == "US" and count_gallery > 9:
        bad = True
        results.append({"errors": [f"US gallery contains {count_gallery} images, max 9"]})

    report = {"market": args.market, "folder": str(args.folder),
              "files_checked": len([r for r in results if "file" in r]),
              "pass": not bad and len(results) > 0, "results": results,
              "note": "Image format and dimensions only. Visual truth, exact text, and policy must be audited separately."}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
