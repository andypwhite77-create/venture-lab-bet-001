import unittest
from colony.solana_vault_spot import spot
OWNER='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
def vault(mint,raw,decimals=6):return {'owner':OWNER,'data':{'parsed':{'type':'account','info':{'mint':mint,'tokenAmount':{'amount':str(raw),'decimals':decimals}}}}}
class VaultSpotTests(unittest.TestCase):
 def test_reserve_ratio_only(self):
  r=spot(vault('mintA',1000000),vault('mintB',2000000),'mintA','mintB')
  self.assertEqual(r['b_per_a'],'2')
  self.assertFalse(r['pool_membership_verified'])
  self.assertFalse(r['fees_included'])
 def test_wrong_mint_rejected(self):
  with self.assertRaises(ValueError):spot(vault('wrong',100),vault('mintB',100),'mintA','mintB')
 def test_zero_vault_rejected(self):
  with self.assertRaises(ValueError):spot(vault('mintA',0),vault('mintB',100),'mintA','mintB')
 def test_non_token_account_rejected(self):
  with self.assertRaises(ValueError):spot({'owner':'System','data':{}},vault('mintB',100),'mintA','mintB')
