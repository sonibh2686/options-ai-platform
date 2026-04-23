import math


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str):
    sigma = max(float(sigma), 1e-6)
    T = max(float(T), 1e-6)
    S = max(float(S), 1e-6)
    K = max(float(K), 1e-6)

    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = (S * norm_pdf(d1) * math.sqrt(T)) / 100.0

    if option_type == "call":
        delta = norm_cdf(d1)
        theta = (
            -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * norm_cdf(d2)
        ) / 365.0
    else:
        delta = norm_cdf(d1) - 1.0
        theta = (
            -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * norm_cdf(-d2)
        ) / 365.0

    return float(delta), float(gamma), float(theta), float(vega)