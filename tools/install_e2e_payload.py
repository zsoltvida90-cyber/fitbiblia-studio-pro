#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]

LOCKED_BLOBS = {
    "content_os/queue/production_queue.py": "a040655f83851272f323453e255b0dff17ea65a2",
    "content_os/archive/product_archive.py": "57efdd67b6d0e5f5ab22f7f5fb10ad82997d2ac6",
    "content_os/performance/objective_engine.py": "e70aa7b424bc91adaf97f01f8755a47974d00fd1",
    "content_os/learning/learning_engine.py": "67b822c4e02f3431af3c0835b511e99a5e52a11b",
    "content_os/integrations/meta_adapter.py": "a98ab7c0ead212ca374f61a8ef989fb9d650bc26",
    "content_os/renderers/carousel_renderer_v2.py": "9ba2d96e0317556c89eda30180cf47b87c321f9a",
    "content_os/renderers/format_pipeline.py": "6ac3da456cb53ada98d69ea40ebb5699721a856f",
    "content_os/renderers/component_registry.py": "f8b1d35abaf6412dbae74a0e727280b6a3770cc0",
    "content_os/renderers/render_primitives.py": "10326d3b286b2b857a41aabcf0a5987c09d1c5e8",
    "content_os/renderers/asset_manifest.json": "63f1456a2cf32b9f74f39ec87efef96fdbf3e6c3",
}

PROTECTED_PREFIXES = tuple(LOCKED_BLOBS)
PAYLOAD_PARTS = [ROOT / "tools" / f"e2e_payload_part{i}.txt" for i in range(1, 5)]


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def verify_repo_contract() -> None:
    failures = []
    for rel, expected in LOCKED_BLOBS.items():
        p = ROOT / rel
        if not p.is_file():
            failures.append(f"MISSING:{rel}")
            continue
        actual = git_blob_sha(p.read_bytes())
        if actual != expected:
            failures.append(f"DRIFT:{rel}:expected={expected}:actual={actual}")
    if failures:
        raise SystemExit("FIT_BIBLIA_CONTRACT_PREFLIGHT_FAIL\n" + "\n".join(failures))


def load_payload() -> bytes:
    missing = [str(p.relative_to(ROOT)) for p in PAYLOAD_PARTS if not p.is_file()]
    if missing:
        raise SystemExit("PAYLOAD_PART_MISSING:" + ",".join(missing))
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in PAYLOAD_PARTS)
    try:
        return lzma.decompress(base64.b64decode(encoded))
    except Exception as exc:
        raise SystemExit(f"PAYLOAD_DECODE_FAIL:{exc}") from exc


def safe_members(tf: tarfile.TarFile):
    for member in tf.getmembers():
        name = member.name.replace("\\", "/").lstrip("/")
        if not name or name.startswith("../") or "/../" in name:
            raise SystemExit(f"PAYLOAD_PATH_INVALID:{member.name}")
        target = (ROOT / name).resolve()
        if ROOT.resolve() not in target.parents and target != ROOT.resolve():
            raise SystemExit(f"PAYLOAD_PATH_ESCAPE:{member.name}")
        if name in PROTECTED_PREFIXES:
            raise SystemExit(f"PROTECTED_OVERWRITE_ATTEMPT:{name}")
        if member.issym() or member.islnk():
            raise SystemExit(f"PAYLOAD_LINK_FORBIDDEN:{name}")
        yield member


def extract_payload(raw_tar: bytes) -> list[str]:
    written = []
    with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:") as tf:
        members = list(safe_members(tf))
        for member in members:
            name = member.name.replace("\\", "/").lstrip("/")
            target = ROOT / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is None:
                raise SystemExit(f"PAYLOAD_FILE_READ_FAIL:{name}")
            target.write_bytes(src.read())
            written.append(name)
    return written


def write_receipt(written: list[str]) -> None:
    receipt = {
        "status": "INSTALLED_TO_INTEGRATION_BRANCH_WORKTREE",
        "protected_contract_verified": True,
        "written_files": [],
    }
    for rel in sorted(written):
        p = ROOT / rel
        receipt["written_files"].append({
            "path": rel,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size,
        })
    (ROOT / "INTEGRATION_BRIDGE_V1_INSTALL_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    verify_repo_contract()
    raw = load_payload()
    written = extract_payload(raw)
    write_receipt(written)
    print("FIT_BIBLIA_E2E_PAYLOAD_INSTALL: PASS")
    print("Written files:", len(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
