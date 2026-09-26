"""Non-signing execution boundary. LIVE signing deliberately absent."""
from dataclasses import dataclass
from time import time
@dataclass
class Limits:
 max_notional:float=10.0; max_slippage_bps:int=150; max_daily_loss:float=50.0
 max_open_notional:float=50.0; max_age_s:int=15

def validate(intent,limits,state):
 required={'intent_id','mint','side','notional','max_slippage_bps','created_at'}
 if not required <= set(intent): return False,'missing_fields'
 if intent['side'] not in ('buy','sell'): return False,'bad_side'
 if float(intent['notional'])<=0 or float(intent['notional'])>limits.max_notional:return False,'notional_limit'
 if int(intent['max_slippage_bps'])>limits.max_slippage_bps:return False,'slippage_limit'
 if time()-float(intent['created_at'])>limits.max_age_s:return False,'stale_intent'
 if state.get('daily_pnl',0)<=-limits.max_daily_loss:return False,'daily_loss_kill'
 if state.get('open_notional',0)+float(intent['notional'])>limits.max_open_notional:return False,'exposure_limit'
 if intent['intent_id'] in state.get('seen_ids',set()):return False,'duplicate'
 return True,'ok'

def execute_simulated(intent,limits,state,quote):
 ok,why=validate(intent,limits,state)
 if not ok:return {'accepted':False,'reason':why,'broadcast':False}
 if quote.get('slippage_bps',10)>intent['max_slippage_bps']:return {'accepted':False,'reason':'quote_slippage','broadcast':False}
 return {'accepted':True,'reason':'ok','broadcast':False,'mode':'simulated','intent_id':intent['intent_id'],'quoted_out':quote.get('out_amount')}
