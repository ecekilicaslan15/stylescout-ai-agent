from agents.planner import plan_user_request
from memory.memory_manager import load_memory, update_memory_from_plan
from agents.stylist_agent import generate_outfit


def run_fashion_agent(user_input: str) -> dict:
    """
    Main orchestrator of StyleScout.

    The orchestrator decides which agents should run
    based on the user's intent.
    """

    # 1. Planner understands the user request
    plan = plan_user_request(user_input)

    # Default response values
    memory = load_memory()
    outfit = None
    message = None

    # 2. Route based on intent
    if plan.intent == "memory_update":
        memory = update_memory_from_plan(plan)
        message = "Got it. I saved this preference to your style memory."

    elif plan.intent == "outfit_request":
        outfit = generate_outfit(plan, memory)

    elif plan.intent == "outfit_request_with_memory_update":
        memory = update_memory_from_plan(plan)
        outfit = generate_outfit(plan, memory)
        message = "Got it. I saved this preference to your style memory."

    else:
        outfit = generate_outfit(plan, memory)

    # 3. Return one standard response object to the UI
    return {
        "plan": plan,
        "memory": memory,
        "outfit": outfit,
        "message": message
    }
