from math import sqrt
from typing import Tuple

import numpy as np
from loguru import logger


class Pool:
    """Liquidity pool."""

    def __init__(self, ticker: str, initial_deposit: float):
        # Ticker for the coin in the pool
        self.ticker = ticker
        # The ongoing reserves of the pool
        self.reserves = [float(initial_deposit)]

    def reset(self):
        """Reset the pool."""
        self.reserves = [self.initial_deposit]

    @property
    def balance(self) -> float:
        """The current balance of the pool."""
        assert len(self.reserves) > 0
        return self.reserves[-1]

    @property
    def initial_deposit(self) -> float:
        """The initial deposit in the pool."""
        assert len(self.reserves) > 0
        return self.reserves[0]


class MarketQuote:
    def __init__(self, trading_pair: str, price: float):
        """Quote for the market price of a trading pair.

        Args:
            trading_pair (str) :
                The trading pair ticker eg. ETH/USD

            price (float) :
                The market price of the trading pair

        """
        assert trading_pair.count("/") == 1
        base_quote = trading_pair.split("/")
        self.token_base = base_quote[0]
        self.token_quote = base_quote[1]
        self.price = price

    @property
    def ticker(self) -> str:
        """The ticker for the trading pair."""
        return f"{self.token_base}/{self.token_quote}"

    def __str__(self):
        return f"{self.ticker}={self.price}"

    def __repr__(self):
        return f"{self.ticker}={self.price}"


class MidPrice:
    def __init__(self, trading_pair: str, x: float, y: float):
        """The price between what users can buy and sell tokens at a given moment. In
        Uniswap this is the ratio of the two ERC20 token reserves.

        Args:
            trading_pair (str) :
                The trading pair ticker eg. ETH/USD

            x (float) :
                Reserve of token A before swap

            y (float) :
                Reserve of token B before swap

        """
        assert x > 0
        assert y > 0
        assert trading_pair.count("/") == 1
        xy_ticker = trading_pair.split("/")
        self.x_ticker = xy_ticker[0]
        self.y_ticker = xy_ticker[1]
        self.x = x
        self.y = y
        self.mid_price = x / y


class PriceImpactRange:
    def __init__(self, start: MidPrice, mid: MidPrice, end: MidPrice):
        """Price impact range of a swap. Starts at mid price before the swap, ends at mid
        price after the swap. Also contains the point where mid price is equal to the
        swap execution price.

        Args:
            start (MidPrice) :
                point corresponding to the mid price of the pool before swap

            mid (MidPrice) :
                point corresponding to the execution price of the swap
                eg. (x,y,x/y) where mid price == execution price

            end (MidPrice) :
                point corresponding to the next mid price of the pool
                eg. next price after swap

        """
        self.start = start
        self.mid = mid
        self.end = end


def reset_pools(*pools):
    for pool in pools:
        assert isinstance(pool, Pool)
        pool.reset()


def init_liquidity(liq_amount: float, quote_1: MarketQuote, quote_2: MarketQuote):
    """Initializes a given amount of liquidity in the AMM.

    Args:
        liq_amount (float) :
            The amount of liquidity to be added expressed
            in FIAT currency or token eg. USD, EUR, USDT, ETH etc.

        quote_1 (MarketQuote) :
            The market quote for the token in the first pool

        quote_2 (MarketQuote) :
            The market quote for the token in the second pool

    Returns:
        None

    """
    liq_per_token = liq_amount / 2.0
    x_0 = liq_per_token / quote_1.price
    y_0 = liq_per_token / quote_2.price
    k_0 = x_0 * y_0
    return Pool(quote_1.token_base, x_0), Pool(quote_2.token_base, y_0), k_0


def add_liquidity(
    x: Pool, y: Pool, liq_amount: float, quote_1: MarketQuote, quote_2: MarketQuote
):
    """Adds a given amount of liquidity in the AMM at the current price of the pool. The
    amount of token to add in each pool is determined from the market price of the tokens
    and the current price of the pool.

    Args:
        x (Pool) :
            Liquidity pool for tokens A

        y (Pool) :
            Liquidity pool for tokens B

        liq_amount (float) :
            The amount of liquidity to be added expressed
            in FIAT currency or token eg. USD, EUR, USDT, ETH etc.

        quote_1 (MarketQuote) :
            The market quote for the token in the first pool

        quote_2 (MarketQuote) :
            The market quote for the token in the second pool

    Returns:
        None

    """
    alpha = (quote_1.price * x.balance) / (
        quote_1.price * x.balance + quote_2.price * y.balance
    )
    liq_amount_1 = liq_amount * alpha / quote_1.price
    liq_amount_2 = liq_amount * (1 - alpha) / quote_2.price
    x.reserves.append(x.balance + liq_amount_1)
    y.reserves.append(y.balance + liq_amount_2)


def assert_cp_invariant(x: float, y: float, k: float, precision: float | None = None):
    """Asserts that the constant product is invariant.

    Args:
        k (float) :
            Constant product

        x (float) :
            Reserve of tokens A

        y (float) :
            Reserve of tokens B

        precision (float) :
            Precision at which the invariant is evaluated

    Returns:
        None

    """
    precision = precision or 1e-7
    try:
        assert abs((x * y) - k) <= precision
    except Exception as e:
        logger.error("Constant product invariant not satisfied")
        logger.error(f"diff={abs((x*y) - k)}")
        logger.error(f"precision={precision}")
        logger.error(f"x={x}")
        logger.error(f"y={y}")
        logger.error(f"x*y={x*y}")
        logger.error(f"k={k}")
        raise e


def constant_product_swap(
    dx: float,
    x: Pool,
    y: Pool,
    k: float | None = None,
    trading_fee: float = 0.003,
    precision: float | None = None,
) -> Tuple[float, float]:
    """Swap tokens A for tokens B from pool with a XY constant product.

    Args:
        dx (float) :
            Amount of tokens A in

        x (Pool) :
            Pool representing the reserve of tokens A

        y (float) :
            Pool representing the reserve of tokens B

    Returns:
        Tuple[float, float] :
            (Amount of tokens B out, Swap execution price)

    """
    assert dx > 0
    # constant product invariant
    k = k or x.balance * y.balance
    # assert k is invariant
    assert_cp_invariant(x.balance, y.balance, k, precision)
    # calculate dy amount of tokens B to be taken out from the AMM
    dy = (y.balance * dx) / (x.balance + dx)
    # add dx amount of tokens A to the AMM
    x.reserves.append(x.balance + dx)
    # take dy amount of tokens B out from the AMM
    y.reserves.append(y.balance - dy)
    # assert k is still invariant
    assert_cp_invariant(x.balance, y.balance, k, precision)
    # return dy amount of tokens B taken out and execution price
    return dy, dx / dy


def swap_price(x: float, y: float, dx: float) -> float:
    """Computes the swap execution price for an order size given two pools with reserves
    x and y.

    Args:
        dx (float) :
            Order size

        x (float) :
            Reserve of tokens A

        y (float) :
            Reserve of tokens B

    Returns:
        float :
            Swap execution price

    """
    return (x + dx) / y


def constant_product_curve(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
) -> Tuple[list[float], list[float]]:
    """Computes the AMM curve Y = K/X for a constant product AMM K = XY

    Args:
        pool_1 (Pool) :
            liquidity pool 1 eg. X

        pool_1 (Pool) :
            liquidity pool 2 eg. Y

        k (float) :
            constant product invariant

        x_min (float) :
            minimum value of X

        x_max (float) :
            maximum value of X

        num (float) :
            number of points to be computed

    Returns:
        Tuple[list[float],list[float]] :
            (Amount of tokens B out, Swap execution price)

    """
    # constant product invariant
    k = k or pool_1.balance * pool_2.balance
    x_min = x_min or 0.1 * pool_1.balance
    x_max = x_max or 5.0 * pool_1.balance
    num = num or 1000
    x = np.linspace(x_min, x_max, num=num)
    y = k / x
    return x, y


def price_impact_range(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    dx: float | None = None,
    precision: float | None = None,
) -> PriceImpactRange:
    """Computes the price impact range given liquidity pool 1, liquidity pool 2 and an
    order size.

    Args:
        pool_1 (Pool) :
            liquidity pool 1 eg. X

        pool_1 (Pool) :
            liquidity pool 2 eg. Y

        k (float) :
            constant product invariant. Defaults to XY.

        dx (float) :
            order size. Defaults to 10% of reserves of liquidity pool 1.

        precision (float) :
            precision at which the invariant is evaluated

    Returns:
        PriceImpactRange :
            Price impact range for given pools and order size

    """
    # constant product invariant
    k = k or pool_1.balance * pool_2.balance
    # trade size provided or defaulted to 10% of x
    dx = dx or 0.1 * pool_1.balance
    # start: (x,y)
    x_start = pool_1.balance
    y_start = pool_2.balance
    # end: (x+dx, y-dy)
    x_end = x_start + dx
    y_end = y_start * (1.0 - dx / (x_start + dx))
    # assert k is invariant at start and end
    assert_cp_invariant(x_start, y_start, k, precision)
    assert_cp_invariant(x_end, y_end, k, precision)
    # swap execution price at start for dx amount of tokens A
    exec_price = swap_price(x_start, y_start, dx)
    # (x, y) of the mid price equal to the execution price
    x_mid = sqrt(k * exec_price)
    y_mid = k / sqrt(k * exec_price)
    # the ticker for the XY pair eg. ETH/DAI
    ticker = f"{pool_1.ticker}/{pool_2.ticker}"
    return PriceImpactRange(
        MidPrice(ticker, x_start, y_start),
        MidPrice(ticker, x_mid, y_mid),
        MidPrice(ticker, x_end, y_end),
    )


def order_book(
    pool_1: Pool,
    pool_2: Pool,
    k: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
    num: int | None = None,
):
    """Computes the cumulative quantity at any mid price according to the formula from
    the paper "Order Book Depth and Liquidity Provision in Automated Market Makers".

    Args:
        pool_1 (Pool) :
            liquidity pool 1 eg. X

        pool_1 (Pool) :
            liquidity pool 2 eg. Y

        k (float) :
            constant product invariant

        x_min (float) :
            minimum value of X

        x_max (float) :
            maximum value of X

        num (float) :
            number of points to be computed

    Returns:
        Tuple[list[float],list[float]] :
            (reserves of token A, reserves of token B)

    """
    q = []
    x_0 = float(pool_1.initial_deposit)
    p_0 = float(pool_1.initial_deposit / pool_2.initial_deposit)
    x, y = constant_product_curve(pool_1, pool_2, k, x_min, x_max, num)
    p = [x_i / y_i for x_i, y_i in zip(x, y)]
    for p_i in p:
        q_i = float(0)
        if p_i < p_0:
            q_i = x_0 * (sqrt(p_0 / p_i) - 1)
        if p_i > p_0:
            q_i = x_0 * (1 - sqrt(p_0 / p_i))
        q.append(q_i)
    return x, p, q
