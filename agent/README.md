# Local Desktop Agent Starter

This project creates a lightweight local agent that talks to Ollama and can call safe desktop tools.

## What it does

- Sends the user's prompt to a local Ollama model
- Requests a structured JSON plan plus tool calls
- Executes tool calls such as opening an app, taking a screenshot, and listing files
- Can uninstall a macOS app after showing a preview and requiring exact confirmation
- Gives the user a working foundation for a desktop automation workflow

## Uninstalling a macOS app

Ask the agent to uninstall an app by its installed name. The uninstall tool only
considers apps in `/Applications` and `~/Applications`, then previews the app and
matching app-specific data in the current user's Library. It preserves any
matching location containing backup-named files, as well as locations it cannot
fully inspect, excludes system apps and
shared/system-wide data, and moves approved items to Trash instead of permanently
deleting them. Confirm each uninstall by typing the exact `UNINSTALL <app name>`
phrase shown in the terminal. A cancelled or unavailable confirmation does not
remove anything.

The tool currently supports macOS only. It does not remove package-manager
receipts or attempt to stop a running application.

## Run it

```bash
source venv/bin/activate
python main.py
```

## Example prompts

- Open DaVinci Resolve
- Take a screenshot of the desktop
- Open my project folder
- Create a new timeline named 'Launch Reel'

## Notes

This is a starter scaffold, not a full Jarvis-level automation system. The next step is wiring in app-specific automation for DaVinci Resolve using AppleScript, UI automation, or Resolve scripting hooks.
