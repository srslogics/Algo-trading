import pytest

from optionlab.analytics.options import implied_volatility, price_and_greeks


def test_black_scholes_reference_and_put_call_parity():
    from math import exp

    call = price_and_greeks(100, 100, 1, 0.05, 0.2, "CE")
    put = price_and_greeks(100, 100, 1, 0.05, 0.2, "PE")
    assert call["price"] == pytest.approx(10.45058357)
    assert put["price"] == pytest.approx(5.57352602)
    assert call["price"] - put["price"] == pytest.approx(100 - 100 * exp(-0.05))
    assert call["delta"] - put["delta"] == pytest.approx(1)


@pytest.mark.parametrize("kind", ["CE", "PE"])
def test_iv_roundtrip(kind):
    p = price_and_greeks(24000, 24500, 0.08, 0.06, 0.23, kind)["price"]
    assert implied_volatility(p, 24000, 24500, 0.08, 0.06, kind) == pytest.approx(0.23)


def test_invalid_and_expired_iv_not_invented():
    assert implied_volatility(0, 100, 100, 1, 0.05, "CE") is None
    assert implied_volatility(150, 100, 100, 1, 0.05, "CE") is None
    assert implied_volatility(10, 100, 100, 0, 0.05, "CE") is None
    with pytest.raises(ValueError):
        price_and_greeks(100, 100, 0, 0.05, 0.2, "CE")
