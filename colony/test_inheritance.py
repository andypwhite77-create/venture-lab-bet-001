import json,unittest
from colony.inheritance import offspring,exploration_slots

P={'family':'x','parameters':{'a':10.0,'b':20.0,'c':5},'bounds':{'a':[1,50],'b':[1,50],'c':[1,20]}}
Q={'family':'x','parameters':{'a':40.0,'b':2.0,'c':15},'bounds':P['bounds']}

class InheritanceTests(unittest.TestCase):
    def test_parent_not_modified(self):
        before=json.dumps(P,sort_keys=True); offspring(P,seed=1)
        self.assertEqual(before,json.dumps(P,sort_keys=True))
    def test_child_has_lineage(self):
        c=offspring(P,Q,seed=2); self.assertEqual(len(c['inheritance']['parents']),2)
    def test_bounds_survive_mutation(self):
        for seed in range(100):
            c=offspring(P,Q,seed=seed,weird_rate=1)
            for k,v in c['parameters'].items():
                lo,hi=P['bounds'][k]; self.assertTrue(lo<=v<=hi)
    def test_exploration_never_zero(self):
        self.assertEqual(exploration_slots(10),1); self.assertEqual(exploration_slots(100),5)

if __name__=='__main__': unittest.main()
