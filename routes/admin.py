"""City Intelligence Center - the operator side of CivicPulse."""
import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, abort, jsonify)

import db
from services import issue_service, routing_service, signal_service
from services import priority_service
from utils.decorators import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@admin_required
def dashboard():
    totals = db.query_one(
        """
        SELECT
          (SELECT COUNT(*) FROM issue_reports) AS total_reports,
          (SELECT COUNT(*) FROM issues) AS total_issues,
          (SELECT COUNT(*) FROM issues WHERE status NOT IN ('Resolved','Closed')) AS active_issues,
          (SELECT COUNT(*) FROM issues WHERE priority_score >= 76
              AND status NOT IN ('Resolved','Closed')) AS critical_issues,
          (SELECT COUNT(*) FROM issues WHERE status IN ('Resolved','Closed')) AS resolved_issues,
          (SELECT COUNT(*) FROM users WHERE role = 'citizen') AS citizens
        """
    )
    total = totals["total_issues"] or 1
    totals["resolution_rate"] = round(100.0 * totals["resolved_issues"] / total)

    queue = [i for i in issue_service.list_issues(order="priority", limit=60)
             if i["status"] not in ("Resolved", "Closed")][:8]
    signals = signal_service.detect(use_ai=False)
    stale = signal_service.stale_issues()

    by_status = db.query_all(
        "SELECT status, COUNT(*) AS c FROM issues GROUP BY status"
    )
    return render_template(
        "admin/dashboard.html", totals=totals, queue=queue, signals=signals,
        signal_count=len(signals), stale=stale, by_status=by_status,
    )


@bp.route("/issues")
@admin_required
def issues():
    status = request.args.get("status") or None
    category_id = request.args.get("category") or None
    rows = issue_service.list_issues(status=status, category_id=category_id, limit=300)
    level = request.args.get("level")
    if level:
        rows = [r for r in rows if r["priority_level"].lower() == level.lower()]
    categories = db.query_all("SELECT * FROM categories ORDER BY name")
    return render_template(
        "admin/issues.html", issues=rows, categories=categories,
        statuses=issue_service.STATUS_FLOW, active_status=status,
        active_category=category_id, active_level=level,
    )


@bp.route("/issue/<int:issue_id>")
@admin_required
def issue_details(issue_id):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        abort(404)
    return render_template(
        "admin/issue_details.html",
        issue=issue,
        analysis=issue_service.get_analysis(issue_id),
        reports=issue_service.get_reports(issue_id),
        timeline=issue_service.get_timeline(issue_id),
        breakdown=issue_service.priority_breakdown(issue),
        departments=routing_service.all_departments(),
        recommended=routing_service.recommend_name(issue.get("category")),
        statuses=issue_service.STATUS_FLOW,
    )


@bp.route("/issue/<int:issue_id>/assign", methods=["POST"])
@admin_required
def assign(issue_id):
    if not issue_service.get_issue(issue_id):
        abort(404)
    department_id = request.form.get("department_id")
    if not department_id:
        flash("Choose a department first.", "warning")
        return redirect(url_for("admin.issue_details", issue_id=issue_id))
    issue_service.assign_department(
        issue_id, int(department_id), session["user_id"],
        (request.form.get("note") or "").strip() or None,
    )
    flash("Department updated.", "success")
    return redirect(url_for("admin.issue_details", issue_id=issue_id))


@bp.route("/issue/<int:issue_id>/status", methods=["POST"])
@admin_required
def change_status(issue_id):
    if not issue_service.get_issue(issue_id):
        abort(404)
    status = request.form.get("status")
    note = (request.form.get("note") or "").strip() or None
    if status not in issue_service.STATUS_FLOW:
        flash("That status is not part of the issue flow.", "danger")
        return redirect(url_for("admin.issue_details", issue_id=issue_id))
    issue_service.set_status(issue_id, status, session["user_id"], note)
    flash("Status changed to %s." % status, "success")
    return redirect(url_for("admin.issue_details", issue_id=issue_id))


@bp.route("/issue/<int:issue_id>/note", methods=["POST"])
@admin_required
def add_note(issue_id):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        abort(404)
    note = (request.form.get("note") or "").strip()
    if not note:
        flash("Write a note before saving.", "warning")
        return redirect(url_for("admin.issue_details", issue_id=issue_id))
    db.execute(
        "INSERT INTO issue_status_history (issue_id, status, changed_by, note, created_at)"
        " VALUES (%s, %s, %s, %s, %s)",
        (issue_id, issue["status"], session["user_id"], note[:500], db.now()),
    )
    flash("Note added to the timeline.", "success")
    return redirect(url_for("admin.issue_details", issue_id=issue_id))


@bp.route("/map")
@admin_required
def city_map():
    categories = db.query_all("SELECT * FROM categories ORDER BY name")
    return render_template("admin/map.html", categories=categories,
                           statuses=issue_service.STATUS_FLOW)


@bp.route("/signals")
@admin_required
def signals():
    detected = signal_service.detect(use_ai=True)
    return render_template("admin/signals.html", signals=detected,
                           stale=signal_service.stale_issues())


@bp.route("/departments")
@admin_required
def departments():
    rows = db.query_all(
        """
        SELECT d.id, d.name, d.description,
          (SELECT COUNT(*) FROM issues i WHERE i.department_id = d.id
             AND i.status NOT IN ('Resolved','Closed')) AS active_issues,
          (SELECT COUNT(*) FROM issues i WHERE i.department_id = d.id
             AND i.priority_score >= 76 AND i.status NOT IN ('Resolved','Closed'))
             AS critical_issues,
          (SELECT COUNT(*) FROM issues i WHERE i.department_id = d.id
             AND i.status IN ('Resolved','Closed')) AS resolved_issues
        FROM departments d ORDER BY d.name
        """
    )
    busiest = max([r["active_issues"] for r in rows] or [1]) or 1
    for row in rows:
        row["workload"] = round(100.0 * row["active_issues"] / busiest)
        total = row["active_issues"] + row["resolved_issues"]
        row["resolution_rate"] = round(100.0 * row["resolved_issues"] / total) if total else 0
    return render_template("admin/departments.html", departments=rows)


@bp.route("/analytics")
@admin_required
def analytics():
    return render_template("admin/analytics.html")


# ----------------------------------------------------------------------
# Chart data (consumed by Chart.js on the analytics page)
# ----------------------------------------------------------------------
@bp.route("/api/analytics")
@admin_required
def analytics_data():
    by_category = db.query_all(
        "SELECT c.name AS label, COUNT(i.id) AS value FROM categories c"
        " LEFT JOIN issues i ON i.category_id = c.id GROUP BY c.name ORDER BY value DESC"
    )
    by_status = db.query_all(
        "SELECT status AS label, COUNT(*) AS value FROM issues GROUP BY status"
    )
    by_department = db.query_all(
        "SELECT d.name AS label, COUNT(i.id) AS value FROM departments d"
        " LEFT JOIN issues i ON i.department_id = d.id"
        " AND i.status NOT IN ('Resolved','Closed') GROUP BY d.name ORDER BY value DESC"
    )
    issues = db.query_all("SELECT priority_score, created_at, status FROM issues")

    buckets = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for row in issues:
        buckets[priority_service.level(row["priority_score"] or 0)] += 1

    reports = db.query_all("SELECT created_at FROM issue_reports")
    today = datetime.date.today()
    days = [today - datetime.timedelta(days=offset) for offset in range(13, -1, -1)]
    labels = [d.strftime("%d %b") for d in days]
    counts = {d: 0 for d in days}
    for row in reports:
        created = db.as_datetime(row["created_at"])
        if created and created.date() in counts:
            counts[created.date()] += 1

    resolved_counts = {d: 0 for d in days}
    for row in db.query_all(
        "SELECT created_at FROM issue_status_history WHERE status = 'Resolved'"
    ):
        created = db.as_datetime(row["created_at"])
        if created and created.date() in resolved_counts:
            resolved_counts[created.date()] += 1

    return jsonify({
        "by_category": by_category,
        "by_status": by_status,
        "by_department": by_department,
        "priority": [{"label": k, "value": v} for k, v in buckets.items()],
        "reports_over_time": {"labels": labels, "values": [counts[d] for d in days]},
        "resolution_trend": {"labels": labels, "values": [resolved_counts[d] for d in days]},
    })
