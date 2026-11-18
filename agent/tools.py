import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict

from .uninstaller import uninstall_application


class ToolRegistry:
    """Registry of safe desktop tools for the local agent."""

    def __init__(self):
        self.tools: Dict[str, Callable[..., Any]] = {
            "open_app": self.open_app,
            "open_application": self.open_app,
            "list_files": self.list_files,
            "list_folder": self.list_files,
            "take_screenshot": self.take_screenshot,
            "open_path": self.open_path,
            "say": self.say,
            "create_timeline": self.create_timeline,
            "create_project": self.create_project,
            "export_video": self.export_video,
            "resolve_status": self.resolve_status,
            "open_resolve": self.open_resolve,
            "resolve_open": self.open_resolve,
            "resolve_create_project": self.create_project,
            "resolve_create_timeline": self.create_timeline,
            "resolve_import_media": self.import_media,
            "resolve_add_title": self.add_title,
            "resolve_export_video": self.export_video,
            "resolve_verify": self.resolve_verify,
            "uninstall_application": uninstall_application,
            "uninstall_app": uninstall_application,
        }

    @staticmethod
    def open_app(app_name: str = "DaVinci Resolve") -> str:
        if not app_name:
            app_name = "DaVinci Resolve"
        app_name = app_name.strip() or "DaVinci Resolve"
        if shutil.which("open") is None:
            return "The macOS 'open' command is not available."
        result = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Failed to open '{app_name}': {result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        return f"Opened '{app_name}'."

    @staticmethod
    def list_files(folder: str) -> str:
        path = Path(folder).expanduser()
        if not path.exists():
            return f"Folder does not exist: {folder}"
        try:
            items = sorted(p.name for p in path.iterdir())
            return json.dumps({"folder": str(path), "items": items[:50]})
        except Exception as exc:  # pragma: no cover - defensive
            return f"Could not list files: {exc}"

    @staticmethod
    def take_screenshot(output_path: str = "~/Desktop/agent_screenshot.png") -> str:
        file_path = Path(output_path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(["screencapture", "-x", str(file_path)], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Failed to capture screenshot: {result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        return f"Screenshot saved to {file_path}"

    @staticmethod
    def open_path(path: str) -> str:
        if not path:
            return "No path supplied."
        target = Path(path).expanduser()
        if not target.exists():
            return f"Path does not exist: {path}"
        result = subprocess.run(["open", str(target)], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Failed to open path '{path}': {result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        return f"Opened path '{path}'."

    @staticmethod
    def say(message: str) -> str:
        return message

    @staticmethod
    def create_timeline(name: str = "New Timeline") -> str:
        return f"Timeline action requested: '{name}'. Ready for Resolve automation to add clips and edits."

    @staticmethod
    def create_project(name: str = "Agent Project") -> str:
        return f"Project creation requested: '{name}'. This is the next Resolve action to trigger a project setup."

    @staticmethod
    def import_media(folder: str = "~/Desktop") -> str:
        target = Path(folder).expanduser()
        if not target.exists():
            return f"Media folder not found: {folder}"
        items = sorted(p.name for p in target.iterdir())[:20]
        return json.dumps({"folder": str(target), "media_items": items})

    @staticmethod
    def add_title(title: str = "Project Title") -> str:
        return f"Title added: '{title}'. Resolve-specific UI automation can place this on the timeline next."

    @staticmethod
    def export_video(output_path: str = "~/Desktop/exported_project.mp4") -> str:
        final_path = Path(output_path).expanduser()
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.touch(exist_ok=True)
        return f"Export requested. Ready to trigger DaVinci Resolve export to {final_path}."

    @staticmethod
    def resolve_status() -> str:
        app_name = "DaVinci Resolve"
        result = subprocess.run(["open", "-Ra", app_name], capture_output=True, text=True)
        if result.returncode == 0:
            return f"{app_name} is installed and available."
        return f"{app_name} is not detected as an installed app on this machine."

    @staticmethod
    def open_resolve(app_name: str = "DaVinci Resolve") -> str:
        return ToolRegistry.open_app(app_name=app_name)

    @staticmethod
    def resolve_verify() -> str:
        return "Verification step ready: capture a screenshot and confirm the app state before the next action."

    def execute(self, tool_name: str, **kwargs) -> str:
        normalized_name = (tool_name or "").strip()
        alias_map = {
            "open_application": "open_app",
            "open_app": "open_app",
            "list_folder": "list_files",
            "list_files": "list_files",
            "take_screenshot": "take_screenshot",
            "open_path": "open_path",
            "say": "say",
            "create_timeline": "create_timeline",
            "create_project": "create_project",
            "export_video": "export_video",
            "resolve_status": "resolve_status",
            "open_resolve": "open_resolve",
            "resolve_open": "open_resolve",
            "resolve_create_project": "create_project",
            "resolve_create_timeline": "create_timeline",
            "resolve_import_media": "import_media",
            "resolve_add_title": "add_title",
            "resolve_export_video": "export_video",
            "resolve_verify": "resolve_verify",
            "uninstall_application": "uninstall_application",
            "uninstall_app": "uninstall_application",
        }
        resolved_name = alias_map.get(normalized_name, normalized_name)
        if resolved_name not in self.tools:
            return f"Tool not found: {tool_name}"
        try:
            return str(self.tools[resolved_name](**kwargs))
        except TypeError as exc:
            return f"Tool call failed because arguments were wrong: {exc}"
        except Exception as exc:  # pragma: no cover
            return f"Tool execution error: {exc}"
