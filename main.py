from agent.agent import DesktopAgent


def main() -> None:
    agent = DesktopAgent(model="qwen2.5-coder:7b")
    print("Local desktop agent ready. Type 'exit' to quit.")

    while True:
        user_prompt = input("\n> ").strip()
        if not user_prompt:
            continue
        if user_prompt.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        try:
            response = agent.handle(user_prompt)
            print(response)
        except Exception as exc:  # pragma: no cover - CLI safety
            print(f"Agent error: {exc}")


if __name__ == "__main__":
    main()
