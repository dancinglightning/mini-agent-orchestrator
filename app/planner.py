import json
import logging
import os
import re
import anthropic
from app.models import TaskStep, PlanResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a planning agent. Given a user's natural language request, break it down into a sequence of actionable steps.

Available tools:
- cancel_order(order_id: str): Cancels an order by its ID.
- send_email(email: str, message: str): Sends an email to the given address.

Respond with ONLY a JSON array of steps. Each step must have:
- "step_id": integer starting from 0
- "action": one of the available tool names
- "params": a dict of parameter names to values
- "depends_on": a list of step_ids that must succeed before this step runs

Example response:
[
  {"step_id": 0, "action": "cancel_order", "params": {"order_id": "9921"}, "depends_on": []},
  {"step_id": 1, "action": "send_email", "params": {"email": "user@example.com", "message": "Your order #9921 has been cancelled."}, "depends_on": [0]}
]

Respond with ONLY the JSON array, no markdown, no explanation."""

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def plan(user_message: str) -> PlanResult:
    logger.info("Sending request to Claude for planning")
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        timeout=15.0,
    )
    raw = response.content[0].text.strip()
    logger.debug("Raw LLM response: %s", raw)

    # Strip markdown code fences if the model wraps its output
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence_match:
        raw = fence_match.group(1).strip()

    steps_data = json.loads(raw)
    steps = [TaskStep(**step) for step in steps_data]
    logger.info("Planned %d steps", len(steps))
    return PlanResult(steps=steps)
