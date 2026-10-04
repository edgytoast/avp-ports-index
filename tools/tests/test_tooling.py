"""Bootstrap re-runs (U16), the main writer's push retry (U9) and the copy rules (spec §4)."""

from __future__ import annotations

import re
import subprocess
import sys

import pytest
from conftest import INDEX, REPO_ROOT, FakeGitHub, git

from avpindex import writer
from avpindex.runtime import Runtime

sys.path.insert(0, str(REPO_ROOT / "tools"))
import bootstrap_repo  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data if data is not None else {}
        self.content = b"x"

    def json(self):
        return self._data


class FakeApi:
    """Records calls; remembers which secrets and rulesets exist."""

    def __init__(self):
        self.calls = []
        self.secret_names = set()
        self.rulesets = []
        self.variables = {}

    def call(self, method, path, body=None, *, ok=(), token=None):
        self.calls.append((method, path))
        if path.endswith("/actions/secrets/public-key") or path.endswith("/secrets/public-key"):
            from nacl import encoding, public
            key = public.PrivateKey.generate().public_key.encode(encoding.Base64Encoder()).decode()
            return FakeResponse(data={"key": key, "key_id": "1"})
        if "/actions/secrets?" in path:
            return FakeResponse(data={"secrets": [{"name": n} for n in self.secret_names]})
        if method == "PUT" and "/actions/secrets/" in path:
            self.secret_names.add(path.rsplit("/", 1)[1])
        if path.endswith("/rulesets") and method == "GET":
            return FakeResponse(data=self.rulesets)
        if path.endswith("/rulesets") and method == "POST":
            self.rulesets.append({"id": 1, "name": body["name"]})
        if path.startswith("/users/"):
            return FakeResponse(data={"id": 146565462})
        if "/actions/variables?" in path:
            return FakeResponse(data={"variables": [{"name": k, "value": v} for k, v in self.variables.items()]})
        if method in ("POST", "PATCH") and "/actions/variables" in path:
            self.variables[body["name"]] = body["value"]
        if path.endswith("/labels?per_page=100"):
            return FakeResponse(data=[])
        if "deployment-branch-policies" in path and method == "GET":
            return FakeResponse(data={"branch_policies": []})
        return FakeResponse()

    def json(self, method, path, body=None, **kw):
        return self.call(method, path, body, **kw).json()


def test_bootstrap_rerun_keeps_salt_and_skip_ruleset(monkeypatch):
    """U16."""
    api = FakeApi()
    creds = {"owner_pat": "x", "app_id": "777", "app_key": "pem", "outreach_pat": "o", "jules_api_key": "j"}
    boot = bootstrap_repo.Bootstrap(api, INDEX, creds, log=lambda *_: None)
    monkeypatch.setattr(boot, "app_info", lambda: {"id": 777, "client_id": "Iv1.x", "slug": "trevorbilt-index"})
    monkeypatch.setattr(type(boot), "has_key", property(lambda self: True))
    boot.run(skip_ruleset=True, health=False)
    salt_puts = [c for c in api.calls if c == ("PUT", f"/repos/{INDEX}/actions/secrets/BLOCKLIST_SALT")]
    assert len(salt_puts) == 1 and api.rulesets == []
    api.variables["STAGE2_ENABLED"] = "false"  # the owner paused Stage 2
    boot.run(skip_ruleset=False, health=False)
    salt_puts = [c for c in api.calls if c == ("PUT", f"/repos/{INDEX}/actions/secrets/BLOCKLIST_SALT")]
    assert len(salt_puts) == 1 and len(api.rulesets) == 1
    assert api.variables["STAGE2_ENABLED"] == "false" and api.variables["OWNER_ID"] == "146565462"


@pytest.fixture
def cloned(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    (work / "state").mkdir()
    (work / "state/a.yaml").write_text("1")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "init")
    git(work, "push", "-q", "origin", "main")
    return work


def test_push_retry(cloned, monkeypatch):
    """U9: a rejected push retries and lands; three rejections open an owner issue."""
    gh = FakeGitHub()
    results = [False, True]
    gh.create_commit = lambda parent, changes, message: "c" * 40
    gh.fast_forward = lambda branch, sha: results.pop(0)
    rt = Runtime(repo=INDEX, gh=gh, root=cloned)
    monkeypatch.setattr("avpindex.generate.generate", lambda root, repo: None)
    attempts = []

    def mutate():
        attempts.append(1)
        (cloned / "state/a.yaml").write_text(str(len(attempts) + 1))
        (cloned / "out").mkdir(exist_ok=True)
        (cloned / "out/outcome.json").write_text("{}")  # never committed

    seen = []
    gh.create_commit = lambda parent, changes, message: seen.append(sorted(changes)) or "c" * 40
    assert writer.commit_main(rt, mutate, "state: x") == "c" * 40
    assert len(attempts) == 2 and seen[-1] == ["state/a.yaml"]
    gh.fast_forward = lambda branch, sha: False
    with pytest.raises(RuntimeError):
        writer.commit_main(rt, mutate, "state: y")
    assert any(i["title"] == "Writing to main failed" for i in gh.issue_store.values())


USER_FACING = ["templates", "brand/brand.yaml", "CONTRIBUTING.md", "SECURITY.md", "README.md", "llms.txt", "docs/feed.md",
               "docs/trust-tiers.md", "skills/avp-index-submit/SKILL.md", "skills/avp-index-submit/assets",
               ".github/ISSUE_TEMPLATE", ".github/PULL_REQUEST_TEMPLATE.md"]


def user_facing_files():
    for rel in USER_FACING:
        path = REPO_ROOT / rel
        if path.is_dir():
            yield from (p for p in path.rglob("*") if p.is_file())
        elif path.exists():
            yield path


def test_copy_rules():
    """No em dashes, and never "seamless", "reimagine" or "unprecedented" (spec §4)."""
    files = list(user_facing_files())
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, f"em dash in {path}"
        assert not re.search(r"seamless|reimagin|unprecedented", text, re.I), path


def test_entry_template_is_valid():
    import jsonschema
    import yaml
    template = yaml.safe_load((REPO_ROOT / "skills/avp-index-submit/assets/entry.template.yaml").read_text())
    schema = __import__("json").loads((REPO_ROOT / "schema/entry.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(template)


def test_changed_files_keeps_modes_and_skips_other_paths(cloned):
    script = cloned / "skills/avp-index-submit/scripts/preflight.py"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env python3\n")
    script.chmod(0o755)
    (cloned / "scratch.txt").write_text("x")
    changes = writer.changed_files(cloned)
    assert changes == {"skills/avp-index-submit/scripts/preflight.py": (b"#!/usr/bin/env python3\n", "100755")}
