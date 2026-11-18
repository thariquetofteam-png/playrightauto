import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .tools import ToolRegistry


class DesktopAgent:
    """A lightweight local-agent controller for desktop tasks using Ollama."""

    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.tools = ToolRegistry()

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "The local Ollama model server is not running. Start it with: ollama serve"
            ) from exc

    def call_model(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a local desktop agent. "
                        "Return a JSON object with a 'plan' and optional 'tool_calls'. "
                        "Use only the tools available in this environment. "
                        "Available tool names: open_app, open_application, list_files, list_folder, take_screenshot, open_path, say, create_project, create_timeline, export_video, resolve_status, open_resolve, resolve_open, resolve_create_project, resolve_create_timeline, resolve_import_media, resolve_add_title, resolve_export_video, resolve_verify, uninstall_application. "
                        "Do not invent unavailable tools. "
                        "For uninstall requests, use uninstall_application with the exact installed app name; it previews locations and requires exact interactive confirmation before moving anything to Trash. "
                        "If the user asks to open an app, call open_app with {'app_name': 'DaVinci Resolve'} or another installed app name. "
                        "If the user wants Resolve actions, prefer resolve_open, resolve_create_project, resolve_create_timeline, resolve_import_media, resolve_add_title, resolve_export_video, and resolve_verify. "
                        "When a required argument is not provided, use the default sensible value such as 'DaVinci Resolve' for app_name, 'Agent Project' for project name, or the desktop path for screenshots. "
                        "Keep the plan concise and practical."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.2},
        }
        result = self._post(payload)
        message = result.get("message", {}).get("content", "")
        return message.strip()

    @staticmethod
    def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            payload = match.group(1)
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                pass

        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _extract_named_value(prompt: str, phrases: List[str]) -> Optional[str]:
        prompt_lower = prompt.lower()
        for phrase in phrases:
            if phrase.lower() in prompt_lower:
                pattern = rf"{re.escape(phrase)}\s*(?:called|named|is|=|:)?\s*['\"]?([A-Za-z0-9 _-]+)"
                match = re.search(pattern, prompt, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None

    def _enrich_tool_args(self, tool_name: str, args: Dict[str, Any], user_prompt: str) -> Dict[str, Any]:
        result = dict(args)

        if tool_name in {"open_app", "open_application", "open_resolve", "resolve_open"}:
            if "app_name" not in result and "app" not in result:
                app_name = self._extract_named_value(user_prompt, ["DaVinci Resolve", "Resolve", "Final Cut Pro", "Photoshop"])
                if app_name:
                    result["app_name"] = app_name

        if tool_name in {"create_project", "resolve_create_project"}:
            if "name" not in result and "project_name" not in result:
                project_name = self._extract_named_value(user_prompt, ["project", "project called", "project named"])
                if project_name:
                    result["name"] = project_name

        if tool_name in {"create_timeline", "resolve_create_timeline"}:
            if "name" not in result and "timeline_name" not in result:
                timeline_name = self._extract_named_value(user_prompt, ["timeline", "timeline called", "timeline named"])
                if timeline_name:
                    result["name"] = timeline_name

        return result

    def handle(self, user_prompt: str) -> str:
        try:
            model_response = self.call_model(user_prompt)
        except RuntimeError as exc:
            return str(exc)

        payload = self._extract_json_block(model_response) or {
            "plan": ["No structured plan returned by the model."],
            "tool_calls": [],
        }
        plan = payload.get("plan", [])
        tool_calls = payload.get("tool_calls", [])

        if not isinstance(plan, list):
            plan = [str(plan)]

        if not isinstance(tool_calls, list):
            tool_calls = [tool_calls]

        tool_outputs = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            tool_name = call.get("name")
            args = call.get("arguments", {}) or {}
            if not tool_name:
                continue
            args = self._enrich_tool_args(tool_name, args, user_prompt)
            result = self.tools.execute(tool_name, **args)
            tool_outputs.append({"tool": tool_name, "result": result})

        if not tool_outputs:
            return "Plan:\n- " + "\n- ".join(plan) + "\n\nNo tool calls were triggered."

        summary = "Plan:\n- " + "\n- ".join(plan) + "\n\nExecuted tools:\n"
        for item in tool_outputs:
            summary += f"- {item['tool']}: {item['result']}\n"
        return summary.strip()
