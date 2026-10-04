#!/usr/bin/env python3
"""Apply the repository configuration in spec §7 to one index repo, idempotently.

    python tools/bootstrap_repo.py --repo edgytoast/avp-ports-index-staging --skip-ruleset
    python tools/bootstrap_repo.py --repo edgytoast/avp-ports-index-staging

Credentials are read from files in AVP_SECRETS_DIR (default ~/.config/avp-index): owner_pat,
app_id, app.pem, outreach_pat, jules_api_key. AVP_OWNER_TOKEN (for example `gh auth token`) can
stand in for owner_pat. Values are never printed. Steps whose credentials aren't there yet are
skipped and listed at the end, so the script can be run again once they are.

Re-running is safe: BLOCKLIST_SALT is created only if it doesn't exist yet (a new salt would
silently unblock everything), the Stage 2 and auto-merge switches are created only if missing
(so a re-run never undoes the owner's pause), and the ruleset and labels are updated in place.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path

import requests

API = "https://api.github.com"
HERE = Path(__file__).resolve().parent

LABELS = {
    "stage1:pass": ("2da44e", "Stage 1 checks passed"),
    "stage1:fail": ("d1242f", "Stage 1 found something to fix"),
    "stage1:route": ("bf8700", "Stage 1 sent this to the curator"),
    "stage2:queued": ("0969da", "Waiting for the automated security review"),
    "stage2:scanning": ("8250df", "Automated security review in progress"),
    "stage2:pass": ("2da44e", "Automated security review passed"),
    "stage2:flagged": ("cf222e", "The automated review asked for a closer look"),
    "needs-author": ("fbca04", "Waiting for the contributor"),
    "needs-owner": ("ED7014", "Waiting for the curator"),
    "owner:scan": ("ED7014", "Curator: waive routes and scan this PR"),
    "blocklist": ("000000", "Curator: block this repo and close"),
    "report": ("d93f0b", "Report about an entry"),
    "takedown": ("b60205", "Takedown request"),
    "appeal": ("5319e7", "Appeal of a decision"),
    "triage": ("c5def5", "Needs the curator"),
    "kill-switch": ("b60205", "Curator: pull this entry"),
    "health-tracking": ("0e8a16", "Daily health notes"),
}
SWITCHES = {"AUTO_MERGE_ENABLED": "true", "STAGE2_ENABLED": "true"}
APP_SLUG = "trevorbilt-index"


class Api:
    def __init__(self, token: str, session: requests.Session | None = None):
        self.http = session or requests.Session()
        self.token = token

    def call(self, method: str, path: str, body: object = None, *, ok: tuple[int, ...] = (),
             token: str | None = None) -> requests.Response:
        headers = {"Authorization": f"Bearer {token or self.token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "avp-ports-index-bootstrap"}
        resp = self.http.request(method, f"{API}{path}", json=body, headers=headers, timeout=30)
        if resp.status_code >= 400 and resp.status_code not in ok:
            raise RuntimeError(f"{method} {path}: {resp.status_code} {resp.text[:300]}")
        return resp

    def json(self, method: str, path: str, body: object = None, **kw) -> dict:
        resp = self.call(method, path, body, **kw)
        return resp.json() if resp.content else {}


def seal(public_key_b64: str, value: str) -> str:
    from nacl import encoding, public
    key = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    return base64.b64encode(public.SealedBox(key).encrypt(value.encode())).decode()


def app_jwt(app_id: str, pem: str) -> str:
    import jwt
    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 540, "iss": app_id}, pem, algorithm="RS256")


def load_credentials(folder: Path) -> dict:
    def read(name: str) -> str | None:
        path = folder / name
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip() + ("\n" if name.endswith(".pem") else "")
    owner = os.environ.get("AVP_OWNER_TOKEN") or read("owner_pat")
    if not owner:
        raise SystemExit(f"no owner token: set AVP_OWNER_TOKEN or create {folder / 'owner_pat'}")
    return {"owner_pat": owner.strip(), "app_id": read("app_id"), "app_key": read("app.pem"),
            "app_client_id": read("app_client_id"),
            "outreach_pat": read("outreach_pat"), "jules_api_key": read("jules_api_key")}


class Bootstrap:
    def __init__(self, api: Api, repo: str, creds: dict, *, owner_login: str = "edgytoast",
                 bot_login: str = "trevorbilt-bot", log=print):
        self.api = api
        self.repo = repo
        self.creds = creds
        self.owner_login = owner_login
        self.bot_login = bot_login
        self.log = log
        self.app: dict = {}
        self.pending: list[str] = []

    @property
    def has_key(self) -> bool:
        """The App's private key is on this machine (otherwise the owner sets APP_KEY himself)."""
        return bool(self.creds.get("app_id") and self.creds.get("app_key"))

    @property
    def has_app(self) -> bool:
        """The App exists, so its ID, client ID and slug can be looked up."""
        return bool(self.app_info())

    @property
    def base(self) -> str:
        return f"/repos/{self.repo}"

    # --- the App -----------------------------------------------------------------------
    def app_info(self) -> dict:
        if not self.app and self.has_key:
            token = app_jwt(self.creds["app_id"].strip(), self.creds["app_key"])
            self.app = self.api.json("GET", "/app", token=token)
            install = self.api.json("GET", f"{self.base}/installation", token=token)
            self.app["installation_id"] = install["id"]
            self.app["jwt"] = token
        elif not self.app:
            # The ID, client ID and slug aren't secret. GitHub shows a private App only to a PAT or
            # an App token, so fall back to the app_id and app_client_id files.
            resp = self.api.call("GET", f"/apps/{APP_SLUG}", ok=(404,))
            if resp.status_code == 200:
                self.app = resp.json()
            elif self.creds.get("app_id") and self.creds.get("app_client_id"):
                self.app = {"id": int(self.creds["app_id"]), "client_id": self.creds["app_client_id"].strip(),
                            "slug": APP_SLUG}
        return self.app

    def installation_token(self, permissions: dict) -> str:
        app = self.app_info()
        data = self.api.json("POST", f"/app/installations/{app['installation_id']}/access_tokens",
                             {"repositories": [self.repo.split("/")[1]], "permissions": permissions},
                             token=app["jwt"])
        return data["token"]

    # --- settings ------------------------------------------------------------------------
    def settings(self) -> None:
        self.api.call("PATCH", self.base, {
            "allow_squash_merge": True, "allow_merge_commit": False, "allow_rebase_merge": False,
            "squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "BLANK",
            "delete_branch_on_merge": True, "allow_auto_merge": False, "has_issues": True})
        self.api.call("PUT", f"{self.base}/actions/permissions/workflow",
                      {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False})
        self.api.call("PUT", f"{self.base}/actions/permissions/fork-pr-contributor-approval",
                      {"approval_policy": "all_external_contributors"})
        self.log("settings: pull requests and Actions configured")

    def variables(self) -> None:
        owner = self.api.json("GET", f"/users/{self.owner_login}")
        values = {"OWNER_LOGIN": self.owner_login, "OWNER_ID": str(owner["id"]), "BOT_LOGIN": self.bot_login}
        if self.has_app:
            app = self.app_info()
            values.update(APP_ID=str(app["id"]), APP_CLIENT_ID=app["client_id"], APP_SLUG=app["slug"])
        else:
            self.pending.append("variables APP_ID, APP_CLIENT_ID, APP_SLUG (need the App)")
        existing = {v["name"]: v["value"] for v in
                    self.api.json("GET", f"{self.base}/actions/variables?per_page=30").get("variables", [])}
        for name, value in {**SWITCHES, **values}.items():
            if name in existing:
                if name in SWITCHES or existing[name] == value:
                    continue
                self.api.call("PATCH", f"{self.base}/actions/variables/{name}", {"name": name, "value": value})
            else:
                self.api.call("POST", f"{self.base}/actions/variables", {"name": name, "value": value})
        self.log("variables: set (switches left as they were if already present)")

    def secrets(self) -> None:
        key = self.api.json("GET", f"{self.base}/actions/secrets/public-key")
        names = {s["name"] for s in self.api.json("GET", f"{self.base}/actions/secrets?per_page=100").get("secrets", [])}
        if self.has_key:
            self.api.call("PUT", f"{self.base}/actions/secrets/APP_KEY",
                          {"encrypted_value": seal(key["key"], self.creds["app_key"]), "key_id": key["key_id"]})
            self.log("secrets: APP_KEY set")
        elif "APP_KEY" in names:
            self.log("secrets: APP_KEY present (set by the owner)")
        else:
            self.pending.append(f"secret APP_KEY (gh secret set APP_KEY -R {self.repo} < <key file>)")
        if "BLOCKLIST_SALT" not in names:
            self.api.call("PUT", f"{self.base}/actions/secrets/BLOCKLIST_SALT",
                          {"encrypted_value": seal(key["key"], secrets.token_hex(32)), "key_id": key["key_id"]})
            self.log("secrets: BLOCKLIST_SALT created")
        else:
            self.log("secrets: BLOCKLIST_SALT already exists; left untouched")

    def environments(self) -> None:
        for env, secret, value in (("jules", "JULES_API_KEY", self.creds["jules_api_key"]),
                                   ("outreach", "OUTREACH_PAT", self.creds["outreach_pat"])):
            self.api.call("PUT", f"{self.base}/environments/{env}",
                          {"deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}})
            policies = self.api.json("GET", f"{self.base}/environments/{env}/deployment-branch-policies")
            if not any(p.get("name") == "main" for p in policies.get("branch_policies", [])):
                self.api.call("POST", f"{self.base}/environments/{env}/deployment-branch-policies",
                              {"name": "main", "type": "branch"})
            if not value:
                present = self.api.json("GET", f"{self.base}/environments/{env}/secrets").get("secrets", [])
                if any(s["name"] == secret for s in present):
                    self.log(f"environments: {env}/{secret} present (set by the owner)")
                else:
                    self.pending.append(f"{env}/{secret} (gh secret set {secret} --env {env} -R {self.repo})")
                continue
            key = self.api.json("GET", f"{self.base}/environments/{env}/secrets/public-key")
            self.api.call("PUT", f"{self.base}/environments/{env}/secrets/{secret}",
                          {"encrypted_value": seal(key["key"], value.strip()), "key_id": key["key_id"]})
        self.log("environments: jules and outreach (main only)")

    def labels(self) -> None:
        existing = {label["name"] for label in self.api.call("GET", f"{self.base}/labels?per_page=100").json()}
        for name, (color, description) in LABELS.items():
            body = {"name": name, "color": color, "description": description}
            if name in existing:
                self.api.call("PATCH", f"{self.base}/labels/{requests.utils.quote(name, safe='')}", body)
            else:
                self.api.call("POST", f"{self.base}/labels", body)
        self.log(f"labels: {len(LABELS)} ensured")

    def ruleset(self) -> None:
        app_id = int(self.app_info()["id"])
        text = (HERE / "ruleset.json").read_text(encoding="utf-8").replace('"APP_ID"', str(app_id))
        body = json.loads(text)
        current = self.api.call("GET", f"{self.base}/rulesets").json()
        match = next((r for r in current if r.get("name") == body["name"]), None)
        if match:
            self.api.call("PUT", f"{self.base}/rulesets/{match['id']}", body)
        else:
            self.api.call("POST", f"{self.base}/rulesets", body)
        self.log("ruleset: main-protection active, checks pinned to the App")

    def health_issue(self) -> None:
        token = self.installation_token({"issues": "write"})
        issues = self.api.call("GET", f"{self.base}/issues?labels=health-tracking&state=open").json()
        issue = next((i for i in issues if i.get("title") == "Health tracking"), None)
        if issue is None:
            issue = self.api.json("POST", f"{self.base}/issues", {
                "title": "Health tracking", "labels": ["health-tracking"],
                "body": "The daily health check notes route and warning changes here, and uses this issue "
                        "when a port's repo can't take an outreach issue."}, token=token)
            self.log(f"health issue: created #{issue['number']}")
        query = "mutation($id: ID!) { pinIssue(input: {issueId: $id}) { issue { number } } }"
        resp = self.api.call("POST", "/graphql", {"query": query, "variables": {"id": issue["node_id"]}}, ok=(403,))
        pinned = resp.status_code < 300 and not resp.json().get("errors")
        self.log("health issue: pinned" if pinned else "health issue: couldn't pin it automatically; pin it once by hand")

    def run(self, *, skip_ruleset: bool, health: bool) -> None:
        self.settings()
        self.variables()
        self.secrets()
        self.environments()
        self.labels()
        if not skip_ruleset:
            if self.has_app:
                self.ruleset()
            else:
                self.pending.append("ruleset main-protection (its required checks are pinned to the App)")
        if health:
            if self.has_key:
                self.health_issue()
            else:
                self.log("health issue: the first build-surfaces run creates it with the App's token")
        if self.pending:
            self.log("pending until the missing credentials exist: " + "; ".join(self.pending))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--skip-ruleset", action="store_true", help="everything except the ruleset (before the import push)")
    parser.add_argument("--health-issue", action="store_true", help="also create and pin the Health tracking issue")
    args = parser.parse_args(argv)
    if args.repo not in ("edgytoast/avp-ports-index", "edgytoast/avp-ports-index-staging"):
        raise SystemExit("refusing to configure a repo other than the two index repos")
    creds = load_credentials(Path(os.environ.get("AVP_SECRETS_DIR", Path.home() / ".config/avp-index")))
    Bootstrap(Api(creds["owner_pat"]), args.repo, creds).run(skip_ruleset=args.skip_ruleset, health=args.health_issue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
