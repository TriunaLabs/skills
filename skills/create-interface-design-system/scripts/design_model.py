"""Shared validation helpers for generated interface design systems."""
from __future__ import annotations
import re

REQUIRED_TOP = {"schema_version","name","generated_at","brief","assumptions","direction","color","typography","components","layout","elevation","guardrails","responsive","agent_prompt","provenance"}
REQUIRED_ROLES = {"background","surface","surface_alt","text","text_muted","border","primary","primary_text","danger","danger_text","success","focus"}
REQUIRED_STATES = {"default","hover","active","focus-visible","disabled","loading","error","success"}

def rgb(value: str) -> tuple[float, float, float]:
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value): raise ValueError(f"invalid hex color: {value!r}")
    return tuple(int(value[i:i+2], 16) / 255 for i in (1, 3, 5))

def luminance(value: str) -> float:
    def channel(c: float) -> float: return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb(value)); return .2126 * r + .7152 * g + .0722 * b

def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True); return (high + .05) / (low + .05)

def validate_system(data: object) -> list[str]:
    if not isinstance(data, dict): return ["root must be an object"]
    errors = []
    missing = REQUIRED_TOP - set(data)
    if missing: errors.append("missing top-level keys: " + ", ".join(sorted(missing)))
    if data.get("schema_version") != "1.0": errors.append("schema_version must be '1.0'")
    if not isinstance(data.get("name"), str) or not data.get("name", "").strip(): errors.append("name must be non-empty")
    color = data.get("color") if isinstance(data.get("color"), dict) else {}
    roles = color.get("roles") if isinstance(color.get("roles"), dict) else {}
    missing_roles = REQUIRED_ROLES - set(roles)
    if missing_roles: errors.append("missing color roles: " + ", ".join(sorted(missing_roles)))
    for name, value in roles.items():
        try: rgb(value)
        except ValueError as exc: errors.append(f"color role {name}: {exc}")
    pairs = color.get("contrast_pairs")
    if not isinstance(pairs, list) or not pairs: errors.append("color.contrast_pairs must be non-empty")
    else:
        for index, pair in enumerate(pairs, 1):
            if not isinstance(pair, dict): errors.append(f"contrast pair {index} must be an object"); continue
            fg, bg, minimum = pair.get("foreground"), pair.get("background"), pair.get("minimum")
            if fg not in roles or bg not in roles: errors.append(f"contrast pair {index} references an unknown role"); continue
            if not isinstance(minimum, (int, float)): errors.append(f"contrast pair {index} minimum must be numeric"); continue
            ratio = contrast(roles[fg], roles[bg])
            if ratio + .005 < minimum: errors.append(f"contrast pair {fg}/{bg} is {ratio:.2f}:1, below {minimum}:1")
    typography = data.get("typography") if isinstance(data.get("typography"), dict) else {}
    if not {"families","scale"} <= set(typography): errors.append("typography requires families and scale")
    components = data.get("components")
    if not isinstance(components, dict) or not components: errors.append("components must be a non-empty object")
    else:
        for name, component in components.items():
            states = set(component.get("states", [])) if isinstance(component, dict) else set()
            missing_states = REQUIRED_STATES - states
            if missing_states: errors.append(f"component {name} missing states: " + ", ".join(sorted(missing_states)))
    guardrails = data.get("guardrails")
    if not isinstance(guardrails, dict) or not guardrails.get("do") or not guardrails.get("dont"): errors.append("guardrails require non-empty do and dont lists")
    responsive = data.get("responsive")
    if not isinstance(responsive, list) or not responsive or any(not isinstance(rule, dict) or not rule.get("condition") or not rule.get("behavior") for rule in responsive): errors.append("responsive requires condition/behavior rules")
    prompt = data.get("agent_prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 100: errors.append("agent_prompt is too short to be operational")
    return errors
