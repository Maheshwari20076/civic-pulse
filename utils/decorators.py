"""Route guards. Sessions carry user_id and role; nothing else is trusted."""
from functools import wraps

from flask import session, redirect, url_for, flash, request

import db


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.query_one(
        "SELECT id, name, email, role, impact_score, created_at FROM users WHERE id = %s",
        (uid,),
    )


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if session.get("role") != role:
                flash("That area is for %s accounts." % role, "danger")
                return redirect(url_for("citizen.dashboard")
                                if session.get("role") == "citizen"
                                else url_for("admin.dashboard"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


citizen_required = role_required("citizen")
admin_required = role_required("admin")
