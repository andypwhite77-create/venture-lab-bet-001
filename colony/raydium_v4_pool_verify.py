"""Verify Raydium AMM v4 vault/mint membership from a pool's own state.
Research only; does not derive a swap execution quote. Official layout: raydium-sdk-V2 liquidity/layout.ts.
"""
import base64,struct
ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
# 32 u64 (256 bytes), followed by four u128 and two interleaved u64 (88 bytes)
# Full first 32 u64 = 256; five swap fields occupy 88 bytes; vault addresses begin at 336.
PROGRAM='675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8'
def pubkey(data):
 n=int.from_bytes(data,'big');s=''
 while n:n,r=divmod(n,58);s=ALPHABET[r]+s
 return '1'*(len(data)-len(data.lstrip(b'\0')))+s
def decode(data,owner):
 if owner!=PROGRAM:raise ValueError('not Raydium AMM v4 program')
 if len(data)!=752:raise ValueError('wrong Raydium v4 state length')
 status=struct.unpack_from('<Q',data,0)[0]
 if status not in (1,2,6,7):raise ValueError('unrecognized pool state')
 return {'status':status,'base_vault':pubkey(data[336:368]),'quote_vault':pubkey(data[368:400]),'base_mint':pubkey(data[400:432]),'quote_mint':pubkey(data[432:464]),'program_verified':True}
def verify(data,owner,base_vault,quote_vault,base_mint,quote_mint):
 decoded=decode(data,owner)
 for k,v in [('base_vault',base_vault),('quote_vault',quote_vault),('base_mint',base_mint),('quote_mint',quote_mint)]:
  if decoded[k]!=v:raise ValueError(k+' does not match pool state')
 return decoded
