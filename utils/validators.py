"""Input validation. Every form goes through here before it reaches the DB."""
import os
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


def validate_registration(name, email, password, confirm):
    errors = []
    if not name or len(name.strip()) < 2:
        errors.append("Enter your full name.")
    if not email or not EMAIL_RE.match(email.strip()):
        errors.append("Enter a valid email address.")
    if not password or len(password) < 8:
        errors.append("Use a password of at least 8 characters.")
    elif password.isalpha() or password.isdigit():
        errors.append("Mix letters and numbers in your password.")
    if password != confirm:
        errors.append("The two passwords do not match.")
    return errors


def validate_report(title, description, latitude, longitude):
    errors = []
    if not title or len(title.strip()) < 5:
        errors.append("Give the issue a title of at least 5 characters.")
    if not description or len(description.strip()) < 15:
        errors.append("Describe the problem in at least 15 characters so it can be analysed.")
    lat, lng = parse_coords(latitude, longitude)
    if lat is None or lng is None:
        errors.append("Pick a location on the map or use your current location.")
    return errors, lat, lng


def parse_coords(latitude, longitude):
    try:
        lat, lng = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None, None
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None, None
    if lat == 0 and lng == 0:
        return None, None
    return round(lat, 7), round(lng, 7)


def allowed_image(filename, allowed):
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in allowed


def image_is_real(path):
    """Extension checks are not enough; confirm the bytes are an image."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False
