"""Scheduled, auditable, one-at-a-time recovery of *empty* Canary token-account rent.

No trading, token swap, or adjustment of Canary execution authority occurs here.
An ambiguous send is permanently quarantined rather than retried.
"""
import asyncio
import json
import time
from db import init_db, connection
from colony.canary_controller import rpc_call, wallet_address
from colony.canary_rent_reclaimer import eligible_mints, zero_accounts, gateway_close

ADVISORY_LOCK=84619321
EXECUTOR_LOCK=84619320  # Same advisory lock as live Canary executor: no concurrent new entry.
MIN_LAMPORTS=1000000
ACTIVE=("claimed","open","recovery","submitting_entry","submitting_exit","uncertain")

async def ensure_table(c):
    await c.execute("""CREATE TABLE IF NOT EXISTS canary_rent_reclaim_audit (
       token_account TEXT PRIMARY KEY,
       mint TEXT NOT NULL,
       lamports BIGINT NOT NULL,
       status TEXT NOT NULL,
       first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       signature TEXT,
       note TEXT
    )""")

async def position_free(c):
    return int(await c.fetchval(
        "SELECT count(*) FROM canary_trade_intents WHERE status=ANY($1::text[])",list(ACTIVE)))==0

def account_still_empty(item):
    v=rpc_call("getAccountInfo",[item["token_account"],{"encoding":"jsonParsed","commitment":"finalized"}])
    a=v.get("value")
    if not a:return False
    try:
        info=a["data"]["parsed"]["info"]
        return (str(info["mint"])==item["mint"] and
                str(info["tokenAmount"]["amount"])=="0" and
                int(a["lamports"])==int(item["lamports"]) and
                str(a["owner"])==item["program"])
    except (KeyError,TypeError,ValueError):
        return False

async def once():
    await init_db()
    async with connection() as c:
        await ensure_table(c)
        if not await c.fetchval("SELECT pg_try_advisory_lock($1)",ADVISORY_LOCK):
            return {"ok":True,"action":"already_running"}
        executor_locked=False
        try:
            executor_locked=bool(await c.fetchval("SELECT pg_try_advisory_lock($1)",EXECUTOR_LOCK))
            if not executor_locked:return {"ok":True,"action":"executor_busy_no_reclaim"}
            # Stop all automatic closure when an earlier broadcast outcome is unknown.
            pending=await c.fetchval("""SELECT count(*) FROM canary_rent_reclaim_audit
                WHERE status IN ('reserved','broadcast_unknown','submitted')""")
            if pending:
                return {"ok":False,"action":"quarantined_pending_confirmation","count":int(pending)}
            if not await position_free(c):
                return {"ok":True,"action":"position_active_no_reclaim"}
            mints=await eligible_mints()
            accounts=sorted(zero_accounts(mints),key=lambda x:x["token_account"])
            for item in accounts:
                if int(item["lamports"])<MIN_LAMPORTS:continue
                if await c.fetchval("SELECT 1 FROM canary_rent_reclaim_audit WHERE token_account=$1",item["token_account"]):continue
                if not await position_free(c):return {"ok":True,"action":"position_became_active"}
                if item["mint"] not in await eligible_mints():continue
                if not account_still_empty(item):continue
                # Simulation must succeed before irreversible submission.
                preview=await asyncio.to_thread(gateway_close,item,False)
                if preview.get("simulated") is not True:continue
                await c.execute("""INSERT INTO canary_rent_reclaim_audit(token_account,mint,lamports,status,note)
                    VALUES($1,$2,$3,'reserved','prebroadcast guard; never blindly retry')""",
                    item["token_account"],item["mint"],int(item["lamports"]))
                if not await position_free(c):
                    await c.execute("""UPDATE canary_rent_reclaim_audit SET status='skipped',
                        updated_at=now(),note='active position appeared' WHERE token_account=$1""",
                        item["token_account"])
                    return {"ok":True,"action":"position_became_active"}
                try:
                    result=await asyncio.to_thread(gateway_close,item,True)
                except Exception as e:
                    await c.execute("""UPDATE canary_rent_reclaim_audit
                      SET status='broadcast_unknown',updated_at=now(),note=$2 WHERE token_account=$1""",
                      item["token_account"],"gateway_error_"+type(e).__name__)
                    return {"ok":False,"action":"ambiguous_send_no_retry","error":type(e).__name__}
                signature=result.get("signature")
                if not signature:
                    await c.execute("""UPDATE canary_rent_reclaim_audit SET status='broadcast_unknown',
                      updated_at=now(),note='gateway_no_signature' WHERE token_account=$1""",item["token_account"])
                    return {"ok":False,"action":"missing_signature_no_retry"}
                await c.execute("""UPDATE canary_rent_reclaim_audit SET status='submitted',
                   signature=$2,updated_at=now() WHERE token_account=$1""",item["token_account"],signature)
                # A submitted transaction is not called complete until on-chain verification.
                for _ in range(8):
                    await asyncio.sleep(3)
                    if not rpc_call("getAccountInfo",[item["token_account"],
                       {"encoding":"base64","commitment":"finalized"}]).get("value"):
                        await c.execute("""UPDATE canary_rent_reclaim_audit
                            SET status='confirmed',updated_at=now(),note='account_absent_finalized'
                            WHERE token_account=$1""",item["token_account"])
                        return {"ok":True,"action":"confirmed","rent_sol":int(item["lamports"])/1e9,"signature":signature}
                return {"ok":False,"action":"submitted_awaits_manual_finality_check","signature":signature}
            return {"ok":True,"action":"no_eligible_new_empty_accounts"}
        finally:
            if executor_locked:await c.execute("SELECT pg_advisory_unlock($1)",EXECUTOR_LOCK)
            await c.execute("SELECT pg_advisory_unlock($1)",ADVISORY_LOCK)

if __name__=="__main__":
    try:
        print(json.dumps(asyncio.run(once()),default=str),flush=True)
    except Exception as e:
        print(json.dumps({"ok":False,"action":"exception_fail_closed","error":type(e).__name__}),flush=True)
        raise
