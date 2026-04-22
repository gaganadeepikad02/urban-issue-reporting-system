try:
    CATEGORY_DEPT = {
        "Pothole": "Roads",
        "Garbage": "Sanitation",
        "Flood": "Disaster"
    }
except Exception as e:
    raise Exception(f"Failed to initialize category-department mapping: {str(e)}")


def get_department(category: str) -> str:

    try:

        if not category:
            return "Unknown"

        category = category.title()

        return CATEGORY_DEPT.get(category, "Unknown")

    except Exception:
        return "Unknown"


def valid_departments():

    try:
        return list(CATEGORY_DEPT.values())
    except Exception:
        return []
