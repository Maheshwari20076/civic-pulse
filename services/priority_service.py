"""Priority engine.

The AI never sets the final priority. It contributes severity / safety / impact
estimates; this module turns those - plus cluster size, location, recency and
citizen support - into a reproducible 0-100 score with a plain-English
explanation.

    Priority = Severity        x 0.30
             + Safety risk     x 0.25
             + Cluster strength x 0.20
             + Location impact x 0.10
             + Recency         x 0.10
             + Citizen support x 0.05
"""
import datetime

WEIGHTS = {
    "severity": 0.30,
    "safety_risk": 0.25,
    "cluster_strength": 0.20,
    "location_impact": 0.10,
    "recency": 0.10,
    "citizen_support": 0.05,
}

# Places where a civic failure hurts more people, or hurts them worse.
HIGH_IMPACT_WORDS = (
    "bus stand", "bus stop", "hospital", "school", "college", "market",
    "station", "highway", "junction", "main road", "circle", "temple",
    "crossing", "signal", "bazaar", "fort road",
)

LEVELS = ((76, "Critical"), (56, "High"), (31, "Medium"), (0, "Low"))


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def cluster_strength(report_count):
    """1 report is weak evidence; 8 independent reports is near-proof."""
    return _clamp(18 + 11 * (max(1, report_count) - 1))


def location_impact(impact_level, address=""):
    base = {"high": 80.0, "medium": 55.0, "low": 30.0}.get(
        str(impact_level or "Medium").lower(), 55.0
    )
    text = (address or "").lower()
    if any(word in text for word in HIGH_IMPACT_WORDS):
        base += 10
    return _clamp(base)


def recency(last_report_at, now=None):
    """Fresh problems outrank stale ones; nothing ever decays below 10."""
    now = now or datetime.datetime.now()
    if not last_report_at:
        return 50.0
    days = max(0.0, (now - last_report_at).total_seconds() / 86400.0)
    return _clamp(100.0 - 6.0 * days, low=10.0)


def support_strength(support_count):
    return _clamp(10.0 * support_count)


def calculate(severity, safety_risk, report_count, impact_level,
              last_report_at=None, support_count=0, address="", now=None):
    """Returns (score 1-100, list of {label, detail, value} breakdown rows)."""
    components = {
        "severity": _clamp(float(severity or 5) * 10),
        "safety_risk": _clamp(float(safety_risk or 5) * 10),
        "cluster_strength": cluster_strength(report_count),
        "location_impact": location_impact(impact_level, address),
        "recency": recency(last_report_at, now=now),
        "citizen_support": support_strength(support_count),
    }
    score = sum(components[k] * WEIGHTS[k] for k in components)
    score = int(round(_clamp(score, low=1.0)))

    breakdown = [
        {"label": "Severity", "detail": "%s/10 reported damage" % int(severity or 5),
         "weight": 30, "value": round(components["severity"])},
        {"label": "Safety risk", "detail": "%s/10 risk to people" % int(safety_risk or 5),
         "weight": 25, "value": round(components["safety_risk"])},
        {"label": "Cluster strength", "detail": "%s citizen %s"
         % (report_count, "report" if report_count == 1 else "reports"),
         "weight": 20, "value": round(components["cluster_strength"])},
        {"label": "Location impact", "detail": "%s-impact location" % (impact_level or "Medium"),
         "weight": 10, "value": round(components["location_impact"])},
        {"label": "Recency", "detail": _recency_words(last_report_at, now),
         "weight": 10, "value": round(components["recency"])},
        {"label": "Citizen support", "detail": "%s %s this issue"
         % (support_count, "citizen supports" if support_count == 1 else "citizens support"),
         "weight": 5, "value": round(components["citizen_support"])},
    ]
    return score, breakdown


def _recency_words(last_report_at, now=None):
    if not last_report_at:
        return "no recent activity recorded"
    now = now or datetime.datetime.now()
    hours = (now - last_report_at).total_seconds() / 3600.0
    if hours < 2:
        return "reported in the last hour"
    if hours < 24:
        return "reported %d hours ago" % int(hours)
    days = int(hours // 24)
    return "last report %d %s ago" % (days, "day" if days == 1 else "days")


def level(score):
    for threshold, name in LEVELS:
        if score >= threshold:
            return name
    return "Low"


def level_class(score):
    return level(score).lower()
