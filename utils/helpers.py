"""Small presentation helpers shared by routes and templates."""
import datetime
import os
import uuid

from werkzeug.utils import secure_filename

from utils.validators import allowed_image, image_is_real

PRIORITY_CLASSES = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low"}

STATUS_CLASSES = {
    "Reported": "reported",
    "AI Verified": "verified",
    "Assigned": "assigned",
    "In Progress": "progress",
    "Resolved": "resolved",
    "Closed": "closed",
}


def save_upload(file_storage, upload_folder, allowed_extensions):
    """Returns (relative_path, error). Rejects anything that is not an image."""
    if not file_storage or not file_storage.filename:
        return None, None
    filename = secure_filename(file_storage.filename)
    if not allowed_image(filename, allowed_extensions):
        return None, "Upload a PNG, JPG, WEBP or GIF image."
    os.makedirs(upload_folder, exist_ok=True)
    ext = filename.rsplit(".", 1)[1].lower()
    stored = "%s.%s" % (uuid.uuid4().hex, ext)
    full_path = os.path.join(upload_folder, stored)
    file_storage.save(full_path)
    if not image_is_real(full_path):
        os.remove(full_path)
        return None, "That file is not a readable image."
    return "uploads/%s" % stored, None


def timeago(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    delta = datetime.datetime.now() - value
    seconds = delta.total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "%d min ago" % (seconds // 60)
    if seconds < 86400:
        return "%d h ago" % (seconds // 3600)
    if seconds < 604800:
        return "%d d ago" % (seconds // 86400)
    return value.strftime("%d %b %Y")


def format_dt(value, fmt="%d %b %Y, %H:%M"):
    if not value:
        return "-"
    if isinstance(value, str):
        return value
    return value.strftime(fmt)
