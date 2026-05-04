"""Customer Loyalty specialist."""

from __future__ import annotations

import asyncio

from shared.agent_host import build_agent, serve
from shared.zava_tools import calculate_discount

INSTRUCTIONS = """
You are the Zava Customer Loyalty specialist. Assign discounts based on the
customer's loyalty tier.

- Always require the customer ID; if missing, ask for it.
- Call `calculate_discount` with the customer ID and report the result in
  first person, with celebratory emojis (🎉 😊 🛍️).

Reply in JSON: {"answer": str, "discount_percentage": int}.
""".strip()


async def main() -> None:
    agent = build_agent(
        name="customer-loyalty",
        instructions=INSTRUCTIONS,
        tools=[calculate_discount],
    )
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
