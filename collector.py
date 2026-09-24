import asyncio
from datetime import datetime, timezone

from db import increment_swap_like, save_transaction, tx_exists, upsert_wallet

JUPITER_V6_PROGRAM = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"


def _iso_from_unix(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def summarize_transaction(signature: str, tx: dict, source_program: str):
    if not tx:
        return None
    meta = tx.get("meta") or {}
    message = ((tx.get("transaction") or {}).get("message") or {})
    account_keys = message.get("accountKeys") or []

    normalized_keys = []
    for item in account_keys:
        if isinstance(item, dict):
            normalized_keys.append(item)
        else:
            normalized_keys.append({"pubkey": item, "signer": False})

    signer = next((k.get("pubkey") for k in normalized_keys if k.get("signer")), None)
    if not signer and normalized_keys:
        signer = normalized_keys[0].get("pubkey")

    pre_balances = meta.get("preBalances") or []
    post_balances = meta.get("postBalances") or []
    native_delta = None
    if signer:
        try:
            signer_index = next(i for i, k in enumerate(normalized_keys) if k.get("pubkey") == signer)
            if signer_index < len(pre_balances) and signer_index < len(post_balances):
                native_delta = int(post_balances[signer_index]) - int(pre_balances[signer_index])
        except (StopIteration, TypeError, ValueError):
            pass

    pre_token = meta.get("preTokenBalances") or []
    post_token = meta.get("postTokenBalances") or []
    deltas = {}

    def ingest(items, sign):
        for b in items:
            owner = b.get("owner")
            if signer and owner != signer:
                continue
            mint = b.get("mint")
            amount_obj = b.get("uiTokenAmount") or {}
            raw = amount_obj.get("amount")
            decimals = amount_obj.get("decimals", 0)
            if not mint or raw is None:
                continue
            try:
                amount = int(raw) / (10 ** int(decimals))
            except (TypeError, ValueError, OverflowError):
                continue
            deltas[mint] = deltas.get(mint, 0.0) + sign * amount

    ingest(pre_token, -1)
    ingest(post_token, 1)
    token_deltas = [
        {"mint": mint, "delta": delta}
        for mint, delta in deltas.items()
        if abs(delta) > 1e-12
    ]

    swap_like = len([d for d in token_deltas if abs(d["delta"]) > 0]) >= 2
    return {
        "signature": signature,
        "slot": tx.get("slot"),
        "block_time": _iso_from_unix(tx.get("blockTime")),
        "wallet": signer,
        "source_program": source_program,
        "fee_lamports": meta.get("fee"),
        "success": meta.get("err") is None,
        "native_delta_lamports": native_delta,
        "token_deltas": token_deltas,
        "raw_summary": {
            "swap_like": swap_like,
            "num_account_keys": len(normalized_keys),
            "log_count": len(meta.get("logMessages") or []),
        },
    }


async def discover_from_jupiter(rpc_call, log, batch_size: int = 2):
    """Sample recent Jupiter transactions to discover active wallets cheaply.

    This intentionally samples rather than attempts a full chain index so the
    experiment stays inside the free/low-cost data budget.
    """
    result = await rpc_call(
        "getSignaturesForAddress",
        [JUPITER_V6_PROGRAM, {"limit": max(batch_size * 4, 8)}],
    )
    discovered = 0
    stored = 0

    for item in result or []:
        if stored >= batch_size:
            break
        signature = item.get("signature")
        if not signature or await tx_exists(signature):
            continue
        tx = await rpc_call(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed",
                },
            ],
        )
        summary = summarize_transaction(signature, tx, JUPITER_V6_PROGRAM)
        if not summary:
            continue
        await save_transaction(summary)
        stored += 1
        wallet = summary.get("wallet")
        if wallet:
            await upsert_wallet(wallet, "jupiter_v6_sample")
            discovered += 1
            if summary.get("raw_summary", {}).get("swap_like"):
                await increment_swap_like(wallet)
        await asyncio.sleep(0.15)

    if stored:
        log.info("Jupiter sampler stored=%s wallet_observations=%s", stored, discovered)
    return {"stored": stored, "wallet_observations": discovered}
