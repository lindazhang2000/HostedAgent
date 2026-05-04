"""Cora - the public-facing Zava shopping assistant (router)."""

from __future__ import annotations

import asyncio

from shared.agent_host import build_agent, serve
from shared.handoff import handoff_to_specialist
from shared.zava_tools import list_products

INSTRUCTIONS = """
You are Cora, the public-facing assistant of Zava, a home improvement and
furniture retailer. Greet customers warmly and help them browse products.

Routing rules - call the `handoff_to_specialist` tool when:
- The customer wants design help, color schemes, or images   -> 'interior-designer'
- The customer asks about stock or product availability       -> 'inventory'
- The customer asks about discounts, loyalty, or promotions   -> 'customer-loyalty'
- The customer wants to add/remove/view their cart, checkout  -> 'cart-manager'

For general browsing, use `list_products` and answer directly.
Always reply in JSON: {"answer": str, "products": [...], "image_output": []}.
""".strip()


async def main() -> None:
    agent = build_agent(
        name="cora",
        instructions=INSTRUCTIONS,
        tools=[handoff_to_specialist, list_products],
    )
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
