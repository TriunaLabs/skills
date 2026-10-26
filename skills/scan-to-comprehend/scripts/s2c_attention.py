#!/usr/bin/env python3
"""Render an untrained, inspectable S2C attention baseline and score held-out fixations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image


VERSION = "s2c-heuristic-attention-v1"
SCALE = 4
TEXT_KINDS = {"heading", "text", "button", "link"}
KIND_WEIGHT = {
    "heading": 1.25, "text": 0.80, "button": 1.20, "link": 0.85,
    "image": 0.90, "logo": 1.00, "face": 1.25, "icon": 0.70,
}


def number(value: object, name: str, *, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return float(value)


def color_rgb(value: str) -> tuple[float, float, float]:
    if not isinstance(value, str) or not value.startswith("#") or len(value) not in (4, 7):
        raise ValueError("Colors must be #RGB or #RRGGBB")
    try:
        digits = value[1:]
        if len(digits) == 3:
            digits = "".join(x * 2 for x in digits)
        return tuple(int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError as exc:
        raise ValueError("Colors must be #RGB or #RRGGBB") from exc


def luminance(color: str) -> float:
    channels = color_rgb(color)
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    a, b = luminance(foreground), luminance(background)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def text_contrast_spotcheck(element: dict) -> dict | None:
    """Screen WCAG 2.2 SC 1.4.3 using supplied solid colors, never certify a page."""
    if element["kind"] not in TEXT_KINDS:
        return None  # Logotypes and non-text graphics require different review.
    font_px = element.get("font_px")
    font_weight = element.get("font_weight", 400)
    threshold = (3.0 if font_px is not None and
                 (font_px >= 24 or (font_px >= 14 * 96 / 72 and font_weight >= 700))
                 else 4.5) if font_px is not None else None
    ratio = (contrast_ratio(element["foreground"], element["background"])
             if "foreground" in element else None)
    status = ("needs_review" if ratio is None or threshold is None else
              "at_or_above_threshold" if ratio >= threshold else "below_threshold")
    return {"id": str(element.get("id", "")), "label": str(element.get("label", "")),
            "kind": element["kind"], "criterion": "WCAG 2.2 SC 1.4.3",
            "font_px": font_px, "font_weight": font_weight if font_px is not None else None,
            "ratio": round(ratio, 3) if ratio is not None else None,
            "threshold": threshold, "status": status}


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def load_capture(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "s2c-attention-capture/v1":
        raise ValueError("Expected s2c-attention-capture/v1")
    if not isinstance(payload.get("frames"), list) or not payload["frames"]:
        raise ValueError("Capture needs frames")
    frames = []
    seen = set()
    root = path.parent.resolve()
    for frame in payload["frames"]:
        if not isinstance(frame, dict) or not isinstance(frame.get("id"), str) or not frame["id"].strip():
            raise ValueError("Each frame needs an id")
        if frame["id"] in seen:
            raise ValueError("Frame IDs must be unique")
        seen.add(frame["id"])
        image_name = frame.get("image")
        if not isinstance(image_name, str) or not image_name:
            raise ValueError("Each frame needs an image")
        image_path = (root / image_name).resolve()
        if not image_path.is_relative_to(root):
            raise ValueError("Image path must stay inside capture directory")
        with Image.open(image_path) as image:
            width, height = image.size
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Screenshot must be PNG, JPEG, or WebP")
        if width * height > 16_000_000:
            raise ValueError("Screenshot exceeds 16 megapixels")
        coordinate_width = number(frame.get("coordinate_width", width), "coordinate_width", minimum=1)
        coordinate_height = number(frame.get("coordinate_height", height), "coordinate_height", minimum=1)
        scale_x, scale_y = width / coordinate_width, height / coordinate_height
        elements = frame.get("elements")
        if not isinstance(elements, list) or not elements or len(elements) > 500:
            raise ValueError("Each frame needs 1–500 elements")
        scaled = []
        for element in elements:
            if not isinstance(element, dict) or element.get("kind") not in KIND_WEIGHT:
                raise ValueError("Element kind is missing or unknown")
            x, y = number(element.get("x"), "x") * scale_x, number(element.get("y"), "y") * scale_y
            w = number(element.get("width"), "width", minimum=0.1) * scale_x
            h = number(element.get("height"), "height", minimum=0.1) * scale_y
            if x + w > width + 1 or y + h > height + 1:
                raise ValueError("Element box must fit within screenshot")
            if "font_px" in element:
                number(element["font_px"], "font_px", minimum=1)
            if "font_weight" in element:
                number(element["font_weight"], "font_weight", minimum=1)
            if ("foreground" in element) != ("background" in element):
                raise ValueError("Provide both foreground and background, or neither")
            if "foreground" in element:
                contrast_ratio(element["foreground"], element["background"])
            scaled.append({**element, "x": x, "y": y, "width": w, "height": h})
        frames.append({**frame, "elements": scaled, "_path": image_path, "_width": width, "_height": height})
    return frames


def element_strength(element: dict, width: int, height: int, *, include_contrast: bool = True) -> dict:
    x, y = float(element["x"]), float(element["y"])
    w, h = float(element["width"]), float(element["height"])
    cx, cy = (x + w / 2) / width, (y + h / 2) / height
    position = (0.55 + 0.45 * math.exp(-1.5 * cy)) * (1.0 + 0.12 * (1 - cx))
    area = clamp(5 * math.sqrt(w * h / (width * height)), 0.15, 1.25)
    font = clamp(0.65 + 0.55 * math.log2(float(element.get("font_px", 16)) / 16), 0.45, 1.5)
    contrast = (contrast_ratio(element["foreground"], element["background"])
                if include_contrast and "foreground" in element else None)
    contrast_term = 0.75 if contrast is None else 0.55 + 0.45 * min(1, math.log(contrast) / math.log(7))
    weight = position * (0.30 + 0.25 * area + 0.25 * font + 0.20 * contrast_term) * KIND_WEIGHT[element["kind"]]
    return {"id": str(element.get("id", "")), "kind": element["kind"], "label": str(element.get("label", "")),
            "weight": round(weight, 4), "position": round(position, 4), "area": round(area, 4),
            "font": round(font, 4), "contrast_ratio": round(contrast, 2) if contrast is not None else None,
            "contrast_status": "computed from supplied colors" if contrast is not None else "unknown"}


def densities(frame: dict, *, include_contrast: bool = True) -> tuple[list[float], list[float], int, int, list[dict]]:
    width, height = frame["_width"], frame["_height"]
    gw, gh = math.ceil(width / SCALE), math.ceil(height / SCALE)
    full, position = [0.0] * (gw * gh), [0.0] * (gw * gh)
    for gy in range(gh):
        cy = min(height - 1, gy * SCALE + SCALE / 2) / height
        for gx in range(gw):
            cx = min(width - 1, gx * SCALE + SCALE / 2) / width
            position[gy * gw + gx] = (0.40 + 0.60 * math.exp(-1.7 * cy)) * (0.85 + 0.15 * (1 - cx))
    ranked = []
    for element in frame["elements"]:
        row = element_strength(element, width, height, include_contrast=include_contrast)
        ranked.append(row)
        x, y, w, h = (float(element[key]) for key in ("x", "y", "width", "height"))
        cx, cy = x + w / 2, y + h / 2
        sx, sy = max(16, min(110, w / 2.5)), max(12, min(75, h / 1.7))
        x0, x1 = max(0, int((cx - 3 * sx) / SCALE)), min(gw, math.ceil((cx + 3 * sx) / SCALE))
        y0, y1 = max(0, int((cy - 3 * sy) / SCALE)), min(gh, math.ceil((cy + 3 * sy) / SCALE))
        for gy in range(y0, y1):
            dy = ((gy * SCALE + SCALE / 2) - cy) / sy
            for gx in range(x0, x1):
                dx = ((gx * SCALE + SCALE / 2) - cx) / sx
                full[gy * gw + gx] += row["weight"] * math.exp(-0.5 * (dx * dx + dy * dy))
    ranked.sort(key=lambda item: item["weight"], reverse=True)
    return full, position, gw, gh, ranked


def probabilities(values: list[float]) -> list[float]:
    total = sum(values)
    if total <= 0:
        raise ValueError("Empty attention map")
    floor = 0.05 / len(values)
    return [0.95 * value / total + floor for value in values]


def heat_color(value: float) -> tuple[int, int, int, int]:
    if value < 0.08:
        return (0, 0, 0, 0)
    stops = [(0.08, (22, 92, 205)), (0.35, (0, 193, 218)),
             (0.65, (255, 225, 55)), (1.0, (228, 39, 35))]
    for (left, a), (right, b) in zip(stops, stops[1:]):
        if value <= right:
            t = clamp((value - left) / (right - left), 0, 1)
            return (*[round(a[i] + t * (b[i] - a[i])) for i in range(3)], round(180 * value))
    return (228, 39, 35, 180)


def save_overlay(values: list[float], gw: int, gh: int, width: int, height: int, output: Path) -> None:
    maximum = max(values)
    pixels = bytes(channel for value in values for channel in heat_color(value / maximum))
    small = Image.frombytes("RGBA", (gw, gh), pixels)
    small.resize((width, height), Image.Resampling.BILINEAR).save(output)


def render(capture: Path, output: Path) -> dict:
    if output.resolve().parent != capture.resolve().parent:
        raise ValueError("Output JSON must be beside the capture manifest")
    frames = load_capture(capture)
    result = {"schema": "s2c-attention/v1", "model_version": VERSION,
              "status": "untrained heuristic; no gaze validation", "frames": []}
    for frame in frames:
        full, _, gw, gh, ranked = densities(frame)
        contrast_checks = [check for element in frame["elements"]
                           if (check := text_contrast_spotcheck(element)) is not None]
        image_name = f"{output.stem}-{frame['id']}.png"
        save_overlay(full, gw, gh, frame["_width"], frame["_height"], output.parent / image_name)
        result["frames"].append({"id": frame["id"], "label": frame.get("label", frame["id"]),
                                 "image": frame["image"], "overlay": image_name,
                                 "width": frame["_width"], "height": frame["_height"],
                                 "captured_at": frame.get("captured_at"),
                                 "provenance": frame.get("provenance", "unspecified element annotations"),
                                 "text_contrast_spotcheck": {
                                     "criterion": "WCAG 2.2 SC 1.4.3",
                                     "color_basis": frame.get("color_basis", "unspecified"),
                                     "scope": "visible annotated text with supplied solid colors; screening only",
                                     "checks": contrast_checks},
                                 "cues": ranked})
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def evaluate(capture: Path, trials_path: Path, output: Path) -> dict:
    frames = {frame["id"]: frame for frame in load_capture(capture)}
    payload = json.loads(trials_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "s2c-attention-fixations/v1":
        raise ValueError("Expected s2c-attention-fixations/v1")
    trials = payload.get("trials")
    if not isinstance(trials, list) or not trials:
        raise ValueError("Fixation file needs trials")
    rows = []
    for trial in trials:
        if not isinstance(trial, dict) or trial.get("split") != "held_out":
            raise ValueError("Every trial must explicitly be marked held_out")
        frame = frames.get(trial.get("frame_id"))
        if frame is None:
            raise ValueError("Fixation trial references an unknown frame")
        fixations = trial.get("fixations")
        if not isinstance(fixations, list) or not fixations:
            raise ValueError("Each trial needs fixations")
        full, position, gw, gh, _ = densities(frame)
        without_contrast, _, _, _, _ = densities(frame, include_contrast=False)
        full, position, without_contrast = (probabilities(values)
                                            for values in (full, position, without_contrast))
        gains_pos, gains_uniform, gains_no_contrast = [], [], []
        for fixation in fixations:
            if not isinstance(fixation, dict):
                raise ValueError("Fixation must be an object")
            x, y = number(fixation.get("x"), "fixation x"), number(fixation.get("y"), "fixation y")
            if x >= frame["_width"] or y >= frame["_height"]:
                raise ValueError("Fixation must fit within screenshot")
            idx = min(gh - 1, int(y / SCALE)) * gw + min(gw - 1, int(x / SCALE))
            gains_pos.append(math.log2(full[idx] / position[idx]))
            gains_uniform.append(math.log2(full[idx] * len(full)))
            gains_no_contrast.append(math.log2(full[idx] / without_contrast[idx]))
        rows.append({"frame_id": frame["id"], "fixation_count": len(fixations),
                     "bits_per_fixation_vs_position": round(sum(gains_pos) / len(gains_pos), 4),
                     "bits_per_fixation_vs_uniform": round(sum(gains_uniform) / len(gains_uniform), 4),
                     "bits_per_fixation_vs_no_contrast": round(sum(gains_no_contrast) / len(gains_no_contrast), 4)})
    result = {"schema": "s2c-attention-evaluation/v1", "model_version": VERSION,
              "split": "user-declared held_out; not independently verified",
              "metric": "mean log2 predicted fixation density ratio; positive beats comparator",
              "trial_count": len(rows), "fixation_count": sum(r["fixation_count"] for r in rows),
              "equal_trial_mean_bits_vs_position": round(sum(r["bits_per_fixation_vs_position"] for r in rows) / len(rows), 4),
              "equal_trial_mean_bits_vs_uniform": round(sum(r["bits_per_fixation_vs_uniform"] for r in rows) / len(rows), 4),
              "equal_trial_mean_bits_vs_no_contrast": round(sum(r["bits_per_fixation_vs_no_contrast"] for r in rows) / len(rows), 4),
              "trials": rows}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    draw = sub.add_parser("render", help="Render one heatmap per captured screenshot")
    draw.add_argument("capture", type=Path)
    draw.add_argument("--output", type=Path, help="Result JSON beside the capture manifest")
    test = sub.add_parser("evaluate", help="Compare fixed heuristic with position-only and uniform baselines")
    test.add_argument("capture", type=Path)
    test.add_argument("fixations", type=Path)
    test.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "render":
        output = args.output or args.capture.with_name("attention.json")
        render(args.capture, output)
    else:
        evaluate(args.capture, args.fixations, args.output)
        output = args.output
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
