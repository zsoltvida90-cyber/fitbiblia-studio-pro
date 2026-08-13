from dataclasses import dataclass

@dataclass(frozen=True)
class LearningDecision:
    confidence_state: str
    eligible: bool
    reason: str

PROTECTED_SCIENCE_FIELDS = {
    'claim_id','wording','plain_wording','topic','domain','claim_type','grade','evidence_grade',
    'validation_status','status','claim_status','freshness_class','last_reviewed','review_due',
    'revalidation_required','revalidation_trigger','conditions','caveats','allowed_wording',
    'forbidden_wording','evidence_packet_ids','source_ids','version','brand_policy'
}

def classify(sample_n, distribution_gate, hypothesis='', source_asset_ids=None, early_signal_min=10, active_balance_min=20):
    if isinstance(sample_n, bool) or not isinstance(sample_n, (int, float)) or sample_n < 0:
        return LearningDecision('INTEGRITY_FAIL', False, 'invalid_sample_n')
    if not isinstance(early_signal_min, (int, float)) or not isinstance(active_balance_min, (int, float)) or early_signal_min < 1 or active_balance_min <= early_signal_min:
        return LearningDecision('INTEGRITY_FAIL', False, 'invalid_thresholds')
    if distribution_gate != 'OK':
        return LearningDecision('REJECTED', False, 'distribution_gate_not_ok')
    if sample_n < early_signal_min:
        return LearningDecision('INSUFFICIENT_DATA', False, 'below_early_signal_min')
    if sample_n < active_balance_min:
        return LearningDecision('EARLY_SIGNAL', True, 'signal_only_not_mature')
    if not str(hypothesis).strip():
        return LearningDecision('INTEGRITY_FAIL', False, 'hypothesis_required')
    if not [x for x in (source_asset_ids or []) if x]:
        return LearningDecision('INTEGRITY_FAIL', False, 'source_assets_required')
    return LearningDecision('HYPOTHESIS_READY', True, 'mature_operational_sample')

def assert_no_science_mutation(target):
    raw = str(target or '').lower().replace('[','.').replace(']','').replace('/','.')
    parts = {p for p in raw.split('.') if p}
    if parts & PROTECTED_SCIENCE_FIELDS or raw.startswith(('claim.','evidence.','knowledge_registry.')):
        raise ValueError('SCIENCE_MUTATION_FORBIDDEN')
    return True
