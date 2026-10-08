import sqlite3

db = "database/civicpulse.sqlite3"

conn = sqlite3.connect(db)
cursor = conn.cursor()

cursor.execute("DELETE FROM issue_images")
cursor.execute("DELETE FROM issue_support")
cursor.execute("DELETE FROM ai_analysis")
cursor.execute("DELETE FROM issue_status_history")
cursor.execute("DELETE FROM notifications")
cursor.execute("DELETE FROM issue_reports")
cursor.execute("DELETE FROM issues")

conn.commit()

print("All reported data has been cleared successfully.")

conn.close()