import ctypes
import gc

import numpy as np
import pandas as pd

from .market import MarketPair, TradeOrder, with_mkt_price
from .swap import calc_arb_trade, constant_product_swap
from .utils import timer_func


class TradeOrderMemoryManager:
    def __init__(self, obj_type):
        self.buffer = (ctypes.c_char * ctypes.sizeof(TradeOrder))()

    def create_object(self, obj_type, *args, **kwargs):
        obj_ptr = ctypes.pointer(obj_type(*args, **kwargs))
        ctypes.memmove(ctypes.addressof(self.buffer), obj_ptr, ctypes.sizeof(obj_type))
        return ctypes.cast(
            ctypes.addressof(self.buffer), ctypes.POINTER(obj_type)
        ).contents


# Create a memory manager for MyObject
# mem_mgr = TradeOrderMemoryManager(TradeOrder)


def resample_df(df: pd.DataFrame, resample_freq: str) -> pd.DataFrame:
    """Resamples the DataFrame based on a given frequency.

    Args:
        df (pd.DataFrame): The DataFrame to be resampled.
        resample_freq (str): The resampling frequency.

    Returns:
        pd.DataFrame: The resampled DataFrame.

    """
    df = df.resample(resample_freq).agg(
        {
            "marketprice": np.mean,
            "buy_volume": np.sum,
            "sell_volume": np.sum,
            "fx_pnl": np.mean,
            "closeprice_x": np.mean,
            "closeprice_y": np.mean,
        }
    )
    df = df.dropna()
    return df


@timer_func
def swap_simulation(
    mkt: MarketPair,
    trade_df: pd.DataFrame,
    is_arb_enabled: bool = True,
) -> dict:
    """Simulates swaps for a given market pair and trade data.

    Args:
        mkt (MarketPair): The market pair for which swaps are to be simulated.
        trade_df (pd.DataFrame): The DataFrame containing trade data.
        is_arb_enabled (bool, optional): Flag to enable/disable arbitrage.
        Defaults to True.

    Returns:
        dict: The results of the simulation.

    """
    gc.disable()
    trade_exec_info = []
    trades = trade_df.reset_index().to_dict(orient="records")
    for row in trades:
        mkt = with_mkt_price(mkt, row["price"])
        if is_arb_enabled:
            quantity, pnl = calc_arb_trade(mkt)
            if pnl > 0:  # only execute if profitable
                trade_exec_info.append(
                    execute_trade(mkt, row["trade_date"], quantity, pnl)
                )
        if row["quantity"] != 0:
            trade_exec_info.append(
                execute_trade(mkt, row["trade_date"], row["quantity"])
            )
    gc.enable()
    return sim_results(trade_exec_info)


def execute_trade(
    mkt: MarketPair, trade_date: object, volume: float, arb_profit: float = 0
) -> dict:
    """Executes a trade for a given market pair and volume.

    Args:
        mkt (MarketPair): The market pair for which the trade is to be executed.
        trade_date (object): The date of the trade.
        volume (object): The volume of the trade.
        arb_profit (float, optional): The profit from arbitrage. Defaults to 0.

    Returns:
        dict: A dictionary with information about the executed trade.

    """
    # trade = mem_mgr.create_object(TradeOrder, mkt.ticker, volume, fee)
    mid_price = mkt.mid_price
    trade = TradeOrder(mkt.ticker, volume, mkt.swap_fee)
    _, exec_price = constant_product_swap(mkt, trade)
    # _, exec_price = mock_constant_product_swap(mkt, trade)
    return {
        "trade_date": trade_date,
        "side": trade.direction,
        "arb_profit": arb_profit,
        "price": exec_price,
        "price_impact": (mid_price - exec_price) / mid_price,
        **mkt.describe(),
    }


@timer_func
def sim_results(sim_outputs: list) -> dict:
    """Processes simulation outputs to provide a structured result.

    Args:
        sim_outputs (list): The list of simulation outputs.

    Returns:
        dict: A dictionary containing the processed simulation results.

    """
    if len(sim_outputs) == 0:
        return {}
    df_sim = pd.DataFrame(sim_outputs).set_index("trade_date")
    trade_data = df_sim[
        ["total_volume_base", "total_volume_quote", "total_fees_paid_quote"]
    ]
    df_sim[
        ["volume_base", "volume_quote", "fees_paid_quote"]
    ] = trade_data.diff().fillna(trade_data)
    df_sim["trade_pnl_pct"] = df_sim["trade_pnl"] / df_sim["hold_portfolio"]
    df_sim["fees_pnl_pct"] = df_sim["total_fees_paid_quote"] / df_sim["hold_portfolio"]
    df_sim["total_arb_profit"] = df_sim["arb_profit"].cumsum()

    return {
        "headline": trade_summary(df_sim),
        "breakdown": df_sim,
    }


@timer_func
def trade_summary(df_trades: pd.DataFrame) -> pd.DataFrame:
    """Generates a summary of trades.

    Args:
        df_trades (pd.DataFrame): The DataFrame containing trade data.

    Returns:
        pd.DataFrame: A DataFrame summarizing the trades.

    """
    df = df_trades[["side", "volume_base", "volume_quote"]].groupby("side")
    df = df.agg(["count", "sum"]).T.droplevel(1).drop_duplicates()
    df.index = ["Number of trades", "volume_base", "volume_quote"]
    df["total"] = df["buy"] + df["sell"]
    df.loc["avg_price"] = -df.loc["volume_quote"] / df.loc["volume_base"]
    df.columns.name = None
    return df
