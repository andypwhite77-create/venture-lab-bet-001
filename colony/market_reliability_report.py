"""Read-only, non-executing market data reliability report.

Coverage is measured over actually required token/cycle pairs; absence of a
candidate is not counted as a failure. No promotion or trading authority.
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from db import init_db, connection


def summarize(cycles, now=None, hours=24):
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    relevant = [c for c in cycles if start <= c['completed_at'] <= now]
    per_token = defaultdict(lambda: {'required': 0, 'observed': 0, 'missing': 0, 'reasons': {}})
    required = observed = 0
    for cycle in relevant:
        details = cycle.get('details') or {}
        if isinstance(details, str):
            details = json.loads(details)
        # Older cycles do not contain a complete required-mint inventory;
        # don't invent token-level successes from them.
        expected_mints = details.get('required_mints')
        missing_mints = set(details.get('missing_mints') or [])
        if expected_mints is not None:
            for mint in set(expected_mints):
                entry = per_token[mint]
                entry['required'] += 1
                if mint in missing_mints:
                    entry['missing'] += 1
                    for reason in details.get('provider_failures', {}).get(mint, []):
                        entry['reasons'][reason] = entry['reasons'].get(reason, 0) + 1
                else:
                    entry['observed'] += 1
        required += int(cycle['active'])
        observed += int(cycle['recorded'])
    tokens = []
    for mint, value in sorted(per_token.items()):
        rate = value['observed'] / value['required'] if value['required'] else None
        tokens.append({'mint': mint, **value, 'coverage': round(rate, 4),
                       'reliable_95pct': value['required'] >= 20 and rate >= .95})
    coverage = observed / required if required else None
    span = (max(c['completed_at'] for c in relevant) - min(c['completed_at'] for c in relevant)).total_seconds() if len(relevant) > 1 else 0
    # A few clean cycles must never pass a 24-hour acceptance gate.
    window_complete = span >= hours * 3600 - 180 and len(relevant) >= hours * 45
    return {'window_hours': hours, 'cycles': len(relevant), 'span_hours': round(span / 3600, 2),
            'required_observations': required, 'recorded_observations': observed,
            'weighted_coverage': round(coverage, 4) if coverage is not None else None,
            'perfect_cycles': sum(c['active'] == c['recorded'] for c in relevant),
            'window_complete': window_complete,
            'coverage_target_met': bool(window_complete and coverage is not None and coverage >= .95),
            'token_scoring_cycles': sum('required_mints' in (c.get('details') or {}) for c in relevant),
            'tokens': tokens,
            'authority': 'diagnostic_only_no_training_no_spartan_no_live',
            'note': 'Token coverage counts required collection cycles, not complete trade holding-period histories. Provider receipt time is not source quote time.'}


async def run(hours=24):
    await init_db()
    async with connection() as conn:
        rows = await conn.fetch('SELECT completed_at,active,recorded,details FROM market_data_cycles WHERE completed_at >= now() - ($1::int * interval \'1 hour\') ORDER BY completed_at', hours)
    return summarize([dict(r) for r in rows], hours=hours)


if __name__ == '__main__':
    print(json.dumps(asyncio.run(run())))
