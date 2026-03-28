"""
Technical indicators using pandas-ta.
"""
from __future__ import annotations
import pandas as pd
try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False

from rich.console import Console
from rich.table import Table

console = Console()


# How many bars each period actually needs for meaningful indicators
_PERIOD_BARS = {
    "1D": None,    # use all (intraday)
    "1W": None,
    "1M": 65,      # 3mo fetched, use last 65 (~1M of trading days)
    "3M": 130,     # 6mo fetched, use last 130
    "1Y": None,    # use all ~250 bars
}

def compute_indicators(bars: list[dict], period: str = "1M") -> dict | None:
    if not bars or len(bars) < 26:
        console.print("[yellow]Not enough bars for indicator calculation (need 26+).[/yellow]")
        return None

    # Slice to the relevant window for this period
    # (we fetch extra bars so indicators have enough history to warm up)
    limit = _PERIOD_BARS.get(period.upper())
    working_bars = bars[-limit:] if limit and len(bars) > limit else bars

    df = pd.DataFrame(working_bars)
    df.set_index("time", inplace=True)
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})

    result: dict = {}

    if HAS_TA:
        # RSI (14)
        rsi = ta.rsi(df["close"], length=14)
        result["rsi"] = round(float(rsi.iloc[-1]), 2) if rsi is not None else None

        # MACD — detect column names dynamically (varies by pandas_ta version)
        macd = ta.macd(df["close"])
        if macd is not None:
            cols = macd.columns.tolist()
            macd_col   = next((c for c in cols if c.startswith("MACD_")),  None)
            signal_col = next((c for c in cols if c.startswith("MACDs_")), None)
            hist_col   = next((c for c in cols if c.startswith("MACDh_")), None)
            if macd_col:   result["macd"]        = round(float(macd[macd_col].iloc[-1]),   4)
            if signal_col: result["macd_signal"] = round(float(macd[signal_col].iloc[-1]), 4)
            if hist_col:   result["macd_hist"]   = round(float(macd[hist_col].iloc[-1]),   4)

        # Bollinger Bands — detect column names dynamically
        bb = ta.bbands(df["close"], length=20)
        if bb is not None:
            cols = bb.columns.tolist()
            upper_col = next((c for c in cols if c.startswith("BBU_")), None)
            mid_col   = next((c for c in cols if c.startswith("BBM_")), None)
            lower_col = next((c for c in cols if c.startswith("BBL_")), None)
            if upper_col: result["bb_upper"] = round(float(bb[upper_col].iloc[-1]), 4)
            if mid_col:   result["bb_mid"]   = round(float(bb[mid_col].iloc[-1]),   4)
            if lower_col: result["bb_lower"] = round(float(bb[lower_col].iloc[-1]), 4)

        # Moving Averages
        result["sma_20"]  = round(float(ta.sma(df["close"], 20).iloc[-1]),  4)
        result["sma_50"]  = round(float(ta.sma(df["close"], 50).iloc[-1]),  4) if len(df) >= 50  else None
        result["ema_12"]  = round(float(ta.ema(df["close"], 12).iloc[-1]),  4)

    else:
        # Fallback: manual SMA
        result["sma_20"] = round(df["close"].tail(20).mean(), 4)

    result["current_close"] = round(float(df["close"].iloc[-1]), 4)
    result["change_pct"]    = round(
        (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100, 2
    ) if len(df) > 1 else 0.0

    return result


def print_indicators(symbol: str, ind: dict) -> None:
    table = Table(title=f"📊 Technical Indicators — {symbol}", border_style="dim")
    table.add_column("Indicator", style="cyan",  min_width=18)
    table.add_column("Value",     style="white", justify="right")
    table.add_column("Signal",    style="bold",  justify="center")

    def rsi_signal(v):
        if v is None: return "—"
        if v >= 70:   return "[red]Overbought[/red]"
        if v <= 30:   return "[green]Oversold[/green]"
        return "[yellow]Neutral[/yellow]"

    def macd_signal(hist):
        if hist is None: return "—"
        return "[green]Bullish[/green]" if hist > 0 else "[red]Bearish[/red]"

    def bb_signal(close, upper, lower):
        if None in (close, upper, lower): return "—"
        if close >= upper: return "[red]Near Upper[/red]"
        if close <= lower: return "[green]Near Lower[/green]"
        return "[yellow]Mid-Range[/yellow]"

    def ma_signal(close, ma):
        if ma is None: return "—"
        return "[green]Above MA[/green]" if close > ma else "[red]Below MA[/red]"

    c = ind.get("current_close")
    rows = [
        ("Current Close",  f"${c:.4f}"  if c else "—",                        ""),
        ("Change %",       f"{ind.get('change_pct', 0):+.2f}%",               "[green]▲[/green]" if ind.get("change_pct", 0) > 0 else "[red]▼[/red]"),
        ("RSI (14)",       str(ind.get("rsi", "—")),                          rsi_signal(ind.get("rsi"))),
        ("MACD",           str(ind.get("macd", "—")),                         macd_signal(ind.get("macd_hist"))),
        ("MACD Signal",    str(ind.get("macd_signal", "—")),                  ""),
        ("BB Upper",       str(ind.get("bb_upper", "—")),                     bb_signal(c, ind.get("bb_upper"), ind.get("bb_lower"))),
        ("BB Mid",         str(ind.get("bb_mid", "—")),                       ""),
        ("BB Lower",       str(ind.get("bb_lower", "—")),                     ""),
        ("SMA 20",         str(ind.get("sma_20", "—")),                       ma_signal(c, ind.get("sma_20"))),
        ("SMA 50",         str(ind.get("sma_50", "—")),                       ma_signal(c, ind.get("sma_50"))),
        ("EMA 12",         str(ind.get("ema_12", "—")),                       ma_signal(c, ind.get("ema_12"))),
    ]

    for name, val, sig in rows:
        table.add_row(name, val, sig)

    console.print(table)