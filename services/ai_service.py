"""Perception agent.

Reads a citizen's words and returns a structured understanding of the problem:
category, severity, safety risk, impact, a short summary, the reasoning behind
the call, and a recommended action.

Gemini does the reading when a key is configured. Everything it returns is
validated and clamped before it goes anywhere near the database, and a
deterministic keyword engine produces the same shape of result whenever Gemini
is missing, rate-limited, slow or malformed - so the product never depends on a
network call to stay usable.
"""
import json
import logging
import re

log = logging.getLogger(__name__)

CATEGORIES = [
    "Pothole", "Garbage", "Water Leakage", "Streetlight", "Road Damage",
    "Drainage", "Fallen Tree", "Traffic Signal", "Public Safety", "Other",
]

IMPACT_LEVELS = ["Low", "Medium", "High"]

# --- keyword tables used by the fallback engine ------------------------
CATEGORY_KEYWORDS = {
    "Pothole": ["pothole", "pot hole", "crater", "hole in the road", "gaddha"],
    "Water Leakage": ["leak", "leakage", "pipeline", "pipe burst", "water supply",
                      "tap", "water pressure", "water wast"],
    "Garbage": ["garbage", "trash", "waste", "dump", "rubbish", "litter",
                "stink", "smell", "bin"],
    "Streetlight": ["streetlight", "street light", "lamp", "light not working",
                    "dark street", "pole light", "flicker"],
    "Drainage": ["drain", "sewage", "gutter", "manhole", "clogged", "overflow water",
                 "waterlog", "flood"],
    "Fallen Tree": ["tree", "branch", "uprooted", "fallen tree"],
    "Traffic Signal": ["traffic signal", "traffic light", "signal not working", "junction light"],
    "Road Damage": ["road damage", "broken road", "cracked road", "damaged road",
                    "road caved", "uneven road", "tar"],
    "Public Safety": ["unsafe", "harassment", "stray dog", "open wire", "electric shock",
                      "no lighting", "crime", "accident prone"],
}

SEVERITY_WORDS = {
    3: ["minor", "small", "slight", "starting"],
    7: ["large", "big", "deep", "broken", "overflowing", "blocked", "damaged", "burst"],
    9: ["huge", "massive", "severe", "dangerous", "emergency", "collapsed", "flooded",
        "very deep", "critical"],
}

SAFETY_WORDS = ["accident", "dangerous", "unsafe", "injury", "injured", "fell",
                "risk", "children", "school", "hospital", "elderly", "slip",
                "shock", "fire", "collapse", "night", "blind turn", "skid"]

CROWD_WORDS = ["bus stop", "bus stand", "market", "school", "hospital", "station",
               "college", "main road", "highway", "junction", "temple", "circle"]

DEFAULT_RECOMMENDATION = {
    "Pothole": "Send a road inspection team and patch the surface before it widens.",
    "Road Damage": "Survey the stretch and schedule resurfacing.",
    "Garbage": "Clear the accumulated waste and review the collection schedule for this point.",
    "Water Leakage": "Isolate the line, repair the leak and check for pressure loss nearby.",
    "Streetlight": "Check the feeder and replace the failed fitting.",
    "Drainage": "De-silt the drain and check downstream flow before the next rain.",
    "Fallen Tree": "Clear the obstruction and inspect neighbouring trees.",
    "Traffic Signal": "Restore signal operation and deploy manual control meanwhile.",
    "Public Safety": "Inspect the location and put an interim safety measure in place.",
    "Other": "Inspect the location and route it to the relevant field team.",
}

PROMPT = """You are the perception module of a civic issue platform.
Read one citizen report and return ONLY a JSON object, no markdown, no commentary.

Report title: {title}
Report description: {description}
Citizen-selected category: {category}
Address / area: {address}

Return exactly these keys:
{{
  "category": one of {categories},
  "severity": integer 1-10,
  "safety_risk": integer 1-10,
  "impact_level": "Low" | "Medium" | "High",
  "summary": one sentence describing the real-world problem,
  "reasoning": one or two sentences explaining why this severity and risk,
  "recommendation": one sentence naming the action a city department should take,
  "confidence": number between 0 and 1
}}
Judge severity by physical damage and safety_risk by danger to people.
"""


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------
def analyze_report(title, description, category_hint=None, address=""):
    """Always returns a validated dict. Never raises."""
    result = _analyze_with_gemini(title, description, category_hint, address)
    if result:
        result["source"] = "gemini"
        return result
    result = fallback_analysis(title, description, category_hint, address)
    result["source"] = "fallback"
    return result


def gemini_available(app_config=None):
    from flask import current_app
    cfg = app_config or current_app.config
    if not cfg.get("GEMINI_API_KEY"):
        return False
    try:
        import google.generativeai  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def explain_signal(prompt_text):
    """Short free-text generation used by the emerging-signals feature."""
    try:
        model = _model()
        if model is None:
            return None
        response = model.generate_content(prompt_text)
        text = (getattr(response, "text", "") or "").strip()
        return text[:400] or None
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini signal explanation failed: %s", exc)
        return None


# ----------------------------------------------------------------------
# Gemini
# ----------------------------------------------------------------------
def _model():
    from flask import current_app
    key = current_app.config.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
    except Exception as exc:  # noqa: BLE001
        log.info("google-generativeai not installed (%s); using fallback engine", exc)
        return None
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(current_app.config.get("GEMINI_MODEL", "gemini-1.5-flash"))
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini configuration failed: %s", exc)
        return None


def _analyze_with_gemini(title, description, category_hint, address):
    model = _model()
    if model is None:
        return None
    prompt = PROMPT.format(
        title=title or "(none)",
        description=description or "(none)",
        category=category_hint or "(not selected)",
        address=address or "(not provided)",
        categories=json.dumps(CATEGORIES),
    )
    try:
        response = model.generate_content(prompt)
        raw = getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini call failed: %s", exc)
        return None
    payload = _extract_json(raw)
    if payload is None:
        log.warning("Gemini returned unparseable output; falling back")
        return None
    return validate(payload, title, description, category_hint, address)


def _extract_json(raw):
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Validation - nothing from the model is trusted as-is
# ----------------------------------------------------------------------
def _as_int(value, default, low=1, high=10):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _as_text(value, default, limit=400):
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()[:limit]


def validate(payload, title, description, category_hint, address):
    if not isinstance(payload, dict):
        return None
    baseline = fallback_analysis(title, description, category_hint, address)

    category = payload.get("category")
    if category not in CATEGORIES:
        category = baseline["category"]

    impact = payload.get("impact_level")
    if not isinstance(impact, str) or impact.title() not in IMPACT_LEVELS:
        impact = baseline["impact_level"]
    else:
        impact = impact.title()

    try:
        confidence = float(payload.get("confidence", 0.8))
    except (TypeError, ValueError):
        confidence = 0.8
    # A value outside 0-1 means the model ignored the contract, so treat it as
    # unreliable rather than clamping 7.5 up into a confident-looking 1.0.
    if not 0.0 <= confidence <= 1.0:
        confidence = 0.6

    return {
        "category": category,
        "severity": _as_int(payload.get("severity"), baseline["severity"]),
        "safety_risk": _as_int(payload.get("safety_risk"), baseline["safety_risk"]),
        "impact_level": impact,
        "summary": _as_text(payload.get("summary"), baseline["summary"], 255),
        "reasoning": _as_text(payload.get("reasoning"), baseline["reasoning"]),
        "recommendation": _as_text(payload.get("recommendation"), baseline["recommendation"]),
        "confidence": round(confidence, 3),
    }


# ----------------------------------------------------------------------
# Deterministic fallback engine
# ----------------------------------------------------------------------
def guess_category(text, category_hint=None):
    blob = (text or "").lower()
    best, best_hits = None, 0
    for name, words in CATEGORY_KEYWORDS.items():
        hits = sum(1 for word in words if word in blob)
        if hits > best_hits:
            best, best_hits = name, hits
    if best_hits >= 1:
        return best
    if category_hint in CATEGORIES:
        return category_hint
    return "Other"


def fallback_analysis(title, description, category_hint=None, address=""):
    blob = (" ".join([title or "", description or "", address or ""])).lower()
    category = guess_category(blob, category_hint)

    severity = 6
    for score, words in sorted(SEVERITY_WORDS.items()):
        if any(word in blob for word in words):
            severity = score
    if category in ("Pothole", "Drainage", "Water Leakage", "Traffic Signal"):
        severity += 1

    safety_hits = sum(1 for word in SAFETY_WORDS if word in blob)
    safety = 4 + 2 * min(3, safety_hits)
    if category in ("Traffic Signal", "Public Safety", "Fallen Tree"):
        safety += 2
    if category == "Garbage":
        safety -= 1

    crowd_hits = sum(1 for word in CROWD_WORDS if word in blob)
    if crowd_hits >= 1:
        impact = "High"
    elif severity >= 7 or safety >= 7:
        impact = "Medium"
    else:
        impact = "Low"

    severity = max(1, min(10, severity))
    safety = max(1, min(10, safety))

    summary = "%s reported%s." % (
        category,
        (" near " + address.split(",")[0]) if address else "",
    )
    reasons = []
    reasons.append("Wording indicates %s physical damage (%s/10)"
                   % ("serious" if severity >= 7 else "moderate", severity))
    if safety_hits:
        reasons.append("the report mentions danger to people")
    if crowd_hits:
        reasons.append("the location is a busy public area")
    reasoning = ", ".join(reasons).capitalize() + "."

    return {
        "category": category,
        "severity": severity,
        "safety_risk": safety,
        "impact_level": impact,
        "summary": summary[:255],
        "reasoning": reasoning,
        "recommendation": DEFAULT_RECOMMENDATION.get(category, DEFAULT_RECOMMENDATION["Other"]),
        "confidence": 0.62,
    }
