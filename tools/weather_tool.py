def get_weather(city: str) -> dict:
    """
    Mock weather tool.
    Later, this function can be connected to a real weather API.
    """

    city = city.lower()

    if city == "istanbul":
        return {
            "city": "Istanbul",
            "temperature": 35,
            "condition": "sunny"
        }

    return {
        "city": city.title(),
        "temperature": 24,
        "condition": "mild"
    }
