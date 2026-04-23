from typing import Optional, Dict
import pandas as pd

from app.services.strategy_builder import (
    build_long_call,
    build_long_put,
    build_bull_call_spread,
    build_bear_put_spread,
    build_straddle,
    build_strangle,
    build_iron_condor,
    pick_atm_row,
    pick_otm_call,
    pick_otm_put,
    find_spread_pair,
)


def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))


def choose_strategy_with_legs(
    stock_bias: str,
    stock_score: float,
    news_score: float,
    expiry: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    call_best: Optional[dict],
    put_best: Optional[dict],
    weekly_best: Optional[dict],
    swing_best: Optional[dict],
    spot: float,
):
    call_score = call_best["total_score"] if call_best else 0
    put_score = put_best["total_score"] if put_best else 0
    call_iv = call_best["iv_score"] if call_best else 50
    put_iv = put_best["iv_score"] if put_best else 50
    score_gap = abs(call_score - put_score)

    result = {
        "strategy_name": "No Clear Strategy",
        "strategy_bias": "neutral",
        "strategy_score": 50,
        "strategy_reason": "No strong strategy edge detected.",
        "legs": [],
        "estimated_debit": 0.0,
        "estimated_credit": 0.0,
        "max_profit": "N/A",
        "max_loss": "N/A",
        "breakeven_low": None,
        "breakeven_high": None,
    }

    # Neutral / range-bound -> Iron Condor
    if stock_bias == "neutral" and score_gap < 8:
        atm_call = pick_atm_row(calls_df, spot)
        atm_put = pick_atm_row(puts_df, spot)
        if atm_call is not None and atm_put is not None:
            short_call = pick_otm_call(calls_df, spot, step=1)
            long_call = pick_otm_call(calls_df, spot, step=2)
            short_put = pick_otm_put(puts_df, spot, step=1)
            long_put = pick_otm_put(puts_df, spot, step=2)

            if short_call is not None and long_call is not None and short_put is not None and long_put is not None:
                built = build_iron_condor(short_call, long_call, short_put, long_put, expiry)
                result.update(built)
                result.update({
                    "strategy_bias": "neutral",
                    "strategy_score": 72,
                    "strategy_reason": "Trend is neutral and both sides are tradable, so a neutral income structure is preferred.",
                })
                return result

    # Bullish
    if stock_bias == "bullish" and call_best and call_score >= 65:
        long_row = calls_df[calls_df["strike"].astype(float) == float(call_best["strike"])]
        long_row = long_row.iloc[0] if not long_row.empty else pick_atm_row(calls_df, spot)

        if long_row is not None:
            if call_iv >= 65:
                short_row = find_spread_pair(calls_df, float(long_row["strike"]), direction="up", width_steps=1)
                if short_row is not None and float(short_row["strike"]) > float(long_row["strike"]):
                    built = build_bull_call_spread(long_row, short_row, expiry)
                    result.update(built)
                    result.update({
                        "strategy_bias": "bullish",
                        "strategy_score": clamp(call_score + 3, 0, 100),
                        "strategy_reason": "Bullish trend exists, but volatility is rich enough that a bull call spread is more efficient than a naked long call.",
                    })
                    return result

            built = build_long_call(long_row, expiry)
            result.update(built)
            result.update({
                "strategy_bias": "bullish",
                "strategy_score": clamp(call_score + 5, 0, 100),
                "strategy_reason": "Bullish directional edge with acceptable premium profile supports a long call.",
            })
            return result

    # Bearish
    if stock_bias == "bearish" and put_best and put_score >= 65:
        long_row = puts_df[puts_df["strike"].astype(float) == float(put_best["strike"])]
        long_row = long_row.iloc[0] if not long_row.empty else pick_atm_row(puts_df, spot)

        if long_row is not None:
            if put_iv >= 65:
                short_row = find_spread_pair(puts_df, float(long_row["strike"]), direction="down", width_steps=1)
                if short_row is not None and float(short_row["strike"]) < float(long_row["strike"]):
                    built = build_bear_put_spread(long_row, short_row, expiry)
                    result.update(built)
                    result.update({
                        "strategy_bias": "bearish",
                        "strategy_score": clamp(put_score + 3, 0, 100),
                        "strategy_reason": "Bearish edge exists, but long premium is relatively expensive, so a bear put spread is more capital efficient.",
                    })
                    return result

            built = build_long_put(long_row, expiry)
            result.update(built)
            result.update({
                "strategy_bias": "bearish",
                "strategy_score": clamp(put_score + 5, 0, 100),
                "strategy_reason": "Bearish directional edge with acceptable premium supports a long put.",
            })
            return result

    # Non-directional large move -> Straddle / Strangle
    if call_best and put_best and abs(stock_score - 50) <= 12:
        atm_call = pick_atm_row(calls_df, spot)
        atm_put = pick_atm_row(puts_df, spot)

        if atm_call is not None and atm_put is not None and score_gap <= 10:
            built = build_straddle(atm_call, atm_put, expiry)
            result.update(built)
            result.update({
                "strategy_bias": "non-directional",
                "strategy_score": 68,
                "strategy_reason": "Direction is unclear, but both sides are active and a large move either way may be tradable with a straddle.",
            })
            return result

        otm_call = pick_otm_call(calls_df, spot, step=1)
        otm_put = pick_otm_put(puts_df, spot, step=1)
        if otm_call is not None and otm_put is not None:
            built = build_strangle(otm_call, otm_put, expiry)
            result.update(built)
            result.update({
                "strategy_bias": "non-directional",
                "strategy_score": 64,
                "strategy_reason": "Direction is mixed, so a cheaper volatility structure like a strangle is favored.",
            })
            return result

    return result