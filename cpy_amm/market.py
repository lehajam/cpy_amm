from __future__ import annotations

from typing import List, Tuple


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
    """A Market pair managing a liquidity pool made up of reserves of two tokens."""

    def __init__(self, pool_1: Pool, pool_2: Pool, swap_fee: float):
        # The ongoing reserves of the pool
        self.pool_1 = pool_1
        # The ongoing reserves of the pool
        self.pool_2 = pool_2
        # The swap fee
        self.swap_fee = swap_fee
        # Transaction fees collected
        self.transaction_fees: dict[str, List[float]] = {
            pool_1.ticker: [],
            pool_2.ticker: [],
        }

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
        """Return pools in correct order based on the trading pairs (normal or inversed).

        Args:
            trading_pair (str) :
                The trading pair ticker eg. ETH/USD

        Returns:
            Tuple[Pool, Pool]:
                (Liquidity pool 1, Liquidity pool 2)

        """

        if trading_pair == self.ticker:
            return self.pool_1, self.pool_2
        elif trading_pair == self.inverse_ticker:
            return self.pool_2, self.pool_1
        else:
            raise Exception(f"Unknown trading pair {trading_pair}")

    def get_reserves(self, trading_pair: str) -> Tuple[float, float]:
        """Return reserves in correct order based on the trading pairs (normal or
        inversed).

        Args:
            trading_pair (str) :
                The trading pair ticker eg. ETH/USD

        Returns:
            Tuple[Pool, Pool]:
                (Liquidity pool 1, Liquidity pool 2)

        """
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
    liq_amount: float, quote_1: MarketQuote, quote_2: MarketQuote, swap_fee: float
) -> MarketPair:
    """Initializes a market with a given amount of liquidity and market prices for the
    tokens.

    Args:
        liq_amount (float) :
            The amount of liquidity to be added expressed
            in FIAT currency or token eg. USD, EUR, USDT, ETH etc.

        quote_1 (MarketQuote) :
            The market quote for the token in the first pool

        quote_2 (MarketQuote) :
            The market quote for the token in the second pool

        swap_fee (float) :
            The transaction fee per swap always paid in the base currency (token in)

    Returns:
        MarketPair:
            New market pair

    """
    liq_per_token = liq_amount / 2.0
    x_0 = liq_per_token / quote_1.price
    y_0 = liq_per_token / quote_2.price
    return MarketPair(
        Pool(quote_1.token_base, x_0), Pool(quote_2.token_base, y_0), swap_fee
    )


class TradeOrder:
    """A trade order for a swap to execute."""

    def __init__(self, trading_pair: str, order_size: float, transaction_fees: float):
        ticker_in, ticker_out = split_ticker(trading_pair)
        # ticker of the tocken swapped in
        self.ticker_in = ticker_in
        # ticker of the tocken swapped out
        self.ticker_out = ticker_out
        # the order size
        self.order_size = order_size
        # the order size minus transaction fees
        self.net_order_size = self.order_size / (1.0 + transaction_fees)
        # the trannsaction fees
        self.cash_transaction_fee = self.order_size - self.net_order_size

    @property
    def ticker(self) -> str:
        """The trading pair ticker for the order."""
        return f"{self.ticker_in}/{self.ticker_out}"

    @classmethod
    def create_default(cls, mkt: MarketPair) -> TradeOrder:
        """Default order equal to 10% of the first pool."""
        return cls(mkt.ticker, 0.1 * mkt.pool_1.balance, mkt.swap_fee)
