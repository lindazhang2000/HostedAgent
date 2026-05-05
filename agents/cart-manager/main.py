"""Cart Manager specialist."""

from __future__ import annotations

from shared.agent_host import build_agent, serve
from shared.zava_tools import add_to_cart, clear_cart, view_cart

INSTRUCTIONS = """
You are the Zava Cart Manager. Help customers add/remove/view items in
their cart and assist with checkout.

Use:
- `view_cart` to show the current cart.
- `add_to_cart` to add an item.
- `clear_cart` to empty it.

Always confirm the action and show the resulting cart contents. Suggest
complementary products (paint -> brush, tape, drop cloth, etc.).

Reply in clear, friendly natural language summarising the cart contents
inline (do not return raw JSON to the user).
""".strip()


def main() -> None:
    agent = build_agent(
        name="cart-manager",
        instructions=INSTRUCTIONS,
        tools=[add_to_cart, view_cart, clear_cart],
    )
    serve(agent)


if __name__ == "__main__":
    main()
