import unittest,urllib.error
from unittest.mock import patch
from colony import jupiter_quotes as j
class Response:
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self):return b'{"inputMint":"A","outputMint":"B","inAmount":"10","outAmount":"20","slippageBps":100}'
class TransportTests(unittest.TestCase):
 def test_retry_on_transient_primary_failure(self):
  with patch.object(j,'KEY','key'),patch.object(j,'BASE','https://primary/quote'),patch.object(j,'_BACKOFF_UNTIL',0),patch.object(j.urllib.request,'urlopen',side_effect=[urllib.error.HTTPError('x',503,'oops',{},None),Response()]) as call:
   self.assertEqual(j.quote('A','B',10)['out_amount'],'20')
   self.assertEqual(call.call_count,2)
 def test_failure_contains_http_status_without_secrets(self):
  with patch.object(j,'KEY','key'),patch.object(j,'BASE','https://primary/quote'),patch.object(j,'_BACKOFF_UNTIL',0),patch.object(j.urllib.request,'urlopen',side_effect=[urllib.error.HTTPError('x',429,'slow',{},None),urllib.error.HTTPError('x',503,'down',{},None)]):
   with self.assertRaises(j.QuoteTransportError) as cm:j.quote('A','B',11)
   self.assertIn('http_429',str(cm.exception));self.assertIn('http_503',str(cm.exception))
