"""The lifecycle state machine (spec §5.6). Every status change goes through transition()."""

from __future__ import annotations

from .store import State, default_health, iso, utcnow

LISTED = "listed"
DECAY = "delisted-decay"
PULLED = "pulled"
TAKEN_DOWN = "taken-down"
WITHDRAWN = "withdrawn"
STATUSES = (LISTED, DECAY, PULLED, TAKEN_DOWN, WITHDRAWN)

MERGE = {"merge", "reconcile"}  # reconcile applies the same rules as a merge (§8.5 step 2)

# (from, to) -> triggers ("by" values) that may cause it. Nothing else is legal.
LEGAL: dict[tuple[str | None, str], set[str]] = {
    (None, LISTED): MERGE,
    (LISTED, LISTED): MERGE | {"kill-switch"},
    (LISTED, DECAY): {"health"},
    (DECAY, LISTED): MERGE,
    (LISTED, PULLED): {"kill-switch", "stage2", "health"},
    (DECAY, PULLED): {"kill-switch"},
    (PULLED, LISTED): {"kill-switch"},
    (TAKEN_DOWN, LISTED): {"kill-switch"},
    (LISTED, WITHDRAWN): {"self-removal"},
    (DECAY, WITHDRAWN): {"self-removal"},
    (WITHDRAWN, LISTED): MERGE,
}
for _source in (LISTED, DECAY, PULLED, WITHDRAWN):
    LEGAL[(_source, TAKEN_DOWN)] = {"kill-switch"}


class IllegalTransition(Exception):
    pass


def is_legal(source: str | None, target: str, by: str) -> bool:
    return by in LEGAL.get((source, target), set())


def transition(state: State, entry_id: str, target: str, by: str, **fields) -> str | None:
    """Move an entry to `target`. Returns the previous status. Raises IllegalTransition.

    Any move into `listed` from another state resets the decay fields (§5.4).
    """
    record = state.lifecycle.get(entry_id)
    source = record.get("status") if record else None
    if not is_legal(source, target, by):
        raise IllegalTransition(f"{entry_id}: {source or 'none'} -> {target} by {by} is not allowed")
    now = iso(utcnow())
    if record is None:
        record = {"repo": None, "repo_id": None, "submitted_by": None, "submitted_by_id": None,
                  "owner_approved": False, "listed_at": None}
        state.lifecycle[entry_id] = record
    record.update(fields)
    record["status"] = target
    record["changed_at"] = now
    record["by"] = by
    if target == LISTED and source in (None, WITHDRAWN):
        record["listed_at"] = now
    if target == LISTED and source != LISTED:
        reset_decay(state, entry_id)
    return source


def reset_decay(state: State, entry_id: str) -> None:
    health = state.health.setdefault(entry_id, default_health())
    health.update({"health": "ok", "failing_since": None, "consecutive_failures": 0,
                   "failures": [], "decay_reset_at": iso(utcnow())})
