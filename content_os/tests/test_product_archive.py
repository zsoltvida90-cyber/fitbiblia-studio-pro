import importlib.util
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


archive = load(ROOT/'archive'/'product_archive.py', 'product_archive')


class ProductArchiveTests(unittest.TestCase):
    def base_spec(self, temp):
        files = []
        for group in archive.REQUIRED_GROUPS:
            p = Path(temp) / f"{group.lower()}.txt"
            p.write_text(group, encoding="utf-8")
            files.append({"group": group, "name": p.name, "source": str(p)})
        return {
            "archive_id": "ARCH-20260814-001",
            "acceptance_confirmed": True,
            "acceptance_command_received": "Elfogadom!",
            "accepted_at": "2026-08-14T10:23:00+02:00",
            "accepted_date": "2026-08-14",
            "accepted_by": "HUMAN",
            "title": "Alvás és testsúly",
            "version": "1.0",
            "master_id": "MASTER-SLEEP-WEIGHT-001",
            "asset_id": "ASSET-IG-CAR-20260814-001",
            "platform": "INSTAGRAM",
            "output_type": "CAROUSEL",
            "publication_status": "PLANNED",
            "research_ids": ["RSH-20260814-001"],
            "evidence_packet_ids": ["EP-SLEEP-WEIGHT-001"],
            "claim_ids": ["CLM-SLEEP-WEIGHT-001"],
            "renderer_version": "1.1.0",
            "asset_manifest_version": "visual-assets-1.0",
            "qa_status": "PASS",
            "files": files,
        }

    def test_acceptance_is_strict(self):
        self.assertTrue(archive.is_explicit_acceptance("ELFOGADOM A TERMÉKET"))
        self.assertTrue(archive.is_explicit_acceptance("Elfogadom!"))
        self.assertTrue(archive.is_explicit_acceptance("Mehet az archívumba!"))
        self.assertFalse(archive.is_explicit_acceptance("jó"))
        self.assertFalse(archive.is_explicit_acceptance("tetszik, mehet tovább"))

    def test_human_readable_name(self):
        name = archive.build_archive_name(
            "2026-08-14", "Alvás és testsúly", "Instagram", "Carousel", "1.0"
        )
        self.assertEqual(
            name,
            "2026-08-14__Alvas-es-testsuly__Instagram-Carousel__v1.0",
        )

    def test_local_package_is_not_final_archive(self):
        with tempfile.TemporaryDirectory() as td:
            spec = self.base_spec(td)
            out = Path(td) / "archive"
            result = archive.build_archive_package(spec, out)
            self.assertEqual(result.archive_status, "PACKAGE_READY")
            self.assertEqual(result.publication_status, "PLANNED")
            self.assertTrue(Path(result.package_path).is_file())
            self.assertTrue((Path(result.archive_dir) / "00_INDEX.md").is_file())
            self.assertTrue((Path(result.archive_dir) / "05_MANIFESTS" / "archive_manifest.json").is_file())

    def test_final_archive_requires_drive_and_ledger(self):
        self.assertEqual(
            archive.archive_completion_state(drive_upload_verified=False, ledger_write_verified=False),
            "PACKAGE_READY",
        )
        self.assertEqual(
            archive.archive_completion_state(drive_upload_verified=True, ledger_write_verified=False),
            "PACKAGE_READY",
        )
        self.assertEqual(
            archive.archive_completion_state(drive_upload_verified=True, ledger_write_verified=True),
            "ACCEPTED_ARCHIVED",
        )

    def test_ledger_row_marks_final_archive_only_after_drive_ref_exists(self):
        with tempfile.TemporaryDirectory() as td:
            spec = self.base_spec(td)
            result = archive.build_archive_package(spec, Path(td) / "archive")
            row = archive.ledger_row(result, spec, "folder-ref", "package-ref")
            self.assertEqual(len(row), 23)
            self.assertEqual(row[9], "ACCEPTED_ARCHIVED")
            self.assertEqual(row[10], "PLANNED")
            with self.assertRaisesRegex(archive.ArchiveError, "ARCHIVE_UPLOAD_FAILED"):
                archive.ledger_row(result, spec, "", "")

    def test_missing_required_group_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            spec = self.base_spec(td)
            spec["files"] = [f for f in spec["files"] if f["group"] != "RESEARCH"]
            with self.assertRaisesRegex(archive.ArchiveError, "ARCHIVE_PACKAGE_INCOMPLETE"):
                archive.build_archive_package(spec, Path(td) / "archive")

    def test_acceptance_required(self):
        with tempfile.TemporaryDirectory() as td:
            spec = self.base_spec(td)
            spec["acceptance_confirmed"] = False
            with self.assertRaisesRegex(archive.ArchiveError, "HUMAN_ACCEPTANCE_REQUIRED"):
                archive.build_archive_package(spec, Path(td) / "archive")

    def test_accepted_archive_candidate_is_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            spec = self.base_spec(td)
            out = Path(td) / "archive"
            archive.build_archive_package(spec, out)
            with self.assertRaisesRegex(archive.ArchiveError, "ARCHIVE_IMMUTABLE_CONFLICT"):
                archive.build_archive_package(spec, out)


if __name__ == '__main__':
    unittest.main()
