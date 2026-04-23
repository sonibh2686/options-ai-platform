import math
import datetime as dt
from typing import Tuple
import numpy as np
import pandas as pd
import requests
from xml.etree import ElementTree as ET

from app.services.market_data import get_stock_price, get_option_chain, get_price_history
from app.utils.greeks import greeks, norm_cdf
from app.services.scoring import (
    score_liquidity,
    score_greeks_for_buy,
    score_iv_for_buy,
    score_iv_for_sell,
    score_pop,
    finalize_score,
    recommend,
    score_open_interest,
)

RISK_FREE_RATE = 0.045

POSITIVE_WORDS = {
    "beat", "beats", "growth", "surge", "bullish", "record", "strong", "upside",
    "upgrade", "outperform", "optimistic", "profit", "profits", "expands",
    "partnership", "win", "wins", "approval", "improves", "improved", "accelerate",
    "positive", "momentum", "rebound", "demand", "innovative"
}

NEGATIVE_WORDS = {
    "miss", "misses", "drop", "plunge", "bearish", "downgrade", "lawsuit", "probe",
    "weak", "decline", "cuts", "cut", "warning", "warns", "risk", "slump", "fall",
    "negative", "recall", "delays", "delay", "investigation", "pressure", "loss",
    "losses", "soft", "uncertain"
}


def safe_float(x, default=0.0):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default


def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = pd.Series(np.where(delta > 0, delta, 0.0), index=series.index).rolling(period).mean()
    loss = pd.Series(np.where(delta < 0, -delta, 0.0), index=series.index).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def stock_strength_score(hist: pd.DataFrame):
    if hist.empty:
        return 50.0, "neutral"

    close = hist["Close"].dropna()
    volume = hist["Volume"].dropna() if "Volume" in hist.columns else pd.Series(dtype=float)

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    rsi = compute_rsi(close, 14)
    macd, signal = compute_macd(close)

    latest_close = safe_float(close.iloc[-1])
    latest_sma20 = safe_float(sma20.iloc[-1], latest_close)
    latest_sma50 = safe_float(sma50.iloc[-1], latest_close)
    latest_sma200 = safe_float(sma200.iloc[-1], latest_close)
    latest_rsi = safe_float(rsi.iloc[-1], 50.0)
    latest_macd = safe_float(macd.iloc[-1], 0.0)
    latest_signal = safe_float(signal.iloc[-1], 0.0)

    ret20 = latest_close / safe_float(close.iloc[-21], latest_close) - 1 if len(close) > 21 else 0.0
    ret60 = latest_close / safe_float(close.iloc[-61], latest_close) - 1 if len(close) > 61 else 0.0

    rel_vol = 1.0
    if len(volume) > 20:
        rel_vol = safe_float(volume.iloc[-1]) / max(safe_float(volume.rolling(20).mean().iloc[-1], 1.0), 1.0)

    score = 50.0
    score += 7 if latest_close > latest_sma20 else -7
    score += 8 if latest_close > latest_sma50 else -8
    score += 10 if latest_close > latest_sma200 else -10
    score += clamp(ret20 * 100, -10, 10)
    score += clamp(ret60 * 80, -10, 10)

    if 52 <= latest_rsi <= 68:
        score += 8
    elif latest_rsi > 75:
        score -= 5
    elif latest_rsi < 35:
        score -= 4

    score += 8 if latest_macd > latest_signal else -8
    score += 4 if rel_vol > 1.2 else (-3 if rel_vol < 0.8 else 0)

    score = clamp(score, 0, 100)
    bias = "bullish" if score >= 60 else "bearish" if score <= 40 else "neutral"
    return score, bias


def sentiment_score_text(text: str) -> float:
    import re
    words = re.findall(r"[A-Za-z']+", text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    return clamp(50 + (pos - neg) * 7, 0, 100)

def build_nearby_oi_levels(calls: pd.DataFrame, puts: pd.DataFrame, selected_strike: float, window: int = 5):
    calls_map = {}
    puts_map = {}

    for _, row in calls.iterrows():
        strike = safe_float(row.get("strike"))
        calls_map[strike] = {
            "call_oi": int(safe_float(row.get("openInterest", 0))),
            "call_volume": int(safe_float(row.get("volume", 0))),
        }

    for _, row in puts.iterrows():
        strike = safe_float(row.get("strike"))
        puts_map[strike] = {
            "put_oi": int(safe_float(row.get("openInterest", 0))),
            "put_volume": int(safe_float(row.get("volume", 0))),
        }

    all_strikes = sorted(set(list(calls_map.keys()) + list(puts_map.keys())))
    if not all_strikes:
        return []

    nearest_idx = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - selected_strike))
    start = max(0, nearest_idx - window)
    end = min(len(all_strikes), nearest_idx + window + 1)

    result = []
    for strike in all_strikes[start:end]:
        c = calls_map.get(strike, {"call_oi": 0, "call_volume": 0})
        p = puts_map.get(strike, {"put_oi": 0, "put_volume": 0})
        result.append({
            "strike": strike,
            "call_oi": c["call_oi"],
            "put_oi": p["put_oi"],
            "call_volume": c["call_volume"],
            "put_volume": p["put_volume"],
        })

    return result

def fetch_news_score(ticker: str):
    query = f"{ticker} stock"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:10]
        titles = [item.findtext("title", default="") for item in items]
        if not titles:
            return 50.0, []
        scores = [sentiment_score_text(t) for t in titles]
        return float(np.mean(scores)), titles[:5]
    except Exception:
        return 50.0, []


def realized_volatility_proxy(hist: pd.DataFrame):
    if hist.empty or len(hist) < 30:
        return {"hv20": 0.25, "hv60": 0.25, "hv252": 0.25}

    close = hist["Close"].dropna()
    log_ret = np.log(close / close.shift(1)).dropna()

    hv20 = log_ret.rolling(20).std().iloc[-1] * np.sqrt(252) if len(log_ret) >= 20 else 0.25
    hv60 = log_ret.rolling(60).std().iloc[-1] * np.sqrt(252) if len(log_ret) >= 60 else 0.25
    hv252 = log_ret.rolling(252).std().iloc[-1] * np.sqrt(252) if len(log_ret) >= 252 else 0.25

    return {
        "hv20": safe_float(hv20, 0.25),
        "hv60": safe_float(hv60, 0.25),
        "hv252": safe_float(hv252, 0.25),
    }


def iv_rank_proxy(contract_iv: float, hist: pd.DataFrame) -> float:
    vols = realized_volatility_proxy(hist)
    low = min(vols["hv20"], vols["hv60"], vols["hv252"])
    high = max(vols["hv20"], vols["hv60"], vols["hv252"], low + 1e-6)
    ivr = 100.0 * (contract_iv - low) / max(high - low, 1e-6)
    return clamp(ivr, 0.0, 100.0)


def probability_of_profit_long(S: float, K: float, premium: float, T: float, r: float, sigma: float, option_type: str):
    sigma = max(sigma, 1e-6)
    T = max(T, 1e-6)
    premium = max(premium, 0.01)

    if option_type == "call":
        breakeven = K + premium
        d2 = (math.log(S / breakeven) + (r - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        return clamp(norm_cdf(d2), 0.0, 1.0)
    else:
        breakeven = max(K - premium, 0.01)
        d2 = (math.log(S / breakeven) + (r - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        return clamp(norm_cdf(-d2), 0.0, 1.0)


def year_fraction_to_expiry(expiry: str) -> float:
    expiry_date = dt.datetime.strptime(expiry, "%Y-%m-%d").date()
    expiry_dt = dt.datetime.combine(expiry_date, dt.time(16, 0))
    now = dt.datetime.now()
    seconds = max((expiry_dt - now).total_seconds(), 60.0)
    return seconds / (365.0 * 24 * 60 * 60)


def build_reasons(option_type: str, stock_bias: str, iv_score: float, liquidity_score: float, greeks_score: float, pop: float):
    reasons = []
    warnings = []

    if option_type == "call" and stock_bias == "bullish":
        reasons.append("Bullish stock trend supports call exposure.")
    if option_type == "put" and stock_bias == "bearish":
        reasons.append("Bearish stock trend supports put exposure.")
    if liquidity_score >= 70:
        reasons.append("Good liquidity and manageable spread.")
    if greeks_score >= 70:
        reasons.append("Greeks profile is favorable.")
    if iv_score >= 70:
        reasons.append("Implied volatility setup is attractive.")
    if pop >= 0.50:
        reasons.append("Probability of profit is acceptable.")

    if liquidity_score < 45:
        warnings.append("Low liquidity may cause slippage.")
    if pop < 0.35:
        warnings.append("Low probability of profit.")
    if greeks_score < 45:
        warnings.append("Greeks profile is weak.")
    if stock_bias == "neutral":
        warnings.append("Underlying trend is not strongly directional.")

    return reasons, warnings


def analyze_contract_row(
    ticker: str,
    expiry: str,
    option_type: str,
    action: str,
    row: pd.Series,
    underlying_price: float,
    hist: pd.DataFrame,
    stock_score: float,
    stock_bias: str,
    news_score: float,
    calls_df: pd.DataFrame | None = None,
    puts_df: pd.DataFrame | None = None,
):
    strike = safe_float(row["strike"])
    bid = safe_float(row.get("bid", 0.0))
    ask = safe_float(row.get("ask", 0.0))
    last_price = safe_float(row.get("lastPrice", 0.0))
    mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else max(last_price, 0.01)
    volume = int(safe_float(row.get("volume", 0.0)))
    oi = int(safe_float(row.get("openInterest", 0.0)))
    iv = safe_float(row.get("impliedVolatility", 0.0))
    if iv > 3.0:
        iv /= 100.0

    T = year_fraction_to_expiry(expiry)
    delta, gamma, theta, vega = greeks(underlying_price, strike, T, RISK_FREE_RATE, iv, option_type)
    pop = probability_of_profit_long(underlying_price, strike, mid_price, T, RISK_FREE_RATE, iv, option_type)
    ivr = iv_rank_proxy(iv, hist)

    spread = max(ask - bid, 0.0)
    spread_pct = spread / max(mid_price, 0.01)

    liquidity_score = score_liquidity(bid, ask, volume, oi, mid_price)
    greeks_score = score_greeks_for_buy(delta, gamma, theta, vega, T)
    iv_score = score_iv_for_buy(ivr) if action == "buy" else score_iv_for_sell(ivr)
    pop_score = score_pop(pop)
    oi_score = score_open_interest(oi, volume, spread_pct)

    direction_bonus = 0.0
    if option_type == "call":
        direction_bonus += 8 if stock_bias == "bullish" else (-10 if stock_bias == "bearish" else 0)
    else:
        direction_bonus += 8 if stock_bias == "bearish" else (-10 if stock_bias == "bullish" else 0)

    total_score = (
        stock_score * 0.22 +
        news_score * 0.12 +
        liquidity_score * 0.16 +
        greeks_score * 0.16 +
        iv_score * 0.10 +
        pop_score * 0.10 +
        oi_score * 0.14 +
        direction_bonus
    )
    total_score = clamp(total_score, 0, 100)

    reasons, warnings = build_reasons(option_type, stock_bias, iv_score, liquidity_score, greeks_score, pop)

    if oi_score >= 75:
        reasons.append("Open interest is strong for this strike.")
    elif oi_score < 45:
        warnings.append("Open interest is weak at this strike.")

    nearby_oi_levels = []
    if calls_df is not None and puts_df is not None:
        nearby_oi_levels = build_nearby_oi_levels(calls_df, puts_df, strike, window=5)

    return {
        "ticker": ticker,
        "expiry": expiry,
        "strike": strike,
        "option_type": option_type,
        "action": action,
        "underlying_price": round(underlying_price, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "last_price": round(last_price, 2),
        "mid_price": round(mid_price, 2),
        "volume": volume,
        "open_interest": oi,
        "selected_strike_oi": oi,
        "implied_volatility": round(iv, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "pop": round(pop, 4),
        "stock_score": round(stock_score, 2),
        "news_score": round(news_score, 2),
        "liquidity_score": round(liquidity_score, 2),
        "greeks_score": round(greeks_score, 2),
        "iv_score": round(iv_score, 2),
        "pop_score": round(pop_score, 2),
        "oi_score": round(oi_score, 2),
        "total_score": round(total_score, 2),
        "recommendation": recommend(total_score),
        "reasons": reasons,
        "warnings": warnings,
        "nearby_oi_levels": nearby_oi_levels,
    }


def get_market_context(ticker: str):
    hist = get_price_history(ticker, period="1y")
    underlying = get_stock_price(ticker)
    stock_score, stock_bias = stock_strength_score(hist)
    news_score, headlines = fetch_news_score(ticker)
    return hist, underlying, stock_score, stock_bias, news_score, headlines