"""Regenerates database/seed.sql.

Kept in the repo so the demo data is reproducible and the priority scores in
the seed are produced by the same formula the running app uses - nothing in
seed.sql is a hand-picked number.

    python database/generate_seed.py
"""
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import priority_service  # noqa: E402

random.seed(20)
NOW = datetime.datetime.now()

ADMIN_HASH = ("pbkdf2:sha256:1000000$gddo0YV2D5DJsMP2$"
              "4eca921d2900393e25a61fad9db429bc799c44f5d79698dc66e9de8ba8a42e44")   # Admin@123
CITIZEN_HASH = ("pbkdf2:sha256:1000000$JlxSNpYBy4dY7opm$"
                "290c7e617fb0faf2c5280453068ae03cf67a83589aa866f95354a278b84a9a81")  # Citizen@123

DEPARTMENTS = [
    ("Road Infrastructure", "Roads, surfaces, footpaths and resurfacing work."),
    ("Waste Management", "Collection, street sweeping and waste points."),
    ("Water Supply", "Distribution lines, leaks, pressure and drainage."),
    ("Electrical Infrastructure", "Street lighting, feeders and traffic signals."),
    ("Public Safety", "Hazards, unsafe locations and emergency response."),
    ("Parks & Environment", "Trees, green spaces and environmental hazards."),
]

CATEGORIES = [
    ("Pothole", "circle-dot", "Holes and craters in the road surface."),
    ("Garbage", "trash-2", "Uncollected waste and overflowing bins."),
    ("Water Leakage", "droplets", "Leaking pipes, mains and taps."),
    ("Streetlight", "lightbulb", "Failed or flickering street lighting."),
    ("Road Damage", "construction", "Cracked, sunken or broken road stretches."),
    ("Drainage", "waves", "Blocked drains, sewage and waterlogging."),
    ("Fallen Tree", "tree-pine", "Fallen trees and dangerous branches."),
    ("Traffic Signal", "traffic-cone", "Signals not working at junctions."),
    ("Public Safety", "shield-alert", "Unsafe public areas and hazards."),
    ("Other", "circle-alert", "Anything that does not fit the list above."),
]

CITIZENS = [
    ("Priya Kulkarni", "priya@example.com"),
    ("Arjun Desai", "arjun@example.com"),
    ("Fatima Sayed", "fatima@example.com"),
    ("Rohit Patil", "rohit@example.com"),
    ("Sneha Joshi", "sneha@example.com"),
    ("Imran Shaikh", "imran@example.com"),
    ("Kavya Rao", "kavya@example.com"),
    ("Manoj Hegde", "manoj@example.com"),
]

CATEGORY_TO_DEPT = {
    "Pothole": 1, "Road Damage": 1, "Garbage": 2, "Water Leakage": 3, "Drainage": 3,
    "Streetlight": 4, "Traffic Signal": 4, "Public Safety": 5, "Fallen Tree": 6, "Other": 5,
}

# (title, category, lat, lng, address, severity, safety, impact, status, reports, supports)
ISSUES = [
    dict(
        title="Large pothole near Central Bus Stand",
        description="Deep pothole in the middle of the carriageway right outside the bus stand. "
                    "Two-wheelers swerve into the next lane to avoid it and it gets worse after rain.",
        category="Pothole", lat=15.85604, lng=74.50612,
        address="Opposite Central Bus Stand, Club Road, Belagavi",
        severity=9, safety=9, impact="High", status="AI Verified", supports=6,
        reports=[
            ("Large pothole near the bus stop. Vehicles are struggling to pass and it could cause accidents.", 4),
            ("Deep pothole on the road near the bus stand, very dangerous at night.", 11),
            ("Road has a dangerous pothole near the bus stop, my scooter almost skidded.", 19),
            ("Huge crater outside the bus stand. Autos are braking suddenly because of it.", 28),
            ("Pothole in front of the bus stand has become very deep after the rain.", 36),
            ("Big hole in the road near Central Bus Stand, water collects inside it.", 44),
            ("Dangerous pothole near bus stand, an elderly man fell off his cycle here.", 55),
        ],
    ),
    dict(
        title="Garbage overflowing at Khade Bazaar collection point",
        description="The collection point has not been cleared for several days. Waste has spread onto "
                    "the footpath and the smell is severe near the vegetable stalls.",
        category="Garbage", lat=15.86173, lng=74.50831,
        address="Khade Bazaar main market, Belagavi",
        severity=7, safety=5, impact="High", status="Assigned", supports=4,
        reports=[
            ("Garbage is overflowing at the market bin and spreading onto the road.", 9),
            ("Waste has not been collected near the bazaar for four days, the smell is terrible.", 17),
            ("Rubbish dumped around the bin at Khade Bazaar, stray dogs all over it.", 26),
            ("Overflowing garbage bin in the market, shoppers have to walk around it.", 41),
            ("Trash spilling out of the collection point near the vegetable stalls.", 58),
        ],
    ),
    dict(
        title="Street lights out on Shivaji Nagar 2nd Cross",
        description="An entire stretch of street lighting has been off for over a week. The road is "
                    "completely dark after 7 pm and there is no footpath lighting either.",
        category="Streetlight", lat=15.84312, lng=74.48903,
        address="2nd Cross, Shivaji Nagar, Belagavi",
        severity=6, safety=8, impact="Medium", status="In Progress", supports=3,
        reports=[
            ("Street light not working on our cross, the whole street is dark at night.", 22),
            ("Lamp posts on 2nd cross have been off for a week, it feels unsafe walking home.", 40),
            ("No street lighting here, children coming back from tuition have to use phone torches.", 63),
            ("Dark street, the light pole near the corner shop has not worked for days.", 90),
        ],
    ),
    dict(
        title="Water pipeline leaking on Tilakwadi 1st Cross",
        description="Continuous leak from the main pipeline. Water has been running down the road "
                    "for days and the surface around it is starting to break up.",
        category="Water Leakage", lat=15.83967, lng=74.50288,
        address="1st Cross, Tilakwadi, Belagavi",
        severity=8, safety=6, impact="High", status="AI Verified", supports=5,
        reports=[
            ("Water leaking from the main pipe, it has been running continuously for days.", 6),
            ("Pipeline burst near the corner, huge amount of water being wasted.", 14),
            ("Leak in the water line on 1st cross, the road is always wet now.", 25),
            ("Water pipe leakage, the tar around it is breaking because of the flow.", 33),
            ("Continuous water leakage near the junction, please repair the pipe.", 52),
            ("Main line leaking, we are also getting low pressure in the taps.", 70),
        ],
    ),
    dict(
        title="Very low water pressure across Tilakwadi 3rd Cross",
        description="Taps have had almost no pressure for a week. Several houses on the street are "
                    "affected at the same time, which suggests a supply problem, not a household one.",
        category="Water Leakage", lat=15.84090, lng=74.50450,
        address="3rd Cross, Tilakwadi, Belagavi",
        severity=6, safety=4, impact="Medium", status="Reported", supports=2,
        reports=[
            ("Very low water pressure in the taps for the last week.", 20),
            ("No proper water supply, the whole street has the same problem.", 47),
            ("Water pressure has dropped a lot, we are unable to fill the tank.", 66),
        ],
    ),
    dict(
        title="Road flooding at Tilakwadi Circle after every rain",
        description="Water stands knee-deep at the circle within minutes of rain because the drain "
                    "beside it is blocked. Vehicles stall in the middle of the junction.",
        category="Drainage", lat=15.83880, lng=74.50190,
        address="Tilakwadi Circle, Belagavi",
        severity=8, safety=7, impact="High", status="AI Verified", supports=4,
        reports=[
            ("Road flooding at the circle after rain, the drain is completely blocked.", 12),
            ("Water logging near Tilakwadi circle, vehicles are getting stuck.", 30),
            ("Drain overflow at the junction, sewage water on the road.", 57),
            ("Every time it rains the circle floods, it is dangerous for two-wheelers.", 74),
        ],
    ),
    dict(
        title="Traffic signal not working at Fort Road junction",
        description="The signal has been dead through peak hours for two days. Traffic from four "
                    "directions crosses without control and there is no manual policing.",
        category="Traffic Signal", lat=15.85672, lng=74.49961,
        address="Fort Road junction, Belagavi",
        severity=8, safety=9, impact="High", status="Assigned", supports=5,
        reports=[
            ("Traffic signal not working at the junction, it is chaos during office hours.", 8),
            ("Signal light is dead at Fort Road, vehicles from all sides crossing together.", 21),
            ("Junction light not working, very dangerous for pedestrians crossing.", 38),
        ],
    ),
    dict(
        title="Blocked drain overflowing near Vadgaon school",
        description="The drain outside the school gate is blocked and overflowing onto the footpath "
                    "children use every morning.",
        category="Drainage", lat=15.82657, lng=74.48312,
        address="Near government school, Vadgaon, Belagavi",
        severity=7, safety=8, impact="High", status="In Progress", supports=3,
        reports=[
            ("Blocked drain overflowing right outside the school gate.", 31),
            ("Sewage water on the footpath near the school, children have to walk through it.", 49),
            ("Manhole is clogged and dirty water is coming onto the road.", 80),
        ],
    ),
    dict(
        title="Damaged road stretch on Udyambag industrial road",
        description="A long stretch of the surface has broken up under heavy vehicle traffic. "
                    "The road is uneven end to end rather than having one pothole.",
        category="Road Damage", lat=15.81405, lng=74.49022,
        address="Udyambag industrial area, Belagavi",
        severity=7, safety=6, impact="Medium", status="Reported", supports=1,
        reports=[
            ("The road is badly damaged and uneven for a long stretch here.", 43),
            ("Broken road surface, lorries are damaging it further every day.", 96),
        ],
    ),
    dict(
        title="Unsafe unlit stretch behind the railway station",
        description="No working lights along the approach road and no security presence. People "
                    "walking to late trains avoid the stretch entirely.",
        category="Public Safety", lat=15.83294, lng=74.50441,
        address="Approach road, Belagavi Railway Station",
        severity=6, safety=9, impact="High", status="AI Verified", supports=7,
        reports=[
            ("This stretch is completely unsafe at night, no lighting at all.", 16),
            ("Dark and deserted road behind the station, women avoid walking here after dark.", 34),
            ("No lighting near the station approach, it feels very unsafe.", 61),
        ],
    ),
    dict(
        title="Street light flickering on Shivaji Nagar 4th Cross",
        description="The light turns on and off through the night. It has been like this since the "
                    "last repair on the neighbouring street.",
        category="Streetlight", lat=15.84402, lng=74.49041,
        address="4th Cross, Shivaji Nagar, Belagavi",
        severity=4, safety=5, impact="Low", status="Reported", supports=1,
        reports=[
            ("Street light keeps flickering the whole night on our cross.", 27),
            ("The lamp on 4th cross goes on and off, needs checking.", 72),
        ],
    ),
    dict(
        title="Two street lights dead on Shivaji Nagar Main Road",
        description="Two adjacent poles on the main road are out. Both went off within a day of "
                    "each other, which points at the feeder rather than the fittings.",
        category="Streetlight", lat=15.84250, lng=74.49150,
        address="Main Road, Shivaji Nagar, Belagavi",
        severity=5, safety=6, impact="Medium", status="Assigned", supports=2,
        reports=[
            ("Two street lights on the main road stopped working on the same day.", 35),
            ("Lights not working near the main road bus stop, quite dark there now.", 59),
            ("Both lamp posts near the shops are dead, please repair.", 88),
        ],
    ),
    dict(
        title="Fallen tree blocking half of Kanbargi Road",
        description="A large branch came down in the storm and is lying across one lane. It has "
                    "been cut back and cleared by the field team.",
        category="Fallen Tree", lat=15.87031, lng=74.52601,
        address="Kanbargi Road, near the water tank, Belagavi",
        severity=8, safety=8, impact="Medium", status="Resolved", supports=2,
        reports=[
            ("A big tree branch has fallen and is blocking half the road.", 120),
            ("Uprooted tree on Kanbargi road, traffic has to use one lane.", 132),
        ],
    ),
    dict(
        title="Garbage dumped on the empty plot at Ganeshpur",
        description="Household waste was being dumped on an empty plot instead of the collection "
                    "point. The plot has been cleared and a bin placed nearby.",
        category="Garbage", lat=15.88024, lng=74.51003,
        address="Ganeshpur Road, Belagavi",
        severity=5, safety=4, impact="Low", status="Resolved", supports=1,
        reports=[
            ("People are dumping garbage on the empty plot near our street.", 150),
            ("Waste dumped on the vacant land, it smells bad in the afternoon.", 163),
        ],
    ),
    dict(
        title="Pothole on Khanapur Road near the petrol pump",
        description="Pothole opposite the fuel station. It was patched by the road team and the "
                    "surface has held since.",
        category="Pothole", lat=15.82041, lng=74.47903,
        address="Khanapur Road, near petrol pump, Belagavi",
        severity=6, safety=6, impact="Medium", status="Closed", supports=1,
        reports=[
            ("Pothole right where vehicles turn into the petrol pump.", 190),
            ("Small but deep pothole on Khanapur road, bikes hit it often.", 205),
        ],
    ),
]

NOTE_BY_STATUS = {
    "AI Verified": "Report analysed and verified automatically.",
    "Assigned": "Routed to the owning department.",
    "In Progress": "Field team scheduled for inspection.",
    "Resolved": "Work completed and verified on site.",
    "Closed": "Issue closed after the repair held.",
}
FLOW = ["Reported", "AI Verified", "Assigned", "In Progress", "Resolved", "Closed"]


def ago(hours):
    return "DATE_SUB(NOW(), INTERVAL %d HOUR)" % hours


def esc(text):
    return text.replace("\\", "\\\\").replace("'", "''")


def build():
    lines = [
        "-- ------------------------------------------------------------------",
        "-- CivicPulse 2.0 - demo data",
        "-- Generated by database/generate_seed.py. Import AFTER schema.sql.",
        "--",
        "-- Demo accounts:  admin@civicpulse.com / Admin@123",
        "--                 priya@example.com   / Citizen@123",
        "-- ------------------------------------------------------------------",
        "USE civicpulse;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE notifications;",
        "TRUNCATE TABLE issue_status_history;",
        "TRUNCATE TABLE ai_analysis;",
        "TRUNCATE TABLE issue_support;",
        "TRUNCATE TABLE issue_images;",
        "TRUNCATE TABLE issue_reports;",
        "TRUNCATE TABLE issues;",
        "TRUNCATE TABLE categories;",
        "TRUNCATE TABLE departments;",
        "TRUNCATE TABLE users;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "-- Departments -----------------------------------------------------",
    ]

    for idx, (name, description) in enumerate(DEPARTMENTS, start=1):
        lines.append(
            "INSERT INTO departments (id, name, description, created_at) VALUES "
            "(%d, '%s', '%s', %s);" % (idx, esc(name), esc(description), ago(720))
        )

    lines += ["", "-- Categories ------------------------------------------------------"]
    for idx, (name, icon, description) in enumerate(CATEGORIES, start=1):
        lines.append(
            "INSERT INTO categories (id, name, icon, description) VALUES "
            "(%d, '%s', '%s', '%s');" % (idx, esc(name), icon, esc(description))
        )

    category_id = {name: i for i, (name, _, _) in enumerate(CATEGORIES, start=1)}

    lines += ["", "-- Users -----------------------------------------------------------"]
    lines.append(
        "INSERT INTO users (id, name, email, password_hash, role, impact_score, created_at) VALUES "
        "(1, 'City Operations Desk', 'admin@civicpulse.com', '%s', 'admin', 0, %s);"
        % (ADMIN_HASH, ago(720))
    )
    for idx, (name, email) in enumerate(CITIZENS, start=2):
        lines.append(
            "INSERT INTO users (id, name, email, password_hash, role, impact_score, created_at) VALUES "
            "(%d, '%s', '%s', '%s', 'citizen', 0, %s);"
            % (idx, esc(name), email, CITIZEN_HASH, ago(700 - idx * 9))
        )

    report_id = 0
    support_id = 0
    history_id = 0
    notification_id = 0
    impact = {i: 0 for i in range(2, len(CITIZENS) + 2)}

    lines += ["", "-- Issues, reports, analysis, history, support --------------------"]

    for issue_index, spec in enumerate(ISSUES, start=1):
        oldest = max(hours for _, hours in spec["reports"])
        newest = min(hours for _, hours in spec["reports"])
        reporters = _assign_reporters(len(spec["reports"]))
        owner = reporters[0]

        score, _ = priority_service.calculate(
            severity=spec["severity"], safety_risk=spec["safety"],
            report_count=len(spec["reports"]), impact_level=spec["impact"],
            last_report_at=NOW - datetime.timedelta(hours=newest),
            support_count=spec["supports"], address=spec["address"], now=NOW,
        )
        status_index = FLOW.index(spec["status"])
        updated_hours = max(1, newest - 1) if status_index < 3 else max(1, newest // 2)

        lines.append(
            "INSERT INTO issues (id, title, description, category_id, latitude, longitude, address, "
            "severity, safety_risk, impact_level, priority_score, status, department_id, created_by, "
            "created_at, updated_at) VALUES (%d, '%s', '%s', %d, %.5f, %.5f, '%s', %d, %d, '%s', %d, "
            "'%s', %d, %d, %s, %s);"
            % (issue_index, esc(spec["title"]), esc(spec["description"]),
               category_id[spec["category"]], spec["lat"], spec["lng"], esc(spec["address"]),
               spec["severity"], spec["safety"], spec["impact"], score, spec["status"],
               CATEGORY_TO_DEPT[spec["category"]], owner, ago(oldest), ago(updated_hours))
        )

        for offset, (text, hours) in enumerate(spec["reports"]):
            report_id += 1
            user_id = reporters[offset]
            impact[user_id] += 5
            jitter_lat = spec["lat"] + random.uniform(-0.00035, 0.00035)
            jitter_lng = spec["lng"] + random.uniform(-0.00035, 0.00035)
            lines.append(
                "INSERT INTO issue_reports (id, issue_id, user_id, description, latitude, longitude, "
                "created_at) VALUES (%d, %d, %d, '%s', %.5f, %.5f, %s);"
                % (report_id, issue_index, user_id, esc(text), jitter_lat, jitter_lng, ago(hours))
            )

        for n, supporter in enumerate(_support_users(reporters, spec["supports"])):
            support_id += 1
            impact[supporter] += 2
            lines.append(
                "INSERT INTO issue_support (id, issue_id, user_id, created_at) VALUES (%d, %d, %d, %s);"
                % (support_id, issue_index, supporter, ago(max(1, newest - n)))
            )

        lines.append(
            "INSERT INTO ai_analysis (issue_id, category, severity, safety_risk, impact_level, "
            "priority_score, duplicate_summary, reasoning, recommendation, confidence, source, created_at) "
            "VALUES (%d, '%s', %d, %d, '%s', %d, '%s', '%s', '%s', %.2f, 'fallback', %s);"
            % (issue_index, esc(spec["category"]), spec["severity"], spec["safety"], spec["impact"],
               score, esc(_dup_summary(spec, issue_index)), esc(_reasoning(spec)),
               esc(_recommendation(spec)), round(random.uniform(0.78, 0.95), 2), ago(oldest))
        )

        for step in FLOW[:status_index + 1]:
            history_id += 1
            step_hours = max(1, int(oldest - (oldest - newest) * (FLOW.index(step) / max(1, status_index))))
            note = NOTE_BY_STATUS.get(step)
            lines.append(
                "INSERT INTO issue_status_history (id, issue_id, status, changed_by, note, created_at) "
                "VALUES (%d, %d, '%s', %s, %s, %s);"
                % (history_id, issue_index, step,
                   str(owner) if step == "Reported" else "1",
                   "NULL" if not note else "'%s'" % esc(note), ago(step_hours))
            )

        for user_id in sorted(set(reporters)):
            notification_id += 1
            message = ("Your report was grouped into %s, which now has %d citizen reports."
                       % ("CP-%04d" % (1000 + issue_index), len(spec["reports"])))
            lines.append(
                "INSERT INTO notifications (id, user_id, issue_id, message, type, is_read, created_at) "
                "VALUES (%d, %d, %d, '%s', 'merged', %d, %s);"
                % (notification_id, user_id, issue_index, esc(message),
                   1 if oldest > 48 else 0, ago(max(1, newest)))
            )
        if spec["status"] in ("Resolved", "Closed"):
            for user_id in sorted(set(reporters)):
                impact[user_id] += 10
                notification_id += 1
                lines.append(
                    "INSERT INTO notifications (id, user_id, issue_id, message, type, is_read, created_at) "
                    "VALUES (%d, %d, %d, '%s', 'resolved', 1, %s);"
                    % (notification_id, user_id, issue_index,
                       esc("%s has been marked resolved. Thank you for reporting it."
                           % ("CP-%04d" % (1000 + issue_index))), ago(max(1, newest // 2)))
                )

    lines += ["", "-- Impact scores --------------------------------------------------"]
    for user_id, points in impact.items():
        lines.append("UPDATE users SET impact_score = %d WHERE id = %d;" % (points, user_id))

    lines.append("")
    return "\n".join(lines) + "\n"


def _assign_reporters(count):
    """Different citizens report the same problem - that is the whole point."""
    ids = list(range(2, len(CITIZENS) + 2))
    random.shuffle(ids)
    picked = []
    while len(picked) < count:
        picked.extend(ids)
    return picked[:count]


def _support_users(reporters, count):
    """Distinct supporters for one issue.

    issue_support has a UNIQUE (issue_id, user_id) constraint - the same rule the
    app enforces when a citizen taps "Support this issue" - so this never repeats
    a user, and quietly caps the count at the number of citizens available.
    """
    ids = [i for i in range(2, len(CITIZENS) + 2) if i not in reporters[:2]]
    return ids[:max(0, count)]


def _dup_summary(spec, issue_index):
    count = len(spec["reports"])
    if count == 1:
        return "No matching open issue nearby; new civic issue opened."
    return ("%d citizen reports within 120 m were matched to one problem on issue CP-%04d."
            % (count, 1000 + issue_index))


def _reasoning(spec):
    parts = ["Severity %d/10 based on the described damage" % spec["severity"],
             "safety risk %d/10" % spec["safety"]]
    if spec["impact"] == "High":
        parts.append("the location is a busy public area")
    if len(spec["reports"]) >= 4:
        parts.append("%d independent reports describe the same problem" % len(spec["reports"]))
    return ", ".join(parts) + "."


def _recommendation(spec):
    return {
        "Pothole": "Inspect and patch the road surface before it widens further.",
        "Road Damage": "Survey the stretch and schedule resurfacing.",
        "Garbage": "Clear the point and review the collection frequency for this location.",
        "Water Leakage": "Isolate the line, repair the leak and re-check pressure in the area.",
        "Drainage": "De-silt the drain and verify downstream flow before the next rain.",
        "Streetlight": "Check the feeder and replace the failed fittings.",
        "Traffic Signal": "Restore the signal and deploy manual traffic control until it is fixed.",
        "Fallen Tree": "Clear the obstruction and inspect neighbouring trees.",
        "Public Safety": "Inspect the location and install interim lighting or patrols.",
    }.get(spec["category"], "Inspect the location and route to the relevant field team.")


if __name__ == "__main__":
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed.sql")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(build())
    print("Wrote %s" % target)
