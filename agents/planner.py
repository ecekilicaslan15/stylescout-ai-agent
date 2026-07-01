from models.plan import Plan


def plan_user_request(user_input: str) -> Plan:
    """
    Converts user input into a structured fashion plan.
    This is a simple rule-based planner for MVP.
    """

    text = user_input.lower()
    plan = Plan()

    # Event detection
    if "office" in text or "work" in text:
        plan.event = "office"
    elif "wedding" in text:
        plan.event = "wedding"
    elif "party" in text:
        plan.event = "party"
    elif "daily" in text or "casual" in text:
        plan.event = "daily"

    # Style detection
    if "elegant" in text or "classy" in text:
        plan.style = "elegant"
    elif "minimal" in text:
        plan.style = "minimal"
    elif "comfortable" in text or "comfy" in text:
        plan.style = "comfortable"

    # Color detection
    colors = ["black", "white", "beige", "navy", "blue", "gray", "pink", "red"]
    for color in colors:
        if color in text:
            plan.colors.append(color)

    # City detection
    if "istanbul" in text:
        plan.city = "Istanbul"
    elif "izmir" in text:
        plan.city = "Izmir"
    elif "ankara" in text:
        plan.city = "Ankara"

    # Date detection
    if "tomorrow" in text:
        plan.date = "tomorrow"
    elif "today" in text:
        plan.date = "today"

    return plan
