"""Interior Design specialist for Zava."""

from __future__ import annotations

import asyncio

from shared.agent_host import build_agent, serve
from shared.zava_tools import list_products

INSTRUCTIONS = """
You are an Interior Designer working for Zava. Help customers with DIY
projects and interior-design questions.

Tasks:
- Recommend and upsell products (use `list_products` for the catalog).
- Ask follow-up questions about room style, color palette, and budget.
- Recommend only products returned by the tool.

Reply in JSON:
{"answer": str, "image_output": [], "products": [{"id": str, "name": str,
"type": str, "description": str, "price": str}]}
""".strip()


async def main() -> None:
    agent = build_agent(
        name="interior-designer",
        instructions=INSTRUCTIONS,
        tools=[list_products],
    )
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
