"""Exercise the repository's design role floor through the ledger reservation API."""

import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from coordination_ledger import LedgerError, apply_command, create_ledger


REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROLES = ("print-art-designer", "print-cad-designer")


class DesignReservationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(patch.dict(os.environ, {"CODEX_HOME": str(scratch / "empty-home")}))
        root = scratch / "project"
        project_roles = root / ".codex" / "agents"
        project_roles.mkdir(parents=True)
        for role in DESIGN_ROLES:
            profile = f"{role}.toml"
            shutil.copyfile(REPO_ROOT / ".codex" / "agents" / profile, project_roles / profile)
        self.ledger = root / ".coordination" / "ledger.json"
        self.state = create_ledger(self.ledger, root, "main")
        self.apply("runtime", worker_ids=[], source="native_runtime",
                   evidence="Isolated fixture has no native workers")

    def apply(self, action, **payload):
        self.state = apply_command(self.ledger, "main", self.state["revision"], action,
                                   payload, self.state["generation"])

    def add_reservation_task(self, role, effort):
        task = f"{role}-{effort}"
        self.apply("add", task_id=task, objective="Author a bounded design revision",
                   dependencies=[], write_scope=[], input_scope=[], acceptance_checks=[],
                   needs_review=True, budget={"max_attempts": 1, "max_seconds": 60})
        return task

    def reserve(self, task, role, model, effort):
        self.apply("reserve", task_id=task, task_revision=0, generation=self.state["generation"],
                   owner="designer", role=role, model=model, effort=effort)

    def test_rejects_low_and_medium_without_changing_the_ledger(self):
        for role in DESIGN_ROLES:
            for effort in ("low", "medium"):
                with self.subTest(role=role, effort=effort):
                    task = self.add_reservation_task(role, effort)
                    before = self.ledger.read_bytes()
                    with self.assertRaisesRegex(LedgerError, f"{role} requires High reasoning or higher"):
                        self.reserve(task, role, "gpt-6.2-sol", effort)
                    self.assertEqual(before, self.ledger.read_bytes())

    def test_accepts_supported_high_or_higher_choices_without_pins(self):
        choices = (("gpt-6.2-sol", "high"), ("gpt-6.2-astra", "xhigh"), ("gpt-6.2-sol", "max"))
        for role in DESIGN_ROLES:
            for model, effort in choices:
                with self.subTest(role=role, model=model, effort=effort):
                    task = self.add_reservation_task(role, effort)
                    self.reserve(task, role, model, effort)
                    result = self.state["tasks"][task]["resolved_settings"]
                    self.assertEqual((role, model, effort),
                                     (result["role"], result["model"], result["effort"]))


if __name__ == "__main__":
    unittest.main()
