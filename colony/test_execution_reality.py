from colony.execution_reconcile import friction
def test_friction_ratio_scales_with_notional_for_bps_cost():
 assert friction(.005,100)==.00005
 assert friction(.05,100)==.0005
def test_fixed_network_cost_hurts_small_notional_more():
 small=friction(.005,0,.00001)/.005
 large=friction(.05,0,.00001)/.05
 assert small>large
