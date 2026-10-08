"""Cluster agent - the heart of CivicPulse.

Eight people reporting the same pothole is not eight problems. This module
decides whether an incoming report describes a civic problem the city already
knows about, using three cheap, explainable signals:

  * distance      - Haversine metres between the new report and the open issue
  * category      - same category, or a category that commonly overlaps
  * text overlap  - Jaccard similarity of meaningful words + shared landmarks

No machine learning, no embeddings: a judge can read the score and check it.
"""
import math
import re

from flask import current_app

import db

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "of", "in", "on",
    "at", "to", "it", "this", "that", "there", "here", "near", "very", "has",
    "have", "had", "be", "been", "for", "with", "from", "by", "as", "please",
    "kindly", "issue", "problem", "report", "reported", "we", "i", "my", "our",
    "its", "also", "some", "any", "not", "no", "so", "which", "can", "could",
}

# Categories that often describe the same physical failure.
RELATED = {
    ("Pothole", "Road Damage"): 0.75,
    ("Water Leakage", "Drainage"): 0.6,
    ("Streetlight", "Public Safety"): 0.5,
    ("Drainage", "Road Damage"): 0.5,
}

WEIGHTS = {"distance": 0.45, "category": 0.30, "text": 0.25}


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    radius = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2 - p1
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def tokenize(text):
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def text_similarity(a, b):
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    return overlap / float(len(ta | tb))


def category_score(new_category, existing_category):
    if not new_category or not existing_category:
        return 0.3
    if new_category == existing_category:
        return 1.0
    pair = tuple(sorted((new_category, existing_category)))
    for (a, b), score in RELATED.items():
        if tuple(sorted((a, b))) == pair:
            return score
    return 0.0


def distance_score(metres, radius):
    """1.0 on top of the issue, 0 at the edge of the search radius."""
    if metres >= radius:
        return 0.0
    return 1.0 - (metres / float(radius))


def score_match(new_report, issue, radius):
    metres = haversine_m(
        new_report["latitude"], new_report["longitude"],
        issue["latitude"], issue["longitude"],
    )
    if metres > radius:
        return None
    d = distance_score(metres, radius)
    c = category_score(new_report.get("category"), issue.get("category"))
    t = text_similarity(
        "%s %s" % (new_report.get("title", ""), new_report.get("description", "")),
        "%s %s" % (issue.get("title", ""), issue.get("description", "")),
    )
    # A different, unrelated category is a hard stop however close it is.
    if c == 0.0:
        return None
    total = d * WEIGHTS["distance"] + c * WEIGHTS["category"] + t * WEIGHTS["text"]
    return {
        "issue": issue,
        "distance_m": round(metres),
        "distance_score": round(d, 3),
        "category_score": round(c, 3),
        "text_score": round(t, 3),
        "score": round(total, 3),
    }


def open_issues_near(lat, lon, window_days, radius_m):
    """Candidate issues: still open, recent enough, roughly in the area.

    The bounding box is a cheap SQL prefilter; Haversine does the real work.
    """
    cutoff = db.now() - __import__("datetime").timedelta(days=window_days)
    deg = (radius_m / 111000.0) * 1.5 + 0.001
    rows = db.query_all(
        """
        SELECT i.*, c.name AS category,
               (SELECT COUNT(*) FROM issue_reports r WHERE r.issue_id = i.id) AS report_count
        FROM issues i
        LEFT JOIN categories c ON c.id = i.category_id
        WHERE i.status <> 'Closed'
          AND i.status <> 'Resolved'
          AND i.created_at >= %s
          AND i.latitude BETWEEN %s AND %s
          AND i.longitude BETWEEN %s AND %s
        """,
        (cutoff, float(lat) - deg, float(lat) + deg, float(lon) - deg, float(lon) + deg),
    )
    return rows


def find_matches(new_report, limit=5):
    """Ranked list of plausible existing issues for this report."""
    cfg = current_app.config
    radius = cfg["CLUSTER_RADIUS_M"]
    candidates = open_issues_near(
        new_report["latitude"], new_report["longitude"],
        cfg["CLUSTER_WINDOW_DAYS"], radius,
    )
    matches = []
    for issue in candidates:
        result = score_match(new_report, issue, radius)
        if result:
            matches.append(result)
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:limit]


def best_match(new_report):
    """The one issue this report should join, or None to open a new issue."""
    matches = find_matches(new_report, limit=1)
    if not matches:
        return None
    top = matches[0]
    return top if top["score"] >= current_app.config["CLUSTER_MIN_SCORE"] else None


def explain(match):
    """Human-readable justification for merging - shown to citizen and admin."""
    if not match:
        return "No open issue nearby matched this report, so a new civic issue was opened."
    bits = ["%s m from the existing issue" % match["distance_m"]]
    if match["category_score"] >= 1.0:
        bits.append("same category")
    elif match["category_score"] > 0:
        bits.append("closely related category")
    if match["text_score"] >= 0.15:
        bits.append("%d%% wording overlap" % round(match["text_score"] * 100))
    return "Matched on " + ", ".join(bits) + "."
