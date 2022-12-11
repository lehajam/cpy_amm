from __future__ import annotations

from typing import Tuple


class Pool:
    """Liquidity pool."""

    def __init__(self, ticker: str, initial_deposit: float):
        # Ticker for the coin in the pool
        self.ticker = ticker
        # The ongoing reserves of the pool
        self.reserves = [float(initial_deposit)]

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


def split_ticker(trading_pair: str) -> Tuple[str, str]:
    assert trading_pair.count("/") == 1
    base_quote = trading_pair.split("/")
    return base_quote[0], base_quote[1]


class MarketQuote:
    def __init__(self, trading_pair: str, price: float):
        """Quote for the market price of a trading pair.

        Args:
            trading_pair (str) :
                The trading pair ticker eg. ETH/USD

            price (float) :
                The market price of the trading pair

        """
        base, quote = split_ticker(trading_pair)
        self.token_base = base
        self.token_quote = quote
        self.price = price

    @property
    def ticker(self) -> str:
        """The ticker for the trading pair."""
        return f"{self.token_base}/{self.token_quote}"

    def __str__(self):
        return f"{self.ticker}={self.price}"

    def __repr__(self):
        return f"{self.ticker}={self.price}"


class MarketPair:
    """Market pair."""

    def __init__(self, pool_1: Pool, pool_2: Pool):
        # The ongoing reserves of the pool
        self.pool_1 = pool_1
        # The ongoing reserves of the pool
        self.pool_2 = pool_2

    @property
    def ticker(self) -> str:
        """The ticker for the trading pair represented by this market."""
        return f"{self.pool_1.ticker}/{self.pool_2.ticker}"

    @property
    def inverse_ticker(self) -> str:
        """The ticker for the inverse trading pair represented by this market."""
        return f"{self.pool_2.ticker}/{self.pool_1.ticker}"

    @property
    def cp_invariant(self) -> float:
        """The constant product invariant."""
        return self.pool_1.balance * self.pool_2.balance

    def get_pools(self, trading_pair: str) -> Tuple[Pool, Pool]:
        """The constant product invariant."""
        if trading_pair == self.ticker:
            return self.pool_1, self.pool_2
        elif trading_pair == self.inverse_ticker:
            return self.pool_2, self.pool_1
        else:
            raise Exception(f"Unknown trading pair {trading_pair}")

    def get_reserves(self, trading_pair: str) -> Tuple[float, float]:
        """The constant product invariant."""
        pool_1, pool_2 = self.get_pools(trading_pair)
        return pool_1.balance, pool_2.balance

    def add_liquidity(
        self, liq_amount: float, quote_1: MarketQuote, quote_2: MarketQuote
    ):
        """Adds a given amount of liquidity in the AMM at the current price of the pool.
        The amount of token to add in each pool is determined from the market price of
        the tokens and the current price of the pool.

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
        x = self.pool_1.balance
        y = self.pool_2.balance
        alpha = (quote_1.price * x) / (quote_1.price * x + quote_2.price * y)
        liq_amount_1 = liq_amount * alpha / quote_1.price
        liq_amount_2 = liq_amount * (1 - alpha) / quote_2.price
        self.pool_1.reserves.append(x + liq_amount_1)
        self.pool_2.reserves.append(y + liq_amount_2)


def new_market(
    liq_amount: float, quote_1: MarketQuote, quote_2: MarketQuote
) -> MarketPair:
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
    return MarketPair(Pool(quote_1.token_base, x_0), Pool(quote_2.token_base, y_0))


class TradeOrder:
    """Trade order."""

    def __init__(self, trading_pair: str, order_size: float):
        #
        ticker_in, ticker_out = split_ticker(trading_pair)
        # The ongoing reserves of the pool
        self.ticker_in = ticker_in
        # The ongoing reserves of the pool
        self.ticker_out = ticker_out
        # The ongoing reserves of the pool
        self.order_size = order_size

    @property
    def ticker(self) -> str:
        """The trading pair ticker for the order."""
        return f"{self.ticker_in}/{self.ticker_out}"

    @classmethod
    def create_default(cls, mkt: MarketPair) -> TradeOrder:
        return cls(mkt.ticker, 0.1 * mkt.pool_1.balance)
