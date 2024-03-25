from curvesim.pool.cryptoswap.calcs.tricrypto_ng import _cbrt
import pandas as pd
import altair as alt

def lp_price(pool):
    price_oracle = pool._price_oracle
    return (
        3 * pool.virtual_price * _cbrt(price_oracle[0] * price_oracle[1])
    ) // 10**24


def post_trade_lp_prices(pool, trade_list):
    with pool.use_snapshot_context():
        pool.last_prices_timestamp = pool._block_timestamp
        pool._increment_timestamp(blocks=1)
        output = [(pool._block_timestamp, pool.last_prices_timestamp, lp_price(pool)/pool.virtual_price, pool.last_prices, pool._price_oracle, pool.price_scale)]
        for trade in trade_list:
            if trade == "next_block":
                pool._increment_timestamp(blocks=1)
            else:
                pool.exchange(*trade)

            output.append((pool._block_timestamp, pool.last_prices_timestamp, lp_price(pool)/pool.virtual_price, pool.last_prices, pool._price_oracle, pool.price_scale))

    return output


def trade_range(pool, initial_size = 10**6, size_res = 10**6, pairs = [(0,1), (0,2)]):
    df = []
    output = []
    size = initial_size

    lp_price_0 = lp_price(pool)/pool.virtual_price
    price_scale = [10**18] + pool.price_scale

    while True:
        try:
            size += size_res
            trade_list = [pair + (size * 10**36 // price_scale[pair[0]],) for pair in pairs]
            trade_list.append("next_block")
            trade_list.append((0,1, 10**18)) #final tiny trade to force oracle update
            _output = post_trade_lp_prices(pool, trade_list)
            output += _output
            df.append((size, _output[-1][2]/lp_price_0 - 1, _output[-1][-2][0]/10**18, _output[-1][-2][1]/10**18))

        except Exception as e:
            print(f"Trade size: {size}")
            print(e)
            break


    return pd.DataFrame(df, columns=["trade_size", "oracle_change", "wbtc_oracle", "eth_oracle"]), output

def run_all_trade_pairs(pool, initial_size = 10**6, size_res = 10**6):
    pairs_list = {
        "USD-wBTC": [(0,1)], 
        "USD-ETH": [(0,2)], 
        "USD-BOTH": [(0,1), (0,2)], 
        "wBTC-USD": [(1,0)], 
        "ETH-USD": [(2,0)], 
        "BOTH-USD": [(1,0), (2,0)]
    }
    
    dfs = []
    outputs = []
    for name, pairs in pairs_list.items():
        if "BOTH" in name:
            size = initial_size//2
            res = size_res//2
        else:
            size = initial_size
            res = size_res
        df, output = trade_range(pool, size, res, pairs)
        df["pair"] = name
        dfs.append(df)
        outputs.append(output)

    return dfs, outputs

def plot(dfs, name="test.html"):
    df_combined = pd.concat(dfs)
    chart1 = alt.Chart(df_combined).mark_line().encode(
        x=alt.X('trade_size', title="Trade Size (USD)"),
        y=alt.Y('oracle_change', title="lp_price Change").axis(format='%'),
        color=alt.Color('pair', title="Trade Pair")
    )

    chart2 = alt.Chart(df_combined).mark_line().encode(
        x=alt.X('trade_size', title="Trade Size (USD)"),
        y=alt.Y('wbtc_oracle', title="wBTC Oracle").scale(zero=False),
        color=alt.Color('pair', title="Trade Pair")
    )

    chart3 = alt.Chart(df_combined).mark_line().encode(
        x=alt.X('trade_size', title="Trade Size (USD)"),
        y=alt.Y('eth_oracle', title="ETH Oracle").scale(zero=False),
        color=alt.Color('pair', title="Trade Pair")
    )

    chart = chart1 | chart2 | chart3

    chart.save(name)
    return chart
