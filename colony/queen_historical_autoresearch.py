"""Queen proposes a bounded research hypothesis; deterministic engine tests it.
One attempt per invocation; no arbitrary SQL, agent tools, auto-promotion, or live trading.
"""
import asyncio,json
from colony.queen_autonomous_research import _inference
from colony.queen_historical_hypothesis import run
from colony.entry_failure_lab import FIELDS
QUEENS=('reversal','momentum','exhaustion','pattern_recognition')
async def propose(queen):
 if queen not in QUEENS:raise ValueError('unknown queen')
 prompt=('You are the '+queen+' strategy Queen. Propose ONE falsifiable historical entry-filter research hypothesis. '
   'Use ONLY one feature from '+','.join(FIELDS)+'. '
   'Choose direction high or low. Historical data is for discovery only, not promotion. '
   'Return only JSON with keys feature, direction, rationale. No commands, URLs or SQL.')
 proposal=await _inference(prompt,150)
 feature=proposal.get('feature');direction=proposal.get('direction')
 if feature not in FIELDS or direction not in ('high','low'):return {'status':'rejected_unapproved_proposal','queen':queen}
 evidence=await run(queen,feature,direction)
 return {'status':'tested_research_only','proposal':{'queen':queen,'feature':feature,'direction':direction,'rationale':str(proposal.get('rationale',''))[:250]},'evidence':evidence,'promotion_allowed':False}
if __name__=='__main__':
 import sys
 if len(sys.argv)!=2:raise SystemExit('usage: python -m colony.queen_historical_autoresearch QUEEN')
 print(json.dumps(asyncio.run(propose(sys.argv[1]))))
