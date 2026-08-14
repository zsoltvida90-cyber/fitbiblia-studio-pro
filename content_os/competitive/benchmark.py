from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

VALID_COHORTS = {"HU_DIRECT","GLOBAL_CATEGORY_LEADER","FORMAT_MASTER","ADJACENT_EXCELLENCE"}
VALID_BUCKETS = {"TOP","MID","LOW","RECENT","MANUAL"}
VALID_PATTERN_STATUS = {"OBSERVATION","EARLY_SIGNAL","HYPOTHESIS","HUMAN_APPROVED","REJECTED"}
VALID_CONFIDENCE = {"LOW","MEDIUM","HIGH","UNKNOWN"}
VALID_ACCESS_LEVELS = {"FULL_CAROUSEL","CAPTION_METADATA_ONLY","METADATA_ONLY","UNKNOWN"}

class BenchmarkError(ValueError):
    pass

def _s(v) -> str:
    return "" if v is None else str(v).strip()

def _f(v):
    if v in (None,"","UNKNOWN"):
        return None
    try:
        return float(v)
    except Exception as exc:
        raise BenchmarkError("METRIC_INVALID") from exc

def validate_account(record: Mapping[str, object]) -> dict:
    out = dict(record)
    if _s(out.get("cohort_type")).upper() not in VALID_COHORTS:
        raise BenchmarkError("COHORT_INVALID")
    if not _s(out.get("handle")):
        raise BenchmarkError("HANDLE_REQUIRED")
    if _s(out.get("platform")).upper() != "INSTAGRAM":
        raise BenchmarkError("PLATFORM_INVALID")
    if not _s(out.get("captured_at")):
        raise BenchmarkError("CAPTURE_TIMESTAMP_REQUIRED")
    if not _s(out.get("source_refs")):
        raise BenchmarkError("SOURCE_REF_REQUIRED")
    for k in ("follower_count","engagement_rate","growth_rate_30d","posting_frequency_30d"):
        if _s(out.get(k)) not in ("","UNKNOWN"):
            _f(out.get(k))
    if any(_s(out.get(k)) not in ("","UNKNOWN") for k in ("follower_count","engagement_rate","growth_rate_30d","posting_frequency_30d")):
        if not _s(out.get("metric_method")) and not _s(out.get("follower_source")):
            raise BenchmarkError("METRIC_METHOD_REQUIRED")
    out["cohort_type"] = _s(out.get("cohort_type")).upper()
    out["platform"] = "INSTAGRAM"
    return out

def validate_swipe(record: Mapping[str, object]) -> dict:
    out = dict(record)
    bucket = _s(out.get("sample_bucket")).upper()
    if bucket not in VALID_BUCKETS:
        raise BenchmarkError("SAMPLE_BUCKET_INVALID")
    if not _s(out.get("competitor_id")):
        raise BenchmarkError("COMPETITOR_ID_REQUIRED")
    if not _s(out.get("post_url")):
        raise BenchmarkError("POST_URL_REQUIRED")
    if not _s(out.get("captured_at")):
        raise BenchmarkError("CAPTURE_TIMESTAMP_REQUIRED")
    if not _s(out.get("source_refs")):
        raise BenchmarkError("SOURCE_REF_REQUIRED")
    access = _s(out.get("content_access_level") or "UNKNOWN").upper()
    if access not in VALID_ACCESS_LEVELS:
        raise BenchmarkError("CONTENT_ACCESS_LEVEL_INVALID")
    for k in ("likes","comments","views","saves_visible","shares_visible","engagement_proxy","account_baseline_proxy"):
        if _s(out.get(k)) not in ("","UNKNOWN"):
            _f(out.get(k))
    if _s(out.get("engagement_proxy")) not in ("","UNKNOWN") and not _s(out.get("metric_method")):
        raise BenchmarkError("METRIC_METHOD_REQUIRED")
    if access == "FULL_CAROUSEL" and _s(out.get("format")).upper() != "CAROUSEL":
        raise BenchmarkError("CONTENT_ACCESS_FORMAT_MISMATCH")
    out["sample_bucket"] = bucket
    out["content_access_level"] = access
    return out

def relative_performance_index(engagement_proxy, account_baseline_proxy):
    a = _f(engagement_proxy)
    b = _f(account_baseline_proxy)
    if a is None or b is None or b <= 0:
        return None
    return round(a / b, 4)

def sample_balance(swipes: Sequence[Mapping[str, object]]) -> dict:
    counts = {k:0 for k in ("TOP","MID","LOW")}
    for r in swipes:
        b = _s(r.get("sample_bucket")).upper()
        if b in counts:
            counts[b]+=1
    target = {"TOP":3,"MID":4,"LOW":3}
    complete = all(counts[k] >= target[k] for k in target)
    return {"counts":counts,"target":target,"balanced_minimum_met":complete}

def classify_pattern(sample_n: int, unique_accounts: int,
                     early_posts: int = 5, early_accounts: int = 3,
                     hypothesis_posts: int = 15, hypothesis_accounts: int = 5) -> str:
    if sample_n >= hypothesis_posts and unique_accounts >= hypothesis_accounts:
        return "HYPOTHESIS"
    if sample_n >= early_posts and unique_accounts >= early_accounts:
        return "EARLY_SIGNAL"
    return "OBSERVATION"

def aggregate_pattern(records: Sequence[Mapping[str, object]], *,
                      pattern_type: str, pattern_name: str,
                      early_posts: int = 5, early_accounts: int = 3,
                      hypothesis_posts: int = 15, hypothesis_accounts: int = 5,
                      require_full_carousel: bool = False) -> dict:
    if not records:
        raise BenchmarkError("SAMPLE_REQUIRED")
    if require_full_carousel:
        records = [r for r in records if _s(r.get("content_access_level")).upper() == "FULL_CAROUSEL"]
        if not records:
            raise BenchmarkError("FULL_CAROUSEL_SAMPLE_REQUIRED")
    ids = [_s(r.get("swipe_id")) for r in records if _s(r.get("swipe_id"))]
    accounts = sorted({_s(r.get("competitor_id")) for r in records if _s(r.get("competitor_id"))})
    status = classify_pattern(len(records), len(accounts), early_posts, early_accounts,
                              hypothesis_posts, hypothesis_accounts)
    perf = []
    for r in records:
        x = relative_performance_index(r.get("engagement_proxy"), r.get("account_baseline_proxy"))
        if x is not None:
            perf.append(x)
    perf_signal = "UNKNOWN"
    if perf:
        perf_signal = round(sum(perf)/len(perf),4)
    confidence = "LOW" if status == "OBSERVATION" else ("MEDIUM" if status == "EARLY_SIGNAL" else "HIGH")
    return {
        "pattern_type": pattern_type,
        "pattern_name": pattern_name,
        "source_swipe_ids": ";".join(ids),
        "source_account_ids": ";".join(accounts),
        "sample_n": len(records),
        "unique_accounts": len(accounts),
        "performance_signal": perf_signal,
        "confidence": confidence,
        "status": status,
        "human_approved": False,
        "auto_policy_adopt": False,
        "science_authority": False,
        "requires_full_carousel": require_full_carousel,
    }

def approve_pattern(pattern: Mapping[str, object], *, human_approved: bool = False) -> dict:
    if not human_approved:
        raise BenchmarkError("HUMAN_POLICY_APPROVAL_REQUIRED")
    out = dict(pattern)
    out["status"] = "HUMAN_APPROVED"
    out["human_approved"] = True
    return out

def science_claim_allowed_from_competitor(_: Mapping[str, object]) -> bool:
    return False

def visual_rule_allowed_from_record(record: Mapping[str, object]) -> bool:
    return _s(record.get("content_access_level")).upper() == "FULL_CAROUSEL"

def metric_or_unknown(v):
    return "UNKNOWN" if v in (None,"") else v
