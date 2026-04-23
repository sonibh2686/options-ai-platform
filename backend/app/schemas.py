from pydantic import BaseModel, Field
from typing import List, Optional, Any


class AnalyzeRequest(BaseModel):
    ticker: str
    strike: float
    expiry: str
    option_type: str
    action: str = "buy"


class GlobalScanRequest(BaseModel):
    ticker: str
    strike_window: int = Field(default=10, ge=4, le=40)
    min_open_interest: int = Field(default=50, ge=0)
    min_volume: int = Field(default=1, ge=0)
    include_calls: bool = True
    include_puts: bool = True
    action: str = "buy"


class SuggestionItem(BaseModel):
    category: str
    ticker: str
    expiry: str
    strike: float
    option_type: str
    action: str
    underlying_price: float
    bid: float
    ask: float
    last_price: float
    mid_price: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    pop: float
    stock_score: float
    news_score: float
    liquidity_score: float
    greeks_score: float
    iv_score: float
    pop_score: float
    total_score: float
    recommendation: str
    reasons: List[str]
    warnings: List[str]


class GlobalScanResponse(BaseModel):
    ticker: str
    underlying_price: float
    stock_score: float
    stock_bias: str
    news_score: float
    headlines: List[str]
    categories: dict[str, Optional[SuggestionItem]]
    ranked_list: List[SuggestionItem]