#!/usr/bin/env python3
"""Project a Chromium S2C snapshot into the experimental attention input schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from PIL import Image


RGB = re.compile(r"^rgba?\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})(?:,\s*([\d.]+))?\)$")


def opaque_hex(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    match = RGB.fullmatch(value)
    if not match or (match[4] is not None and float(match[4]) < 1):
        return None
    channels = [int(match[i]) for i in (1, 2, 3)]
    if any(channel > 255 for channel in channels):
        return None
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def kind_for(node: dict) -> str | None:
    tag = node.get("tag")
    if node.get("heading_level") is not None:
        return "heading"
    if tag == "p":
        return "text"
    if tag == "a":
        return "link"
    if tag in {"button", "input", "select", "textarea", "summary"} or node.get("role") == "button":
        return "button"
    if tag == "img":
        return "image"
    if tag == "svg" and node.get("role") == "img":
        return "icon"
    return None


def painted_background_matches(image: Image.Image, box: dict, background: str) -> bool:
    """Require the captured pixels to support a supplied solid CSS background."""
    rgb = tuple(int(background[index:index + 2], 16) for index in (1, 3, 5))
    left = max(0, int(box["x"]))
    top = max(0, int(box["y"]))
    right = min(image.width, int(box["x"] + box["width"]))
    bottom = min(image.height, int(box["y"] + box["height"]))
    if right - left < 2 or bottom - top < 2:
        return False
    matches = total = 0
    for yi in range(1, 8):
        y = top + (bottom - top - 1) * yi // 8
        for xi in range(1, 8):
            x = left + (right - left - 1) * xi // 8
            sample = image.getpixel((x, y))[:3]
            total += 1
            matches += max(abs(sample[channel] - rgb[channel]) for channel in range(3)) <= 24
    return matches / total >= 0.55


def project(snapshot: dict, image_dir: Path | None = None) -> dict:
    if snapshot.get("schema") != "s2c-browser-capture/v1":
        raise ValueError("Expected s2c-browser-capture/v1")
    frames = []
    for frame in snapshot.get("frames", []):
        width, height = frame["viewport"]["width"], frame["viewport"]["height"]
        screenshot = None
        if image_dir is not None:
            image_path = (image_dir / frame["image"]).resolve()
            if not image_path.is_relative_to(image_dir.resolve()):
                raise ValueError("Screenshot path must stay inside the capture directory")
            screenshot = Image.open(image_path).convert("RGB")
        image_boxes = [node["box"] for node in frame["nodes"]
                       if node.get("tag") == "img" and node.get("in_viewport")]
        elements = []
        for node in frame["nodes"]:
            kind = kind_for(node)
            if not kind or not node.get("in_viewport") or node.get("aria_hidden"):
                continue
            box = node["box"]
            x0, y0 = max(0, box["x"]), max(0, box["y"])
            x1, y1 = min(width, box["x"] + box["width"]), min(height, box["y"] + box["height"])
            if x1 - x0 < 1 or y1 - y0 < 1:
                continue
            style = node.get("style", {})
            element = {"id": node["id"], "kind": kind,
                       "label": (node.get("name") or node.get("text") or node.get("alt") or kind)[:120],
                       "x": round(x0, 2), "y": round(y0, 2),
                       "width": round(x1 - x0, 2), "height": round(y1 - y0, 2)}
            if kind in {"heading", "text", "link", "button"}:
                element["painted_text"] = bool((node.get("text") or "").strip())
            font_px = style.get("font_size")
            if isinstance(font_px, (int, float)) and font_px >= 1:
                element["font_px"] = font_px
            weight = style.get("font_weight")
            if isinstance(weight, str):
                weight = {"normal": 400, "bold": 700}.get(weight, weight)
            try:
                if float(weight) >= 1:
                    element["font_weight"] = float(weight)
            except (TypeError, ValueError):
                pass
            foreground = opaque_hex(style.get("color"))
            background = opaque_hex(style.get("background"))
            # Computed ancestor colors can describe the page behind a photo that is
            # painted as a sibling. Do not assert a text ratio over that image.
            over_image = False
            if kind in {"heading", "text", "link", "button"}:
                area = (x1 - x0) * (y1 - y0)
                for image in image_boxes:
                    overlap = (max(0, min(x1, image["x"] + image["width"]) - max(x0, image["x"]))
                               * max(0, min(y1, image["y"] + image["height"]) - max(y0, image["y"])))
                    if overlap >= area * 0.5 and image["width"] * image["height"] >= area:
                        over_image = True
                        break
            if foreground and background and not over_image and element.get("painted_text", True) and (
                    screenshot is None or painted_background_matches(screenshot, element, background)):
                element["foreground"] = foreground
                element["background"] = background
            elements.append(element)
        if not elements:
            raise ValueError(f"No visible attention elements in {frame['id']}")
        frames.append({"id": frame["id"], "label": frame["id"], "image": frame["image"],
                       "coordinate_width": width, "coordinate_height": height,
                       "captured_at": frame["captured_at"],
                       "provenance": "Chromium first-viewport DOM boxes; automatic mapping, not hand-verified; no face detection",
                       "color_basis": "Computed opaque CSS colors confirmed against screenshot pixels where supplied; image, gradient, opacity and mismatched cases need review",
                       "elements": elements})
    if not frames:
        raise ValueError("Capture needs frames")
    return {"schema": "s2c-attention-capture/v1", "frames": frames}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = project(json.loads(args.snapshot.read_text(encoding="utf-8")), args.snapshot.parent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
