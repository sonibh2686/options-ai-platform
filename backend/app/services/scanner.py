from typing import List, Dict, Optional
import pandas as pd

from app.services.market_data import get_expiries, get_option_chain
from app.services.analyzer import get_market_context, analyze_contract_row
from app.services.strategy_engine import choose_strategy_with_legs
from app.services.market_data import get_option_chain


def classify_expiries(expiries: List[str]) -> Dict[str, Optional[str]]:
    """
    best call today  -> nearest expiry
    best put today   -> nearest expiry
    best weekly      -> first expiry at least 5 and up to 14 calendar days away
    best swing       -> first expiry at least 21 and up to 60 calendar days away
    """
    import datetime as dt

    today = dt.date.today()
    parsed = []
    for e in expiries:
        try:
            d = dt.datetime.strptime(e, "%Y-%m-%d").date()
            parsed.append((e, (d - today).days))
        except Exception:
            continue

    parsed = [x for x in parsed if x[1] >= 0]
    parsed.sort(key=lambda x: x[1])

    nearest = parsed[0][0] if parsed else None

    weekly = None
    for e, days in parsed:
        if 5 <= days <= 14:
            weekly = e
            break
    if weekly is None and len(parsed) >= 2:
        weekly = parsed[min(1, len(parsed) - 1)][0]

    swing = None
    for e, days in parsed:
        if 21 <= days <= 60:
            swing = e
            break
    if swing is None and parsed:
        swing = parsed[min(len(parsed) - 1, 2)][0]

    return {
        "today": nearest,
        "weekly": weekly,
        "swing": swing,
    }

def scan_best_today_trades(
    ticker: str,
    strike_window: int = 10,
    min_open_interest: int = 50,
    min_volume: int = 1,
    action: str = "buy",
):
    expiries = get_expiries(ticker)
    if not expiries:
        raise ValueError(f"No expiries found for {ticker}")

    expiry_buckets = classify_expiries(expiries)
    nearest_expiry = expiry_buckets["today"]
    if not nearest_expiry:
        raise ValueError(f"No same/nearest expiry found for {ticker}")

    hist, spot, stock_score, stock_bias, news_score, headlines = get_market_context(ticker)

    best_call = None
    call_candidates = []
    best_put = None
    put_candidates = []

    best_call, call_candidates = best_from_chain(
        ticker=ticker,
        expiry=nearest_expiry,
        option_type="call",
        action=action,
        spot=spot,
        hist=hist,
        stock_score=stock_score,
        stock_bias=stock_bias,
        news_score=news_score,
        strike_window=strike_window,
        min_oi=min_open_interest,
        min_vol=min_volume,
    )

    best_put, put_candidates = best_from_chain(
        ticker=ticker,
        expiry=nearest_expiry,
        option_type="put",
        action=action,
        spot=spot,
        hist=hist,
        stock_score=stock_score,
        stock_bias=stock_bias,
        news_score=news_score,
        strike_window=strike_window,
        min_oi=min_open_interest,
        min_vol=min_volume,
    )

    ranked_today = []
    if call_candidates:
        ranked_today.extend([{**x, "category": "today_call_pool"} for x in call_candidates])
    if put_candidates:
        ranked_today.extend([{**x, "category": "today_put_pool"} for x in put_candidates])

    ranked_today.sort(key=lambda x: x["total_score"], reverse=True)

    if best_call:
        best_call["category"] = "best_call_today"
    if best_put:
        best_put["category"] = "best_put_today"

    # ===== ADD STRATEGY BLOCK HERE =====
    calls_df, puts_df = get_option_chain(ticker, nearest_expiry)

    strategy = choose_strategy_with_legs(
        stock_bias=stock_bias,
        stock_score=stock_score,
        news_score=news_score,
        expiry=nearest_expiry,
        calls_df=calls_df,
        puts_df=puts_df,
        call_best=best_call,
        put_best=best_put,
        weekly_best=None,
        swing_best=None,
        spot=spot,
    )
    # ===== END STRATEGY BLOCK =====

    return {
        "ticker": ticker,
        "expiry": nearest_expiry,
        "underlying_price": round(spot, 2),
        "stock_score": round(stock_score, 2),
        "stock_bias": stock_bias,
        "news_score": round(news_score, 2),
        "headlines": headlines,
        "best_call_today": best_call,
        "best_put_today": best_put,
        "ranked_today": ranked_today,
        "strategy_recommendation": strategy,
    }
    
def filter_nearby_strikes(chain: pd.DataFrame, spot: float, strike_window: int, min_oi: int, min_vol: int) -> pd.DataFrame:
    chain = chain.copy()
    chain["strike_dist"] = (chain["strike"] - spot).abs()
    chain = chain.sort_values("strike_dist").head(strike_window * 3)

    filtered = chain[
        (chain["openInterest"].fillna(0) >= min_oi) &
        (chain["volume"].fillna(0) >= min_vol)
    ]

    if filtered.empty:
        return chain.head(strike_window)
    return filtered.head(strike_window)


def best_from_chain(
    ticker: str,
    expiry: str,
    option_type: str,
    action: str,
    spot: float,
    hist,
    stock_score: float,
    stock_bias: str,
    news_score: float,
    strike_window: int,
    min_oi: int,
    min_vol: int,
):
    calls, puts = get_option_chain(ticker, expiry)
    chain = calls if option_type == "call" else puts
    if chain.empty:
        return None, []

    chain = filter_nearby_strikes(chain, spot, strike_window, min_oi, min_vol)
    candidates = []

    for _, row in chain.iterrows():
        try:
            item = analyze_contract_row(
                    ticker=ticker,
                        expiry=expiry,
                        option_type=option_type,
                        action=action,
                        row=row,
                        underlying_price=spot,
                        hist=hist,
                        stock_score=stock_score,
                        stock_bias=stock_bias,
                        news_score=news_score,
                        calls_df=calls,
                        puts_df=puts,
            )
            candidates.append(item)
        except Exception:
            continue

    candidates.sort(key=lambda x: x["total_score"], reverse=True)
    return (candidates[0] if candidates else None), candidates


def scan_global_ranked_trades(
    ticker: str,
    strike_window: int = 10,
    min_open_interest: int = 50,
    min_volume: int = 1,
    include_calls: bool = True,
    include_puts: bool = True,
    action: str = "buy",
):
    expiries = get_expiries(ticker)
    if not expiries:
        raise ValueError(f"No expiries found for {ticker}")

    expiry_buckets = classify_expiries(expiries)
    hist, spot, stock_score, stock_bias, news_score, headlines = get_market_context(ticker)

    categories = {
        "best_call_today": None,
        "best_put_today": None,
        "best_weekly": None,
        "best_swing_option": None,
    }

    ranked_list = []

    nearest_expiry = expiry_buckets["today"]
    weekly_expiry = expiry_buckets["weekly"]
    swing_expiry = expiry_buckets["swing"]

    if include_calls and nearest_expiry:
        best, all_items = best_from_chain(
            ticker=ticker,
            expiry=nearest_expiry,
            option_type="call",
            action=action,
            spot=spot,
            hist=hist,
            stock_score=stock_score,
            stock_bias=stock_bias,
            news_score=news_score,
            strike_window=strike_window,
            min_oi=min_open_interest,
            min_vol=min_volume,
        )
        if best:
            best["category"] = "best_call_today"
            categories["best_call_today"] = best
        ranked_list.extend([{**x, "category": "best_call_today_pool"} for x in all_items])

    if include_puts and nearest_expiry:
        best, all_items = best_from_chain(
            ticker=ticker,
            expiry=nearest_expiry,
            option_type="put",
            action=action,
            spot=spot,
            hist=hist,
            stock_score=stock_score,
            stock_bias=stock_bias,
            news_score=news_score,
            strike_window=strike_window,
            min_oi=min_open_interest,
            min_vol=min_volume,
        )
        if best:
            best["category"] = "best_put_today"
            categories["best_put_today"] = best
        ranked_list.extend([{**x, "category": "best_put_today_pool"} for x in all_items])

    weekly_candidates = []
    if weekly_expiry:
        if include_calls:
            _, items = best_from_chain(
                ticker=ticker,
                expiry=weekly_expiry,
                option_type="call",
                action=action,
                spot=spot,
                hist=hist,
                stock_score=stock_score,
                stock_bias=stock_bias,
                news_score=news_score,
                strike_window=strike_window,
                min_oi=min_open_interest,
                min_vol=min_volume,
            )
            weekly_candidates.extend(items)

        if include_puts:
            _, items = best_from_chain(
                ticker=ticker,
                expiry=weekly_expiry,
                option_type="put",
                action=action,
                spot=spot,
                hist=hist,
                stock_score=stock_score,
                stock_bias=stock_bias,
                news_score=news_score,
                strike_window=strike_window,
                min_oi=min_open_interest,
                min_vol=min_volume,
            )
            weekly_candidates.extend(items)

    weekly_candidates.sort(key=lambda x: x["total_score"], reverse=True)
    if weekly_candidates:
        categories["best_weekly"] = {**weekly_candidates[0], "category": "best_weekly"}
    ranked_list.extend([{**x, "category": "best_weekly_pool"} for x in weekly_candidates])

    swing_candidates = []
    if swing_expiry:
        if include_calls:
            _, items = best_from_chain(
                ticker=ticker,
                expiry=swing_expiry,
                option_type="call",
                action=action,
                spot=spot,
                hist=hist,
                stock_score=stock_score,
                stock_bias=stock_bias,
                news_score=news_score,
                strike_window=strike_window,
                min_oi=min_open_interest,
                min_vol=min_volume,
            )
            swing_candidates.extend(items)

        if include_puts:
            _, items = best_from_chain(
                ticker=ticker,
                expiry=swing_expiry,
                option_type="put",
                action=action,
                spot=spot,
                hist=hist,
                stock_score=stock_score,
                stock_bias=stock_bias,
                news_score=news_score,
                strike_window=strike_window,
                min_oi=min_open_interest,
                min_vol=min_volume,
            )
            swing_candidates.extend(items)

    swing_candidates.sort(key=lambda x: x["total_score"], reverse=True)
    if swing_candidates:
        categories["best_swing_option"] = {**swing_candidates[0], "category": "best_swing_option"}
    ranked_list.extend([{**x, "category": "best_swing_pool"} for x in swing_candidates])

    ranked_list.sort(key=lambda x: x["total_score"], reverse=True)

    strategy_expiry = categories["best_swing_option"]["expiry"] if categories.get("best_swing_option") else (
        categories["best_weekly"]["expiry"] if categories.get("best_weekly") else nearest_expiry
    )

    if not strategy_expiry:
        strategy_expiry = nearest_expiry

    strategy_calls, strategy_puts = get_option_chain(ticker, strategy_expiry)

    strategy = choose_strategy_with_legs(
        stock_bias=stock_bias,
        stock_score=stock_score,
        news_score=news_score,
        expiry=strategy_expiry,
        calls_df=strategy_calls,
        puts_df=strategy_puts,
        call_best=categories.get("best_call_today"),
        put_best=categories.get("best_put_today"),
        weekly_best=categories.get("best_weekly"),
        swing_best=categories.get("best_swing_option"),
        spot=spot,
    )
    
    return {
        "ticker": ticker,
        "underlying_price": round(spot, 2),
        "stock_score": round(stock_score, 2),
        "stock_bias": stock_bias,
        "news_score": round(news_score, 2),
        "headlines": headlines,
        "categories": categories,
        "ranked_list": ranked_list[:50],
        "strategy_recommendation": strategy,
    }