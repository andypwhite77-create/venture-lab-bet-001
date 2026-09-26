"""Read-only Core/Sceptic precursor. It observes; it cannot mutate the live colony."""
import json
from db import connection
from colony.scoreboard import report as scoreboard
from colony.independence import opportunity_report

async def observe():
    board=await scoreboard()
    if board.get('status')=='no_run': return board
    groups={g['name']:g for g in board['groups']}
    evolved=groups.get('evolved_gen3',{}); blind=groups.get('blind',{})
    opp=await opportunity_report(board['run_id'])
    evidence=opp['comparable_mints']
    delta=opp['mean_opportunity_edge_pct'] or 0.0
    core={'mode':'observe_only','evolved_minus_blind_pct':round(delta,4),
          'comparison_evidence_mints':evidence,'opportunity_wins':opp['wins'],'opportunity_losses':opp['losses'],'recommendation':'collect_more_data'}
    sceptic={'mode':'veto_only','objections':[]}
    if evidence < 30: sceptic['objections'].append('insufficient_independent_opportunities')
    if abs(delta) < 5: sceptic['objections'].append('evolved_not_clearly_separated_from_blind')
    if evolved.get('scored_ants',0) and evolved.get('independent_mints',0) < evolved.get('scored_ants',0)/2:
        sceptic['objections'].append('many_ant_scores_share_few_underlying_tokens')
    return board,core,sceptic

async def persist():
    result=await observe()
    if isinstance(result,dict): return result
    board,core,sceptic=result; run_id=board['run_id']
    async with connection() as conn:
        for role,payload in [('core',core),('sceptic',sceptic)]:
            await conn.execute("INSERT INTO colony_observer_reports(run_id,role,report) VALUES($1,$2,$3::jsonb)",run_id,role,json.dumps(payload))
    return {'run_id':run_id,'core':core,'sceptic':sceptic}

async def main(): print(json.dumps(await persist(),indent=2,default=str))
if __name__=='__main__':
    import asyncio
    asyncio.run(main())
