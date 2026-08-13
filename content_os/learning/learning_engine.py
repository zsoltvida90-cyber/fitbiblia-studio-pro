from dataclasses import dataclass

@dataclass(frozen=True)
class LearningDecision:
    confidence_state: str
    eligible: bool
    reason: str

def classify(sample_n, distribution_gate, hypothesis='', source_asset_ids=None, early_signal_min=10, active_balance_min=20):
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
    if target in {'claim_status','validation_status','grade','evidence_grade','allowed_wording','brand_policy'}:
        raise ValueError('SCIENCE_MUTATION_FORBIDDEN')
    return True
