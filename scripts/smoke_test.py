"""Quick smoke test for hosted agents using AIProjectClient.get_openai_client.

Usage:
    # Single prompt (default agent: cora)
    python scripts/smoke_test.py cora "Hi! What can you help me with?"

    # Scripted multi-turn shopping conversation against cora (paint scenario)
    python scripts/smoke_test.py --script
    python scripts/smoke_test.py --script cora
"""
import os
import sys
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


# Scripted multi-turn shopping conversation. Threaded via previous_response_id so
# Cora keeps context across turns (cart contents, paint chosen, etc.).
SCRIPTED_TURNS = [
    "What colors of green paint do you have?",
    "I think I'm interested in Deep Forest. How many gallons would I need to paint a medium sized bedroom?",
    "How much of PROD0018 do you have in stock?",
    "Let's add two gallons to the cart, please.",
    "Please also add one paint tray and two of your All-Purpose Wall Paint Brushes.",
    "What items are in my cart right now?",
    "I'd like to check out now.",
]


def _print_response(resp) -> None:
    text = getattr(resp, "output_text", None)
    if text:
        print(text)
    else:
        print(resp.model_dump_json(indent=2))
    for item in getattr(resp, "output", []) or []:
        item_type = getattr(item, "type", None) or ""
        name = getattr(item, "name", None)
        if ("function_call" in item_type or "tool" in item_type) and name:
            args = getattr(item, "arguments", "")
            print(f"  [tool] {name} {args}")


def _client(agent_name: str):
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    project = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    return project.get_openai_client(agent_name=agent_name)


def run_single(agent_name: str, prompt: str) -> None:
    client = _client(agent_name)
    resp = client.responses.create(input=prompt)
    print("=== raw response ===")
    print(resp.model_dump_json(indent=2))


def run_script(agent_name: str) -> None:
    client = _client(agent_name)
    previous_id = None
    for i, prompt in enumerate(SCRIPTED_TURNS, 1):
        print(f"\n=== Turn {i}/{len(SCRIPTED_TURNS)} - user ===")
        print(prompt)
        kwargs = {"input": prompt}
        if previous_id:
            kwargs["previous_response_id"] = previous_id
        resp = client.responses.create(**kwargs)
        previous_id = getattr(resp, "id", None)
        print(f"--- {agent_name} ---")
        _print_response(resp)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--script":
        agent = args[1] if len(args) > 1 else "cora"
        run_script(agent)
        return
    name = args[0] if len(args) > 0 else "cora"
    msg = args[1] if len(args) > 1 else "Hi! Briefly, what can you help me with?"
    run_single(name, msg)


if __name__ == "__main__":
    main()
