from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import models


SEVERITY = {
    "Garbage": 1,
    "Pothole": 2,
    "Flood": 3
}

DUPLICATE_RADIUS = 50


def haversine(lat1, lon1, lat2, lon2):

    try:

        R = 6371000

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )

        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    except Exception as e:
        raise Exception(f"Haversine calculation failed: {str(e)}")


def detect_duplicate(db, category, lat, lon):

    try:

        if lat is None or lon is None:
            return False, None, 0

        complaints = db.query(models.Complaint)\
            .filter(
                models.Complaint.category == category,
                models.Complaint.status != "Resolved"
            )\
            .all()

        duplicates = []

        for c in complaints:

            try:
                c_lat = float(c.latitude)
                c_lon = float(c.longitude)
            except Exception:
                continue

            try:
                dist = haversine(
                    float(lat),
                    float(lon),
                    c_lat,
                    c_lon
                )
            except Exception:
                continue

            if dist <= DUPLICATE_RADIUS:
                duplicates.append(c)

        if duplicates:
            return True, duplicates[0].id, len(duplicates)

        return False, None, 0

    except Exception as e:
        raise Exception(f"Duplicate detection failed: {str(e)}")


def compute_priority(category, duplicate_count, created_at=None):

    try:

        severity = SEVERITY.get(category, 1)

        age_days = 0

        if created_at:
            try:
                age_days = (datetime.utcnow() - created_at).days
            except Exception:
                age_days = 0

        score = (
            severity
            + (duplicate_count * 0.5)
            + (age_days * 0.2)
        )

        if score < 3:
            return score, "Low"

        if score <= 6:
            return score, "Medium"

        return score, "High"

    except Exception as e:
        raise Exception(f"Priority computation failed: {str(e)}")
