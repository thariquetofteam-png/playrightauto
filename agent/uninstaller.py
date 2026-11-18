import os
import plistlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class UninstallPlan:
    app_path: Path
    data_paths: Tuple[Path, ...]
    skipped_backup_paths: Tuple[Path, ...]

    @property
    def paths(self) -> Tuple[Path, ...]:
        return (self.app_path, *self.data_paths)


_SUPPORT_LOCATIONS = (
    "Application Support",
    "Caches",
    "Preferences",
    "Logs",
    "Containers",
    "Saved Application State",
    "WebKit",
    "HTTPStorages",
    "Cookies",
)
_BACKUP_SUFFIXES = (".bak", ".backup", ".old", ".orig", ".save", ".swp")


def _normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _is_backup_name(name: str) -> bool:
    lowered = name.casefold()
    return (
        "backup" in lowered
        or lowered.endswith(_BACKUP_SUFFIXES)
        or lowered.endswith("~")
    )


def _contains_backup(path: Path) -> bool:
    if _is_backup_name(path.name):
        return True
    if not path.is_dir():
        return False

    def raise_walk_error(error: OSError) -> None:
        raise error

    try:
        for root, directories, files in os.walk(
            path,
            followlinks=False,
            onerror=raise_walk_error,
        ):
            if any(_is_backup_name(name) for name in directories + files):
                return True
    except OSError:
        return True
    return False


def _within(path: Path, root: Path) -> bool:
    if path.is_symlink():
        return False
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def build_uninstall_plan(
    app_name: str,
    application_dirs: Optional[Sequence[Path]] = None,
    library_dir: Optional[Path] = None,
) -> UninstallPlan:
    if not app_name or not app_name.strip():
        raise ValueError("An application name is required.")

    requested_name = app_name.strip()
    requested_stem = requested_name[:-4] if requested_name.casefold().endswith(".app") else requested_name
    requested_key = _normalized_name(requested_stem)
    if application_dirs is None:
        application_dirs = (Path("/Applications"), Path.home() / "Applications")

    matches: List[Path] = []
    for directory in application_dirs:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if (
                path.is_dir()
                and path.name.casefold().endswith(".app")
                and _normalized_name(path.name[:-4]) == requested_key
                and _within(path, directory)
            ):
                matches.append(path)

    if not matches:
        raise FileNotFoundError(
            f"Could not find '{requested_name}' in /Applications or ~/Applications. "
            "System applications are not eligible for removal."
        )
    if len(matches) > 1:
        locations = "\n".join(f"- {path}" for path in sorted(matches))
        raise ValueError(f"More than one app matches '{requested_name}':\n{locations}")

    app_path = matches[0]
    info_path = app_path / "Contents" / "Info.plist"
    try:
        with info_path.open("rb") as info_file:
            info = plistlib.load(info_file)
    except (OSError, plistlib.InvalidFileException, ValueError) as exc:
        raise RuntimeError(f"Could not read app metadata at {info_path}: {exc}") from exc
    if not isinstance(info, dict):
        raise RuntimeError(f"App metadata at {info_path} is not a dictionary.")

    bundle_id = info.get("CFBundleIdentifier")
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        raise RuntimeError(f"The app bundle identifier is missing from {info_path}.")

    app_display_name = info.get("CFBundleName")
    aliases = {
        _normalized_name(requested_stem),
        _normalized_name(app_path.name[:-4]),
        _normalized_name(bundle_id),
    }
    if isinstance(app_display_name, str) and app_display_name.strip():
        aliases.add(_normalized_name(app_display_name))

    if library_dir is None:
        library_dir = Path.home() / "Library"

    data_paths: List[Path] = []
    skipped_backup_paths: List[Path] = []
    for location in _SUPPORT_LOCATIONS:
        root = library_dir / location
        if not root.is_dir():
            continue
        for path in root.iterdir():
            key = _normalized_name(path.name)
            if path.is_file() and path.suffix.casefold() == ".plist":
                key = _normalized_name(path.stem)
            elif path.name.casefold().endswith(".savedstate"):
                key = _normalized_name(path.name[:-11])
            if key not in aliases or not _within(path, root):
                continue
            if _contains_backup(path):
                skipped_backup_paths.append(path)
            else:
                data_paths.append(path)

    return UninstallPlan(
        app_path=app_path,
        data_paths=tuple(sorted(set(data_paths))),
        skipped_backup_paths=tuple(sorted(set(skipped_backup_paths))),
    )


def _move_to_trash(path: Path) -> None:
    osascript = shutil.which("osascript")
    if osascript is None:
        raise RuntimeError("The macOS osascript command is not available.")

    script = (
        'on run argv\n'
        '    tell application "Finder" to delete (POSIX file (item 1 of argv) as alias)\n'
        'end run'
    )
    result = subprocess.run(
        [osascript, "-e", script, str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"Could not move '{path}' to Trash: {message}")


def uninstall_application(app_name: str) -> str:
    if sys.platform != "darwin":
        return "Application uninstall is currently supported only on macOS."

    plan = build_uninstall_plan(app_name)
    print(f"Uninstall preview for {app_name}:")
    for path in plan.paths:
        print(f"- {path}")
    if plan.skipped_backup_paths:
        print("Backup-containing or unreadable locations will be preserved:")
        for path in plan.skipped_backup_paths:
            print(f"- {path}")

    expected_confirmation = f"UNINSTALL {app_name.strip()}"
    try:
        confirmation = input(
            f"Type '{expected_confirmation}' to move these items to Trash: "
        ).strip()
    except EOFError:
        return "Uninstall cancelled: no interactive confirmation was available."
    if confirmation != expected_confirmation:
        return "Uninstall cancelled: confirmation did not match."

    try:
        _move_to_trash(plan.app_path)
    except (OSError, RuntimeError) as exc:
        return f"Uninstall stopped; the application was not moved to Trash: {exc}"

    moved = [plan.app_path]
    failures = []
    for path in plan.data_paths:
        try:
            _move_to_trash(path)
            moved.append(path)
        except (OSError, RuntimeError) as exc:
            failures.append(f"{path}: {exc}")

    result = "Moved to Trash:\n" + "\n".join(f"- {path}" for path in moved)
    if plan.skipped_backup_paths:
        result += "\nPreserved backup-containing or unreadable locations:\n" + "\n".join(
            f"- {path}" for path in plan.skipped_backup_paths
        )
    if failures:
        result += "\nCould not move:\n" + "\n".join(f"- {failure}" for failure in failures)
    return result
