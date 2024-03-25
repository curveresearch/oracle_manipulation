Initial code to examine effects of trade size on various cryptoswap oracles. Very much a work in progress.

Depends only on curvesim and its dependencies

Example:
import curvesim, oracle_manipulation
pool = curvesim.pool.get_sim_pool("0xf5f5b97624542d72a9e06f04804bf81baa15e2b4", balanced=False)
dfs, outputs = oracle_manipulation.run_all_trade_pairs(pool)
chart = oracle_manipulation.plot(dfs, "tricryptoUSDT.html")


