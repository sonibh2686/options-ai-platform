from typing import Optional, List, Dict, Tuple
import math
import pandas as pd


def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def get_mid(row: pd.Series) -> float:
    bid = safe_float(row.get("bid", 0.0))
    ask = safe_float(row.get("ask", 0.0))
    last_price = safe_float(row.get("lastPrice", 0.0))
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2.0, 4)
    return round(max(last_price, 0.01), 4)


def nearest_strike_rows(df: pd.DataFrame, strike: float, count: int = 1, above: bool | None = None) -> pd.DataFrame:
    data = df.copy()
    if above is True:
        data = data[data["strike"] >= strike]
    elif above is False:
        data = data[data["strike"] <= strike]

    if data.empty:
        return pd.DataFrame()

    data["dist"] = (data["strike"] - strike).abs()
    data = data.sort_values(["dist", "strike"])
    return data.head(count).copy()


def pick_atm_row(df: pd.DataFrame, spot: float) -> Optional[pd.Series]:
    rows = nearest_strike_rows(df, spot, count=1)
    if rows.empty:
        return None
    return rows.iloc[0]


def pick_otm_call(df: pd.DataFrame, spot: float, step: int = 1) -> Optional[pd.Series]:
    higher = df[df["strike"] >= spot].sort_values("strike")
    if higher.empty:
        return None
    idx = min(max(step - 1, 0), len(higher) - 1)
    return higher.iloc[idx]


def pick_otm_put(df: pd.DataFrame, spot: float, step: int = 1) -> Optional[pd.Series]:
    lower = df[df["strike"] <= spot].sort_values("strike", ascending=False)
    if lower.empty:
        return None
    idx = min(max(step - 1, 0), len(lower) - 1)
    return lower.iloc[idx]


def find_spread_pair(df: pd.DataFrame, long_strike: float, direction: str, width_steps: int = 1) -> Optional[pd.Series]:
    strikes = sorted(df["strike"].dropna().astype(float).unique())
    if not strikes:
        return None

    try:
        idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - long_strike))
    except Exception:
        return None

    if direction == "up":
        target_idx = min(idx + width_steps, len(strikes) - 1)
    else:
        target_idx = max(idx - width_steps, 0)

    target_strike = strikes[target_idx]
    rows = df[df["strike"].astype(float) == target_strike]
    if rows.empty:
        return None
    return rows.iloc[0]


def build_long_call(row: pd.Series, expiry: str) -> Dict:
    strike = safe_float(row["strike"])
    premium = get_mid(row)
    return {
        "strategy_name": "Long Call",
        "legs": [
            {"action": "BUY", "type": "CALL", "strike": strike, "expiry": expiry, "premium": premium}
        ],
        "estimated_debit": round(premium, 4),
        "estimated_credit": 0.0,
        "max_profit": "Unlimited",
        "max_loss": round(premium, 4),
        "breakeven_low": None,
        "breakeven_high": round(strike + premium, 4),
    }


def build_long_put(row: pd.Series, expiry: str) -> Dict:
    strike = safe_float(row["strike"])
    premium = get_mid(row)
    return {
        "strategy_name": "Long Put",
        "legs": [
            {"action": "BUY", "type": "PUT", "strike": strike, "expiry": expiry, "premium": premium}
        ],
        "estimated_debit": round(premium, 4),
        "estimated_credit": 0.0,
        "max_profit": round(max(strike - premium, 0), 4),
        "max_loss": round(premium, 4),
        "breakeven_low": round(strike - premium, 4),
        "breakeven_high": None,
    }


def build_bull_call_spread(long_call: pd.Series, short_call: pd.Series, expiry: str) -> Dict:
    long_strike = safe_float(long_call["strike"])
    short_strike = safe_float(short_call["strike"])
    buy_premium = get_mid(long_call)
    sell_premium = get_mid(short_call)
    debit = round(max(buy_premium - sell_premium, 0.01), 4)
    width = round(short_strike - long_strike, 4)
    max_profit = round(max(width - debit, 0.0), 4)

    return {
        "strategy_name": "Bull Call Spread",
        "legs": [
            {"action": "BUY", "type": "CALL", "strike": long_strike, "expiry": expiry, "premium": buy_premium},
            {"action": "SELL", "type": "CALL", "strike": short_strike, "expiry": expiry, "premium": sell_premium},
        ],
        "estimated_debit": debit,
        "estimated_credit": 0.0,
        "max_profit": max_profit,
        "max_loss": debit,
        "breakeven_low": None,
        "breakeven_high": round(long_strike + debit, 4),
    }


def build_bear_put_spread(long_put: pd.Series, short_put: pd.Series, expiry: str) -> Dict:
    long_strike = safe_float(long_put["strike"])
    short_strike = safe_float(short_put["strike"])
    buy_premium = get_mid(long_put)
    sell_premium = get_mid(short_put)
    debit = round(max(buy_premium - sell_premium, 0.01), 4)
    width = round(long_strike - short_strike, 4)
    max_profit = round(max(width - debit, 0.0), 4)

    return {
        "strategy_name": "Bear Put Spread",
        "legs": [
            {"action": "BUY", "type": "PUT", "strike": long_strike, "expiry": expiry, "premium": buy_premium},
            {"action": "SELL", "type": "PUT", "strike": short_strike, "expiry": expiry, "premium": sell_premium},
        ],
        "estimated_debit": debit,
        "estimated_credit": 0.0,
        "max_profit": max_profit,
        "max_loss": debit,
        "breakeven_low": round(long_strike - debit, 4),
        "breakeven_high": None,
    }


def build_straddle(call_row: pd.Series, put_row: pd.Series, expiry: str) -> Dict:
    call_strike = safe_float(call_row["strike"])
    put_strike = safe_float(put_row["strike"])
    call_premium = get_mid(call_row)
    put_premium = get_mid(put_row)
    debit = round(call_premium + put_premium, 4)
    atm_strike = round((call_strike + put_strike) / 2.0, 4)

    return {
        "strategy_name": "Long Straddle",
        "legs": [
            {"action": "BUY", "type": "CALL", "strike": call_strike, "expiry": expiry, "premium": call_premium},
            {"action": "BUY", "type": "PUT", "strike": put_strike, "expiry": expiry, "premium": put_premium},
        ],
        "estimated_debit": debit,
        "estimated_credit": 0.0,
        "max_profit": "Unlimited / Large on downside to strike",
        "max_loss": debit,
        "breakeven_low": round(atm_strike - debit, 4),
        "breakeven_high": round(atm_strike + debit, 4),
    }


def build_strangle(call_row: pd.Series, put_row: pd.Series, expiry: str) -> Dict:
    call_strike = safe_float(call_row["strike"])
    put_strike = safe_float(put_row["strike"])
    call_premium = get_mid(call_row)
    put_premium = get_mid(put_row)
    debit = round(call_premium + put_premium, 4)

    return {
        "strategy_name": "Long Strangle",
        "legs": [
            {"action": "BUY", "type": "CALL", "strike": call_strike, "expiry": expiry, "premium": call_premium},
            {"action": "BUY", "type": "PUT", "strike": put_strike, "expiry": expiry, "premium": put_premium},
        ],
        "estimated_debit": debit,
        "estimated_credit": 0.0,
        "max_profit": "Unlimited / Large on downside to strike",
        "max_loss": debit,
        "breakeven_low": round(put_strike - debit, 4),
        "breakeven_high": round(call_strike + debit, 4),
    }


def build_iron_condor(short_call: pd.Series, long_call: pd.Series, short_put: pd.Series, long_put: pd.Series, expiry: str) -> Dict:
    sc = safe_float(short_call["strike"])
    lc = safe_float(long_call["strike"])
    sp = safe_float(short_put["strike"])
    lp = safe_float(long_put["strike"])

    sc_p = get_mid(short_call)
    lc_p = get_mid(long_call)
    sp_p = get_mid(short_put)
    lp_p = get_mid(long_put)

    credit = round((sc_p - lc_p) + (sp_p - lp_p), 4)
    call_width = max(lc - sc, 0.0)
    put_width = max(sp - lp, 0.0)
    max_width = max(call_width, put_width)
    max_loss = round(max(max_width - credit, 0.0), 4)

    return {
        "strategy_name": "Iron Condor",
        "legs": [
            {"action": "SELL", "type": "CALL", "strike": sc, "expiry": expiry, "premium": sc_p},
            {"action": "BUY", "type": "CALL", "strike": lc, "expiry": expiry, "premium": lc_p},
            {"action": "SELL", "type": "PUT", "strike": sp, "expiry": expiry, "premium": sp_p},
            {"action": "BUY", "type": "PUT", "strike": lp, "expiry": expiry, "premium": lp_p},
        ],
        "estimated_debit": 0.0,
        "estimated_credit": credit,
        "max_profit": credit,
        "max_loss": max_loss,
        "breakeven_low": round(sp - credit, 4),
        "breakeven_high": round(sc + credit, 4),
    }