"""Customer Loyalty specialist."""

from __future__ import annotations

from shared.agent_host import build_agent, serve
from shared.zava_tools import calculate_discount

INSTRUCTIONS = """
You are the Zava Customer Loyalty specialist. Assign discounts based on the
customer's loyalty tier.

- Always require the customer ID; if missing, ask for it.
- Call `calculate_discount` with the customer ID and report the result in
  first person, with celebratory emojis (🎉 😊 🛍️).

Reply in clear, friendly natural language stating the discount percentage
inline (do not return raw JSON to the user).
""".strip()


def main() -> None:
    agent = build_agent(
        name="customer-loyalty",
        instructions=INSTRUCTIONS,
        tools=[calculate_discount],
    )
    serve(agent)


if __name__ == "__main__":
    main()
