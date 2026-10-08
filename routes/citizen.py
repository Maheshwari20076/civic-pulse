"""Everything a citizen can do: report, track, support, get notified."""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app, abort)

import db
from services import issue_service, routing_service
from services import notification_service as notify_svc
from utils.decorators import login_required, citizen_required, current_user
from utils.helpers import save_upload
from utils.validators import validate_report

bp = Blueprint("citizen", __name__)


@bp.route("/dashboard")
@citizen_required
def dashboard():
    user_id = session["user_id"]
    user = current_user()

    stats = db.query_one(
        """
        SELECT
          (SELECT COUNT(DISTINCT issue_id) FROM issue_reports WHERE user_id = %s) AS my_issues,
          (SELECT COUNT(*) FROM issue_reports WHERE user_id = %s) AS my_reports,
          (SELECT COUNT(*) FROM issue_support WHERE user_id = %s) AS supported
        """,
        (user_id, user_id, user_id),
    )
    mine = issue_service.list_issues(created_by=user_id, limit=100)
    resolved = len([i for i in mine if i["status"] in ("Resolved", "Closed")])
    active = len(mine) - resolved

    nearby = issue_service.list_issues(order="priority", limit=6)
    nearby = [i for i in nearby if i["status"] not in ("Resolved", "Closed")][:4]

    return render_template(
        "citizen/dashboard.html",
        user=user, stats=stats, my_count=len(mine), resolved=resolved,
        active=active, nearby=nearby, recent=mine[:4],
    )


@bp.route("/report", methods=["GET", "POST"])
@citizen_required
def report():
    categories = db.query_all("SELECT * FROM categories ORDER BY id")

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        category = request.form.get("category") or None
        address = (request.form.get("address") or "").strip()
        errors, lat, lng = validate_report(
            title, description, request.form.get("latitude"), request.form.get("longitude")
        )

        image_path = None
        if not errors:
            image_path, upload_error = save_upload(
                request.files.get("image"),
                current_app.config["UPLOAD_FOLDER"],
                current_app.config["ALLOWED_EXTENSIONS"],
            )
            if upload_error:
                errors.append(upload_error)

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("citizen/report.html", categories=categories,
                                   form=request.form), 400

        try:
            result = issue_service.intake_report(
                user_id=session["user_id"], title=title, description=description,
                category_hint=category, latitude=lat, longitude=lng, address=address,
                image_paths=[image_path] if image_path else [],
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            current_app.logger.exception("Report intake failed")
            flash("We could not process that report: %s" % exc, "danger")
            return render_template("citizen/report.html", categories=categories,
                                   form=request.form), 500

        session["last_result_issue"] = result["issue_id"]
        return redirect(url_for("citizen.ai_result", issue_id=result["issue_id"],
                                merged=1 if result["merged"] else 0,
                                report_id=result["report_id"]))

    return render_template("citizen/report.html", categories=categories, form={})


@bp.route("/report/<int:issue_id>/result")
@citizen_required
def ai_result(issue_id):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        abort(404)
    analysis = issue_service.get_analysis(issue_id)
    breakdown = issue_service.priority_breakdown(issue)
    merged = request.args.get("merged") == "1"
    recommended = routing_service.recommend_name(issue.get("category"))
    return render_template(
        "citizen/ai_result.html", issue=issue, analysis=analysis,
        breakdown=breakdown, merged=merged, recommended=recommended,
    )


@bp.route("/my-reports")
@citizen_required
def my_reports():
    status_filter = request.args.get("filter", "all")
    issues = issue_service.list_issues(created_by=session["user_id"], limit=200)
    if status_filter == "active":
        issues = [i for i in issues if i["status"] not in ("Resolved", "Closed")]
    elif status_filter == "resolved":
        issues = [i for i in issues if i["status"] in ("Resolved", "Closed")]
    return render_template("citizen/reports.html", issues=issues, active_filter=status_filter)


@bp.route("/issue/<int:issue_id>")
@login_required
def issue_details(issue_id):
    issue = issue_service.get_issue(issue_id)
    if not issue:
        abort(404)
    return render_template(
        "citizen/issue_details.html",
        issue=issue,
        analysis=issue_service.get_analysis(issue_id),
        reports=issue_service.get_reports(issue_id),
        timeline=issue_service.get_timeline(issue_id),
        breakdown=issue_service.priority_breakdown(issue),
        supported=issue_service.has_supported(issue_id, session.get("user_id")),
    )


@bp.route("/issue/<int:issue_id>/support", methods=["POST"])
@citizen_required
def support(issue_id):
    if not issue_service.get_issue(issue_id):
        abort(404)
    ok, message = issue_service.support_issue(issue_id, session["user_id"])
    flash(message, "success" if ok else "warning")
    return redirect(url_for("citizen.issue_details", issue_id=issue_id))


@bp.route("/map")
@login_required
def city_map():
    categories = db.query_all("SELECT * FROM categories ORDER BY name")
    return render_template("citizen/map.html", categories=categories,
                           statuses=issue_service.STATUS_FLOW)


@bp.route("/profile")
@citizen_required
def profile():
    user_id = session["user_id"]
    user = current_user()
    mine = issue_service.list_issues(created_by=user_id, limit=500)
    resolved = [i for i in mine if i["status"] in ("Resolved", "Closed")]
    supported = db.query_one(
        "SELECT COUNT(*) AS c FROM issue_support WHERE user_id = %s", (user_id,)
    )["c"]
    reports = db.query_one(
        "SELECT COUNT(*) AS c FROM issue_reports WHERE user_id = %s", (user_id,)
    )["c"]
    return render_template(
        "citizen/profile.html", user=user, issues=mine, reports=reports,
        resolved=len(resolved), supported=supported,
    )


@bp.route("/notifications")
@login_required
def notifications():
    user_id = session["user_id"]
    items = notify_svc.list_for(user_id)
    for item in items:
        item["created_at"] = db.as_datetime(item["created_at"])
    notify_svc.mark_all_read(user_id)
    return render_template("citizen/notifications.html", items=items)
