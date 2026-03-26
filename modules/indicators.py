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


# ---------------------------
# Helpers
# ---------------------------
def safe_last(series):
    if series is None or len(series) == 0:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)


def round_or_none(val, digits=4):
    return round(val, digits) if val is not None else None


# ---------------------------
# MAIN
# ---------------------------
def compute_indicators(bars: list[dict]) -> dict | None:
    if not bars or len(bars) < 30:
        console.print("[yellow]Not enough bars for indicator calculation (need ~30+).[/yellow]")
        return None

    df = pd.DataFrame(bars)

    # Ensure datetime index
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])
    df.set_index("time", inplace=True)
    df.sort_index(inplace=True)

    df = df.astype({
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": float
    })

    close = df["close"]

    result: dict = {}
    score = 0

    # ---------------------------
    # INDICATORS
    # ---------------------------
    if HAS_TA:

        # RSI
        rsi_series = ta.rsi(close, length=14)
        rsi_val = safe_last(rsi_series)
        result["rsi"] = round_or_none(rsi_val, 2)

        # MACD
        macd_df = ta.macd(close)
        macd_val = signal_val = hist_val = None

        if macd_df is not None:
            cols = macd_df.columns.tolist()

            macd_col   = next((c for c in cols if c.startswith("MACD_")), None)
            signal_col = next((c for c in cols if c.startswith("MACDs_")), None)
            hist_col   = next((c for c in cols if c.startswith("MACDh_")), None)

            macd_val   = safe_last(macd_df[macd_col]) if macd_col else None
            signal_val = safe_last(macd_df[signal_col]) if signal_col else None
            hist_val   = safe_last(macd_df[hist_col]) if hist_col else None

            result["macd"]        = round_or_none(macd_val, 4)
            result["macd_signal"] = round_or_none(signal_val, 4)
            result["macd_hist"]   = round_or_none(hist_val, 4)

        # Bollinger Bands
        bb = ta.bbands(close, length=20)
        if bb is not None:
            cols = bb.columns.tolist()

            upper_col = next((c for c in cols if c.startswith("BBU_")), None)
            mid_col   = next((c for c in cols if c.startswith("BBM_")), None)
            lower_col = next((c for c in cols if c.startswith("BBL_")), None)

            result["bb_upper"] = round_or_none(safe_last(bb[upper_col]), 4) if upper_col else None
            result["bb_mid"]   = round_or_none(safe_last(bb[mid_col]),   4) if mid_col else None
            result["bb_lower"] = round_or_none(safe_last(bb[lower_col]), 4) if lower_col else None

        # Moving averages (cached)
        sma20 = ta.sma(close, 20)
        sma50 = ta.sma(close, 50)
        ema12 = ta.ema(close, 12)

        result["sma_20"] = round_or_none(safe_last(sma20), 4)
        result["sma_50"] = round_or_none(safe_last(sma50), 4) if len(df) >= 50 else None
        result["ema_12"] = round_or_none(safe_last(ema12), 4)

    else:
        result["sma_20"] = round(close.tail(20).mean(), 4)

    # ---------------------------
    # PRICE INFO
    # ---------------------------
    current = close.iloc[-1]
    prev = close.iloc[-2] if len(close) > 1 else None

    result["current_close"] = round(float(current), 4)

    if prev and prev != 0:
        result["change_pct"] = round((current - prev) / prev * 100, 2)
    else:
        result["change_pct"] = 0.0

    # ---------------------------
    # SIGNALS (NEW)
    # ---------------------------

    # RSI signal
    if rsi_val is not None:
        if rsi_val <= 30:
            result["signal_rsi"] = "BUY"
            score += 2
        elif rsi_val >= 70:
            result["signal_rsi"] = "SELL"
            score -= 2
        else:
            result["signal_rsi"] = "NEUTRAL"
    else:
        result["signal_rsi"] = None

    # MACD signal (proper logic)
    if macd_val is not None and signal_val is not None:
        if macd_val > signal_val:
            result["signal_macd"] = "BUY"
            score += 2
        elif macd_val < signal_val:
            result["signal_macd"] = "SELL"
            score -= 2
        else:
            result["signal_macd"] = "NEUTRAL"
    else:
        result["signal_macd"] = None

    if result.get("sma_20") is not None:
        score += 1 if current > result["sma_20"] else -1

    if result.get("sma_50") is not None:
        score += 1 if current > result["sma_50"] else -1

    if result.get("ema_12") is not None:
        score += 1 if current > result["ema_12"] else -1

    # COMBINED strategy (RSI + MACD)
    # if result["signal_rsi"] == "BUY" and result["signal_macd"] == "BUY":
    #     result["signal_combo"] = "STRONG BUY"
    # elif result["signal_rsi"] == "SELL" and result["signal_macd"] == "SELL":
    #     result["signal_combo"] = "STRONG SELL"
    # else:
    #     result["signal_combo"] = "NEUTRAL"

    if score >= 3:
        result["signal_combo"] = "BUY"
    elif score <= -3:
        result["signal_combo"] = "SELL"
    else:
        result["signal_combo"] = "NEUTRAL"
    result["score"] = score

    return result


# ---------------------------
# PRINT
# ---------------------------
def print_indicators(symbol: str, ind: dict) -> None:
    table = Table(title=f"📊 Technical Indicators — {symbol}", border_style="dim")
    table.add_column("Indicator", style="cyan", min_width=18)
    table.add_column("Value", style="white", justify="right")
    table.add_column("Signal", style="bold", justify="center")

    def ma_signal(close, ma):
        if ma is None:
            return "—"
        return "[green]Above[/green]" if close > ma else "[red]Below[/red]"

    c = ind.get("current_close")

    rows = [
        ("Current Close",  f"${c:.4f}" if c else "—", ""),
        ("Change %",       f"{ind.get('change_pct', 0):+.2f}%", ""),

        ("RSI (14)",       str(ind.get("rsi", "—")), ind.get("signal_rsi", "—")),
        ("MACD",           str(ind.get("macd", "—")), ind.get("signal_macd", "—")),
        ("MACD Signal",    str(ind.get("macd_signal", "—")), ""),

        ("BB Upper",       str(ind.get("bb_upper", "—")), ""),
        ("BB Mid",         str(ind.get("bb_mid", "—")), ""),
        ("BB Lower",       str(ind.get("bb_lower", "—")), ""),

        ("SMA 20",         str(ind.get("sma_20", "—")), ma_signal(c, ind.get("sma_20"))),
        ("SMA 50",         str(ind.get("sma_50", "—")), ma_signal(c, ind.get("sma_50"))),
        ("EMA 12",         str(ind.get("ema_12", "—")), ma_signal(c, ind.get("ema_12"))),

        ("STRATEGY",       "", f"[bold yellow]{ind.get('signal_combo', '—')}[/bold yellow]"),
    ]

    for name, val, sig in rows:
        table.add_row(name, val, sig)

    console.print(table)