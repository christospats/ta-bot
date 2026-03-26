"""
Market data via yfinance (global coverage).
Portfolio via Alpaca (paper trading account).
"""
from __future__ import annotations

from datetime import datetime
import yfinance as yf
from rich.console import Console

import config

console = Console()

# ── Symbol normalizer ────────────────────────────────────
_CRYPTO = {"BTC","ETH","SOL","ADA","XRP","DOGE","BNB","AVAX","DOT","MATIC","LTC","LINK"}

def _normalize(symbol: str) -> str:
    """Auto-append -USD for known crypto tickers."""
    s = symbol.upper()
    if s in _CRYPTO:
        return s + "-USD"
    return s

# ── Period map yfinance ──────────────────────────────────
_PERIOD_MAP = {
    "1D": ("1d",  "5m"),
    "1W": ("5d",  "30m"),
    "1M": ("3mo", "1d"),   # 3mo → ~65 bars, αρκετό για RSI/MACD/BB
    "3M": ("6mo", "1d"),
    "1Y": ("1y",  "1d"),
}


# ── Quote ────────────────────────────────────────────────
def get_quote(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(_normalize(symbol))
        info   = ticker.fast_info

        price   = getattr(info, "last_price",       None)
        prev    = getattr(info, "previous_close",   None)
        high    = getattr(info, "day_high",         None)
        low     = getattr(info, "day_low",          None)
        volume  = getattr(info, "last_volume",      None)
        mktcap  = getattr(info, "market_cap",       None)

        if price is None:
            console.print(f"[red]No data found for symbol: {symbol}[/red]")
            return None

        change     = price - prev if prev else 0
        change_pct = (change / prev * 100) if prev else 0

        return {
            "symbol"    : _normalize(symbol),
            "price"     : round(float(price), 4),
            "prev_close": round(float(prev),  4) if prev  else None,
            "change"    : round(float(change),     4),
            "change_pct": round(float(change_pct), 2),
            "day_high"  : round(float(high),   4) if high   else None,
            "day_low"   : round(float(low),    4) if low    else None,
            "volume"    : int(volume)  if volume  else None,
            "market_cap": int(mktcap)  if mktcap  else None,
            "time"      : datetime.now().strftime("%Y-%m-%d %H:%M:%S local (15-20min delay)"),
        }
    except Exception as e:
        console.print(f"[red]Quote error for {symbol}: {e}[/red]")
        return None


# ── Historical bars ──────────────────────────────────────
def get_bars(symbol: str, period: str = "1M") -> list[dict] | None:
    yf_period, yf_interval = _PERIOD_MAP.get(period.upper(), ("1mo", "1d"))
    try:
        ticker = yf.Ticker(_normalize(symbol))
        df     = ticker.history(period=yf_period, interval=yf_interval)

        if df.empty:
            console.print(f"[red]No bar data for {symbol}[/red]")
            return None

        return [
            {
                "time"  : str(idx)[:16],
                "open"  : round(float(row["Open"]),   4),
                "high"  : round(float(row["High"]),   4),
                "low"   : round(float(row["Low"]),    4),
                "close" : round(float(row["Close"]),  4),
                "volume": int(row["Volume"]),
            }
            for idx, row in df.iterrows()
        ]
    except Exception as e:
        console.print(f"[red]Bars error for {symbol}: {e}[/red]")
        return None


# ── Company info ─────────────────────────────────────────
def get_info(symbol: str) -> dict | None:
    try:
        info = yf.Ticker(_normalize(symbol)).info
        return {
            "name"     : info.get("longName")       or info.get("shortName", symbol),
            "sector"   : info.get("sector",         "—"),
            "industry" : info.get("industry",       "—"),
            "country"  : info.get("country",        "—"),
            "pe_ratio" : info.get("trailingPE"),
            "eps"      : info.get("trailingEps"),
            "52w_high" : info.get("fiftyTwoWeekHigh"),
            "52w_low"  : info.get("fiftyTwoWeekLow"),
            "avg_vol"  : info.get("averageVolume"),
            "website"  : info.get("website",        "—"),
        }
    except Exception as e:
        console.print(f"[yellow]Info error for {symbol}: {e}[/yellow]")
        return None


# ── Portfolio (Alpaca) ───────────────────────────────────
def get_portfolio() -> dict | None:
    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        console.print("[yellow]Alpaca keys not set — portfolio unavailable.[/yellow]")
        return None
    try:
        from alpaca.trading.client import TradingClient
        client    = TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)
        account   = client.get_account()
        positions = client.get_all_positions()
        return {
            "equity"         : float(account.equity),
            "cash"           : float(account.cash),
            "buying_power"   : float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "positions"      : [
                {
                    "symbol"         : p.symbol,
                    "qty"            : float(p.qty),
                    "avg_cost"       : float(p.avg_entry_price),
                    "current"        : float(p.current_price),
                    "market_value"   : float(p.market_value),
                    "unrealized_pl"  : float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc) * 100,
                }
                for p in positions
            ],
        }
    except Exception as e:
        console.print(f"[red]Portfolio error: {e}[/red]")
        return None