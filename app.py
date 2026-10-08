"""CivicPulse 2.0 - application entry point.

    python app.py   ->  http://127.0.0.1:5000
"""
import logging
import os

from flask import (Blueprint, Flask, render_template, session, g, request,
                   redirect, url_for, flash)

import db
from config import Config
from routes.auth import bp as auth_bp
from routes.citizen import bp as citizen_bp
from routes.admin import bp as admin_bp
from routes.api import bp as api_bp
from services import ai_service, priority_service
from services import notification_service as notify_svc
from utils.helpers import timeago, format_dt, PRIORITY_CLASSES, STATUS_CLASSES

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.teardown_appcontext(db.close_conn)

    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    _register_main(app)
    _register_template_helpers(app)
    _register_error_handlers(app)

    @app.before_request
    def guard_database():
        """One friendly setup screen instead of a stack trace on every route."""
        if request.endpoint in ("static", "main.setup", None):
            return None
        ok, message = db.healthcheck()
        if not ok:
            g.db_error = message
            return render_template("setup.html", error=message), 503
        return None

    @app.context_processor
    def inject_globals():
        unread = 0
        if session.get("user_id"):
            try:
                unread = notify_svc.unread_count(session["user_id"])
            except Exception:  # noqa: BLE001
                unread = 0
        return {
            "current_role": session.get("role"),
            "current_name": session.get("name"),
            "unread_count": unread,
            "ai_mode": "Gemini" if ai_service.gemini_available(app.config) else "Local engine",
        }

    return app


def _register_main(app):
    """Public pages: landing, the setup helper, and the post-login redirect."""
    bp = Blueprint("main", __name__)

    @bp.route("/")
    def landing():
        stats = {"reports": 0, "active": 0, "resolved": 0, "rate": 0}
        try:
            row = db.query_one(
                """
                SELECT
                  (SELECT COUNT(*) FROM issue_reports) AS reports,
                  (SELECT COUNT(*) FROM issues WHERE status NOT IN ('Resolved','Closed')) AS active,
                  (SELECT COUNT(*) FROM issues WHERE status IN ('Resolved','Closed')) AS resolved,
                  (SELECT COUNT(*) FROM issues) AS total
                """
            )
            stats = {
                "reports": row["reports"],
                "active": row["active"],
                "resolved": row["resolved"],
                "rate": round(100.0 * row["resolved"] / (row["total"] or 1)),
            }
        except Exception:  # noqa: BLE001
            pass
        return render_template("landing.html", stats=stats)

    @bp.route("/business")
    def business():
        return render_template("business.html", pilot_email=os.getenv("PILOT_CONTACT_EMAIL", ""))

    @bp.route("/setup")
    def setup():
        ok, message = db.healthcheck()
        return render_template("setup.html", error=None if ok else message, ok=ok)

    @bp.route("/home")
    def home_redirect():
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        if session.get("role") == "citizen":
            return redirect(url_for("citizen.dashboard"))
        return redirect(url_for("auth.login"))

    app.register_blueprint(bp)


def _register_template_helpers(app):
    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["dt"] = format_dt

    @app.template_global()
    def priority_class(score):
        return PRIORITY_CLASSES.get(priority_service.level(score or 0), "low")

    @app.template_global()
    def priority_level(score):
        return priority_service.level(score or 0)

    @app.template_global()
    def status_class(status):
        return STATUS_CLASSES.get(status, "reported")

    @app.template_global()
    def issue_code(issue_id):
        return "CP-%04d" % (1000 + int(issue_id))


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404,
                               title="That page does not exist",
                               message="Check the link, or go back to your dashboard."), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               title="You do not have access to that",
                               message="Sign in with an account that has the right role."), 403

    @app.errorhandler(413)
    def too_large(_e):
        flash("That image is larger than 5 MB. Upload a smaller photo.", "danger")
        return redirect(url_for("citizen.report"))

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled error: %s", e)
        db.rollback()
        return render_template("error.html", code=500,
                               title="Something broke on our side",
                               message="The error has been logged. Try that action again."), 500


app = create_app()

if __name__ == "__main__":
    # Debug is opt-in (FLASK_DEBUG=1) so a slip during the demo shows the
    # friendly error page rather than an interactive traceback on the projector.
    debug = os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="127.0.0.1", port=5000, debug=debug)
