"""Validators, classification and the lifecycle state machine (U10)."""

from __future__ import annotations

import itertools

import pytest
from conftest import BOT_ID, OWNER_ID

from avpindex import lifecycle, store, validate
from avpindex.classify import classify


class TestValidate:
    def test_ids_and_shas(self):
        assert validate.entry_id("good-port-2") == "good-port-2"
        for bad in ('x"; curl evil | sh #', "Upper", "a--b", "-a", "a" * 65, "", None, 3):
            with pytest.raises(validate.InvalidInput):
                validate.entry_id(bad)
        assert validate.sha("a" * 40)
        for bad in ("A" * 40, "a" * 39, "g" * 40):
            with pytest.raises(validate.InvalidInput):
                validate.sha(bad)
        assert validate.pr_number("12") == 12
        for bad in ("0", "-1", "1e3", "12 ", True, 0):
            with pytest.raises(validate.InvalidInput):
                validate.pr_number(bad)
        assert validate.repo_name("a-b/c.d_e") == "a-b/c.d_e"
        assert validate.label("tpvr-candidate-1") == "tpvr-candidate-1"
        for bad in ("Upper", "a b", "a--b", "x" * 41, "", None, "a;rm -rf", "a/b", "${{ x }}"):
            with pytest.raises(validate.InvalidInput):
                validate.label(bad)
        for bad in ("a/b/c", "a b/c", "a/b.git"):
            with pytest.raises(validate.InvalidInput):
                validate.repo_name(bad)

    def test_yaml_rejects_anchors_aliases_and_size(self):
        with pytest.raises(validate.YamlError):
            validate.load_untrusted_yaml(b"a: &x 1\nb: *x\n")
        with pytest.raises(validate.YamlError):
            validate.load_untrusted_yaml(b"a: " + b"x" * 17000)
        with pytest.raises(validate.YamlError):
            validate.load_untrusted_yaml(b"a: !!python/object:os.system x\n")
        assert validate.load_untrusted_yaml(b"d: 2026-10-10\n") == {"d": "2026-10-10"}

    def test_escaping(self):
        text = validate.md_inline("hi @edgytoast [link](https://x) <b>| `x`")
        assert "@⁠edgytoast" in text and "\\[" in text and "&lt;b&gt;" in text and "\\|" in text
        fenced = validate.fence("```\n@someone")
        assert fenced.startswith("````text") and fenced.endswith("````")


class TestClassify:
    def files(self, *pairs):
        return [{"filename": f, "status": s} for f, s in pairs]

    def test_entry_classes(self):
        assert classify(self.files(("entries/x.yaml", "added")), BOT_ID, "bot", OWNER_ID).kind == "entry-add"
        assert classify(self.files(("entries/x.yaml", "modified")), OWNER_ID, "o", OWNER_ID).kind == "entry-edit"
        assert classify(self.files(("entries/x.yaml", "removed")), BOT_ID, "b", OWNER_ID).kind == "entry-remove"

    def test_invalid_mixes_and_renames(self):
        mixed = self.files(("entries/x.yaml", "added"), ("README.md", "modified"))
        assert classify(mixed, OWNER_ID, "o", OWNER_ID).kind == "invalid"
        tamper = self.files((".github/workflows/pr-gate.yml", "modified"), ("entries/x.yaml", "added"))
        assert classify(tamper, BOT_ID, "b", OWNER_ID).kind == "invalid"
        rename = [{"filename": "entries/y.yaml", "previous_filename": "entries/x.yaml", "status": "renamed"}]
        assert classify(rename, OWNER_ID, "o", OWNER_ID).kind == "invalid"
        assert classify(self.files(("entries/sub/x.yaml", "added")), BOT_ID, "b", OWNER_ID).kind == "invalid"

    def test_owner_classes_and_dependabot(self):
        verify = self.files(("verification/owner-verified.yaml", "modified"))
        assert classify(verify, OWNER_ID, "o", OWNER_ID).kind == "owner-verify"
        assert classify(verify, BOT_ID, "b", OWNER_ID).kind == "invalid"
        assert classify(self.files(("docs/x.md", "modified")), OWNER_ID, "o", OWNER_ID).kind == "owner-admin"
        assert classify(self.files(("docs/x.md", "modified")), 1, "dependabot[bot]", OWNER_ID).kind == "skip"


class TestLifecycle:
    """U10: every transition in §5.6 is accepted, and every other is refused."""

    TRIGGERS = ["merge", "reconcile", "health", "kill-switch", "stage2", "self-removal"]

    def test_table(self):
        legal = {
            (None, "listed"): {"merge", "reconcile"},
            ("listed", "listed"): {"merge", "reconcile", "kill-switch"},
            ("listed", "delisted-decay"): {"health"},
            ("delisted-decay", "listed"): {"merge", "reconcile"},
            ("listed", "pulled"): {"kill-switch", "stage2", "health"},
            ("delisted-decay", "pulled"): {"kill-switch"},
            ("pulled", "listed"): {"kill-switch"},
            ("taken-down", "listed"): {"kill-switch"},
            ("listed", "withdrawn"): {"self-removal"},
            ("delisted-decay", "withdrawn"): {"self-removal"},
            ("withdrawn", "listed"): {"merge", "reconcile"},
        }
        for src in ("listed", "delisted-decay", "pulled", "withdrawn"):
            legal[(src, "taken-down")] = {"kill-switch"}
        sources = [None, *lifecycle.STATUSES]
        for src, dst, by in itertools.product(sources, lifecycle.STATUSES, self.TRIGGERS):
            assert lifecycle.is_legal(src, dst, by) == (by in legal.get((src, dst), set())), (src, dst, by)

    def test_transition_records_and_resets_decay(self, root):
        state = store.State.load(root)
        lifecycle.transition(state, "x", "listed", "merge", repo="https://github.com/a/b", repo_id=1)
        assert state.lifecycle["x"]["listed_at"] == "2026-10-03T12:00:00Z"
        state.health["x"].update(health="issues", consecutive_failures=3, failures=["S1-07"])
        lifecycle.transition(state, "x", "pulled", "kill-switch")
        lifecycle.transition(state, "x", "listed", "kill-switch")
        assert state.health["x"]["consecutive_failures"] == 0 and state.health["x"]["decay_reset_at"]
        with pytest.raises(lifecycle.IllegalTransition):
            lifecycle.transition(state, "x", "delisted-decay", "merge")
