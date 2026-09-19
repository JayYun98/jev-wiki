import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import decisions
import jev_wiki as wiki
import storage
from storage import Vault, WikiError, digest, encode


def selected(label, confidence=0.99):
    return {"type": "choice", "choice": label, "confidence": confidence}


def probability(value):
    return {"type": "noul", "noul": value}


class FakeJev:
    def __init__(self, answers):
        self.answers, self.calls = answers, 0

    def decide(self, operation, state, questions):
        self.calls += 1
        return self.answers


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Vault(Path(self.temp.name) / "vault")
        self.vault.init()
        self.source = "# Policy\nAs of 2026-09-20, refunds are allowed within 30 days.\n"
        self.sid, _ = self.vault.add_source(self.source)

    def seed(self, name="policy", body=None):
        body = body or self.source
        sid, _ = self.vault.add_source(body)
        return self.vault.publish(name, body, [sid], "new")

    def test_malformed_choice_is_rejected(self):
        with self.assertRaises(WikiError):
            decisions.validate_answers({"answers": {"route": selected([])}},
                                       {"route": decisions.choice("Route", {"create": "New"})})

    def test_init_is_idempotent_and_preserves_settings(self):
        config = self.vault.config()
        config["support"] = 0.95
        self.vault.path(".jev-wiki/config.json").write_text(encode(config))
        self.vault.init()
        self.assertEqual(self.vault.config()["support"], 0.95)

    def test_source_hash_detects_mutation(self):
        self.vault.path(f"sources/{self.sid}.md").write_text("changed")
        with self.assertRaisesRegex(WikiError, "integrity"):
            self.vault.source(self.sid)

    def test_paths_reject_traversal_and_symlinks(self):
        for slug in ("../escape", "a/b", "A", "a" * 65):
            with self.assertRaises(WikiError):
                self.vault.revision(slug)
        self.vault.path("wiki/evil.md").symlink_to(Path(self.temp.name) / "elsewhere")
        with self.assertRaisesRegex(WikiError, "Symlink"):
            self.vault.page("evil")
        with self.assertRaises(WikiError):
            self.vault.path("../outside")

    def test_lock_is_exclusive(self):
        with self.vault.lock():
            with self.assertRaisesRegex(WikiError, "busy"):
                with self.vault.lock():
                    pass

    def test_atomic_failure_preserves_old_file(self):
        path = self.vault.path("wiki/test.md")
        path.write_text("original")
        with patch("storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                storage.atomic_write(path, "replacement")
        self.assertEqual(path.read_text(), "original")
        self.assertEqual(list(path.parent.glob(".pending-*")), [])

    def test_publish_revision_backup_and_stale_write(self):
        old = self.seed()
        raw = self.vault.path("wiki/policy.md").read_text()
        new = self.vault.publish("policy", self.source + "\nA heading.\n", [self.sid], old["revision"])
        self.assertNotEqual(old["revision"], new["revision"])
        self.assertEqual(self.vault.path(f'.jev-wiki/history/policy/{old["revision"]}.md').read_text(), raw)
        with self.assertRaisesRegex(WikiError, "Revision conflict"):
            self.vault.publish("policy", self.source, [self.sid], old["revision"])

    def test_exact_duplicate_uses_no_model(self):
        source_file = Path(self.temp.name) / "source.md"
        source_file.write_text(self.source)
        client = FakeJev({})
        result = wiki.ingest(self.vault, client, source_file)
        self.assertEqual(result["status"], "already_ingested")
        self.assertEqual(client.calls, 0)

    def test_ambiguous_target_and_prompt_injection_route_to_review(self):
        source_file = Path(self.temp.name) / "new.md"
        source_file.write_text("# New facts\nSomething new")
        client = FakeJev({"route": selected("update"), "target": selected("none"), "injection": probability(0), "page_type": selected("source")})
        self.assertEqual(wiki.ingest(self.vault, client, source_file)["route"], "review")
        client.answers = {"route": selected("create"), "target": selected("none"), "injection": probability(0.9), "page_type": selected("source")}
        self.assertEqual(wiki.ingest(self.vault, client, source_file, True)["route"], "review")

    def test_unsupported_draft_does_not_write(self):
        client = FakeJev({"support": selected("contradicted"), "injection": probability(0)})
        result = wiki.publish(self.vault, client, "bad", "# Policy\nNo refunds.", [self.sid], "new")
        self.assertFalse(result["written"])
        self.assertFalse(self.vault.path("wiki/bad.md").exists())

    def test_absent_confidence_abstains(self):
        client = FakeJev({"support": {"type": "choice", "choice": "supported"}, "injection": probability(0)})
        self.assertEqual(wiki.verify(self.vault, client, self.source, [self.sid])["status"], "review")

    def test_deterministic_failures_happen_before_paid_request(self):
        client = FakeJev({})
        with self.assertRaisesRegex(WikiError, "Revision"):
            wiki.publish(self.vault, client, "policy", self.source, [self.sid], "wrong")
        with self.assertRaisesRegex(WikiError, "wikilink"):
            wiki.publish(self.vault, client, "policy", "# Title\n[[missing]]", [self.sid], "new")
        self.assertEqual(client.calls, 0)

    def test_external_change_during_verification_is_not_overwritten(self):
        old = self.seed()
        class ConcurrentJev:
            def decide(inner, *args):
                self.vault.path("wiki/policy.md").write_text(self.vault.path("wiki/policy.md").read_text() + "\nExternal edit.")
                return {"support": selected("supported"), "injection": probability(0)}
        with self.assertRaisesRegex(WikiError, "Revision conflict"):
            wiki.publish(self.vault, ConcurrentJev(), "policy", self.source, [self.sid], old["revision"])
        self.assertIn("External edit", self.vault.page("policy")["content"])

    def test_retrieval_reports_coverage_and_abstains(self):
        self.seed()
        self.seed("weather", "# Weather\nRain tomorrow.")
        evidence, coverage = storage.candidates(self.vault.pages(), "refunds", 1)
        self.assertEqual(evidence[0]["id"], "policy")
        self.assertFalse(coverage["complete"])
        client = FakeJev({"p0": {"type": "score", "score": 1, "confidence": 0.99},
                          "p1": {"type": "score", "score": 0, "confidence": 0.99}, "sufficient": probability(0.1)})
        self.assertEqual(wiki.query(self.vault, client, "refunds")["route"], "retrieve_more")

    def test_same_date_cannot_be_a_stale_warning(self):
        self.seed()
        self.seed("faq", "# FAQ\nAs of 2026-09-20, refunds are never allowed.")
        client = FakeJev({"relation": selected("left_superseded"), "duplicate": probability(0)})
        result = wiki.lint(self.vault, client, semantic=True)
        self.assertFalse(any(f["severity"] == "warning" for f in result["findings"]))
        self.assertTrue(any(f["type"] == "review" for f in result["findings"]))
        self.assertEqual(result["coverage"]["checked_pairs"], 1)

    def test_lint_reports_corrupt_pages_broken_links_and_missing_sources(self):
        self.seed()
        path = self.vault.path("wiki/policy.md")
        path.write_text(path.read_text() + "\n[[missing]]")
        self.vault.path("wiki/corrupt.md").write_text("no metadata")
        self.vault.path(f"sources/{self.sid}.md").unlink()
        types = {f["type"] for f in wiki.lint(self.vault, FakeJev({}))["findings"]}
        self.assertTrue({"invalid-source", "invalid-page", "broken-link"} <= types)

    def test_binary_oversized_and_invalid_metadata_are_rejected(self):
        path = Path(self.temp.name) / "input.md"
        for value in (b"\xff", b"a\x00b", b"a" * 16001):
            path.write_bytes(value)
            with self.assertRaises(WikiError):
                storage.read_text(path)
        self.vault.path("wiki/invalid.md").write_text('<!-- jev-wiki {"version":1,"sources":[]} -->\n# X')
        with self.assertRaises(WikiError):
            self.vault.page("invalid")

    def test_cli_offline_init_status_and_lint(self):
        for args in (["status", str(self.vault.root)], ["lint", str(self.vault.root)]):
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(wiki.main(args), 0)
            self.assertIsInstance(json.loads(stream.getvalue()), dict)

    def test_batched_plan_reports_multiple_edits_and_manifest_rebuilds(self):
        self.seed("policy")
        self.seed("faq", "# FAQ\nRefunds are allowed.")
        path = Path(self.temp.name) / "update.md"
        path.write_text("# Refunds\nRefunds now take three days to process.")
        client = FakeJev({"route": selected("update"), "target": selected("p0"), "injection": probability(0),
                          "page_type": selected("concept"), "edit_p0": selected("update"), "edit_p1": selected("conflict")})
        result = wiki.ingest(self.vault, client, path)
        self.assertEqual(result["route"], "review")
        self.assertEqual(len(result["page_actions"]), 2)
        self.assertEqual(client.calls, 1)
        self.assertEqual(wiki.build_index(self.vault)["pages"], 2)
        manifest = json.loads(self.vault.path(".jev-wiki/index.json").read_text())
        self.assertEqual({p["id"] for p in manifest["pages"]}, {"policy", "faq"})


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Vault(self.temp.name)
        self.vault.init()
        self.questions = {"q": decisions.choice("Check", {"yes": "Yes", "no": "No"})}
        self.response = {"model": "typesafe/jev-1.13-20260917", "answers": {"q": selected("yes")}, "usage": {"cost": 0.00001, "input_tokens": 200}}
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "unit-test-secret"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def client(self, budget=0.01):
        client = decisions.Jev(self.vault, budget)
        client.ceiling = 0.001344
        return client

    def test_cached_request_has_no_second_charge_or_secret_log(self):
        client = self.client()
        with patch("decisions.request_json", return_value=self.response) as request:
            client.decide("check", {"text": "evidence"}, self.questions)
            client.decide("check", {"text": "evidence"}, self.questions)
        self.assertEqual(request.call_count, 1)
        self.assertAlmostEqual(client.spent, 0.00001)
        self.assertEqual(client.events[-1]["status"], "cache")
        for path in self.vault.path(".jev-wiki").rglob("*"):
            if path.is_file():
                self.assertNotIn("unit-test-secret", path.read_text())

    def test_budget_exhaustion_and_oversize_prevent_network(self):
        with patch("decisions.request_json") as request:
            with self.assertRaisesRegex(WikiError, "budget"):
                self.client(0.001).decide("check", {}, self.questions)
            with self.assertRaisesRegex(WikiError, "28 KB"):
                self.client().decide("check", {"text": "a" * 28000}, self.questions)
            request.assert_not_called()

    def test_timeout_retains_reservation_and_is_not_retried(self):
        client = self.client()
        with patch("decisions.request_json", side_effect=WikiError("timeout")) as request:
            with self.assertRaises(WikiError):
                client.decide("check", {}, self.questions)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(client.spent, 0.001344)
        self.assertEqual(client.events[-1]["status"], "reserved")

    def test_invalid_response_and_missing_usage_fail_closed(self):
        for response in ({"answers": {}}, {**self.response, "answers": {"q": selected("invented")}},
                         {**self.response, "usage": {"cost": float("nan")}}):
            with patch("decisions.request_json", return_value=response):
                with self.assertRaises(WikiError):
                    self.client().decide("check", {}, self.questions)

    def test_all_three_primitives_validate_ranges(self):
        questions = {"a": decisions.noul("True?"), "b": decisions.score("How much?", ["None", "All"])}
        for answer in ({"type": "noul", "noul": True}, {"type": "noul", "noul": 1.1}):
            with self.assertRaises(WikiError):
                decisions.validate_answers({"answers": {"a": answer}}, questions)
        with self.assertRaises(WikiError):
            decisions.validate_answers({"answers": {"a": probability(0.2), "b": {"type": "score", "score": 2}}}, questions)

    def test_env_is_parsed_not_executed(self):
        path = Path(self.temp.name) / "global.env"
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            path.write_text('OTHER=private\nexport OPENROUTER_API_KEY="literal-key" # comment')
            self.assertEqual(decisions.api_key(path), "literal-key")
            for text in ('OPENROUTER_API_KEY=$(touch /tmp/no)', 'OPENROUTER_API_KEY="unterminated'):
                path.write_text(text)
                with self.assertRaises(WikiError):
                    decisions.api_key(path)

    def test_invalid_config_and_pricing_fail_closed(self):
        config = self.vault.config()
        config["support"] = float("nan")
        self.vault.path(".jev-wiki/config.json").write_text(json.dumps(config))
        with self.assertRaises(WikiError):
            self.vault.config()
        client = decisions.Jev(self.vault)
        with patch("decisions.request_json", return_value={"data": {"endpoints": []}}):
            with self.assertRaises(WikiError):
                client.pricing_ceiling()


if __name__ == "__main__":
    unittest.main()
