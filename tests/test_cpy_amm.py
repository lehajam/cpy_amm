#!/usr/bin/env python

"""Tests for `cpy_amm` package."""

import numpy as np
import pytest

from cpy_amm.swap import Pool, constant_product_curve, constant_product_swap


def test_pool_creation():
    """Tests creation of a pool."""
    ticker = "A"
    reserve = 100
    pool = Pool(ticker, reserve)
    assert pool.ticker == ticker
    assert pool.balance == reserve
    assert pool.reserves == [reserve]
    assert pool.initial_deposit == reserve


@pytest.mark.parametrize(
    "reserve_1,reserve_2",
    [
        (10, 2),
        (100, 100),
        (1000, 1000),
        (10000, 10000),
        (100000, 100000),
        (1000000, 1000000),
        (10000000, 10000000),
        (100000000, 100000000),
        (1000000000, 1000000000),
        (
            134566.678899,
            134566.67889927,
        ),
    ],
)
def test_constant_product_curve(reserve_1, reserve_2):
    """Tests that the constant product curve remains invariant in the XY curve produced
    by constant_product_curve."""
    x, y = constant_product_curve(
        Pool("A", reserve_1),
        Pool("B", reserve_2),
        x_min=0.1 * reserve_1,
        x_max=10.0 * reserve_2,
        num=1000,
    )
    assert len(x) == len(y) == 1000
    k_actual = np.multiply(x, y)
    k_expected = [reserve_1 * reserve_2] * len(k_actual)
    assert np.allclose(k_expected, k_actual, rtol=1e-14)


@pytest.mark.parametrize(
    "reserve_1,reserve_2,precision",
    [
        (10, 2, 1e-14),
        (100, 100, 1e-10),
        (1000, 1000, 1e-09),
        (10000, 10000, 1e-07),
        (100000, 100000, 1e-05),
        (1000000, 1000000, 1e-3),
        (10000000, 10000000, 1e-1),
        (100000000, 100000000, 1e1),
        (1000000000, 1000000000, 1e3),
        (
            134566.678899,
            134566.67889927,
            1e-05,
        ),
    ],
)
def test_constant_product_swap(reserve_1, reserve_2, precision):
    """Tests that swaping produces the same curve as constant_product_curve."""
    x, y = constant_product_curve(
        Pool("A", reserve_1),
        Pool("B", reserve_2),
        x_min=0.01 * reserve_1,
        x_max=10.0 * reserve_2,
        num=10000,
    )

    i = 0
    dx = np.diff(x)
    x_actual, y_actual = [x[0]], [y[0]]
    pool_1, pool_2 = Pool("A", x[0]), Pool("B", y[0])
    while i < len(dx):
        dy, _ = constant_product_swap(dx[i], pool_1, pool_2, precision=precision)
        x_actual.append(x_actual[i] + dx[i])
        y_actual.append(y_actual[i] - dy)
        i = i + 1
    assert np.allclose(x_actual, x, rtol=1e-14)
    assert np.allclose(y_actual, y, rtol=1e-14)
