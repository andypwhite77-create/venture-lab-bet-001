"""Create immutable founder and blind-mutation control populations."""
import json, random
from pathlib import Path
from colony.evolve import load_seeds, make_generation
from colony.genome import genome_id
ROOT=Path(__file__).resolve().parent

def founder_control():
    return load_seeds()

def blind_control(size=100,seed=99173):
    # Same mutation machinery, no fitness selection and no Core guidance.
    return make_generation(load_seeds(),size,seed)

def main():
    founders=founder_control(); blind=blind_control()
    (ROOT/'control-founders.json').write_text(json.dumps(founders,indent=2)+'\n')
    (ROOT/'control-blind.json').write_text(json.dumps(blind,indent=2)+'\n')
    print(json.dumps({"founders":len(founders),"blind":len(blind),
      "founder_ids":[genome_id(g) for g in founders],"blind_unique":len({genome_id(g) for g in blind})},indent=2))
if __name__=='__main__': main()
