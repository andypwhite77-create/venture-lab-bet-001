"""Continuously grow a local Solana DEX OHLCV research bank.

GeckoTerminal is the zero-credential backfill source. Data is research-only and
never grants promotion/live authority. Existing forward candidate/path logging remains primary.
"""
import asyncio, json, logging, time, urllib.parse, urllib.request, urllib.error, random
from datetime import datetime, timezone, timedelta
from db import init_db, connection

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
BASE='https://api.geckoterminal.com/api/v2/networks/solana/pools'
RATE_SLEEP=12.0
MAX_RETRIES=5
TRANSIENT_HTTP={401,403,429}
SIX_MONTHS=int((datetime.now(timezone.utc)-timedelta(days=183)).timestamp())

async def schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS historical_ohlcv(
      pair_address TEXT NOT NULL, timeframe TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
      open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION, close DOUBLE PRECISION,
      volume_usd DOUBLE PRECISION, source TEXT NOT NULL DEFAULT 'geckoterminal', fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY(pair_address,timeframe,ts));
      CREATE INDEX IF NOT EXISTS historical_ohlcv_ts_idx ON historical_ohlcv(ts);''')


def fetch(pair,before=None):
    q={'aggregate':1,'limit':1000,'currency':'usd'}
    if before:q['before_timestamp']=before
    url=f"{BASE}/{urllib.parse.quote(pair,safe='')}/ohlcv/hour?"+urllib.parse.urlencode(q)
    req=urllib.request.Request(url,headers={'Accept':'application/json;version=20230203','User-Agent':'venture-lab-research/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
async def backfill_pair(c,pair):
    oldest=await c.fetchval("SELECT extract(epoch from min(ts))::bigint FROM historical_ohlcv WHERE pair_address=$1 AND timeframe='1h'",pair)
    before=int(oldest)-1 if oldest else None; added=0
    while before is None or before>SIX_MONTHS:
        data=None
        for attempt in range(MAX_RETRIES):
            try:
                data=await asyncio.to_thread(fetch,pair,before); break
            except urllib.error.HTTPError as e:
                if e.code not in TRANSIENT_HTTP:
                    logging.warning('backfill_fetch_failed pair=%s http=%s err=%s',pair,e.code,e); break
                retry_after=e.headers.get('Retry-After') if e.headers else None
                if retry_after and retry_after.isdigit():
                    delay=float(retry_after)
                elif e.code in (401,403):
                    # GeckoTerminal is credential-free here; intermittent 401/403s
                    # observed during throttle bursts are edge/WAF responses. Back off
                    # much harder instead of retrying as if credentials were wrong.
                    delay=min(180.0, 30.0*(attempt+1))
                else:
                    delay=min(120.0, 8.0*(2**attempt))
                delay+=random.uniform(0,3.0)
                logging.warning('backfill_transient_http pair=%s http=%s attempt=%s sleep=%.1fs',pair,e.code,attempt+1,delay)
                await asyncio.sleep(delay)
            except Exception as e:
                logging.warning('backfill_fetch_failed pair=%s err=%s',pair,e); break
        if data is None: break
        bars=((data.get('data') or {}).get('attributes') or {}).get('ohlcv_list') or []
        if not bars:break
        rows=[]
        for b in bars:
            if int(b[0])<SIX_MONTHS:continue
            rows.append((pair,'1h',datetime.fromtimestamp(int(b[0]),timezone.utc),*map(float,b[1:6])))
        if rows:
            await c.executemany('''INSERT INTO historical_ohlcv(pair_address,timeframe,ts,open,high,low,close,volume_usd)
              VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING''',rows); added+=len(rows)
        nxt=min(int(b[0]) for b in bars)-1
        if before is not None and nxt>=before:break
        before=nxt
        if before<=SIX_MONTHS or len(bars)<1000:break
        await asyncio.sleep(RATE_SLEEP)
    return added

async def cycle():
    async with connection() as c:
        await schema(c)
        pairs=await c.fetch('''SELECT DISTINCT market::jsonb->>'pair_address' pair FROM research_candidates
          WHERE market IS NOT NULL AND market::jsonb->>'pair_address' IS NOT NULL ORDER BY 1''')
        total=0
        for r in pairs:
            n=await backfill_pair(c,r['pair']); total+=n
            logging.info('historical_bank pair=%s added=%s total_added=%s',r['pair'],n,total)
            await asyncio.sleep(RATE_SLEEP)
        return {'pairs':len(pairs),'added':total}

async def main():
    await init_db()
    while True:
        try:logging.info('historical_backfill %s',await cycle())
        except Exception:logging.exception('historical_backfill_error')
        await asyncio.sleep(21600)

if __name__=='__main__':asyncio.run(main())
