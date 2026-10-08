"""Register, sign in, sign out."""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)
from werkzeug.security import generate_password_hash, check_password_hash

import db
from utils.validators import validate_registration

bp = Blueprint("auth", __name__)


def _home_for(role):
    return url_for("admin.dashboard") if role == "admin" else url_for("citizen.dashboard")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(_home_for(session.get("role")))

    form = {"name": "", "email": ""}
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        form = {"name": name, "email": email}

        errors = validate_registration(name, email, password, confirm)
        if not errors and db.query_one("SELECT id FROM users WHERE email = %s", (email,)):
            errors.append("That email already has an account. Sign in instead.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html", form=form), 400

        user_id = db.execute(
            "INSERT INTO users (name, email, password_hash, role, impact_score, created_at)"
            " VALUES (%s, %s, %s, 'citizen', 0, %s)",
            (name, email, generate_password_hash(password, method="pbkdf2:sha256"), db.now()),
        )
        session.clear()
        session["user_id"] = user_id
        session["role"] = "citizen"
        session["name"] = name
        flash("Welcome to CivicPulse, %s." % name.split(" ")[0], "success")
        return redirect(url_for("citizen.dashboard"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(_home_for(session.get("role")))

    email = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = db.query_one("SELECT * FROM users WHERE email = %s", (email,))
        if not user or not check_password_hash(user["password_hash"], password):
            flash("That email and password combination does not match an account.", "danger")
            return render_template("auth/login.html", email=email), 401

        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        flash("Signed in as %s." % user["name"], "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(_home_for(user["role"]))

    return render_template("auth/login.html", email=email)


@bp.route("/logout")
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("main.landing"))
