import plistlib
from pathlib import Path

import pytest

from agent import uninstaller
from agent.uninstaller import build_uninstall_plan, uninstall_application


def make_app(applications: Path, name: str = "Example App") -> Path:
    app = applications / f"{name}.app"
    info_path = app / "Contents" / "Info.plist"
    info_path.parent.mkdir(parents=True)
    info_path.write_bytes(
        plistlib.dumps(
            {
                "CFBundleIdentifier": "com.example.app",
                "CFBundleName": name,
            }
        )
    )
    return app


def test_plan_includes_app_data_and_preserves_backup_locations(tmp_path):
    applications = tmp_path / "Applications"
    applications.mkdir()
    app = make_app(applications)
    library = tmp_path / "Library"
    support = library / "Application Support" / "com.example.app"
    support.mkdir(parents=True)
    (support / "settings.json").write_text("{}")
    backup_cache = library / "Caches" / "Example App"
    backup_cache.mkdir(parents=True)
    (backup_cache / "profile.backup").write_text("keep")
    preferences = library / "Preferences" / "com.example.app.plist"
    preferences.parent.mkdir(parents=True)
    preferences.write_text("plist")

    plan = build_uninstall_plan(
        "Example App",
        application_dirs=[applications],
        library_dir=library,
    )

    assert plan.app_path == app
    assert plan.data_paths == (support, preferences)
    assert plan.skipped_backup_paths == (backup_cache,)


def test_plan_does_not_match_apps_by_partial_name(tmp_path):
    applications = tmp_path / "Applications"
    applications.mkdir()
    make_app(applications, "Example App Pro")

    with pytest.raises(FileNotFoundError):
        build_uninstall_plan(
            "Example App",
            application_dirs=[applications],
            library_dir=tmp_path / "Library",
        )


def test_plan_preserves_locations_that_cannot_be_scanned(tmp_path, monkeypatch):
    applications = tmp_path / "Applications"
    applications.mkdir()
    make_app(applications)
    library = tmp_path / "Library"
    support = library / "Application Support" / "com.example.app"
    support.mkdir(parents=True)

    def interrupted_walk(path, **kwargs):
        raise OSError("interrupted scan")

    monkeypatch.setattr(uninstaller.os, "walk", interrupted_walk)

    plan = build_uninstall_plan(
        "Example App",
        application_dirs=[applications],
        library_dir=library,
    )

    assert plan.data_paths == ()
    assert plan.skipped_backup_paths == (support,)


def test_uninstall_requires_exact_confirmation(monkeypatch):
    plan = uninstaller.UninstallPlan(
        app_path=Path("/Applications/Example App.app"),
        data_paths=(),
        skipped_backup_paths=(),
    )
    monkeypatch.setattr(uninstaller, "build_uninstall_plan", lambda name: plan)
    monkeypatch.setattr(uninstaller.sys, "platform", "darwin")
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    move_calls = []
    monkeypatch.setattr(uninstaller, "_move_to_trash", move_calls.append)

    result = uninstall_application("Example App")

    assert result == "Uninstall cancelled: confirmation did not match."
    assert move_calls == []


def test_uninstall_moves_app_and_data_to_trash(monkeypatch):
    plan = uninstaller.UninstallPlan(
        app_path=Path("/Applications/Example App.app"),
        data_paths=(Path("/Users/test/Library/Application Support/com.example.app"),),
        skipped_backup_paths=(),
    )
    monkeypatch.setattr(uninstaller, "build_uninstall_plan", lambda name: plan)
    monkeypatch.setattr(uninstaller.sys, "platform", "darwin")
    monkeypatch.setattr("builtins.input", lambda _: "UNINSTALL Example App")
    move_calls = []
    monkeypatch.setattr(uninstaller, "_move_to_trash", move_calls.append)

    result = uninstall_application("Example App")

    assert move_calls == list(plan.paths)
    assert "Moved to Trash:" in result
    assert all(str(path) in result for path in plan.paths)


def test_uninstall_stops_if_app_cannot_be_moved(monkeypatch):
    plan = uninstaller.UninstallPlan(
        app_path=Path("/Applications/Example App.app"),
        data_paths=(Path("/Users/test/Library/Application Support/com.example.app"),),
        skipped_backup_paths=(),
    )
    monkeypatch.setattr(uninstaller, "build_uninstall_plan", lambda name: plan)
    monkeypatch.setattr(uninstaller.sys, "platform", "darwin")
    monkeypatch.setattr("builtins.input", lambda _: "UNINSTALL Example App")

    def fail_to_move(path):
        raise RuntimeError("permission denied")

    monkeypatch.setattr(uninstaller, "_move_to_trash", fail_to_move)

    result = uninstall_application("Example App")

    assert "application was not moved to Trash" in result
    assert str(plan.data_paths[0]) not in result


def test_move_to_trash_passes_path_as_an_argument(monkeypatch, tmp_path):
    app_path = tmp_path / 'App "quoted".app'
    calls = []
    monkeypatch.setattr(uninstaller.shutil, "which", lambda _: "/usr/bin/osascript")

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(uninstaller.subprocess, "run", fake_run)

    uninstaller._move_to_trash(app_path)

    args, kwargs = calls[0]
    assert args[0:2] == ["/usr/bin/osascript", "-e"]
    assert args[2].startswith("on run argv")
    assert args[3] == str(app_path)
    assert kwargs == {"capture_output": True, "text": True}
