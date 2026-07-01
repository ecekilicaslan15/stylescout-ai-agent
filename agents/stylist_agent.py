from models.plan import Plan


def create_outfit(plan: Plan, trends: dict) -> dict:
    outfit = {
        "top": None,
        "bottom": None,
        "dress": None,
        "shoes": None,
        "bag": None,
        "accessories": []
    }

    selected_color = plan.color if plan.color else "neutral"

    if plan.event == "wedding":
        outfit["dress"] = f"{selected_color} satin dress"
        outfit["shoes"] = "Minimal heels"
        outfit["bag"] = "Small clutch bag"
        outfit["accessories"] = [
            "Pearl earrings",
            "Simple necklace"
        ]

    elif plan.event == "office":
        outfit["top"] = "White shirt"
        outfit["bottom"] = "Black tailored pants"
        outfit["shoes"] = "Loafers"
        outfit["bag"] = "Leather tote"
        outfit["accessories"] = [
            "Minimal watch"
        ]

    else:
        outfit["top"] = f"{selected_color} basic top"
        outfit["bottom"] = "Straight-leg jeans"
        outfit["shoes"] = "Clean sneakers"
        outfit["bag"] = "Everyday shoulder bag"
        outfit["accessories"] = [
            "Simple earrings"
        ]

    return outfit
