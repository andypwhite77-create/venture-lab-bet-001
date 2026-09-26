"""Prospective validation: discovery data can never validate its own niche."""
from dataclasses import dataclass,field

@dataclass
class Validation:
    features:tuple
    discovered_through_id:int
    discovery_effect:float
    future_yes:list=field(default_factory=list)
    future_no:list=field(default_factory=list)

    def observe(self,row_id,features,return_pct):
        if row_id<=self.discovered_through_id:return False
        hit=all(features.get(k,False) for k in self.features)
        (self.future_yes if hit else self.future_no).append(float(return_pct)); return True

    def result(self,min_each=10,min_effect=3.0):
        if len(self.future_yes)<min_each or len(self.future_no)<min_each:
            return {'validated':False,'reason':'insufficient_future_data','yes_n':len(self.future_yes),'no_n':len(self.future_no)}
        effect=sum(self.future_yes)/len(self.future_yes)-sum(self.future_no)/len(self.future_no)
        same_direction=effect*self.discovery_effect>0
        return {'validated':same_direction and abs(effect)>=min_effect,'future_effect_pct':round(effect,4),
                'same_direction':same_direction,'yes_n':len(self.future_yes),'no_n':len(self.future_no)}
