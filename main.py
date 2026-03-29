from agent import agent, new_session_config
from config import APP_TITLE, SEPARATOR


def main() -> None:
    print(APP_TITLE)
    print("Type your question and press Enter.")
    print("Commands: 'exit' / 'quit' to leave,")
    print("          'new' to start a fresh conversation.")
    print(SEPARATOR)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"exit", "quit"}:
            print("Goodbye!")
            break

        if lowered == "new":
            new_session_config()
            print("\nStarted a fresh conversation.")
            continue

        try:
            answer = agent.run(user_input)
            print(f"\nAgent:\n{answer}")
        except Exception as exc:
            print(f"\nAgent error: {exc}")


if __name__ == "__main__":
    main()
