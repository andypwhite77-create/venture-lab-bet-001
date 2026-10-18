"""Bounded Queen historical research with shared-memory duplicate rejection."""
import asyncio,json
from db import init_db,connection
from colony.queen_autonomous_research import _inference
from colony.queen_historical_hypothesis import run
from colony.entry_failure_lab import FIELDS
from colony.queen_research_memory import summarize
QUEENS=('reversal','momentum','exhaustion','pattern_recognition')

def allowed(feature,direction,memory):
 return feature in FIELDS and direction in ('high','low') and not any(x['feature']==feature and x['direction']==direction for x in memory['experiments'])

async def propose(queen):
 if queen not in QUEENS:raise ValueError('unknown queen')
 await init_db()
 async with connection() as c:
  history=await c.fetch('SELECT queen,feature,direction,result FROM queen_historical_hypotheses ORDER BY id')
 memory=summarize(history)
 if len(memory['experiments'])>=len(FIELDS)*2:return {'status':'research_space_exhausted','queen':queen,'promotion_allowed':False}
 prompt=('You are the '+queen+' strategy Queen. Propose ONE falsifiable historical entry-filter hypothesis. '
  'Use one feature from '+','.join(FIELDS)+' and direction high or low. '
  'Do NOT repeat an earlier hypothesis (same feature and direction). Previous experiments: '
  +json.dumps(memory['experiments'])[:1900]+'. Historical outcomes are discovery only, not independent validation. '
  'Return JSON keys feature, direction, rationale. No code, URLs or SQL.')
 proposal=await _inference(prompt,220)
 feature=proposal.get('feature');direction=proposal.get('direction')
 if not allowed(feature,direction,memory):return {'status':'rejected_duplicate_or_unapproved_proposal','queen':queen,'promotion_allowed':False}
 evidence=await run(queen,feature,direction)
 return {'status':'tested_research_only','proposal':{'queen':queen,'feature':feature,'direction':direction,'rationale':str(proposal.get('rationale',''))[:250]},'evidence':evidence,'promotion_allowed':False}
if __name__=='__main__':
 import sys
 if len(sys.argv)!=2:raise SystemExit('usage: python -m colony.queen_historical_autoresearch QUEEN')
 print(json.dumps(asyncio.run(propose(sys.argv[1]))))
