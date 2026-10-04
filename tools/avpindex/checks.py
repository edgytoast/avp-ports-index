"""Stage 1 checks (spec §6.1). Shared by the PR gate, the daily health check and the
submit skill's preflight script.

Each check returns pass, fail (the contributor must fix something) or route (the curator
must look). The linked repo is read only through GitHub's REST metadata endpoints; nothing
from it is ever cloned, built or run.
"""

from __future__ import annotations

import base64
import hashlib
import re
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import quote

import jsonschema
import requests

from .validate import SOURCE_REF_RE, YamlError, load_untrusted_yaml, parse_repo_url

PASS, FAIL, ROUTE = "pass", "fail", "route"
API = "https://api.github.com"
USER_AGENT = "avp-ports-index"


# --- read-only GitHub access ----------------------------------------------------------

class GitHubError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


class LinkedRepoReader:
    """Read-only REST access to public GitHub data. Rate-limit aware, with retries."""

    def __init__(self, token: str | None = None, session: requests.Session | None = None,
                 api: str = API, max_wait: int = 600):
        self.api = api.rstrip("/")
        self.session = session or requests.Session()
        self.token = token
        self.max_wait = max_wait

    def _headers(self, token: str | None = None) -> dict:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": USER_AGENT}
        tok = token if token is not None else self.token
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return headers

    def request(self, method: str, path: str, *, params: dict | None = None, json: object = None,
                token: str | None = None, ok: tuple[int, ...] = ()) -> requests.Response:
        """Send a request; retry 5xx, secondary rate limits and network errors."""
        url = path if path.startswith("http") else f"{self.api}{path}"
        delay = 2.0
        for attempt in range(6):
            try:
                resp = self.session.request(method, url, params=params, json=json,
                                            headers=self._headers(token), timeout=30)
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code in ok or resp.status_code < 400:
                return resp
            if resp.status_code in (403, 429) and self._rate_limited(resp):
                self._wait_for_rate_limit(resp)
                continue
            if resp.status_code >= 500 and attempt < 5:
                time.sleep(delay)
                delay *= 2
                continue
            return resp
        return resp

    @staticmethod
    def _rate_limited(resp: requests.Response) -> bool:
        if resp.headers.get("retry-after") or resp.headers.get("x-ratelimit-remaining") == "0":
            return True
        return "rate limit" in resp.text.lower()

    def _wait_for_rate_limit(self, resp: requests.Response) -> None:
        if resp.headers.get("retry-after"):
            wait = int(resp.headers["retry-after"])
        elif resp.headers.get("x-ratelimit-reset"):
            wait = max(1, int(resp.headers["x-ratelimit-reset"]) - int(time.time()) + 1)
        else:
            wait = 60
        if wait > self.max_wait:
            raise GitHubError(resp.status_code, "rate limit exceeded")
        time.sleep(wait)

    def get(self, path: str, params: dict | None = None, *, allow404: bool = True) -> object | None:
        resp = self.request("GET", path, params=params, ok=(404, 409, 410, 451) if allow404 else ())
        if resp.status_code in (404, 409, 410, 451) and allow404:
            return None
        if resp.status_code >= 400:
            raise GitHubError(resp.status_code, resp.text[:200])
        return resp.json()

    def paginate(self, path: str, params: dict | None = None, key: str | None = None,
                 limit: int = 1000) -> list:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url: str | None = path
        items: list = []
        while url and len(items) < limit:
            resp = self.request("GET", url, params=params)
            if resp.status_code >= 400:
                raise GitHubError(resp.status_code, resp.text[:200])
            data = resp.json()
            items.extend(data[key] if key else data)
            url = resp.links.get("next", {}).get("url")
            params = None
        return items[:limit]

    # repos and users
    def repo(self, owner: str, name: str) -> dict | None:
        """Repository metadata. Renames are followed (GitHub answers with a redirect)."""
        return self.get(f"/repos/{quote(owner)}/{quote(name)}")

    def repo_by_id(self, repo_id: int) -> dict | None:
        return self.get(f"/repositories/{int(repo_id)}")

    def user_by_id(self, user_id: int) -> dict | None:
        return self.get(f"/user/{int(user_id)}")

    def user(self, login: str) -> dict | None:
        return self.get(f"/users/{quote(login)}")

    def is_public_member(self, org: str, login: str) -> bool:
        resp = self.request("GET", f"/orgs/{quote(org)}/public_members/{quote(login)}", ok=(404, 302))
        return resp.status_code == 204

    def branch_head(self, owner: str, name: str, branch: str) -> str | None:
        try:
            data = self.get(f"/repos/{quote(owner)}/{quote(name)}/commits/{quote(branch, safe='')}")
        except GitHubError as exc:
            if exc.status == 422:  # GitHub's answer for a branch that doesn't exist
                return None
            raise
        return data["sha"] if data else None

    def commit(self, owner: str, name: str, sha: str) -> dict | None:
        return self.get(f"/repos/{quote(owner)}/{quote(name)}/commits/{sha}")

    def contents(self, owner: str, name: str, path: str, ref: str) -> dict | None:
        data = self.get(f"/repos/{quote(owner)}/{quote(name)}/contents/{quote(path)}", {"ref": ref})
        return data if isinstance(data, dict) else None

    def tree(self, owner: str, name: str, sha: str) -> dict | None:
        return self.get(f"/repos/{quote(owner)}/{quote(name)}/git/trees/{sha}", {"recursive": "1"})

    def releases(self, owner: str, name: str, count: int = 30) -> list:
        data = self.get(f"/repos/{quote(owner)}/{quote(name)}/releases", {"per_page": count})
        return data or []

    def license(self, owner: str, name: str, ref: str) -> dict | None:
        return self.get(f"/repos/{quote(owner)}/{quote(name)}/license", {"ref": ref})

    def compare(self, owner: str, name: str, base: str, head: str) -> dict | None:
        return self.get(f"/repos/{quote(owner)}/{quote(name)}/compare/{base}...{head}", {"per_page": 1})


def decode_content(item: dict) -> bytes:
    if item.get("encoding") == "base64" and item.get("content") is not None:
        return base64.b64decode(item["content"])
    return (item.get("content") or "").encode("utf-8")


# --- link probing (S1-10) --------------------------------------------------------------

def _is_dns_failure(exc: BaseException) -> bool:
    seen = set()
    stack = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen or current is None:
            continue
        seen.add(id(current))
        if isinstance(current, socket.gaierror) or type(current).__name__ == "NameResolutionError":
            return True
        text = str(current)
        if "Name or service not known" in text or "nodename nor servname" in text \
                or "Failed to resolve" in text or "No address associated" in text:
            return True
        stack.extend([getattr(current, "reason", None), current.__cause__, current.__context__])
        stack.extend(a for a in getattr(current, "args", ()) if isinstance(a, BaseException))
    return False


def probe_url(session: requests.Session, url: str) -> tuple[str, str]:
    """HEAD, then GET on 405. Returns (ok|fail|warn, detail). Only 404, 410 and DNS failure fail."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; avp-ports-index link check)"}
    try:
        resp = session.head(url, allow_redirects=True, timeout=15, headers=headers)
        if resp.status_code == 405:
            resp = session.get(url, allow_redirects=True, timeout=15, headers=headers, stream=True)
            resp.close()
    except requests.RequestException as exc:
        if _is_dns_failure(exc):
            return "fail", "the domain doesn't resolve"
        return "warn", f"couldn't be checked ({type(exc).__name__})"
    if resp.status_code in (404, 410):
        return "fail", f"returns {resp.status_code}"
    if resp.status_code >= 400:
        return "warn", f"returned {resp.status_code}"
    return "ok", ""


# --- results ----------------------------------------------------------------------------

@dataclass
class Result:
    id: str
    outcome: str
    detail: str = ""
    waivable: bool = True
    waived: bool = False

    @property
    def effective(self) -> str:
        return PASS if self.waived else self.outcome


@dataclass
class Subject:
    """What is being checked, and on whose behalf."""

    mode: str                       # gate | health | preflight
    entry_id: str                   # the file name's stem
    raw: bytes | None = None        # the entry file's bytes
    change: str = "add"             # add | edit | remove (gate); listed (health)
    author_id: int | None = None
    author_login: str | None = None
    old_entry: dict | None = None   # main's copy of the file (edits and removals)
    record: dict | None = None      # lifecycle record
    health: dict | None = None      # health record (scanned_commit)
    flagged_pr: bool = False        # the PR carries stage2:flagged: skip S1-17
    owner_scan: bool = False        # the PR carries owner:scan: waive routes except S1-08(a), S1-16


@dataclass
class IndexView:
    """The index's own data that the checks read."""

    policy: dict
    schema: dict
    index_repo: str = ""
    entries: dict = field(default_factory=dict)          # current entry files on main, by id
    lifecycle: dict = field(default_factory=dict)
    blocked: set = field(default_factory=set)            # blocklist hashes
    flagged: set = field(default_factory=set)            # flag-memory hashes
    salt: str | None = None


@dataclass
class Report:
    results: list = field(default_factory=list)
    warnings: list = field(default_factory=list)     # (check id, text)
    entry: dict | None = None
    repo: dict | None = None                         # linked repo metadata
    head: str | None = None                          # linked HEAD (see linked_head)
    license: dict | None = None
    curator_flags: dict = field(default_factory=dict)

    def add(self, result: Result | None) -> None:
        if result is not None:
            self.results.append(result)

    def get(self, check_id: str) -> Result | None:
        return next((r for r in self.results if r.id == check_id), None)

    @property
    def overall(self) -> str:
        outcomes = [r.effective for r in self.results]
        if FAIL in outcomes:
            return FAIL
        if ROUTE in outcomes:
            return ROUTE
        return PASS

    @property
    def failures(self) -> list[str]:
        return [r.id for r in self.results if r.effective == FAIL]

    @property
    def routes(self) -> list[str]:
        return [r.id for r in self.results if r.effective == ROUTE]

    @property
    def waived(self) -> list[str]:
        return [r.id for r in self.results if r.waived]

    @property
    def external_id(self) -> str | None:
        if self.repo and self.head:
            return f"{self.repo['id']}@{self.head}"
        return None


class Ctx:
    def __init__(self, subject: Subject, index: IndexView, reader: LinkedRepoReader,
                 http: requests.Session | None):
        self.s = subject
        self.idx = index
        self.gh = reader
        self.http = http or requests.Session()
        self.report = Report()
        self.entry: dict | None = None
        self.owner: str | None = None
        self.name: str | None = None
        self.repo: dict | None = None
        self.head: str | None = None
        self.tree: dict | None = None

    @property
    def stop(self) -> bool:
        """Later checks can't run once the file itself is unusable."""
        return any(r.id in ("S1-02", "S1-03") and r.outcome == FAIL for r in self.report.results)

    @property
    def repo_changed(self) -> bool:
        old = (self.s.old_entry or {}).get("repo") or (self.s.record or {}).get("repo")
        return bool(old and self.entry and old.lower() != str(self.entry.get("repo", "")).lower())

    def hash(self, key: str) -> str:
        """sha256(BLOCKLIST_SALT + key), as in blocklist.h()."""
        return hashlib.sha256(((self.idx.salt or "") + key).encode("utf-8")).hexdigest()

    def repo_names(self) -> list[str]:
        names = []
        if self.entry and isinstance(self.entry.get("repo"), str):
            try:
                owner, name = parse_repo_url(self.entry["repo"])
                names.append(f"{owner}/{name}".lower())
            except ValueError:
                pass
        if self.repo:
            names.append(self.repo["full_name"].lower())
        return sorted(set(names))


def linked_head(gh, repo: dict, entry: dict | None) -> str | None:
    """The linked HEAD: the newest commit on the entry's `source_ref` branch if it sets one, else
    on the repo's default branch. A `source_ref` that is invalid or isn't a branch (a tag, SHA or
    pull request ref) resolves to nothing."""
    ref = (entry or {}).get("source_ref")
    if ref is None:
        ref = repo["default_branch"]
    elif isinstance(ref, str) and SOURCE_REF_RE.fullmatch(ref):
        ref = f"refs/heads/{ref}"
    else:
        return None
    return gh.branch_head(repo["owner"]["login"], repo["name"], ref)


# --- the checks -------------------------------------------------------------------------

def s1_01(ctx: Ctx) -> Result | None:
    """S1-01 · One file. The PR changes exactly one path, under `entries/`, and nothing else."""
    if ctx.s.mode != "gate":
        return None
    return Result("S1-01", PASS)


def s1_02(ctx: Ctx) -> Result | None:
    """S1-02 · Safe YAML. The entry parses with a safe YAML loader, is at most 16 KB, and uses no
    anchors or aliases."""
    if ctx.s.raw is None:
        return Result("S1-02", FAIL, "the entry file couldn't be read")
    try:
        data = load_untrusted_yaml(ctx.s.raw)
    except YamlError as exc:
        return Result("S1-02", FAIL, str(exc))
    if not isinstance(data, dict):
        return Result("S1-02", FAIL, "the file must be a YAML mapping of fields")
    ctx.entry = data
    return Result("S1-02", PASS)


def s1_03(ctx: Ctx) -> Result | None:
    """S1-03 · Schema. The entry is valid against `schema/entry.schema.json`, and its `id`
    equals the file name."""
    if ctx.entry is None:
        return None
    validator = jsonschema.Draft202012Validator(ctx.idx.schema)
    errors = sorted(validator.iter_errors(ctx.entry), key=lambda e: list(e.absolute_path))
    if errors:
        err = jsonschema.exceptions.best_match(errors)
        where = ".".join(str(p) for p in err.absolute_path) or "(top level)"
        hint = ""
        if list(err.absolute_path) == ["visionos_min"]:
            hint = ' (write it in quotes, like "26.0")'
        return Result("S1-03", FAIL, f"{where}: {_schema_message(err)}{hint}")
    if ctx.entry.get("id") != ctx.s.entry_id:
        return Result("S1-03", FAIL, f"id must equal the file name ({ctx.s.entry_id}.yaml)")
    return Result("S1-03", PASS)


def _schema_message(err) -> str:
    if err.validator == "additionalProperties":
        extra = sorted(set(err.instance) - set(err.schema.get("properties", {})))
        return f"field(s) not allowed: {', '.join(extra)}"
    if err.validator == "required":
        return err.message.replace("is a required property", "is required")
    if err.validator == "enum":
        return "must be one of: " + ", ".join(str(v) for v in err.validator_value)
    if err.validator == "pattern":
        return "doesn't have the expected format"
    if err.validator == "not":
        return "must not end in .git"
    return err.message[:200]


def s1_06(ctx: Ctx) -> Result | None:
    """S1-06 · Repo resolves. The linked repo resolves (renames followed), is public, is not
    disabled, has at least one commit, and is not this index. Archived repos are allowed and
    recorded. If the entry sets `source_ref`, that branch must exist."""
    if ctx.entry is None:
        return None
    try:
        ctx.owner, ctx.name = parse_repo_url(ctx.entry["repo"])
    except (ValueError, KeyError):
        return Result("S1-06", FAIL, "repo isn't a GitHub repository URL")
    repo = ctx.gh.repo(ctx.owner, ctx.name)
    if repo is None:
        return Result("S1-06", FAIL, "the repo doesn't exist or isn't public")
    if repo.get("private") or repo.get("visibility") not in (None, "public"):
        return Result("S1-06", FAIL, "the repo isn't public")
    if repo.get("disabled"):
        return Result("S1-06", FAIL, "the repo is disabled")
    if ctx.idx.index_repo and repo["full_name"].lower() == ctx.idx.index_repo.lower():
        return Result("S1-06", FAIL, "the repo is this index")
    head = linked_head(ctx.gh, repo, ctx.entry)
    if not head:
        if "source_ref" in ctx.entry:
            return Result("S1-06", FAIL, "source_ref doesn't name a branch in the repo")
        return Result("S1-06", FAIL, "the repo has no commits")
    ctx.owner, ctx.name = repo["owner"]["login"], repo["name"]
    ctx.repo, ctx.head = repo, head
    ctx.report.repo, ctx.report.head = repo, head
    return Result("S1-06", PASS, "archived" if repo.get("archived") else "")


def s1_04(ctx: Ctx) -> Result | None:
    """S1-04 · Unique. The `id` is unique, and `repo` is not used by another current entry file
    (compared case-insensitively and by repo ID). Re-checked right before every merge."""
    if ctx.s.mode != "gate" or ctx.entry is None:
        return None
    return uniqueness(ctx.s.entry_id, ctx.s.change, ctx.entry.get("repo", ""),
                      ctx.repo["id"] if ctx.repo else None, ctx.idx)


def uniqueness(entry_id: str, change: str, repo_url: str, repo_id: int | None,
               index: IndexView) -> Result:
    if change == "add" and entry_id in index.entries:
        return Result("S1-04", FAIL, f"the id {entry_id} is already used")
    for other_id, other in index.entries.items():
        if other_id == entry_id:
            continue
        if str(other.get("repo", "")).lower() == str(repo_url).lower():
            return Result("S1-04", FAIL, f"this repo is already listed as {other_id}")
        other_record = index.lifecycle.get(other_id) or {}
        if repo_id is not None and other_record.get("repo_id") == repo_id:
            return Result("S1-04", FAIL, f"this repo is already listed as {other_id}")
    return Result("S1-04", PASS)


def s1_05(ctx: Ctx) -> Result | None:
    """S1-05 · Not blocklisted. None of the entry's hashes (repo ID, repo name, entry id) is on
    the blocklist."""
    if ctx.s.mode == "preflight" or ctx.entry is None:
        return None
    keys = [f"repo_name:{n}" for n in ctx.repo_names()]
    if ctx.repo:
        keys.append(f"repo_id:{ctx.repo['id']}")
    keys.append(f"slug:{ctx.s.entry_id}")
    if any(ctx.hash(k) in ctx.idx.blocked for k in keys):
        return Result("S1-05", FAIL, "this entry or repo can't be listed", waivable=False)
    return Result("S1-05", PASS)


def s1_07(ctx: Ctx) -> Result | None:
    """S1-07 · Install guide. `AVP-INSTALL.md` is at the root of the linked repo (exact name),
    at most 256 KB, and not empty."""
    if ctx.repo is None:
        return None
    install = ctx.idx.policy.get("install_file", "AVP-INSTALL.md")
    item = ctx.gh.contents(ctx.owner, ctx.name, install, ctx.head)
    if item is None or item.get("type") != "file" or item.get("name") != install:
        return Result("S1-07", FAIL, f"{install} isn't at the repo root")
    if int(item.get("size", 0)) > 256 * 1024:
        return Result("S1-07", FAIL, f"{install} is larger than 256 KB")
    body = decode_content(item)
    if not body.strip():
        return Result("S1-07", FAIL, f"{install} is empty")
    return Result("S1-07", PASS)


def s1_08(ctx: Ctx) -> Result | None:
    """S1-08 · Authority. Decided by numeric user IDs. Adds: the PR author owns the linked repo
    or is a public member of its owning org. Edits and deletes: the author owns (or is a public
    member of the org that owns) the entry's current repo, found by its recorded repo ID, or is
    the person who first listed the entry. An edit that changes `repo` must pass both."""
    if ctx.s.mode == "health":
        return None
    if ctx.s.mode == "preflight":
        if ctx.repo is None or ctx.s.author_id is None:
            return None
        ok = controls(ctx.gh, ctx.repo, ctx.s.author_id, ctx.s.author_login)
        return Result("S1-08", PASS if ok else ROUTE,
                      "" if ok else "you don't own this repo, so the curator will review the PR first")
    if ctx.s.change in ("edit", "remove"):
        ok_a = authority_a(ctx.gh, ctx.s, ctx.entry)
        if not ok_a:
            return Result("S1-08", ROUTE, "the PR author has no authority over the listed entry",
                          waivable=False)
        if ctx.s.change == "remove" or not ctx.repo_changed:
            return Result("S1-08", PASS)
    if ctx.repo is None:
        return None
    if controls(ctx.gh, ctx.repo, ctx.s.author_id, ctx.s.author_login):
        return Result("S1-08", PASS)
    return Result("S1-08", ROUTE, "the PR author doesn't own the linked repo")


def controls(reader: LinkedRepoReader, repo: dict, user_id: int | None, login: str | None) -> bool:
    """The user owns the repo, or is a public member of the org that owns it."""
    if user_id is None:
        return False
    owner = repo.get("owner") or {}
    if owner.get("id") == user_id:
        return True
    if owner.get("type") == "Organization" and login:
        return reader.is_public_member(owner["login"], login)
    return False


def authority_a(reader: LinkedRepoReader, subject: Subject, entry: dict | None) -> bool:
    """S1-08(a): authority over the entry as it is listed now."""
    record = subject.record or {}
    if subject.author_id is not None and record.get("submitted_by_id") == subject.author_id:
        return True
    current = None
    if record.get("repo_id"):
        current = reader.repo_by_id(record["repo_id"])
        if current is None:
            return False  # the recorded repo is gone: only the original submitter qualifies
    elif subject.old_entry and subject.old_entry.get("repo"):
        try:
            owner, name = parse_repo_url(subject.old_entry["repo"])
            current = reader.repo(owner, name)
        except ValueError:
            current = None
    return bool(current) and controls(reader, current, subject.author_id, subject.author_login)


def s1_09(ctx: Ctx) -> Result | None:
    """S1-09 · License. Never fails. Records the license as open-source, custom or none. If a
    license outside the open-source list appears to forbid personal use, the curator looks first."""
    if ctx.repo is None:
        return None
    data = ctx.gh.license(ctx.owner, ctx.name, ctx.head)
    if not data or not data.get("license"):
        ctx.report.license = {"spdx": None, "kind": "none"}
        return Result("S1-09", PASS, "no license stated")
    spdx = data["license"].get("spdx_id")
    if spdx in ctx.idx.policy.get("license_open_source", []):
        ctx.report.license = {"spdx": spdx, "kind": "open-source"}
        return Result("S1-09", PASS, spdx)
    ctx.report.license = {"spdx": None if spdx in (None, "NOASSERTION", "Other") else spdx,
                          "kind": "custom"}
    text = decode_content(data).decode("utf-8", "replace")
    for phrase in ctx.idx.policy.get("license_route_phrases", []):
        if re.search(phrase, text, re.IGNORECASE):
            return Result("S1-09", ROUTE, "the license may not allow personal use")
    return Result("S1-09", PASS, "custom license")


def s1_10(ctx: Ctx) -> Result | None:
    """S1-10 · Links. Every URL in the entry resolves. Only 404, 410 or a DNS failure fails;
    other errors (bot protection, rate limits, timeouts, server errors) are warnings that never
    block a PR or affect an entry."""
    if ctx.entry is None:
        return None
    urls = entry_urls(ctx.entry)
    failed = []
    for url in urls:
        outcome, detail = probe_url(ctx.http, url)
        if outcome == "fail":
            failed.append(f"{url} {detail}")
        elif outcome == "warn":
            ctx.report.warnings.append(("S1-10", f"{url} {detail}"))
    if failed:
        return Result("S1-10", FAIL, "; ".join(failed))
    return Result("S1-10", PASS)


def entry_urls(entry: dict) -> list[str]:
    urls = [entry.get("repo")]
    urls.append((entry.get("developer") or {}).get("url"))
    urls.extend(c.get("url") for c in entry.get("credits") or [] if isinstance(c, dict))
    urls.extend(entry.get("upstream") or [])
    seen, out = set(), []
    for url in urls:
        if isinstance(url, str) and url.startswith("https://") and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _ensure_tree(ctx: Ctx) -> dict | None:
    if ctx.tree is None and ctx.repo is not None:
        ctx.tree = ctx.gh.tree(ctx.owner, ctx.name, ctx.head) or {"tree": [], "truncated": False}
    return ctx.tree


def _ends(path: str, extensions: list[str]) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext.lower()) for ext in extensions)


def s1_11a(ctx: Ctx) -> Result | None:
    """S1-11a · No game data. The repo's tree contains no file with a disc-image or game-data
    extension (`forbidden_extensions` in `config/policy.yaml`)."""
    tree = _ensure_tree(ctx)
    if tree is None:
        return None
    bad = [i["path"] for i in tree.get("tree", []) if i.get("type") == "blob"
           and _ends(i["path"], ctx.idx.policy["forbidden_extensions"])]
    if bad:
        return Result("S1-11a", FAIL, "game data or disc images: " + ", ".join(bad[:5]))
    return Result("S1-11a", PASS)


def s1_11b(ctx: Ctx) -> Result | None:
    """S1-11b · Tree size. GitHub returned the whole tree (not truncated)."""
    tree = _ensure_tree(ctx)
    if tree is None:
        return None
    if tree.get("truncated"):
        return Result("S1-11b", ROUTE, "the repo is too large to check automatically")
    return Result("S1-11b", PASS)


def s1_11c(ctx: Ctx) -> Result | None:
    """S1-11c · No archives or large files. The tree has no archive, no blob over
    `large_blob_bytes`, and no `.gitattributes` with `filter=lfs`."""
    tree = _ensure_tree(ctx)
    if tree is None:
        return None
    policy = ctx.idx.policy
    items = [i for i in tree.get("tree", []) if i.get("type") == "blob"]
    archives = [i["path"] for i in items if _ends(i["path"], policy["archive_extensions"])]
    large = [i["path"] for i in items if int(i.get("size") or 0) > int(policy["large_blob_bytes"])]
    lfs = []
    for item in [i for i in items if i["path"].rsplit("/", 1)[-1] == ".gitattributes"][:25]:
        content = ctx.gh.contents(ctx.owner, ctx.name, item["path"], ctx.head)
        if content and re.search(rb"filter\s*=\s*lfs", decode_content(content)):
            lfs.append(item["path"])
    reasons = []
    if archives:
        reasons.append("archives: " + ", ".join(archives[:5]))
    if large:
        reasons.append("large files: " + ", ".join(large[:5]))
    if lfs:
        reasons.append("Git LFS")
    if reasons:
        return Result("S1-11c", ROUTE, "; ".join(reasons))
    return Result("S1-11c", PASS)


def s1_11d(ctx: Ctx) -> Result | None:
    """S1-11d · Release assets. In the newest 30 releases, an asset with a game-data extension
    fails; an archive or prebuilt binary goes to the curator."""
    if ctx.repo is None:
        return None
    policy = ctx.idx.policy
    names = [a.get("name", "") for r in ctx.gh.releases(ctx.owner, ctx.name, 30)
             for a in r.get("assets") or []]
    bad = [n for n in names if _ends(n, policy["forbidden_extensions"])]
    if bad:
        return Result("S1-11d", FAIL, "release assets with game data: " + ", ".join(bad[:5]))
    binaries = [n for n in names if _ends(n, policy["archive_extensions"] + policy["release_binary_extensions"])]
    if binaries:
        return Result("S1-11d", ROUTE, "release assets with prebuilt apps or archives: " + ", ".join(binaries[:5]))
    return Result("S1-11d", PASS)


def s1_15(ctx: Ctx) -> Result | None:
    """S1-15 · Not pulled. Entries the curator has pulled can't be added, edited or removed by a
    pull request."""
    if ctx.s.mode != "gate":
        return None
    if (ctx.s.record or {}).get("status") == "pulled":
        return Result("S1-15", FAIL, "this entry is currently pulled and waiting for the curator",
                      waivable=False)
    return Result("S1-15", PASS)


def s1_16(ctx: Ctx) -> Result | None:
    """S1-16 · Same repo. When the entry's `repo` URL is unchanged, the linked repo's numeric ID
    still equals the one recorded at listing. A mismatch means the name was reclaimed by someone
    else."""
    record = ctx.s.record or {}
    if ctx.s.mode == "preflight" or ctx.entry is None or ctx.repo is None:
        return None
    if record.get("status") not in ("listed", "delisted-decay") or not record.get("repo_id"):
        return None
    if str(ctx.entry.get("repo", "")).lower() != str(record.get("repo", "")).lower():
        return None
    if ctx.repo["id"] != record["repo_id"]:
        return Result("S1-16", ROUTE, "the repo at this address isn't the one originally listed",
                      waivable=False)
    return Result("S1-16", PASS)


def s1_17(ctx: Ctx) -> Result | None:
    """S1-17 · Previously flagged. If an earlier automated review flagged this repo, a PR that
    would need a new scan (an add, a change of repo, or new commits since the last scan) goes to
    the curator."""
    if ctx.s.mode != "gate" or ctx.s.flagged_pr or ctx.repo is None:
        return None
    if not needs_scan(ctx.s.change, ctx.repo_changed, ctx.head, (ctx.s.health or {}).get("scanned_commit")):
        return Result("S1-17", PASS)
    if ctx.hash(f"repo_id:{ctx.repo['id']}") in ctx.idx.flagged:
        return Result("S1-17", ROUTE, "an earlier automated review of this repo asked for a closer look")
    return Result("S1-17", PASS)


def needs_scan(change: str, repo_changed: bool, head: str | None, scanned: str | None) -> bool:
    return change == "add" or repo_changed or head != scanned


def s1_18(ctx: Ctx) -> Result | None:
    """S1-18 · Reclaimed id. Adding an id that was withdrawn, for a different repo than before,
    goes to the curator, because directories key on `id`."""
    if ctx.s.mode != "gate" or ctx.s.change != "add" or ctx.repo is None:
        return None
    record = ctx.s.record or {}
    if record.get("status") == "withdrawn" and record.get("repo_id") not in (None, ctx.repo["id"]):
        return Result("S1-18", ROUTE, "this entry id belonged to a different port before")
    return Result("S1-18", PASS)


ORDER = ["S1-01", "S1-02", "S1-03", "S1-04", "S1-05", "S1-06", "S1-07", "S1-08", "S1-09",
         "S1-10", "S1-11a", "S1-11b", "S1-11c", "S1-11d", "S1-15", "S1-16", "S1-17", "S1-18"]

# Execution order differs from display order: S1-04 and S1-05 use the resolved repo.
RUN = [s1_01, s1_02, s1_03, s1_06, s1_04, s1_05, s1_07, s1_08, s1_09, s1_10,
       s1_11a, s1_11b, s1_11c, s1_11d, s1_15, s1_16, s1_17, s1_18]

ALL_CHECKS = sorted(RUN, key=lambda f: ORDER.index(f.__doc__.split(" ")[0]))

HEALTH_IDS = {"S1-02", "S1-03", "S1-05", "S1-06", "S1-07", "S1-09", "S1-10",
              "S1-11a", "S1-11b", "S1-11c", "S1-11d", "S1-16"}
PREFLIGHT_SKIPS = {"S1-01", "S1-04", "S1-05", "S1-15", "S1-16", "S1-17", "S1-18"}

FIXES = {
    "S1-01": "Change only your one file under entries/ in this PR.",
    "S1-02": "Fix the YAML so it parses, keep it under 16 KB, and don't use anchors (&) or aliases (*).",
    "S1-03": "Fix the field named here. The field reference lists every allowed field.",
    "S1-04": "Pick a different id, or edit the existing entry instead of adding a new one.",
    "S1-05": "This one can't be fixed in the PR. If you think it's a mistake, open an appeal.",
    "S1-06": "Make sure the repo URL is right, the repo is public and has at least one commit, and "
             "source_ref (if you set it) names a branch that exists.",
    "S1-07": "Add a non-empty AVP-INSTALL.md at the root of your repo (exact name, under 256 KB).",
    "S1-09": "Nothing to fix; the curator will check the license.",
    "S1-10": "Fix or remove the link named here.",
    "S1-11a": "Remove game data and disc images from the repo (and its history, if you can).",
    "S1-11d": "Remove game data from your releases.",
    "S1-15": "Nothing to do here; the curator will look at this entry.",
}


def run(subject: Subject, index: IndexView, reader: LinkedRepoReader,
        http: requests.Session | None = None) -> Report:
    """Run the checks that apply to subject.mode and return the report."""
    ctx = Ctx(subject, index, reader, http)
    if subject.change == "remove":
        return _run_remove(ctx)
    for check in RUN:
        check_id = check.__doc__.split(" ")[0]
        if subject.mode == "health" and check_id not in HEALTH_IDS:
            continue
        if subject.mode == "preflight" and check_id in PREFLIGHT_SKIPS:
            continue
        if ctx.stop:
            break
        ctx.report.add(check(ctx))
    ctx.report.entry = ctx.entry
    ctx.report.results.sort(key=lambda r: ORDER.index(r.id))
    if subject.owner_scan:
        for result in ctx.report.results:
            if result.outcome == ROUTE and result.waivable:
                result.waived = True
    return ctx.report


def _run_remove(ctx: Ctx) -> Report:
    ok = authority_a(ctx.gh, ctx.s, ctx.s.old_entry)
    ctx.report.add(Result("S1-08", PASS) if ok else
                   Result("S1-08", ROUTE, "the PR author has no authority over the listed entry", waivable=False))
    ctx.report.add(s1_15(ctx))
    ctx.report.entry = ctx.s.old_entry
    return ctx.report
