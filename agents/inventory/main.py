"""Inventory specialist."""

from __future__ import annotations

from shared.agent_host import build_agent, serve
from shared.zava_tools import inventory_check

INSTRUCTIONS = """
You are the Zava Inventory specialist. When a user asks about stock for one
or more products, call `inventory_check` with the matching product IDs and
report stock levels and warehouse locations.

Reply in clear, friendly natural language listing each item with its stock
count and warehouse location (do not return raw JSON to the user).
""".strip()


def main() -> None:
    agent = build_agent(
        name="inventory",
        instructions=INSTRUCTIONS,
        tools=[inventory_check],
    )
    serve(agent)


if __name__ == "__main__":
    main()
