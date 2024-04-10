from copy import deepcopy
import altair as alt
import curvesim
from numpy import Inf
from pandas import DataFrame
from arb_to_oracle import get_arb_trades
from v1_oracle import calc_moving_average

pools = {
    "mkUSD/crvUSD": 4773223722723833465762050,
    "mkUSD/USDC": 1747380044737968369848729,
    "mkUSD/USDe": 11965455173112847335371401
}


def run_all():
    trades = {}
    logs = {}
    pool_metadata = {}

    pool = curvesim.pool.get_sim_pool("0x3de254a0f838a844f727fee81040e0fa7884b935")
    pool.fee_mul = 50000000000

    for name, D in pools.items():
        pool.balances = [D//2] * 2

        _trades, _logs = manipulate(pool)

        trades[name] = _trades
        logs[name] = _logs

    return trades, logs


def plot(trades):
    charts = []
    for name, df in trades.items():
        chart = plot_single(df).properties(title=name)
        charts.append(chart)

    return alt.vconcat(*charts).configure_title(fontSize=20)


def manipulate(pool):
    pool = deepcopy(pool)
    price_range = [x/10000 for x in range(9870,10131,10)]

    logs = []
    trades = []

    start_price = 1

    for target_price in price_range:
        trade, res = get_trades(pool, target_price)
        trade = trade[0]
        
        with pool.use_snapshot_context():
            output = pool.trade(*trade)
            price = pool.price(0,1, use_fee=False)

        if trade.coin_in == 0:
            in_value = trade.amount_in / 10**18
            out_value = output[0] * start_price / 10**18
        elif trade.coin_in == 1:
            in_value = trade.amount_in * start_price / 10**18
            out_value = output[0] / 10**18


        trades.append({
            "coin_in": trade.coin_in, 
            "coin_out": trade.coin_out,
            "amount_in": trade.amount_in / 10**18,
            "amount_out": output[0] / 10**18,
            "target_price": target_price,
            "pool_price": price, 
            "in_value": in_value, 
            "out_value": out_value, 
            "cost": in_value - out_value
        })

        logs.append(res)

    return DataFrame(trades), logs


def get_trades(pool, price_target):
    price_targets = {(0,1): price_target}
    last_ema_value = int(pool.price(0, 1, use_fee=False) * 10 ** 18)
    return get_arb_trades(pool, price_targets, last_ema_value)



def plot_single(df):
    chart1 = alt.Chart(df).mark_line().encode(
        x=alt.X('target_price', title="Target Oracle Price"),
        y=alt.Y('amount_in', title="Required Trade Size"),
    )

    chart2 = alt.Chart(df).mark_line().encode(
        x=alt.X('target_price', title="Target Oracle Price"),
        y=alt.Y('cost', title="Cost to Shift Price"),
    )

    chart3 = alt.Chart(df).mark_line().encode(
        x=alt.X('target_price', title="Target Oracle Price"),
        y=alt.Y('pool_price', title="Required Spot Price"),
    )

    chart = chart1 | chart2 | chart3

    return chart

