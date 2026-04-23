import json
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.schemas import AnalyzeRequest, GlobalScanRequest
from app.services.market_data import get_expiries
from app.services.analyzer import get_market_context, analyze_contract_row
from app.services.scanner import scan_global_ranked_trades
from app.services.market_data import get_option_chain
from app.db.database import SessionLocal
from app.db.models import ScanHistory

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/ticker/{ticker}/expiries")
def ticker_expiries(ticker: str):
    try:
        expiries = get_expiries(ticker.upper())
        return {"ticker": ticker.upper(), "expiries": expiries}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        hist, spot, stock_score, stock_bias, news_score, _ = get_market_context(req.ticker.upper())

        calls, puts = get_option_chain(req.ticker.upper(), req.expiry)
        chain = calls if req.option_type == "call" else puts

        row = chain.iloc[(chain["strike"] - req.strike).abs().argsort()[:1]].iloc[0]

        result = analyze_contract_row(
            ticker=req.ticker.upper(),
            expiry=req.expiry,
            option_type=req.option_type,
            action=req.action,
            row=row,
            underlying_price=spot,
            hist=hist,
            stock_score=stock_score,
            stock_bias=stock_bias,
            news_score=news_score,
            calls_df=calls,
            puts_df=puts,
        )

        result["category"] = "manual_analysis"
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan/global")
def scan_global(req: GlobalScanRequest):
    try:
        result = scan_global_ranked_trades(
            ticker=req.ticker.upper(),
            strike_window=req.strike_window,
            min_open_interest=req.min_open_interest,
            min_volume=req.min_volume,
            include_calls=req.include_calls,
            include_puts=req.include_puts,
            action=req.action,
        )

        db: Session = SessionLocal()
        try:
            for item in result["ranked_list"][:10]:
                db.add(
                    ScanHistory(
                        ticker=req.ticker.upper(),
                        mode=item["category"],
                        option_type=item["option_type"],
                        action=item["action"],
                        expiry=item["expiry"],
                        score=item["total_score"],
                        recommendation=item["recommendation"],
                        payload=json.dumps(item),
                    )
                )
            db.commit()
        finally:
            db.close()

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{ticker}")
def history(ticker: str):
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(ScanHistory)
            .filter(ScanHistory.ticker == ticker.upper())
            .order_by(ScanHistory.created_at.desc())
            .limit(50)
            .all()
        )
        return {
            "ticker": ticker.upper(),
            "items": [
                {
                    "id": r.id,
                    "mode": r.mode,
                    "option_type": r.option_type,
                    "action": r.action,
                    "expiry": r.expiry,
                    "score": r.score,
                    "recommendation": r.recommendation,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
        }
    finally:
        db.close()