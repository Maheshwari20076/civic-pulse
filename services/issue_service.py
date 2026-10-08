"""The civic intelligence pipeline.

    citizen report -> perception -> cluster -> priority -> routing -> notify

Every step here writes to the database, so what the citizen sees, what the
admin sees and what the map draws are all the same records.
"""
import db
from services import ai_service, duplicate_service, priority_service, routing_service
from services import notification_service as notify_svc

STATUS_FLOW = ["Reported", "AI Verified", "Assigned", "In Progress", "Resolved", "Closed"]


# ----------------------------------------------------------------------
# Reads
# ----------------------------------------------------------------------
ISSUE_SELECT = """
SELECT i.*, c.name AS category, c.icon AS category_icon,
       d.name AS department,
       u.name AS reporter_name,
       (SELECT COUNT(*) FROM issue_reports r WHERE r.issue_id = i.id) AS report_count,
       (SELECT COUNT(*) FROM issue_support s WHERE s.issue_id = i.id) AS support_count,
       (SELECT MAX(r2.created_at) FROM issue_reports r2 WHERE r2.issue_id = i.id) AS last_report_at
FROM issues i
LEFT JOIN categories c ON c.id = i.category_id
LEFT JOIN departments d ON d.id = i.department_id
LEFT JOIN users u ON u.id = i.created_by
"""


def get_issue(issue_id):
    issue = db.query_one(ISSUE_SELECT + " WHERE i.id = %s", (issue_id,))
    return _decorate(issue)


def list_issues(status=None, category_id=None, order="priority", limit=200, created_by=None):
    sql = ISSUE_SELECT
    where, params = [], []
    if status:
        where.append("i.status = %s")
        params.append(status)
    if category_id:
        where.append("i.category_id = %s")
        params.append(category_id)
    if created_by:
        where.append("i.id IN (SELECT issue_id FROM issue_reports WHERE user_id = %s)")
        params.append(created_by)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += {
        "priority": " ORDER BY i.priority_score DESC, i.updated_at DESC",
        "recent": " ORDER BY i.created_at DESC",
    }.get(order, " ORDER BY i.priority_score DESC")
    sql += " LIMIT %s"
    params.append(limit)
    return [_decorate(row) for row in db.query_all(sql, params)]


def _decorate(issue):
    if not issue:
        return None
    issue["priority_level"] = priority_service.level(issue.get("priority_score") or 0)
    issue["latitude"] = float(issue["latitude"])
    issue["longitude"] = float(issue["longitude"])
    issue["created_at"] = db.as_datetime(issue.get("created_at"))
    issue["updated_at"] = db.as_datetime(issue.get("updated_at"))
    issue["last_report_at"] = db.as_datetime(issue.get("last_report_at"))
    issue["code"] = "CP-%04d" % (1000 + int(issue["id"]))
    return issue


def get_reports(issue_id):
    rows = db.query_all(
        "SELECT r.*, u.name AS user_name FROM issue_reports r"
        " LEFT JOIN users u ON u.id = r.user_id"
        " WHERE r.issue_id = %s ORDER BY r.created_at DESC, r.id DESC",
        (issue_id,),
    )
    for row in rows:
        row["created_at"] = db.as_datetime(row["created_at"])
        row["images"] = db.query_all(
            "SELECT * FROM issue_images WHERE report_id = %s", (row["id"],)
        )
    return rows


def get_analysis(issue_id):
    row = db.query_one(
        "SELECT * FROM ai_analysis WHERE issue_id = %s ORDER BY id DESC LIMIT 1",
        (issue_id,),
    )
    if row:
        row["created_at"] = db.as_datetime(row["created_at"])
        row["confidence"] = float(row["confidence"] or 0)
    return row


def get_timeline(issue_id):
    rows = db.query_all(
        "SELECT h.*, u.name AS actor FROM issue_status_history h"
        " LEFT JOIN users u ON u.id = h.changed_by"
        " WHERE h.issue_id = %s ORDER BY h.created_at ASC, h.id ASC",
        (issue_id,),
    )
    for row in rows:
        row["created_at"] = db.as_datetime(row["created_at"])
    return rows


def has_supported(issue_id, user_id):
    if not user_id:
        return False
    return db.query_one(
        "SELECT id FROM issue_support WHERE issue_id = %s AND user_id = %s",
        (issue_id, user_id),
    ) is not None


def category_id_for(name):
    row = db.query_one("SELECT id FROM categories WHERE name = %s", (name,))
    return row["id"] if row else None


# ----------------------------------------------------------------------
# Priority recalculation
# ----------------------------------------------------------------------
def recalculate_priority(issue_id, persist=True):
    issue = get_issue(issue_id)
    if not issue:
        return None, []
    score, breakdown = priority_service.calculate(
        severity=issue["severity"],
        safety_risk=issue["safety_risk"],
        report_count=issue["report_count"],
        impact_level=issue["impact_level"],
        last_report_at=issue["last_report_at"] or issue["created_at"],
        support_count=issue["support_count"],
        address=issue.get("address") or "",
    )
    if persist:
        db.execute(
            "UPDATE issues SET priority_score = %s, updated_at = %s WHERE id = %s",
            (score, db.now(), issue_id),
        )
    return score, breakdown


def priority_breakdown(issue):
    _, breakdown = priority_service.calculate(
        severity=issue["severity"],
        safety_risk=issue["safety_risk"],
        report_count=issue["report_count"],
        impact_level=issue["impact_level"],
        last_report_at=issue["last_report_at"] or issue["created_at"],
        support_count=issue["support_count"],
        address=issue.get("address") or "",
    )
    return breakdown


# ----------------------------------------------------------------------
# Status
# ----------------------------------------------------------------------
def set_status(issue_id, status, changed_by=None, note=None, notify=True):
    if status not in STATUS_FLOW:
        raise ValueError("Unknown status: %s" % status)
    db.execute(
        "UPDATE issues SET status = %s, updated_at = %s WHERE id = %s",
        (status, db.now(), issue_id),
    )
    db.execute(
        "INSERT INTO issue_status_history (issue_id, status, changed_by, note, created_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (issue_id, status, changed_by, (note or "")[:500] or None, db.now()),
    )
    if notify:
        issue = get_issue(issue_id)
        messages = {
            "AI Verified": "%s has been verified and added to the city priority queue.",
            "Assigned": "%s has been assigned to a department.",
            "In Progress": "%s is now being worked on.",
            "Resolved": "%s has been marked resolved. Thank you for reporting it.",
            "Closed": "%s has been closed.",
        }
        template = messages.get(status, "%s status changed to " + status + ".")
        notify_svc.notify_issue_followers(
            issue_id, template % issue["code"],
            "resolved" if status == "Resolved" else "status",
        )
        if status == "Resolved":
            _award_resolution_points(issue_id)


def _award_resolution_points(issue_id):
    rows = db.query_all(
        "SELECT DISTINCT user_id FROM issue_reports WHERE issue_id = %s AND user_id IS NOT NULL",
        (issue_id,),
    )
    for row in rows:
        db.execute(
            "UPDATE users SET impact_score = impact_score + 10 WHERE id = %s",
            (row["user_id"],),
        )


def assign_department(issue_id, department_id, changed_by=None, note=None):
    db.execute(
        "UPDATE issues SET department_id = %s, updated_at = %s WHERE id = %s",
        (department_id, db.now(), issue_id),
    )
    issue = get_issue(issue_id)
    if issue["status"] in ("Reported", "AI Verified"):
        set_status(issue_id, "Assigned", changed_by, note or
                   "Routed to %s." % (issue.get("department") or "department"))
    else:
        db.execute(
            "INSERT INTO issue_status_history (issue_id, status, changed_by, note, created_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (issue_id, issue["status"], changed_by,
             "Department changed to %s." % (issue.get("department") or "-"), db.now()),
        )
        notify_svc.notify_issue_followers(
            issue_id, "%s was routed to %s." % (issue["code"], issue.get("department") or "a department"),
            "assigned",
        )


# ----------------------------------------------------------------------
# Support
# ----------------------------------------------------------------------
def support_issue(issue_id, user_id):
    """Returns (ok, message)."""
    if has_supported(issue_id, user_id):
        return False, "You have already supported this issue."
    db.execute(
        "INSERT INTO issue_support (issue_id, user_id, created_at) VALUES (%s, %s, %s)",
        (issue_id, user_id, db.now()),
    )
    db.execute("UPDATE users SET impact_score = impact_score + 2 WHERE id = %s", (user_id,))
    recalculate_priority(issue_id)
    return True, "You helped strengthen this report."


# ----------------------------------------------------------------------
# Intake - the main pipeline
# ----------------------------------------------------------------------
def intake_report(user_id, title, description, category_hint, latitude, longitude,
                  address="", image_paths=None):
    """Runs one citizen report through the whole pipeline.

    Returns a dict describing what happened, which is exactly what the
    AI-result screen renders.
    """
    image_paths = image_paths or []

    # 1. Perception ----------------------------------------------------
    analysis = ai_service.analyze_report(title, description, category_hint, address)

    # 2. Cluster -------------------------------------------------------
    candidate = {
        "title": title,
        "description": description,
        "category": analysis["category"],
        "latitude": latitude,
        "longitude": longitude,
    }
    matches = duplicate_service.find_matches(candidate, limit=5)
    match = matches[0] if matches and matches[0]["score"] >= _min_score() else None

    merged = match is not None
    if merged:
        issue_id = match["issue"]["id"]
        _blend_analysis_into_issue(issue_id, analysis)
    else:
        issue_id = _create_issue(user_id, title, description, analysis,
                                 latitude, longitude, address)

    # 3. Attach this citizen's report to the issue ---------------------
    report_id = db.execute(
        "INSERT INTO issue_reports (issue_id, user_id, description, latitude, longitude, created_at)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (issue_id, user_id, description, latitude, longitude, db.now()),
    )
    for path in image_paths:
        db.execute(
            "INSERT INTO issue_images (report_id, image_path, created_at) VALUES (%s, %s, %s)",
            (report_id, path, db.now()),
        )

    # 4. Store the AI record and re-score ------------------------------
    duplicate_summary = (
        "Merged with %s existing report(s) on issue CP-%04d."
        % (match["issue"]["report_count"], 1000 + issue_id) if merged
        else "No matching open issue nearby; new civic issue opened."
    )
    db.execute(
        """INSERT INTO ai_analysis
           (issue_id, category, severity, safety_risk, impact_level, priority_score,
            duplicate_summary, reasoning, recommendation, confidence, source, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (issue_id, analysis["category"], analysis["severity"], analysis["safety_risk"],
         analysis["impact_level"], 0, duplicate_summary[:255], analysis["reasoning"],
         analysis["recommendation"], analysis["confidence"], analysis["source"], db.now()),
    )
    score, breakdown = recalculate_priority(issue_id)
    db.execute(
        "UPDATE ai_analysis SET priority_score = %s WHERE issue_id = %s AND priority_score = 0",
        (score, issue_id),
    )

    # 5. Route ---------------------------------------------------------
    issue = get_issue(issue_id)
    recommended = routing_service.recommend(analysis["category"])
    if recommended and not issue["department_id"]:
        db.execute("UPDATE issues SET department_id = %s WHERE id = %s",
                   (recommended["id"], issue_id))

    # 6. Verify + notify ----------------------------------------------
    if issue["status"] == "Reported":
        set_status(issue_id, "AI Verified", user_id,
                   "Report analysed and verified automatically.", notify=False)

    db.execute("UPDATE users SET impact_score = impact_score + 5 WHERE id = %s", (user_id,))

    issue = get_issue(issue_id)
    if merged:
        notify_svc.notify(
            user_id,
            "Your report was grouped with %s other reports into %s."
            % (issue["report_count"] - 1, issue["code"]),
            "merged", issue_id,
        )
        notify_svc.notify_issue_followers(
            issue_id,
            "%s received another citizen report. It now has %s reports."
            % (issue["code"], issue["report_count"]),
            "info", exclude_user=user_id,
        )
    else:
        notify_svc.notify(
            user_id,
            "Your report was analysed and opened as civic issue %s." % issue["code"],
            "submitted", issue_id,
        )

    return {
        "issue": issue,
        "issue_id": issue_id,
        "report_id": report_id,
        "merged": merged,
        "match": match,
        "matches": matches,
        "analysis": analysis,
        "cluster_explanation": duplicate_service.explain(match),
        "priority": score,
        "breakdown": breakdown,
        "department": issue.get("department"),
    }


def _min_score():
    from flask import current_app
    return current_app.config["CLUSTER_MIN_SCORE"]


def _create_issue(user_id, title, description, analysis, latitude, longitude, address):
    category_id = category_id_for(analysis["category"])
    now = db.now()
    return db.execute(
        """INSERT INTO issues
           (title, description, category_id, latitude, longitude, address, severity,
            safety_risk, impact_level, priority_score, status, department_id,
            created_by, created_at, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (title[:200], description, category_id, latitude, longitude, address[:255],
         analysis["severity"], analysis["safety_risk"], analysis["impact_level"],
         0, "Reported", None, user_id, now, now),
    )


def _blend_analysis_into_issue(issue_id, analysis):
    """More reports sharpen the picture: keep the worst observed severity/risk."""
    issue = get_issue(issue_id)
    severity = max(issue["severity"], analysis["severity"])
    safety = max(issue["safety_risk"], analysis["safety_risk"])
    rank = {"Low": 1, "Medium": 2, "High": 3}
    impact = issue["impact_level"]
    if rank.get(analysis["impact_level"], 2) > rank.get(impact, 2):
        impact = analysis["impact_level"]
    db.execute(
        "UPDATE issues SET severity = %s, safety_risk = %s, impact_level = %s, updated_at = %s"
        " WHERE id = %s",
        (severity, safety, impact, db.now(), issue_id),
    )
