"""Ground Mind proposals in mechanisms and experiment capabilities that actually exist."""
KNOWN_MECHANISMS={
 'selection':['rank_fraction','evidence_n','catastrophe_rate','age_windows','family_share','specialist_bonus'],
 'validation':['prospective_cutoff','independent_opportunities','future_return','shadow_plan'],
 'ecology':['reproductive_access','replacement_pressure','rare_family_protection'],
 'reproduction':['bloodline_reproductive_credit','shadow_brood','parent_genome','mutation','descendant_quality','nursery_stage','extinction'],
 'population':['dynamic_worker_count','per_bloodline_soft_cap','evidence_justified_capacity','new_bloodline_admission']}
ALLOWED_EXPERIMENTS={'compare_selection_rule','ablate_selection_feature','raise_evidence_requirement',
                     'stratify_by_regime','stratify_by_niche','request_more_data','queen_shadow_scouts'}
FORBIDDEN_PARAM_HINTS={'learning_rate','epochs','batch_size','optimizer','gradient','loss_function'}

def mechanism_packet():
 return {'known_mechanisms':KNOWN_MECHANISMS,'available_experiments':sorted(ALLOWED_EXPERIMENTS),
         'epistemic_rule':'Label claims as known, inferred, or speculative. Unknown mechanisms must be requested as data, never invented.'}

def validate_grounding(message):
 payload=message.get('payload') or {}; blob=str(payload).lower()
 if any(x in blob for x in FORBIDDEN_PARAM_HINTS): return False,'invented_training_parameter'
 exp=payload.get('experiment_type')
 if message.get('action')=='request_experiment' and exp not in ALLOWED_EXPERIMENTS:return False,'unsupported_experiment'
 claims=payload.get('claims',[])
 if claims and any(c.get('status') not in ('known','inferred','speculative') for c in claims if isinstance(c,dict)):return False,'unlabelled_claim'
 return True,'ok'
