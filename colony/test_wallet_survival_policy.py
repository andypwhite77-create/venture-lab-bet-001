import unittest
from colony.wallet_survival_policy import WalletEvidence,classify
class TestWalletSurvival(unittest.TestCase):
 def test_realized_loss_demotes(self):
  self.assertEqual(classify(WalletEvidence(30,-2,100,True,0))['stage'],'demote_to_research')
 def test_wallet_without_proof_suspended(self):
  self.assertEqual(classify(WalletEvidence(30,100,0,False,0))['stage'],'suspend_for_review')
 def test_short_winning_streak_still_probation(self):
  self.assertEqual(classify(WalletEvidence(3,2,0,True,0))['stage'],'probation')
