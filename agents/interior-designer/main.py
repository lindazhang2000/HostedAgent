"""Interior Design specialist for Zava."""

from __future__ import annotations

from shared.agent_host import build_agent, serve
from shared.zava_tools import list_products

INSTRUCTIONS = """
You are an Interior Designer working for Zava. Help customers with DIY
projects and interior-design questions.

Tasks:
- Recommend and upsell products (use `list_products` for the catalog).
- Ask follow-up questions about room style, color palette, and budget.
- Recommend only products returned by the tool.

Reply in clear, friendly natural language. When you mention products,
include the product name and price inline in the sentence (do not return
raw JSON to the user).
""".strip()


def main() -> None:
    agent = build_agent(
        name="interior-designer",
        instructions=INSTRUCTIONS,
        tools=[list_products],
    )
    serve(agent)


if __name__ == "__main__":
    main()
