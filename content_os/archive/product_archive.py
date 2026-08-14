from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ARCHIVE_STATUS = "ACCEPTED_ARCHIVED"
CANONICAL_ACCEPT_COMMAND = "ELFOGADOM A TERMÉKET"
ACCEPTANCE_ALIASES = {
    "elfogadom a termeket",
    "termek elfogadva",
    "mehet az archivumba",
    "ez a verzio elfogadva",
}

GROUP_DIRS = {
    "PRODUCT": "01_PRODUCT",
    "COPY": "02_COPY",
    "MASTER": "03_CONTENT_MASTER",
    "RESEARCH": "04_RESEARCH",
    "MANIFESTS": "05_MANIFESTS",
    "REPRODUCE": "06_REPRODUCE",
}
REQUIRED_GROUPS = tuple(GROUP_DIRS)


class ArchiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArchiveResult:
    archive_id: str
    archive_name: str
    package_path: str
    package_sha256: str
    content_tree_sha256: str
    archive_dir: str
    archive_status: str
    publication_status: str


def _ascii(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in value if not unicodedata.combining(c))


def _norm_command(value: str) -> str:
    value = _ascii(value).lower().strip()
    value = re.sub(r"[^\w\s-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_explicit_acceptance(message: str) -> bool:
    """Strict human gate. Ordinary praise like 'jó' or 'tetszik' must not archive."""
    return _norm_command(message) in ACCEPTANCE_ALIASES


def human_slug(title: str) -> str:
    value = _ascii(title).strip()
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise ArchiveError("ARCHIVE_TITLE_INVALID")
    return value


def normalize_token(value: str) -> str:
    value = human_slug(value)
    return "-".join(part.capitalize() for part in value.split("-"))


def build_archive_name(
    accepted_date: str,
    title: str,
    platform: str,
    output_type: str,
    version: str,
) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", accepted_date):
        raise ArchiveError("ARCHIVE_DATE_INVALID")
    if not re.fullmatch(r"\d+\.\d+", str(version)):
        raise ArchiveError("ARCHIVE_VERSION_INVALID")
    return (
        f"{accepted_date}__{human_slug(title)}__"
        f"{normalize_token(platform)}-{normalize_token(output_type)}__v{version}"
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_hash(files: Iterable[tuple[str, str]]) -> str:
    payload = "\n".join(f"{rel}\t{digest}" for rel, digest in sorted(files))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require(spec: dict[str, Any], key: str) -> Any:
    value = spec.get(key)
    if value in (None, "", []):
        raise ArchiveError(f"ARCHIVE_REQUIRED_FIELD:{key}")
    return value


def _safe_name(name: str) -> str:
    p = Path(name)
    if p.name != name or name in {"", ".", ".."}:
        raise ArchiveError("ARCHIVE_FILE_NAME_INVALID")
    return name


def _copy_entry(entry: dict[str, Any], archive_dir: Path) -> tuple[str, str]:
    group = str(_require(entry, "group")).upper()
    if group not in GROUP_DIRS:
        raise ArchiveError(f"ARCHIVE_GROUP_INVALID:{group}")
    target_dir = archive_dir / GROUP_DIRS[group]
    target_dir.mkdir(parents=True, exist_ok=True)

    name = _safe_name(str(_require(entry, "name")))
    target = target_dir / name
    if target.exists():
        raise ArchiveError(f"ARCHIVE_DUPLICATE_FILE:{group}/{name}")

    has_source = bool(entry.get("source"))
    has_content = entry.get("content") is not None
    if has_source == has_content:
        raise ArchiveError("ARCHIVE_FILE_SOURCE_CONFLICT")

    if has_source:
        source = Path(str(entry["source"]))
        if not source.is_file():
            raise ArchiveError(f"ARCHIVE_SOURCE_MISSING:{source}")
        shutil.copy2(source, target)
    else:
        target.write_text(str(entry["content"]), encoding="utf-8")

    rel = target.relative_to(archive_dir).as_posix()
    return rel, sha256_file(target)


def _human_index(spec: dict[str, Any], archive_id: str, archive_name: str) -> str:
    research_ids = ", ".join(spec.get("research_ids") or []) or "—"
    evidence_ids = ", ".join(spec.get("evidence_packet_ids") or []) or "—"
    claim_ids = ", ".join(spec.get("claim_ids") or []) or "—"
    return f"""# Fit Biblia Product Archive

Cím: {spec['title']}
Dátum: {spec['accepted_date']}
Platform: {spec['platform']}
Formátum: {spec['output_type']}
Verzió: {spec['version']}

Archive ID: {archive_id}
Asset ID: {spec['asset_id']}
Master ID: {spec['master_id']}
Research ID(k): {research_ids}
Evidence Packet ID(k): {evidence_ids}
Claim ID(k): {claim_ids}

Archív állapot: {ARCHIVE_STATUS}
Publikációs állapot az elfogadáskor: {spec['publication_status']}

Csomagnév:
{archive_name}__PACKAGE.zip

Fontos:
Az emberi termékelfogadás nem jelent publikálást. Az elfogadott csomag immutábilis;
minden későbbi változat új verzióként archiválandó.
"""


def _acceptance_record(spec: dict[str, Any], archive_id: str) -> str:
    return f"""# Product Acceptance Record

archive_id: {archive_id}
accepted_at: {spec['accepted_at']}
accepted_by: {spec.get('accepted_by', 'HUMAN')}
acceptance_command: {CANONICAL_ACCEPT_COMMAND}
asset_id: {spec['asset_id']}
master_id: {spec['master_id']}
version: {spec['version']}
archive_status: {ARCHIVE_STATUS}
publication_status_at_acceptance: {spec['publication_status']}

This record freezes the accepted product version for archival purposes.
It does not assert that the product was published.
"""


def validate_spec(spec: dict[str, Any]) -> None:
    for key in (
        "archive_id",
        "accepted_at",
        "accepted_date",
        "title",
        "version",
        "master_id",
        "asset_id",
        "platform",
        "output_type",
        "publication_status",
        "files",
    ):
        _require(spec, key)
    if spec.get("acceptance_confirmed") is not True:
        raise ArchiveError("HUMAN_ACCEPTANCE_REQUIRED")
    if spec.get("archive_status") not in (None, ARCHIVE_STATUS):
        raise ArchiveError("ARCHIVE_STATUS_INVALID")
    if not isinstance(spec["files"], list):
        raise ArchiveError("ARCHIVE_FILES_INVALID")
    groups = {str(item.get("group", "")).upper() for item in spec["files"]}
    missing = [g for g in REQUIRED_GROUPS if g not in groups]
    if missing:
        raise ArchiveError("ARCHIVE_PACKAGE_INCOMPLETE:" + ",".join(missing))


def build_archive_package(
    spec: dict[str, Any],
    output_root: str | Path,
) -> ArchiveResult:
    """
    Freeze one explicitly accepted product into a human-readable immutable folder + ZIP.

    Drive upload and PRODUCT_ARCHIVE Ledger write are intentionally separate connector
    actions performed only after this local package returns successfully.
    """
    validate_spec(spec)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    archive_name = build_archive_name(
        str(spec["accepted_date"]),
        str(spec["title"]),
        str(spec["platform"]),
        str(spec["output_type"]),
        str(spec["version"]),
    )
    archive_dir = output_root / archive_name
    zip_path = output_root / f"{archive_name}__PACKAGE.zip"
    if archive_dir.exists() or zip_path.exists():
        raise ArchiveError("ARCHIVE_IMMUTABLE_CONFLICT")

    archive_dir.mkdir(parents=True)
    copied: list[tuple[str, str]] = []
    for entry in spec["files"]:
        copied.append(_copy_entry(entry, archive_dir))

    index_path = archive_dir / "00_INDEX.md"
    index_path.write_text(
        _human_index(spec, str(spec["archive_id"]), archive_name),
        encoding="utf-8",
    )
    copied.append(("00_INDEX.md", sha256_file(index_path)))

    acceptance_dir = archive_dir / "07_ACCEPTANCE"
    acceptance_dir.mkdir(parents=True, exist_ok=True)
    acceptance_path = acceptance_dir / "acceptance_record.md"
    acceptance_path.write_text(
        _acceptance_record(spec, str(spec["archive_id"])),
        encoding="utf-8",
    )
    copied.append((
        acceptance_path.relative_to(archive_dir).as_posix(),
        sha256_file(acceptance_path),
    ))

    content_tree_sha256 = _tree_hash(copied)
    manifest = {
        "archive_schema_version": "1.0",
        "archive_id": spec["archive_id"],
        "title": spec["title"],
        "archive_name": archive_name,
        "accepted_at": spec["accepted_at"],
        "accepted_by": spec.get("accepted_by", "HUMAN"),
        "master_id": spec["master_id"],
        "asset_id": spec["asset_id"],
        "research_ids": spec.get("research_ids", []),
        "evidence_packet_ids": spec.get("evidence_packet_ids", []),
        "claim_ids": spec.get("claim_ids", []),
        "platform": spec["platform"],
        "output_type": spec["output_type"],
        "version": spec["version"],
        "publication_status_at_acceptance": spec["publication_status"],
        "archive_status": ARCHIVE_STATUS,
        "renderer_version": spec.get("renderer_version", ""),
        "asset_manifest_version": spec.get("asset_manifest_version", ""),
        "qa_status": spec.get("qa_status", ""),
        "content_tree_sha256": content_tree_sha256,
        "package_sha256_scope": "ZIP bytes; stored in PRODUCT_ARCHIVE Ledger after ZIP creation",
        "files": [
            {"path": rel, "sha256": digest}
            for rel, digest in sorted(copied)
        ],
    }
    manifest_path = archive_dir / "05_MANIFESTS" / "archive_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        raise ArchiveError("ARCHIVE_DUPLICATE_FILE:05_MANIFESTS/archive_manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in archive_dir.rglob("*") if p.is_file()):
            zf.write(path, arcname=path.relative_to(archive_dir).as_posix())

    package_sha256 = sha256_file(zip_path)
    receipt = {
        "archive_id": spec["archive_id"],
        "archive_name": archive_name,
        "archive_status": ARCHIVE_STATUS,
        "publication_status": spec["publication_status"],
        "package_path": str(zip_path),
        "package_sha256": package_sha256,
        "content_tree_sha256": content_tree_sha256,
        "ledger_sheet": "PRODUCT_ARCHIVE",
    }
    receipt_path = output_root / f"{archive_name}__ARCHIVE_RECEIPT.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ArchiveResult(
        archive_id=str(spec["archive_id"]),
        archive_name=archive_name,
        package_path=str(zip_path),
        package_sha256=package_sha256,
        content_tree_sha256=content_tree_sha256,
        archive_dir=str(archive_dir),
        archive_status=ARCHIVE_STATUS,
        publication_status=str(spec["publication_status"]),
    )


def ledger_row(result: ArchiveResult, spec: dict[str, Any], drive_folder_ref: str, drive_package_ref: str) -> list[str]:
    """Return columns A:W for FIT_BIBLIA_CONTENT_LEDGER / PRODUCT_ARCHIVE."""
    return [
        result.archive_id,
        str(spec["accepted_at"]),
        str(spec["title"]),
        result.archive_name,
        str(spec["version"]),
        str(spec["master_id"]),
        str(spec["asset_id"]),
        str(spec["platform"]),
        str(spec["output_type"]),
        result.archive_status,
        result.publication_status,
        drive_folder_ref,
        drive_package_ref,
        result.package_sha256,
        result.content_tree_sha256,
        ",".join(spec.get("research_ids", [])),
        ",".join(spec.get("evidence_packet_ids", [])),
        ",".join(spec.get("claim_ids", [])),
        str(spec.get("renderer_version", "")),
        str(spec.get("asset_manifest_version", "")),
        str(spec.get("qa_status", "")),
        str(spec.get("accepted_by", "HUMAN")),
        str(spec.get("notes", "")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze an accepted Fit Biblia product archive package.")
    parser.add_argument("spec", help="Path to archive spec JSON")
    parser.add_argument("output_root", help="Local archive staging root")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = build_archive_package(spec, args.output_root)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
