import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_script("release_gate")
distribution = load_script("check_distribution")


@pytest.mark.parametrize(
    "product",
    [
        {"stage": "unreleased-preparation", "release_authorized": False},
        {"stage": "release-ready", "release_authorized": False},
        {"stage": "release-ready", "release_authorized": "true"},
    ],
)
def test_preparation_cannot_pass_publish_gate(product):
    with pytest.raises(ValueError, match="preparation-only"):
        gate.validate_publish_state("0.2.0", product, "## 0.2.0 — 2026-09-17", "Ready")


def test_publication_requires_finalized_versioned_docs():
    state = {"stage": "release-ready", "release_authorized": True}
    for changelog in ("## 0.2.0 — unreleased", "## 0.3.0 — 2026-09-17"):
        with pytest.raises(ValueError, match="dated entry"):
            gate.validate_publish_state("0.2.0", state, changelog, "Ready")
    with pytest.raises(ValueError, match="banner"):
        gate.validate_publish_state(
            "0.2.0", state, "## 0.2.0 — 2026-09-17", "0.2.0 is in release preparation"
        )
    gate.validate_publish_state(
        "0.2.0", state, "## 0.2.0 — 2026-09-17", "Install the released package"
    )


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/absolute",
        "a\\..\\secret",
        "pkg/.env",
        "pkg/.env.production",
        "pkg/.gemini/settings.json",
        "pkg/.venv/config",
    ],
)
def test_distribution_rejects_private_or_unsafe_paths(path):
    with pytest.raises(ValueError):
        distribution.check_paths([path])


def test_distribution_allows_documented_environment_template():
    distribution.check_paths(["pkg/.env.example", "pkg/src/cite_nexus_mcp/server.py"])


def test_publication_directory_cannot_mix_plugin_or_stale_archives(tmp_path):
    for name in (
        "cite_nexus_mcp-0.2.0-py3-none-any.whl",
        "cite_nexus_mcp-0.2.0.tar.gz",
        "plugin.zip",
    ):
        (tmp_path / name).write_bytes(b"")
    with pytest.raises(ValueError, match="exactly"):
        distribution.inspect(tmp_path, "0.2.0")


@pytest.mark.parametrize("case", ["approved", "lightweight", "wrong_head"])
def test_publication_tag_identity_in_disposable_repository(tmp_path, monkeypatch, case):
    def git(*args):
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=Release Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgsign=false",
                *args,
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    (tmp_path / "release").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n')
    (tmp_path / "server.json").write_text(
        json.dumps({"version": "0.2.0", "packages": [{"version": "0.2.0"}]})
    )
    (tmp_path / "release/product.json").write_text(
        json.dumps({"stage": "release-ready", "release_authorized": True})
    )
    (tmp_path / "CHANGELOG.md").write_text("## 0.2.0 — 2026-09-17\n")
    (tmp_path / "README.md").write_text("Install the release\n")
    git("init", "--initial-branch=master")
    git("add", ".")
    git("commit", "-m", "Reviewed fixture")
    git("update-ref", "refs/remotes/origin/master", "HEAD")
    if case == "lightweight":
        git("tag", "v0.2.0")
    else:
        git("tag", "-a", "v0.2.0", "-m", "Release fixture")
    if case == "wrong_head":
        git("commit", "--allow-empty", "-m", "Different commit")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["release_gate.py", "--tag", "v0.2.0"])
    if case == "approved":
        gate.main()
    else:
        with pytest.raises(SystemExit, match="annotated tag|HEAD is not"):
            gate.main()
