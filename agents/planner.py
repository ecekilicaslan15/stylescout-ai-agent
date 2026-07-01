from models.plan import Plan


def plan_user_request(user_input: str) -> Plan:
    user_input_lower = user_input.lower()

    plan = Plan()
    plan.raw_input = user_input

    # Event detection
    if "wedding" in user_input_lower:
        plan.event = "wedding"
    elif "party" in user_input_lower:
        plan.event = "party"
    elif "office" in user_input_lower or "work" in user_input_lower:
        plan.event = "office"

    # Style detection
    if "elegant" in user_input_lower:
        plan.style = "elegant"
    elif "casual" in user_input_lower:
        plan.style = "casual"
    elif "sport" in user_input_lower:
        plan.style = "sporty"

    # Color detection
    colors = ["black", "white", "red", "blue",
              "green", "beige", "pink", "brown"]
    for color in colors:
        if color in user_input_lower:
            plan.color = color
            break

    # Clothing type detection
    clothing_types = ["dress", "shirt", "pants",
                      "skirt", "jacket", "blazer", "coat"]
    for item in clothing_types:
        if item in user_input_lower:
            plan.clothing_type = item
            break

    # Budget detection
    words = user_input_lower.replace("$", " $ ").split()
    for word in words:
        if word.isdigit():
            plan.budget = int(word)
            break

    # Season detection
    seasons = ["summer", "winter", "spring", "fall", "autumn"]
    for season in seasons:
        if season in user_input_lower:
            plan.season = season
            break

    return plan
