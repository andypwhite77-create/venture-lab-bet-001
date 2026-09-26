"""Capability boundary for Queen/Core and Sceptic model outputs."""
ALLOWED_CORE={'observe','hypothesis','request_experiment','explain','ask_for_data'}
ALLOWED_SCEPTIC={'accept_for_test','veto','request_more_evidence','identify_confounder'}
FORBIDDEN={'execute_trade','edit_code','change_threshold','change_population','approve_self','read_secret','shell'}

def validate(message,role):
    if not isinstance(message,dict): return False,'not_object'
    action=message.get('action'); allowed=ALLOWED_CORE if role=='core' else ALLOWED_SCEPTIC
    if action in FORBIDDEN:return False,'forbidden_capability'
    if action not in allowed:return False,'unknown_action'
    if not isinstance(message.get('reasoning_summary',''),str):return False,'bad_reasoning_summary'
    return True,'ok'

def envelope(role,action,reasoning_summary,payload=None):
    msg={'role':role,'action':action,'reasoning_summary':reasoning_summary,'payload':payload or {}}
    ok,why=validate(msg,role)
    if not ok:raise ValueError(why)
    return msg
