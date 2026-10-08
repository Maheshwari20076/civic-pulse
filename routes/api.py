"""JSON endpoints. The map, the live duplicate check and the analytics charts
all read from here, so the front end never holds its own copy of the truth."""
from flask import Blueprint, jsonify, request, session

import db
from services import ai_service, duplicate_service, issue_service, priority_service
from utils.decorators import login_required

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/issues")
@login_required
def issues():
    """Map markers, with optional level / category / status filters."""
    rows = issue_service.list_issues(
        status=request.args.get("status") or None,
        category_id=request.args.get("category") or None,
        limit=500,
    )
    level = request.args.get("level")
    if level and level.lower() != "all":
        rows = [r for r in rows if r["priority_level"].lower() == level.lower()]
    return jsonify([
        {
            "id": r["id"],
            "code": r["code"],
            "title": r["title"],
            "category": r["category"],
            "status": r["status"],
            "priority": r["priority_score"],
            "level": r["priority_level"],
            "reports": r["report_count"],
            "supports": r["support_count"],
            "address": r["address"],
            "lat": r["latitude"],
            "lng": r["longitude"],
            "department": r["department"],
        }
        for r in rows
    ])


@bp.route("/analyze-issue", methods=["POST"])
@login_required
def analyze_issue():
    """Perception only - no writes. Used for the live preview on the form."""
    payload = request.get_json(silent=True) or request.form
    analysis = ai_service.analyze_report(
        payload.get("title", ""), payload.get("description", ""),
        payload.get("category"), payload.get("address", ""),
    )
    return jsonify(analysis)


@bp.route("/find-duplicates", methods=["POST"])
@login_required
def find_duplicates():
    """Tells the citizen, before they submit, that the city already knows."""
    payload = request.get_json(silent=True) or request.form
    try:
        lat = float(payload.get("latitude"))
        lng = float(payload.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"error": "A valid latitude and longitude are required."}), 400

    category = payload.get("category")
    if not category:
        category = ai_service.guess_category(
            "%s %s" % (payload.get("title", ""), payload.get("description", ""))
        )
    matches = duplicate_service.find_matches({
        "title": payload.get("title", ""),
        "description": payload.get("description", ""),
        "category": category,
        "latitude": lat, "longitude": lng,
    })
    return jsonify({
        "count": len(matches),
        "matches": [
            {
                "issue_id": m["issue"]["id"],
                "code": "CP-%04d" % (1000 + m["issue"]["id"]),
                "title": m["issue"]["title"],
                "reports": m["issue"]["report_count"],
                "distance_m": m["distance_m"],
                "score": m["score"],
                "explanation": duplicate_service.explain(m),
            }
            for m in matches
        ],
    })


@bp.route("/calculate-priority", methods=["POST"])
@login_required
def calculate_priority():
    payload = request.get_json(silent=True) or request.form
    issue_id = payload.get("issue_id")
    if issue_id:
        issue = issue_service.get_issue(int(issue_id))
        if not issue:
            return jsonify({"error": "Issue not found."}), 404
        score, breakdown = issue_service.recalculate_priority(int(issue_id))
        return jsonify({"priority": score, "level": priority_service.level(score),
                        "breakdown": breakdown})

    score, breakdown = priority_service.calculate(
        severity=payload.get("severity", 5),
        safety_risk=payload.get("safety_risk", 5),
        report_count=int(payload.get("report_count", 1)),
        impact_level=payload.get("impact_level", "Medium"),
        support_count=int(payload.get("support_count", 0)),
        address=payload.get("address", ""),
    )
    return jsonify({"priority": score, "level": priority_service.level(score),
                    "breakdown": breakdown})


@bp.route("/notifications/unread")
@login_required
def unread():
    from services import notification_service
    return jsonify({"count": notification_service.unread_count(session["user_id"])})
