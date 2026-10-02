"""Admin authentication persistence and one-time recovery tokens.

The environment password remains an emergency fallback. A successful recovery writes a
new scrypt hash to the database and increments auth_epoch so existing sessions expire.
Recovery tokens are high-entropy, short-lived and stored only as hashes.
"""
from __future__ import annotations
import base64, hashlib, hmac, secrets
from datetime import datetime, timezone, timedelta

SCRYPT_N=2**14
RECOVERY_TTL_MINUTES=15

def scrypt_hash(password:str,salt:bytes)->bytes:
    return hashlib.scrypt(password.encode(),salt=salt,n=SCRYPT_N,r=8,p=1,dklen=32)

def encode_password(password:str)->str:
    salt=secrets.token_bytes(16)
    return salt.hex()+"$"+scrypt_hash(password,salt).hex()

def verify_password(encoded:str,password:str)->bool:
    try:
        salt_hex,digest_hex=encoded.split("$",1)
        return hmac.compare_digest(scrypt_hash(password,bytes.fromhex(salt_hex)),bytes.fromhex(digest_hex))
    except Exception:
        return False

def _token_hash(token:str)->str:
    return hashlib.sha256(token.strip().encode()).hexdigest()

def _display_token()->str:
    raw=base64.b32encode(secrets.token_bytes(16)).decode().rstrip('=')
    return 'C27-'+'-'.join(raw[i:i+4] for i in range(0,len(raw),4))

async def ensure_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS admin_auth_state(
      id INT PRIMARY KEY CHECK(id=1),password_scrypt TEXT,auth_epoch BIGINT NOT NULL DEFAULT 1,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
    INSERT INTO admin_auth_state(id) VALUES(1) ON CONFLICT DO NOTHING;
    CREATE TABLE IF NOT EXISTS admin_recovery_tokens(
      id BIGSERIAL PRIMARY KEY,token_sha256 TEXT UNIQUE NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),expires_at TIMESTAMPTZ NOT NULL,
      used_at TIMESTAMPTZ);''')

async def auth_state(c):
    await ensure_schema(c)
    r=await c.fetchrow('SELECT password_scrypt,auth_epoch,updated_at FROM admin_auth_state WHERE id=1')
    return dict(r)

async def current_password_hash(c,env_fallback:str)->str:
    s=await auth_state(c)
    return s.get('password_scrypt') or env_fallback

async def create_recovery_token(c):
    await ensure_schema(c)
    token=_display_token(); expires=datetime.now(timezone.utc)+timedelta(minutes=RECOVERY_TTL_MINUTES)
    async with c.transaction():
        await c.execute('UPDATE admin_recovery_tokens SET used_at=now() WHERE used_at IS NULL')
        await c.execute('INSERT INTO admin_recovery_tokens(token_sha256,expires_at) VALUES($1,$2)',_token_hash(token),expires)
    return {'token':token,'expires_at':expires,'ttl_minutes':RECOVERY_TTL_MINUTES}

async def reset_password_with_token(c,token:str,new_password:str):
    await ensure_schema(c)
    if len(new_password)<12:
        return {'ok':False,'reason':'password_too_short'}
    digest=_token_hash(token)
    async with c.transaction():
        r=await c.fetchrow('''SELECT id,expires_at FROM admin_recovery_tokens
          WHERE token_sha256=$1 AND used_at IS NULL FOR UPDATE''',digest)
        if not r:return {'ok':False,'reason':'invalid_or_used_recovery_code'}
        if r['expires_at']<=datetime.now(timezone.utc):
            await c.execute('UPDATE admin_recovery_tokens SET used_at=now() WHERE id=$1',r['id'])
            return {'ok':False,'reason':'expired_recovery_code'}
        encoded=encode_password(new_password)
        epoch=await c.fetchval('''UPDATE admin_auth_state SET password_scrypt=$1,auth_epoch=auth_epoch+1,updated_at=now()
          WHERE id=1 RETURNING auth_epoch''',encoded)
        await c.execute('UPDATE admin_recovery_tokens SET used_at=now() WHERE id=$1',r['id'])
        await c.execute('UPDATE admin_recovery_tokens SET used_at=now() WHERE used_at IS NULL')
    return {'ok':True,'auth_epoch':int(epoch)}
