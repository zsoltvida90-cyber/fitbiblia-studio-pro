from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

VALID_OBJECTIVES = {"FOLLOW", "SAVE", "SHARE", "COMMENT", "TRUST", "CONVERT"}
RESOLVED_NODE_STATES = {"VALIDATED", "PARTIAL_REUSED", "EVIDENCE_LIMITED", "DEFERRED", "OUT_OF_SCOPE"}
UNRESOLVED_NODE_STATES = {"RESEARCH_NEEDED", "GAP_UNASSESSED", "UNKNOWN", ""}
VALID_CAMPAIGN_STATES = {
    "DRAFT_RESEARCH_DEPENDENT", "READY_FOR_HUMAN_REVIEW", "APPROVED",
    "ACTIVE", "PAUSED", "COMPLETE", "SYNTHESIS", "CLOSED"
}
VALID_ASSET_STATES = {
    "RESEARCH_DEPENDENT", "READY_FOR_MASTER", "MASTERED", "PLANNED",
    "SCHEDULED", "PUBLISHED", "FAILED", "ARCHIVED"
}
VALID_PRODUCT_AUTHORITY_SOURCES = {
    "TOPIC_DOSSIER", "RESEARCH_BUNDLE", "KNOWLEDGE_CLAIM",
    "EVIDENCE_PACKET", "APPROVED_MASTER"
}
SOCIAL_DERIVATIVE_SOURCES = {"CAROUSEL", "REEL", "STORY", "STATIC_POST", "CAPTION", "SOCIAL_ASSET"}


class CampaignError(ValueError):
    pass


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def validate_topic_hub(record: Mapping[str, object]) -> dict:
    out = dict(record)
    required = ("topic_hub_id", "title", "dossier_ref", "dossier_version", "research_status")
    for field in required:
        if not _s(out.get(field)):
            raise CampaignError(f"{field.upper()}_REQUIRED")
    if _s(out.get("campaign_readiness")).upper() == "READY" and _s(out.get("research_status")).upper() != "DOSSIER_READY":
        raise CampaignError("CAMPAIGN_READINESS_REQUIRES_DOSSIER_READY")
    return out


def validate_topic_node(record: Mapping[str, object]) -> dict:
    out = dict(record)
    for field in ("node_id", "topic_hub_id", "title", "research_question", "research_status"):
        if not _s(out.get(field)):
            raise CampaignError(f"{field.upper()}_REQUIRED")
    status = _s(out.get("research_status")).upper()
    if status in {"VALIDATED", "PARTIAL_REUSED"} and not (_s(out.get("research_ids")) or _s(out.get("claim_ids"))):
        raise CampaignError("RESOLVED_NODE_REQUIRES_PROVENANCE")
    return out


def dossier_readiness(nodes: Sequence[Mapping[str, object]]) -> dict:
    if not nodes:
        raise CampaignError("TOPIC_NODES_REQUIRED")
    unresolved = []
    high_priority_unresolved = []
    resolved = 0
    for node in nodes:
        validate_topic_node(node)
        status = _s(node.get("research_status")).upper()
        nid = _s(node.get("node_id"))
        if status in RESOLVED_NODE_STATES:
            resolved += 1
        else:
            unresolved.append(nid)
            if _s(node.get("human_priority")).upper() == "HIGH":
                high_priority_unresolved.append(nid)
    coverage = round(resolved / len(nodes), 4)
    return {
        "node_count": len(nodes),
        "resolved_node_count": resolved,
        "coverage_ratio": coverage,
        "unresolved_node_ids": unresolved,
        "high_priority_unresolved_node_ids": high_priority_unresolved,
        "dossier_ready": len(unresolved) == 0,
    }


def validate_campaign(record: Mapping[str, object], *, dossier_ready: bool = False, human_approved: bool = False) -> dict:
    out = dict(record)
    for field in ("campaign_id", "topic_hub_id", "title", "status"):
        if not _s(out.get(field)):
            raise CampaignError(f"{field.upper()}_REQUIRED")
    state = _s(out.get("status")).upper()
    if state not in VALID_CAMPAIGN_STATES:
        raise CampaignError("CAMPAIGN_STATUS_INVALID")
    try:
        weeks = int(out.get("campaign_weeks", 0))
    except Exception as exc:
        raise CampaignError("CAMPAIGN_WEEKS_INVALID") from exc
    if weeks < 1:
        raise CampaignError("CAMPAIGN_WEEKS_INVALID")
    if state in {"APPROVED", "ACTIVE"}:
        if not dossier_ready:
            raise CampaignError("DOSSIER_NOT_READY")
        if not human_approved:
            raise CampaignError("HUMAN_CAMPAIGN_APPROVAL_REQUIRED")
    if state == "ACTIVE" and not _s(out.get("start_date")):
        raise CampaignError("CAMPAIGN_START_DATE_REQUIRED")
    return out


def validate_campaign_asset(record: Mapping[str, object], *, node: Mapping[str, object] | None = None) -> dict:
    out = dict(record)
    for field in ("campaign_asset_id", "campaign_id", "topic_hub_id", "objective", "status"):
        if not _s(out.get(field)):
            raise CampaignError(f"{field.upper()}_REQUIRED")
    objective = _s(out.get("objective")).upper()
    if objective not in VALID_OBJECTIVES:
        raise CampaignError("OBJECTIVE_INVALID")
    state = _s(out.get("status")).upper()
    if state not in VALID_ASSET_STATES:
        raise CampaignError("CAMPAIGN_ASSET_STATUS_INVALID")
    if state in {"MASTERED", "PLANNED", "SCHEDULED", "PUBLISHED", "ARCHIVED"} and not _s(out.get("master_id")):
        raise CampaignError("MASTER_AUTHORITY_REQUIRED")
    if node is not None:
        validate_topic_node(node)
        node_status = _s(node.get("research_status")).upper()
        if state != "RESEARCH_DEPENDENT" and node_status in UNRESOLVED_NODE_STATES:
            raise CampaignError("NODE_RESEARCH_REQUIRED")
    return out


def campaign_balance(assets: Sequence[Mapping[str, object]]) -> dict:
    if not assets:
        raise CampaignError("CAMPAIGN_ASSETS_REQUIRED")
    waves = Counter()
    objectives = Counter()
    outputs = Counter()
    for asset in assets:
        validate_campaign_asset(asset)
        waves[_s(asset.get("wave")).upper() or "UNSPECIFIED"] += 1
        objectives[_s(asset.get("objective")).upper()] += 1
        outputs[_s(asset.get("output_type")).upper() or "UNSPECIFIED"] += 1
    warnings = []
    if len(objectives) == 1 and len(assets) >= 4:
        warnings.append("OBJECTIVE_MONOTONY")
    if len(outputs) == 1 and len(assets) >= 6:
        warnings.append("FORMAT_MONOTONY")
    if len(waves) == 1 and len(assets) >= 6:
        warnings.append("NARRATIVE_WAVE_MONOTONY")
    return {"wave_counts": dict(waves), "objective_counts": dict(objectives), "output_counts": dict(outputs), "warnings": warnings}


def threaded_feed_share(*, campaign_social_per_week: int, flex_social_per_week: int) -> float:
    if campaign_social_per_week < 0 or flex_social_per_week < 0:
        raise CampaignError("CADENCE_INVALID")
    total = campaign_social_per_week + flex_social_per_week
    if total == 0:
        raise CampaignError("CADENCE_INVALID")
    return round(campaign_social_per_week / total, 4)


def validate_product_authority_sources(source_types: Sequence[str]) -> dict:
    normalized = {_s(x).upper() for x in source_types if _s(x)}
    if not normalized:
        raise CampaignError("PRODUCT_SOURCE_REQUIRED")
    authoritative = normalized & VALID_PRODUCT_AUTHORITY_SOURCES
    social_only = normalized and normalized <= SOCIAL_DERIVATIVE_SOURCES
    if social_only or not authoritative:
        raise CampaignError("PRODUCT_SOURCE_AUTHORITY_INVALID")
    return {
        "authoritative_source_types": sorted(authoritative),
        "social_derivative_refs_allowed_as_packaging_context": bool(normalized & SOCIAL_DERIVATIVE_SOURCES),
        "authority_ok": True,
    }


def productization_gate(*, dossier_ready: bool, claim_integrity_ok: bool, unique_value_defined: bool,
                        human_product_decision: bool, audience_signal_available: bool = False) -> dict:
    blockers = []
    if not dossier_ready:
        blockers.append("DOSSIER_NOT_READY")
    if not claim_integrity_ok:
        blockers.append("CLAIM_INTEGRITY_REQUIRED")
    if not unique_value_defined:
        blockers.append("PRODUCT_UNIQUE_VALUE_REQUIRED")
    if blockers:
        return {"status": "NOT_READY", "blockers": blockers, "audience_signal_available": audience_signal_available}
    if not human_product_decision:
        return {"status": "READY_FOR_HUMAN_PRODUCT_DECISION", "blockers": ["HUMAN_PRODUCT_DECISION_REQUIRED"], "audience_signal_available": audience_signal_available}
    return {"status": "PRODUCT_BLUEPRINT_ALLOWED", "blockers": [], "audience_signal_available": audience_signal_available}


def can_launch_campaign(*, hub: Mapping[str, object], nodes: Sequence[Mapping[str, object]],
                        campaign: Mapping[str, object], assets: Sequence[Mapping[str, object]],
                        human_approved: bool = False) -> dict:
    validate_topic_hub(hub)
    readiness = dossier_readiness(nodes)
    validate_campaign(campaign, dossier_ready=readiness["dossier_ready"], human_approved=human_approved)
    node_map = {_s(n.get("node_id")): n for n in nodes}
    for asset in assets:
        node_id = _s(asset.get("node_id"))
        node = node_map.get(node_id)
        validate_campaign_asset(asset, node=node)
    return {
        "launch_allowed": readiness["dossier_ready"] and human_approved,
        "dossier": readiness,
        "balance": campaign_balance(assets),
    }
