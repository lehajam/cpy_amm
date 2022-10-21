from bokeh.io import show
from bokeh.layouts import column, grid
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import Figure, figure
from bokeh.transform import dodge

from .swap import (
    MidPrice,
    Pool,
    constant_product_curve,
    constant_product_swap,
    order_book,
    price_impact_range,
    reset_pools,
)


def new_constant_product_figure(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
    bokeh_figure: Figure | None = None,
    plot_width=900,
    plot_height=600,
):
    """Plots the constant product AMM curve Y = K / X

    Args:
        pool_1 (Pool):
            Liquidity pool 1

        pool_2 (Pool):
            Liquidity pool 2

        k (float, optional):
            Constant product invariant

        x_min (float, optional):
            Start of the range for the x-axis

        x_max (float, optional):
            End of the range for the x-axis

        num (int, optional):
            Number of points to plot

        bokeh_figure (Figure, optional):
            Bokeh figure to plot on

        plot_width (int, optional):
            Width of the plot

        plot_height (int, optional):
            Height of the plot

    """
    p = bokeh_figure or figure(
        title=f"Constant Product AMM Curve for the pair {pool_1.ticker}/{pool_2.ticker}",
        plot_width=plot_width,
        plot_height=plot_height,
    )
    p.xaxis.axis_label = f"Amount {pool_1.ticker}"
    p.yaxis.axis_label = f"Amount {pool_2.ticker}"
    x, y = constant_product_curve(
        pool_1, pool_2, k=k, x_min=x_min, x_max=x_max, num=num
    )
    p.line(x, y, line_width=2, color="navy", alpha=0.6, legend_label="Y=K/X")
    # display current mid price of the pools
    p = with_price_info(
        p,
        MidPrice(f"{pool_1.ticker}/{pool_2.ticker}", pool_1.balance, pool_2.balance),
        "Mid Price",
    )
    return p


def new_price_impact_figure(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    dx: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
    precision: float | None = None,
    bokeh_figure: Figure | None = None,
    plot_width=900,
    plot_height=600,
):
    """Plots the constant product AMM curve with price impact range for the oder of size
    dx.

    Args:
        pool_1 (Pool):
            Liquidity pool 1

        pool_2 (Pool):
            Liquidity pool 2

        k (float, optional):
            Constant product invariant

        dx (float, optional):
            The order size

        x_min (float, optional):
            Start of the range for the x-axis

        x_max (float, optional):
            End of the range for the x-axis

        num (int, optional):
            Number of points to plot

        bokeh_figure (Figure, optional):
            Bokeh figure to plot on

        plot_width (int, optional):
            Width of the plot

        plot_height (int, optional):
            Height of the plot

    """
    p = new_constant_product_figure(
        pool_1, pool_2, k, x_min, x_max, num, bokeh_figure, plot_width, plot_height
    )
    # coomputes price impact range
    price_impact = price_impact_range(pool_1, pool_2, k=k, dx=dx, precision=precision)
    # plot price impact range
    p.line(
        [price_impact.start.x, price_impact.end.x],
        [price_impact.start.y, price_impact.end.y],
        line_width=20,
        color="red",
        alpha=0.3,
    )
    # add price impact range tooltips
    p = with_price_info(p, price_impact.mid, "Swap Execution Price")
    p = with_price_info(p, price_impact.end, "Mid Price (after swap)")
    return p


def new_order_book_figure(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
    plot_width=900,
    plot_height=600,
):
    """Plots the cumulative quantity at any mid price according to the formula from the
    paper "Order Book Depth and Liquidity Provision in Automated Market Makers. Orders
    under current mid price are on the bid, and those above the ask.

    Args:
        pool_1 (Pool):
            Liquidity pool 1

        pool_2 (Pool):
            Liquidity pool 2

        k (float, optional):
            Constant product invariant

        x_min (float, optional):
            Start of the range for the x-axis

        x_max (float, optional):
            End of the range for the x-axis

        num (int, optional):
            Number of points to plot

        bokeh_figure (Figure, optional):
            Bokeh figure to plot on

        plot_width (int, optional):
            Width of the plot

        plot_height (int, optional):
            Height of the plot

    """
    p = figure(
        title=f"Constant Product AMM Depth for the pair {pool_1.ticker}/{pool_2.ticker}",
        plot_width=plot_width,
        plot_height=plot_height,
    )
    p.xaxis.axis_label = f"{pool_1.ticker}/{pool_2.ticker} Mid Price"
    p.yaxis.axis_label = "Order Size"
    x, mid, q = order_book(pool_1, pool_2, k=k, x_min=x_min, x_max=x_max, num=num)
    bid = [q_i if x_i < pool_1.initial_deposit else 0 for (x_i, q_i) in zip(x, q)]
    ask = [q_i if x_i > pool_1.initial_deposit else 0 for (x_i, q_i) in zip(x, q)]
    source = ColumnDataSource(data={"mid": mid, "bid": bid, "ask": ask})
    # depth eg. binance style order book
    p.varea_stack(
        ["bid", "ask"],
        x="mid",
        color=("green", "red"),
        source=source,
        alpha=0.4,
        legend_label=["Bid", "Ask"],
    )
    p.x_range.range_padding = 0
    p.y_range.range_padding = 0
    return p


def new_pool_figure(
    pool_1: Pool, pool_2: Pool, steps=None, plot_width=900, plot_height=600
):
    """Plots eveolution of token reserves by steps (time, simulations, blocks etc.).

    Args:
        pool_1 (Pool):
            Liquidity pool 1

        pool_2 (Pool):
            Liquidity pool 2

        steps (list, optional):
            List of steps

        plot_width (int, optional):
            Width of the plot

        plot_height (int, optional):
            Height of the plot

    """
    TOOLTIPS = [
        (f"{pool_1.ticker}", f"@{pool_1.ticker}" + "{0,0.000}"),
        (f"{pool_2.ticker}", f"@{pool_2.ticker}" + "{0,0.000}"),
    ]

    steps = steps if steps else range(len(pool_1.reserves))
    p = figure(
        title="Pool balance history",
        plot_width=plot_width,
        plot_height=plot_height,
        x_range=steps,
        tooltips=TOOLTIPS,
    )
    p.xaxis.axis_label = "Simulation Steps"
    p.yaxis.axis_label = "Reserves"
    p.x_range.range_padding = 0
    p.xgrid.grid_line_color = None
    source = ColumnDataSource(
        data={
            pool_1.ticker: pool_1.reserves,
            pool_2.ticker: pool_2.reserves,
            "steps": steps,
        }
    )
    p.vbar(
        x=dodge("steps", -0.1, range=p.x_range),
        top=pool_1.ticker,
        source=source,
        width=0.2,
        alpha=0.5,
        color="blue",
        legend_label=f"{pool_1.ticker} Pool",
    )
    p.vbar(
        x=dodge("steps", 0.1, range=p.x_range),
        top=pool_2.ticker,
        source=source,
        width=0.2,
        alpha=0.5,
        color="red",
        legend_label=f"{pool_2.ticker} Pool",
    )
    return p


def with_price_info(p, mid: MidPrice, price_label: str) -> figure:
    """Hover tool with price info for the given point."""
    point_id = str(hash(str(mid.x) + str(mid.y)))
    p.circle([mid.x], [mid.y], size=10, color="red", alpha=0.4, name=point_id)
    # use hover tool to display info
    hover = p.select(dict(type=HoverTool, names=[point_id]))
    if not hover:
        hover = HoverTool(names=[point_id])
        p.add_tools(hover)
    hover.tooltips = [
        (f"{mid.x_ticker}", f"{mid.x:.3f}"),
        (f"{mid.y_ticker}", f"{mid.y:.3f}"),
        (f"{price_label}", f"{mid.mid_price:.3f}"),
    ]
    return p


def cp_amm_autoviz(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    dx: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
    precision: float | None = None,
    plot_width=900,
    plot_height=600,
    compact=True,
):
    """Autoviz for liquidity pools.

    Args:
        pool_1 (Pool):
            Liquidity pool 1

        pool_2 (Pool):
            Liquidity pool 2

        k (float, optional):
            Constant product invariant

        dx (float, optional):
            The order size

        x_min (float, optional):
            Start of the range for the x-axis

        x_max (float, optional):
            End of the range for the x-axis

        num (int, optional):
            Number of points to plot

        precision (float, optional):
            Precision at which the invariant is evaluated

        plot_width (int, optional):
            Width of the plot

        plot_height (int, optional):
            Height of the plot

        compact (bool, optional):
            If True, 2 plots per row are displayed
            Else, 1 plot per row is displayed

    """

    dx = dx or 0.1 * pool_1.balance
    p1 = new_constant_product_figure(
        pool_1,
        pool_2,
        k=k,
        plot_width=plot_width,
        plot_height=plot_height,
        x_min=x_min,
        x_max=x_max,
        num=num,
    )
    p2 = new_price_impact_figure(
        pool_1,
        pool_2,
        k=k,
        dx=dx,
        precision=precision,
        plot_width=plot_width,
        plot_height=plot_height,
        x_min=x_min,
        x_max=x_max,
        num=num,
    )
    constant_product_swap(dx, pool_1, pool_2, k=k, precision=precision)
    p3 = new_pool_figure(
        pool_1,
        pool_2,
        ["Before Swap", "After Swap"],
        plot_width=plot_width,
        plot_height=plot_height,
    )
    reset_pools(pool_1, pool_2)
    p4 = new_order_book_figure(
        pool_1, pool_2, k=k, plot_width=plot_width, plot_height=plot_height
    )
    if compact:
        show(grid([[p1, p2], [p3, p4]], sizing_mode="stretch_both"))
    else:
        show(column([p1, p2, p3, p4], sizing_mode="stretch_both"))
