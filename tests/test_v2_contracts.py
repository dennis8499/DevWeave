from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".agents" / "skills" / "devweave" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from devweave_v2 import SCHEMA_VERSION, VERSION
from devweave_v2.canonical import dumps, loads
from devweave_v2.cli import PUBLIC_COMMANDS, build_parser
from devweave_v2.errors import ContractError, DevWeaveError, ErrorCode
from devweave_v2.schemas import PUBLIC_SCHEMA_TRACES, PUBLIC_SCHEMA_TYPES, parse_public_schema, schema_catalog


class PublicContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = ROOT / "fixtures" / "devweave_v2"

    def test_all_five_golden_contracts_round_trip_canonically(self) -> None:
        mapping = {
            "RunSnapshot": "run-snapshot.json",
            "RunPlanDraft": "run-plan-draft.json",
            "PendingDecision": "pending-decision.json",
            "VerificationPlan": "verification-plan.json",
            "ReviewFinding": "review-finding.json",
        }
        self.assertEqual(set(mapping), set(PUBLIC_SCHEMA_TYPES))
        for name, filename in mapping.items():
            text = (self.fixtures / filename).read_text(encoding="utf-8")
            parsed = parse_public_schema(name, loads(text))
            self.assertEqual(json.loads(dumps(parsed)), json.loads(text), name)

    def test_unknown_fields_and_invalid_versions_fail_closed(self) -> None:
        raw = json.loads((self.fixtures / "run-snapshot.json").read_text(encoding="utf-8"))
        raw["surprise"] = True
        with self.assertRaises(ContractError) as unknown:
            parse_public_schema("RunSnapshot", raw)
        self.assertEqual(unknown.exception.code, ErrorCode.UNKNOWN_FIELD)
        del raw["surprise"]
        raw["schema_version"] = 1
        with self.assertRaises(ContractError) as version:
            parse_public_schema("RunSnapshot", raw)
        self.assertEqual(version.exception.code, ErrorCode.SCHEMA_VERSION)

    def test_schema_catalog_is_sorted_and_traced(self) -> None:
        catalog = schema_catalog()
        self.assertEqual(catalog["schema_version"], SCHEMA_VERSION)
        names = [item["name"] for item in catalog["schemas"]]
        self.assertEqual(names, sorted(names))
        for name in names:
            traces = PUBLIC_SCHEMA_TRACES[name]
            self.assertTrue(any(item.startswith("REQ-") for item in traces))
            self.assertTrue(any(item.startswith("AC-") for item in traces))

    def test_canonical_json_is_byte_stable(self) -> None:
        left = dumps({"z": [2, 1], "a": "繁體中文"})
        right = dumps({"a": "繁體中文", "z": [2, 1]})
        self.assertEqual(left, right)
        self.assertTrue(left.endswith("\n"))


class PackageContractTests(unittest.TestCase):
    def test_product_versions_are_2_0_0(self) -> None:
        package = json.loads((ROOT / "vscode-extension" / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "vscode-extension" / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(VERSION, "2.0.0")
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), VERSION)
        self.assertEqual(package["version"], VERSION)
        self.assertEqual(lock["version"], VERSION)
        self.assertEqual(lock["packages"][""]["version"], VERSION)

    def test_v2_parser_has_only_the_public_surface(self) -> None:
        parser = build_parser()
        action = next(item for item in parser._actions if item.dest == "command")
        self.assertEqual(tuple(action.choices), PUBLIC_COMMANDS)
        for legacy in ("start", "approve", "task", "close", "revise", "knowledge"):
            with self.assertRaises(DevWeaveError) as rejected:
                parser.parse_args([legacy])
            self.assertEqual(rejected.exception.code, ErrorCode.INVALID_ARGUMENT)

    def test_transitional_launcher_emits_stable_error_envelope(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT_ROOT / "devweave_v2_cli.py"), "check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 4)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["error"]["code"], ErrorCode.NOT_IMPLEMENTED)

    def test_public_package_has_no_reverse_extension_dependency(self) -> None:
        package_root = SCRIPT_ROOT / "devweave_v2"
        for path in package_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("vscode-extension", source, str(path))
            self.assertNotIn("devweave_core", source, str(path))
            self.assertLessEqual(len(source.splitlines()), 500, str(path))


if __name__ == "__main__":
    unittest.main()
