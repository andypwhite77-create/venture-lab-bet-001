"""Periodic read-only Queen research priorities, written atomically for inspection.
No reward, resource increase, breeding, promotion, or order authority.
"""
import asyncio,json,os,tempfile
from datetime import datetime,timezone
from colony.queen_funded_attribution import run as attribution
from colony.queen_economic_feedback import explain
OUTPUT='/queen-state/queen_economic_feedback_snapshot.json'

def snapshot(attributed,now):
 report=explain(attributed)
 return {'generated_at':now.isoformat(),'feedback':report,'reward_authorized':False,'research_capacity_increase':0,'authority':'research_diagnostics_only'}
async def run(path=OUTPUT):
 data=snapshot(await attribution(),datetime.now(timezone.utc))
 os.makedirs(os.path.dirname(path),exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.queen_feedback_',dir=os.path.dirname(path),text=True)
 try:
  with os.fdopen(fd,'w') as f:json.dump(data,f,sort_keys=True)
  os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)
 return {'path':path,'families':list(data['feedback']['families']),'authority':data['authority']}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))
