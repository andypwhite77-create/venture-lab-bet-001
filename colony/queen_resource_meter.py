"""Host-only resource sampling using Docker stats. Observations, not billed costs."""
import datetime,json,subprocess
CONTAINERS={'eth':'venture-lab-eth-queen-1','solana':'venture-lab-queen-survival-1','swarm':'venture-lab-swarm-queen-1'}
def sample():
 observations=[]
 for queen,container in CONTAINERS.items():
  try:
   output=subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}',container],timeout=12,text=True)
   row=json.loads(output.strip().splitlines()[0]);observations.append({'queen':queen,'container':container,'cpu_percent_observed':row.get('CPUPerc'),'memory_usage_observed':row.get('MemUsage'),'memory_percent_observed':row.get('MemPerc'),'pids_observed':row.get('PIDs')})
  except Exception as ex:observations.append({'queen':queen,'error':type(ex).__name__})
 return {'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'resource_samples':observations,'billed_costs_usd':None,'notes':'Instantaneous CPU and memory use. Cannot calculate spend without hosting and inference pricing.'}
if __name__=='__main__':print(json.dumps(sample()))
