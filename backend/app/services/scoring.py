def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))


def score_liquidity(bid: float, ask: float, volume: float, oi: float, mid: float) -> float:
    score = 50.0
    spread = max(ask - bid, 0.0)
    spread_pct = spread / max(mid, 0.01)

    if spread_pct < 0.05:
        score += 25
    elif spread_pct < 0.10:
        score += 15
    elif spread_pct < 0.20:
        score += 5
    else:
        score -= 20

    if volume >= 1000:
        score += 12
    elif volume >= 250:
        score += 8
    elif volume >= 50:
        score += 4
    else:
        score -= 8

    if oi >= 3000:
        score += 13
    elif oi >= 1000:
        score += 8
    elif oi >= 100:
        score += 3
    else:
        score -= 10

    return clamp(score, 0, 100)


def score_greeks_for_buy(delta: float, gamma: float, theta: float, vega: float, T: float) -> float:
    score = 50.0
    abs_delta = abs(delta)

    if 0.35 <= abs_delta <= 0.65:
        score += 18
    elif 0.20 <= abs_delta < 0.35 or 0.65 < abs_delta <= 0.80:
        score += 8
    else:
        score -= 8

    if gamma >= 0.03:
        score += 12
    elif gamma >= 0.015:
        score += 7
    else:
        score -= 4

    if theta >= -0.10:
        score += 10
    elif theta >= -0.30:
        score += 3
    elif theta < -0.75:
        score -= 15
    else:
        score -= 6

    if 0.02 <= vega <= 0.20:
        score += 8
    elif vega < 0.01:
        score -= 3
    else:
        score += 3

    if T < 2 / 365:
        score -= 10
    elif T < 7 / 365:
        score -= 4
    else:
        score += 3

    return clamp(score, 0, 100)


def score_iv_for_buy(iv_rank_proxy: float) -> float:
    if iv_rank_proxy <= 20:
        return 90
    if iv_rank_proxy <= 35:
        return 78
    if iv_rank_proxy <= 50:
        return 65
    if iv_rank_proxy <= 70:
        return 45
    return 25


def score_iv_for_sell(iv_rank_proxy: float) -> float:
    if iv_rank_proxy >= 80:
        return 90
    if iv_rank_proxy >= 65:
        return 78
    if iv_rank_proxy >= 50:
        return 65
    if iv_rank_proxy >= 35:
        return 45
    return 25


def score_pop(pop: float) -> float:
    return clamp(pop * 100.0, 0, 100)


def recommend(score: float) -> str:
    if score >= 78:
        return "STRONG BUY"
    if score >= 65:
        return "BUY"
    if score >= 50:
        return "NEUTRAL"
    return "AVOID"

def score_open_interest(oi: float, volume: float, spread_pct: float) -> float:
    score = 50.0

    if oi >= 5000:
        score += 25
    elif oi >= 2000:
        score += 18
    elif oi >= 500:
        score += 10
    elif oi >= 100:
        score += 4
    else:
        score -= 20

    if volume >= 1000:
        score += 10
    elif volume >= 250:
        score += 6
    elif volume < 10:
        score -= 8

    if spread_pct < 0.05:
        score += 10
    elif spread_pct > 0.20:
        score -= 10

    return clamp(score, 0, 100)

def finalize_score(
    stock_score: float,
    news_score: float,
    liquidity_score: float,
    greeks_score: float,
    iv_score: float,
    pop_score: float,
    direction_bonus: float = 0.0,
) -> float:
    total = (
        stock_score * 0.25 +
        news_score * 0.15 +
        liquidity_score * 0.20 +
        greeks_score * 0.20 +
        iv_score * 0.10 +
        pop_score * 0.10 +
        direction_bonus
    )
    return clamp(total, 0, 100)