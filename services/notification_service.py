"""In-app notifications. No email or SMS: everything lives in the product."""
import db

TYPES = ("submitted", "merged", "verified", "assigned", "status", "resolved", "info")


def notify(user_id, message, ntype="info", issue_id=None):
    if not user_id:
        return None
    return db.execute(
        "INSERT INTO notifications (user_id, issue_id, message, type, is_read, created_at)"
        " VALUES (%s, %s, %s, %s, 0, %s)",
        (user_id, issue_id, message[:400], ntype if ntype in TYPES else "info", db.now()),
    )


def notify_issue_followers(issue_id, message, ntype="status", exclude_user=None):
    """Everyone who reported or supported this issue hears about a change."""
    rows = db.query_all(
        """
        SELECT DISTINCT user_id FROM (
            SELECT user_id FROM issue_reports WHERE issue_id = %s AND user_id IS NOT NULL
            UNION
            SELECT user_id FROM issue_support WHERE issue_id = %s
        ) AS followers
        """,
        (issue_id, issue_id),
    )
    sent = 0
    for row in rows:
        if exclude_user and row["user_id"] == exclude_user:
            continue
        notify(row["user_id"], message, ntype, issue_id)
        sent += 1
    return sent


def unread_count(user_id):
    row = db.query_one(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = %s AND is_read = 0",
        (user_id,),
    )
    return row["c"] if row else 0


def list_for(user_id, limit=50):
    return db.query_all(
        "SELECT n.*, i.title AS issue_title FROM notifications n"
        " LEFT JOIN issues i ON i.id = n.issue_id"
        " WHERE n.user_id = %s ORDER BY n.created_at DESC, n.id DESC LIMIT %s",
        (user_id, limit),
    )


def mark_all_read(user_id):
    return db.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
        (user_id,),
    )
