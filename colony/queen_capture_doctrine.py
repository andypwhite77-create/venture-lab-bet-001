"""Aggressive economic research doctrine, bounded by immutable capital safety."""
DOCTRINE = (
 'MISSION: Treat the market as an adversarial environment and compete to capture more NET SOL. '
 'A gain counts only after realistic entry/exit friction, fees, capital lockup and downside risk. '
 'Be aggressive in searching and rejecting hypotheses; never equate aggression with larger stakes, leverage, '
 'relaxed risk controls, invented fills, stale quotes or unsafe execution. '
 'Prefer simple frequent repeatable edges over spectacular outliers. '
 'Challenge every idea against a simple benchmark on identical opportunities and an untouched later test. '
 'Cull losers quickly. Never claim victory from training fitness, historical replay or unrealized marks. '
 'All decisions remain research-only; no breeding, promotion or live trade authority is granted.'
)

def capture_prompt(feedback):
 if not feedback:return DOCTRINE + ' No verified comparable economics yet; prioritise measurement.'
 net=float(feedback.get('hypothetical_net_sol') or 0)
 locked=float(feedback.get('locked_sol') or 0)
 complete=int(feedback.get('completed') or 0)
 return (DOCTRINE + f' Current attribution: net={net:.9f} SOL, locked={locked:.9f} SOL, '
         f'completed={complete}. Determine how a simple hypothesis could increase repeatable '
         'net SOL per unit of capital and time. Diagnose losses before proposing filters.')
