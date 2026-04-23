import yfinance as yf
import pandas as pd


def get_ticker(ticker: str):
    return yf.Ticker(ticker)


def get_stock_price(ticker: str) -> float:
    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d", auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No price data for {ticker}")
    return float(hist["Close"].iloc[-1])


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    hist = tk.history(period=period, auto_adjust=True)
    return hist.copy()


def get_expiries(ticker: str):
    return list(yf.Ticker(ticker).options)


def get_option_chain(ticker: str, expiry: str):
    tk = yf.Ticker(ticker)
    chain = tk.option_chain(expiry)
    return chain.calls.copy(), chain.puts.copy()