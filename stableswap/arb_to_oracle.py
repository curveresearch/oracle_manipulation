#Modified from curvesim to exclude fees from optimizer

from pprint import pformat

from numpy import isnan
from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.templates.trader import Trade
from curvesim.pipelines.common import get_arb_trades

from v1_oracle import calc_moving_average

logger = get_logger(__name__)


def get_arb_trades(pool, prices, last_ema_value, averaging_window = 865, interval = 12):
    """
    Returns triples of "trades", one for each coin pair in `combo`.

    Each trade is a triple consisting of size, ordered coin-pair,
    and price target to move the pool price to.

    Parameters
    ----------
    pool: SimPool
        Pool to arbitrage on

    prices : iterable
        External market prices for each coin-pair


    Returns
    -------
    trades: List[Tuple]
        List of triples (size, coins, price_target)
        "size": trade size
        "coins": in token, out token
        "price_target": price target for arbing the token pair
    """

    def post_trade_price_error(dx, coin_in, coin_out, price_target):
        with pool.use_snapshot_context():
            dx = int(dx)
            if dx > 0:
                pool.trade(coin_in, coin_out, dx)

            price = int(pool.price(1, 0, use_fee=False) * 10**18) # coin 0 is always quote asset
            oracle = calc_moving_average(price, last_ema_value, averaging_window, interval)

        return (oracle-price_target)/10**18

    trades = []

    for pair in prices:
        coin_in, coin_out, target_price = _get_arb_direction(pair, pool, prices[pair])

        lower_bound = 0
        upper_bound = pool.D() * 10
        res = root_scalar(
            post_trade_price_error,
            args=(coin_in, coin_out, target_price),
            bracket=(lower_bound, upper_bound),
            method="brentq",
        )
        size = int(res.root)
        trades.append(Trade(coin_in, coin_out, size))

    return trades, res


def _get_arb_direction(pair, pool, target_price):
    i, j = pair
    price_error_i = pool.price(i, j, use_fee=False) - target_price
    price_error_j = pool.price(j, i, use_fee=False) - 1 / target_price

    if price_error_i >= price_error_j:
        coin_in, coin_out = i, j
    else:
        coin_in, coin_out = j, i

    return coin_in, coin_out, int(10**18 // target_price)