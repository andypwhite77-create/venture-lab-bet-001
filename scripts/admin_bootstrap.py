#!/usr/bin/env python3
from getpass import getpass
from pathlib import Path
import hashlib, secrets

p1=getpass('New admin password: ')
p2=getpass('Repeat password: ')
if p1!=p2: raise SystemExit('Passwords do not match')
if len(p1)<14: raise SystemExit('Use at least 14 characters')
salt=secrets.token_bytes(16)
digest=hashlib.scrypt(p1.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
session=secrets.token_hex(32)
out=Path('/home/deploy/venture-lab/secrets/admin.env')
out.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
out.write_text(f'ADMIN_USERNAME=admin\nADMIN_PASSWORD_SCRYPT={salt.hex()}${digest.hex()}\nADMIN_SESSION_SECRET={session}\n')
out.chmod(0o600)
print('Admin credentials configured.')
