from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from config import SYSTEM_PROMPT, get_settings
from tools import TOOL_DEFINITIONS, execute_tool

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key.get_secret_value())


class ResearchAgent:
    def __init__(self) -> None:
        self.settings = settings
        self.messages: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _append(self, role: str, content: str, **extra: Any) -> None:
        message: dict[str, Any] = {"role": role, "content": content}
        message.update(extra)
        self.messages.append(message)

    def _tool_message(self, tool_call_id: str, name: str, content: str) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        }

    def _create_completion(self):
        return client.chat.completions.create(
            model=self.settings.model_name,
            messages=self.messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.2,
        )

    def _safe_parse_tool_arguments(self, raw_arguments: str, tool_name: str) -> tuple[dict[str, Any], str | None]:
        raw_arguments = (raw_arguments or "{}").strip()
        if not raw_arguments:
            return {}, None

        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            return {}, (
                f"Error: invalid JSON arguments for tool '{tool_name}'. "
                f"The model returned malformed or truncated JSON. Raw arguments: {raw_arguments!r}. "
                f"Parser message: {exc.msg} at position {exc.pos}."
            )

        if not isinstance(parsed, dict):
            return {}, (
                f"Error: invalid arguments for tool '{tool_name}'. "
                f"Expected a JSON object, got {type(parsed).__name__}."
            )

        return parsed, None

    def _make_default_report_name(self, user_input: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯіїєІЇЄ_-]+", "_", user_input.strip().lower())
        slug = slug.strip("_")
        if not slug:
            slug = "research_report"
        return f"{slug[:60]}.md"

    def run(self, user_input: str) -> str:
        self._append("user", user_input)

        report_saved = False
        report_path_message = None

        for _ in range(self.settings.max_iterations):
            response = self._create_completion()
            message = response.choices[0].message

            assistant_payload: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                assistant_payload["tool_calls"] = [tool_call.model_dump() for tool_call in message.tool_calls]
            self.messages.append(assistant_payload)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    raw_arguments = tool_call.function.arguments or "{}"
                    print(f"\n🔧 Tool call: {name}({raw_arguments})")

                    arguments, parse_error = self._safe_parse_tool_arguments(raw_arguments, name)
                    if parse_error:
                        result = parse_error
                    else:
                        result = execute_tool(name, arguments)

                    if name == "write_report" and not result.startswith("Error"):
                        report_saved = True
                        report_path_message = result

                    preview = result.replace("\n", " ")[:200]
                    suffix = "..." if len(result) > 200 else ""
                    print(f"📎 Result: {preview}{suffix}")
                    self.messages.append(self._tool_message(tool_call.id, name, result))
                continue

            final_text = (message.content or "").strip()
            if final_text:
                if not report_saved:
                    auto_filename = self._make_default_report_name(user_input)
                    save_result = execute_tool(
                        "write_report",
                        {
                            "filename": auto_filename,
                            "content": final_text,
                        },
                    )
                    print(f"\n🔧 Tool call: write_report({{'filename': '{auto_filename}', 'content': '...'}})")
                    print(f"📎 Result: {save_result}")

                    if not save_result.startswith("Error"):
                        report_saved = True
                        report_path_message = save_result

                if report_path_message and report_path_message not in final_text:
                    final_text = f"{final_text}\n\n{report_path_message}"

                return final_text

        fallback = (
            "Я зупинився через ліміт ітерацій. Спробуйте уточнити запит або звузити тему, "
            "щоб я міг завершити дослідження коротшим циклом."
        )

        if not report_saved:
            auto_filename = self._make_default_report_name(user_input)
            save_result = execute_tool(
                "write_report",
                {
                    "filename": auto_filename,
                    "content": fallback,
                },
            )
            print(f"\n🔧 Tool call: write_report({{'filename': '{auto_filename}', 'content': '...'}})")
            print(f"📎 Result: {save_result}")

            if not save_result.startswith("Error"):
                fallback = f"{fallback}\n\n{save_result}"

        self._append("assistant", fallback)
        return fallback


agent = ResearchAgent()


def new_session_config() -> None:
    agent.reset()