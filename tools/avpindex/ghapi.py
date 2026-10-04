"""REST helpers for the index repo: checks, labels, comments, issues, merges, workflow runs
and commits through the Git Data API. Rate-limit aware with retries (via LinkedRepoReader).

In dry-run mode every write is logged and skipped.
"""

from __future__ import annotations

import base64
import sys
from urllib.parse import quote

from .checks import GitHubError, LinkedRepoReader


class GitHub(LinkedRepoReader):
    def __init__(self, repo: str, token: str | None, *, dry_run: bool = False, **kwargs):
        super().__init__(token=token, **kwargs)
        self.repo_full = repo
        self.dry_run = dry_run
        self.log: list[str] = []

    @property
    def base(self) -> str:
        return f"/repos/{self.repo_full}"

    def _write(self, method: str, path: str, *, json: object = None, token: str | None = None,
               ok: tuple[int, ...] = (), what: str = "") -> object:
        if self.dry_run:
            self.log.append(f"[dry run] {method} {path} {what}".rstrip())
            print(self.log[-1], file=sys.stderr)
            return {}
        resp = self.request(method, path, json=json, token=token, ok=ok)
        if resp.status_code >= 400 and resp.status_code not in ok:
            raise GitHubError(resp.status_code, f"{method} {path}: {resp.text[:300]}")
        if resp.status_code in ok and resp.status_code >= 400:
            return {"_status": resp.status_code}
        return resp.json() if resp.content else {}

    # --- pull requests ------------------------------------------------------------------
    def pr(self, number: int) -> dict:
        data = self.get(f"{self.base}/pulls/{int(number)}", allow404=False)
        return data  # type: ignore[return-value]

    def pr_files(self, number: int) -> list[dict]:
        return self.paginate(f"{self.base}/pulls/{int(number)}/files", limit=3000)

    def open_prs(self) -> list[dict]:
        return self.paginate(f"{self.base}/pulls", {"state": "open"})

    def merge_pr(self, number: int, sha: str, title: str, token: str) -> int:
        if self.dry_run:
            self.log.append(f"[dry run] merge #{number} at {sha}")
            return 200
        resp = self.request("PUT", f"{self.base}/pulls/{int(number)}/merge", token=token,
                            json={"merge_method": "squash", "sha": sha, "commit_title": title,
                                  "commit_message": ""}, ok=(405, 409, 422))
        return resp.status_code

    def close_pr(self, number: int) -> None:
        self._write("PATCH", f"{self.base}/pulls/{int(number)}", json={"state": "closed"})

    def commit_pulls(self, sha: str) -> list[dict]:
        return self.get(f"{self.base}/commits/{sha}/pulls") or []  # type: ignore[return-value]

    # --- issues, labels and comments ----------------------------------------------------
    def issue(self, number: int, repo: str | None = None) -> dict | None:
        return self.get(f"/repos/{repo or self.repo_full}/issues/{int(number)}")  # type: ignore[return-value]

    def issue_events(self, number: int) -> list[dict]:
        return self.paginate(f"{self.base}/issues/{int(number)}/events")

    def issues(self, *, labels: str | None = None, state: str = "open", creator: str | None = None) -> list[dict]:
        params = {"state": state}
        if labels:
            params["labels"] = labels
        if creator:
            params["creator"] = creator
        return self.paginate(f"{self.base}/issues", params)

    def add_labels(self, number: int, labels: list[str]) -> None:
        if labels:
            self._write("POST", f"{self.base}/issues/{int(number)}/labels", json={"labels": labels},
                        what=",".join(labels))

    def remove_label(self, number: int, label: str) -> None:
        self._write("DELETE", f"{self.base}/issues/{int(number)}/labels/{quote(label, safe='')}",
                    ok=(404,), what=label)

    def comments(self, number: int, repo: str | None = None) -> list[dict]:
        return self.paginate(f"/repos/{repo or self.repo_full}/issues/{int(number)}/comments")

    def comment(self, number: int, body: str, *, repo: str | None = None, token: str | None = None) -> dict:
        return self._write("POST", f"/repos/{repo or self.repo_full}/issues/{int(number)}/comments",
                           json={"body": body}, token=token, what=f"comment #{number}")  # type: ignore[return-value]

    def update_comment(self, comment_id: int, body: str) -> None:
        self._write("PATCH", f"{self.base}/issues/comments/{int(comment_id)}", json={"body": body})

    def create_issue(self, title: str, body: str, *, labels: list[str] | None = None,
                     assignees: list[str] | None = None, repo: str | None = None,
                     token: str | None = None) -> dict:
        payload: dict = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return self._write("POST", f"/repos/{repo or self.repo_full}/issues", json=payload, token=token,
                           ok=(404, 410), what=title)  # type: ignore[return-value]

    def close_issue(self, number: int, *, repo: str | None = None, token: str | None = None) -> None:
        self._write("PATCH", f"/repos/{repo or self.repo_full}/issues/{int(number)}",
                    json={"state": "closed"}, token=token, ok=(404, 410))

    def assign(self, number: int, logins: list[str]) -> None:
        self._write("POST", f"{self.base}/issues/{int(number)}/assignees", json={"assignees": logins})

    # --- checks -------------------------------------------------------------------------
    def create_check(self, head_sha: str, name: str, *, status: str = "completed",
                     conclusion: str | None = None, title: str = "", summary: str = "",
                     external_id: str | None = None) -> None:
        payload: dict = {"name": name, "head_sha": head_sha, "status": status,
                         "output": {"title": title[:250] or name, "summary": summary[:65000] or title or name}}
        if status == "completed":
            payload["conclusion"] = conclusion
        if external_id:
            payload["external_id"] = external_id
        self._write("POST", f"{self.base}/check-runs", json=payload, what=f"{name}={conclusion or status}")

    def check_runs(self, sha: str, app_id: int | None, name: str | None = None) -> list[dict]:
        params: dict = {"filter": "latest"}
        if app_id:
            params["app_id"] = app_id
        if name:
            params["check_name"] = name
        runs = self.paginate(f"{self.base}/commits/{sha}/check-runs", params, key="check_runs")
        if app_id:
            runs = [r for r in runs if (r.get("app") or {}).get("id") == app_id]
        return runs

    # --- actions ------------------------------------------------------------------------
    def workflow_runs(self, workflow: str, created_since: str) -> list[dict]:
        return self.paginate(f"{self.base}/actions/workflows/{workflow}/runs",
                             {"created": f">={created_since}"}, key="workflow_runs", limit=300)

    def run_artifacts(self, run_id: int) -> list[dict]:
        return self.paginate(f"{self.base}/actions/runs/{int(run_id)}/artifacts", key="artifacts")

    def dispatch(self, workflow: str, inputs: dict, ref: str = "main") -> bool:
        if self.dry_run:
            self.log.append(f"[dry run] dispatch {workflow} {inputs}")
            return True
        resp = self.request("POST", f"{self.base}/actions/workflows/{workflow}/dispatches",
                            json={"ref": ref, "inputs": inputs}, ok=(404, 422))
        return resp.status_code < 300

    # --- commits through the Git Data API -----------------------------------------------
    def head_of(self, branch: str = "main") -> str:
        data = self.get(f"{self.base}/git/ref/heads/{branch}", allow404=False)
        return data["object"]["sha"]  # type: ignore[index]

    def create_commit(self, parent: str, changes: dict, message: str) -> str:
        """Create a commit on top of `parent`. changes maps path -> (bytes, mode), or None to delete."""
        parent_commit = self.get(f"{self.base}/git/commits/{parent}", allow404=False)
        tree = []
        for path, change in sorted(changes.items()):
            if change is None:
                tree.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                continue
            data, mode = change
            blob = self._write("POST", f"{self.base}/git/blobs",
                               json={"content": base64.b64encode(data).decode(), "encoding": "base64"})
            tree.append({"path": path, "mode": mode, "type": "blob", "sha": blob.get("sha")})
        new_tree = self._write("POST", f"{self.base}/git/trees",
                               json={"base_tree": parent_commit["tree"]["sha"], "tree": tree})  # type: ignore[index]
        commit = self._write("POST", f"{self.base}/git/commits",
                             json={"message": message, "tree": new_tree.get("sha"), "parents": [parent]})
        return commit.get("sha", "")  # type: ignore[union-attr]

    def fast_forward(self, branch: str, sha: str) -> bool:
        """Move the branch to sha without force. False if main moved meanwhile."""
        if self.dry_run:
            return True
        resp = self.request("PATCH", f"{self.base}/git/refs/heads/{branch}",
                            json={"sha": sha, "force": False}, ok=(409, 422))
        return resp.status_code < 300
