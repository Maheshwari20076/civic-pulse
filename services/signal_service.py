"""Emerging signals + follow-up.

A single pothole is an issue. Three water complaints inside one neighbourhood
in one week is a symptom of something larger, and that is what a city needs to
see early. We group open issues by infrastructure family and geography, score
the cluster, and ask Gemini for a readable explanation (with a written fallback
when Gemini is not available).
"""
import datetime

from flask import current_app

import db
from services import ai_service
from services.duplicate_service import haversine_m

FAMILIES = {
    "Water infrastructure": ["Water Leakage", "Drainage"],
    "Electrical infrastructure": ["Streetlight", "Traffic Signal"],
    "Road infrastructure": ["Pothole", "Road Damage"],
    "Sanitation": ["Garbage"],
    "Public safety": ["Public Safety", "Fallen Tree"],
}

FALLBACK_TEXT = {
    "Water infrastructure": "Several water-related reports have appeared inside a small area "
                            "in a short window, which usually points to one failing line rather "
                            "than separate faults.",
    "Electrical infrastructure": "Repeated lighting and signal failures in the same neighbourhood "
                                 "often share one feeder or one damaged cable.",
    "Road infrastructure": "Clustered surface damage in one stretch usually means the base layer "
                           "is failing, not just the top surface.",
    "Sanitation": "Repeated waste build-up at nearby points suggests the collection route for this "
                  "area is not keeping up.",
    "Public safety": "Multiple safety reports in one area indicate a location that needs an "
                     "on-ground inspection.",
}


def _open_issues(window_hours):
    cutoff = db.now() - datetime.timedelta(hours=window_hours)
    rows = db.query_all(
        """
        SELECT i.id, i.title, i.latitude, i.longitude, i.address, i.priority_score,
               i.created_at, c.name AS category,
               (SELECT COUNT(*) FROM issue_reports r WHERE r.issue_id = i.id) AS report_count
        FROM issues i LEFT JOIN categories c ON c.id = i.category_id
        WHERE i.status NOT IN ('Resolved', 'Closed') AND i.created_at >= %s
        """,
        (cutoff,),
    )
    for row in rows:
        row["latitude"] = float(row["latitude"])
        row["longitude"] = float(row["longitude"])
        row["created_at"] = db.as_datetime(row["created_at"])
    return rows


def detect(use_ai=True):
    cfg = current_app.config
    radius = cfg["SIGNAL_RADIUS_M"]
    window = cfg["SIGNAL_WINDOW_HOURS"]
    issues = _open_issues(window)

    signals = []
    for family, categories in FAMILIES.items():
        pool = [i for i in issues if i["category"] in categories]
        if len(pool) < 2:
            continue
        for cluster in _geo_cluster(pool, radius):
            if len(cluster) < 2:
                continue
            reports = sum(c["report_count"] for c in cluster)
            if len(cluster) < 3 and reports < 5:
                continue
            signals.append(_build_signal(family, cluster, radius, window, use_ai))
    signals.sort(key=lambda s: s["confidence"], reverse=True)
    return signals


def _geo_cluster(issues, radius):
    """Simple single-pass grouping: seed on an issue, absorb everything within
    the radius. Good enough at city scale and easy to explain."""
    remaining = list(issues)
    clusters = []
    while remaining:
        seed = remaining.pop(0)
        group = [seed]
        rest = []
        for other in remaining:
            if haversine_m(seed["latitude"], seed["longitude"],
                           other["latitude"], other["longitude"]) <= radius:
                group.append(other)
            else:
                rest.append(other)
        remaining = rest
        clusters.append(group)
    return clusters


def _area_name(cluster):
    for issue in cluster:
        address = (issue.get("address") or "").strip()
        if address:
            parts = [p.strip() for p in address.split(",") if p.strip()]
            if len(parts) >= 2:
                return parts[-2]
            return parts[0]
    return "Unmapped area"


def _build_signal(family, cluster, radius, window, use_ai):
    reports = sum(c["report_count"] for c in cluster)
    # More issues, more reports and tighter geography = more confident.
    confidence = min(0.97, 0.35 + 0.12 * len(cluster) + 0.02 * reports)
    area = _area_name(cluster)
    explanation = None
    if use_ai:
        explanation = ai_service.explain_signal(
            "You are a city operations analyst. In two plain sentences, explain what these "
            "open civic issues taken together might indicate, and what to inspect first. "
            "Do not invent facts.\nArea: %s\nIssue family: %s\nIssues: %s"
            % (area, family, "; ".join("%s (%s reports)" % (c["title"], c["report_count"])
                                       for c in cluster))
        )
    if not explanation:
        explanation = "%s %d related issues and %d citizen reports have appeared within %d m " \
                      "of each other in the last %d hours." % (
                          FALLBACK_TEXT.get(family, ""), len(cluster), reports, radius,
                          window)
    return {
        "family": family,
        "title": "Possible %s problem" % family.lower(),
        "area": area,
        "issue_count": len(cluster),
        "report_count": reports,
        "confidence": round(confidence, 2),
        "explanation": explanation.strip(),
        "issues": sorted(cluster, key=lambda c: c["priority_score"], reverse=True),
        "center": {
            "lat": sum(c["latitude"] for c in cluster) / len(cluster),
            "lng": sum(c["longitude"] for c in cluster) / len(cluster),
        },
    }


# ----------------------------------------------------------------------
# Follow-up agent
# ----------------------------------------------------------------------
def stale_issues():
    """Issues sitting in Assigned / In Progress past the escalation window."""
    hours = current_app.config["ESCALATION_HOURS"]
    cutoff = db.now() - datetime.timedelta(hours=hours)
    rows = db.query_all(
        """
        SELECT i.id, i.title, i.status, i.priority_score, i.updated_at, d.name AS department
        FROM issues i LEFT JOIN departments d ON d.id = i.department_id
        WHERE i.status IN ('Assigned', 'In Progress') AND i.updated_at <= %s
        ORDER BY i.priority_score DESC
        """,
        (cutoff,),
    )
    now = db.now()
    for row in rows:
        row["updated_at"] = db.as_datetime(row["updated_at"])
        delta = now - row["updated_at"] if row["updated_at"] else datetime.timedelta()
        row["hours_stale"] = int(delta.total_seconds() // 3600)
        row["code"] = "CP-%04d" % (1000 + int(row["id"]))
    return rows
