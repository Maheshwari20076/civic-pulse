"""Routing agent: category -> the department that actually owns the work.

The recommendation is advisory. An admin can always override it on the issue
page, and the override is what gets stored.
"""
import db

CATEGORY_TO_DEPARTMENT = {
    "Pothole": "Road Infrastructure",
    "Road Damage": "Road Infrastructure",
    "Garbage": "Waste Management",
    "Water Leakage": "Water Supply",
    "Drainage": "Water Supply",
    "Streetlight": "Electrical Infrastructure",
    "Traffic Signal": "Electrical Infrastructure",
    "Fallen Tree": "Parks & Environment",
    "Public Safety": "Public Safety",
    "Other": "Public Safety",
}


def recommend_name(category_name):
    return CATEGORY_TO_DEPARTMENT.get(category_name, "Public Safety")


def recommend(category_name):
    """Returns the department row for a category, or None if unseeded."""
    name = recommend_name(category_name)
    return db.query_one("SELECT * FROM departments WHERE name = %s", (name,))


def recommend_id(category_name):
    dept = recommend(category_name)
    return dept["id"] if dept else None


def all_departments():
    return db.query_all("SELECT * FROM departments ORDER BY name")
