"""Frozen deterministic ETH paper genomes; mutation proposals use only prior marks."""
import hashlib,json
SEEDS=[('momentum',2,0.0),('momentum',3,0.001),('momentum',4,0.002),('reversal',2,0.0),('reversal',3,0.001),('reversal',4,0.002)]
def genome_id(direction,lookback,threshold):
 return 'eth_'+hashlib.sha256(f'{direction}:{lookback}:{threshold:.5f}'.encode()).hexdigest()[:12]
def seeds():return [(genome_id(*g),*g) for g in SEEDS]
def signal_genome(direction,lookback,threshold,closed):
 if len(closed)<lookback+1:return False
 prices=[float(x[4]) for x in closed[-(lookback+1):]]
 if min(prices)<=0:return False
 change=prices[-1]/prices[-lookback-1]-1
 if direction=='momentum':return change>threshold and prices[-1]>prices[-2]
 return change < -threshold and prices[-1]<prices[-2]
def child_of(parent,step):
 _,direction,lookback,threshold=parent
 new_lookback=max(2,min(12,lookback+((-1,1)[step%2])))
 new_threshold=max(0.,min(.02,round(threshold+((-.0005,.0005)[step%2]),5)))
 return (genome_id(direction,new_lookback,new_threshold),direction,new_lookback,new_threshold)
