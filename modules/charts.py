"""
ASCII charts using plotext.
- draw_price_chart     : απλό price chart (υπάρχον)
- draw_indicator_charts: 4 ξεχωριστά panels με δείκτες
"""
from __future__ import annotations

import plotext as plt
import pandas as pd
try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False

from rich.console import Console
from rich.rule import Rule

import config

console = Console()


# ── Helpers ──────────────────────────────────────────────

def _build_df(bars: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(bars)
    df = df.astype({"open": float, "high": float, "low": float,
                    "close": float, "volume": float})
    return df


def _xticks(labels: list[str], n: int = 8) -> tuple[list[int], list[str]]:
    """Thin out x-axis labels so they don't overlap."""
    step = max(1, len(labels) // n)
    idx  = list(range(len(labels)))
    return idx[::step], labels[::step]


def _plt_reset(width: int | None = None, height: int | None = None) -> None:
    plt.clf()
    plt.theme("dark")
    plt.plot_size(
        width  or config.CHART_WIDTH,
        height or config.CHART_HEIGHT,
    )


# ── Chart 1 : Plain price ────────────────────────────────

def draw_price_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars:
        console.print("[yellow]No bar data available.[/yellow]")
        return

    closes = [b["close"] for b in bars]
    labels = [b["time"]  for b in bars]
    x      = list(range(len(closes)))
    xi, xl = _xticks(labels)

    _plt_reset()
    plt.title(f"{symbol}  [{period}]  — Close Price")
    plt.xlabel("Date"); plt.ylabel("Price ($)")
    plt.plot(x, closes, marker="braille", color="cyan")

    min_i = closes.index(min(closes))
    max_i = closes.index(max(closes))
    plt.scatter([x[min_i]], [closes[min_i]], marker="x", color="red",
                label=f"Low  ${closes[min_i]:.2f}")
    plt.scatter([x[max_i]], [closes[max_i]], marker="x", color="green",
                label=f"High ${closes[max_i]:.2f}")
    plt.xticks(xi, xl)
    plt.show()


def draw_volume_chart(symbol: str, bars: list[dict]) -> None:
    if not bars:
        return
    volumes = [b["volume"] for b in bars]
    x       = list(range(len(volumes)))
    _plt_reset(height=config.CHART_HEIGHT // 2)
    plt.title(f"{symbol}  — Volume")
    plt.bar(x, volumes, color="blue")
    plt.show()


# ── Chart 2a : Price + SMA 20 ───────────────────────────

def draw_sma20_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars:
        return
    df     = _build_df(bars)
    closes = df["close"].tolist()
    labels = [b["time"] for b in bars]
    x      = list(range(len(closes)))
    xi, xl = _xticks(labels)

    _plt_reset()
    plt.title(f"{symbol}  [{period}]  — Price + SMA 20")
    plt.xlabel("Date"); plt.ylabel("Price ($)")
    plt.plot(x, closes, marker="braille", color="cyan", label="Price")

    if HAS_TA:
        s20 = ta.sma(df["close"], 20)
        if s20 is not None:
            y20 = [v if pd.notna(v) else None for v in s20.tolist()]
            plt.plot(x, y20, marker="dot", color="yellow", label="SMA 20")

    plt.xticks(xi, xl)
    plt.show()


# ── Chart 2b : Price + SMA 50 ───────────────────────────

def draw_sma50_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars:
        return
    df     = _build_df(bars)
    closes = df["close"].tolist()
    labels = [b["time"] for b in bars]
    x      = list(range(len(closes)))
    xi, xl = _xticks(labels)

    _plt_reset()
    plt.title(f"{symbol}  [{period}]  — Price + SMA 50")
    plt.xlabel("Date"); plt.ylabel("Price ($)")
    plt.plot(x, closes, marker="braille", color="cyan", label="Price")

    if HAS_TA:
        s50 = ta.sma(df["close"], 50)
        if s50 is not None:
            y50 = [v if pd.notna(v) else None for v in s50.tolist()]
            plt.plot(x, y50, marker="dot", color="magenta", label="SMA 50")

    plt.xticks(xi, xl)
    plt.show()


# ── Chart 3 : Price + RSI ────────────────────────────────

def draw_rsi_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars or not HAS_TA:
        return
    df     = _build_df(bars)
    closes = df["close"].tolist()
    labels = [b["time"] for b in bars]
    x      = list(range(len(closes)))
    xi, xl = _xticks(labels)

    rsi_series = ta.rsi(df["close"], length=14)
    if rsi_series is None:
        console.print("[yellow]Not enough data for RSI.[/yellow]")
        return
    rsi_vals = [v if pd.notna(v) else None for v in rsi_series.tolist()]

    # ── subplot 1: price ────────────────────────────────
    plt.clf()
    plt.theme("dark")
    plt.subplots(2, 1)

    plt.subplot(1, 1)
    plt.plot_size(config.CHART_WIDTH, config.CHART_HEIGHT)
    plt.title(f"{symbol}  [{period}]  — Price")
    plt.ylabel("Price ($)")
    plt.plot(x, closes, marker="braille", color="cyan", label="Price")
    plt.xticks(xi, xl)

    # ── subplot 2: RSI ──────────────────────────────────
    plt.subplot(2, 1)
    plt.plot_size(config.CHART_WIDTH, config.CHART_HEIGHT // 2)
    plt.title("RSI (14)")
    plt.ylabel("RSI")
    plt.ylim(0, 100)

    plt.plot(x, rsi_vals, marker="braille", color="white", label="RSI")

    # Overbought / oversold lines
    plt.horizontal_line(70, color="red")
    plt.horizontal_line(30, color="green")
    plt.horizontal_line(50, color="gray+")

    plt.xticks(xi, xl)
    plt.show()


# ── Chart 4 : Price + MACD (3 subplots) ─────────────────

def draw_macd_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars or not HAS_TA:
        return
    df     = _build_df(bars)
    closes = df["close"].tolist()
    labels = [b["time"] for b in bars]
    x      = list(range(len(closes)))
    xi, xl = _xticks(labels)

    macd_df = ta.macd(df["close"])
    if macd_df is None:
        console.print("[yellow]Not enough data for MACD.[/yellow]")
        return

    cols       = macd_df.columns.tolist()
    macd_col   = next((col for col in cols if col.startswith("MACD_")),  None)
    signal_col = next((col for col in cols if col.startswith("MACDs_")), None)
    hist_col   = next((col for col in cols if col.startswith("MACDh_")), None)

    def _clean(series):
        return [v if pd.notna(v) else None for v in series.tolist()]

    macd_line   = _clean(macd_df[macd_col])   if macd_col   else []
    signal_line = _clean(macd_df[signal_col]) if signal_col else []
    hist_vals   = _clean(macd_df[hist_col])   if hist_col   else []

    hist_pos = [v if (v is not None and v >= 0) else 0 for v in hist_vals]
    hist_neg = [v if (v is not None and v <  0) else 0 for v in hist_vals]

    h_price  = config.CHART_HEIGHT
    h_lines  = max(8, config.CHART_HEIGHT // 2)
    h_hist   = max(6, config.CHART_HEIGHT // 3)

    plt.clf()
    plt.theme("dark")
    plt.subplots(3, 1)

    # ── subplot 1: Price ────────────────────────────────
    plt.subplot(1, 1)
    plt.plot_size(config.CHART_WIDTH, h_price)
    plt.title(f"{symbol}  [{period}]  — Price")
    plt.ylabel("Price ($)")
    plt.plot(x, closes, marker="braille", color="cyan", label="Price")
    plt.xticks(xi, xl)

    # ── subplot 2: MACD line + Signal line ──────────────
    plt.subplot(2, 1)
    plt.plot_size(config.CHART_WIDTH, h_lines)
    plt.title("MACD Line vs Signal Line")
    plt.ylabel("Value")
    if macd_line:   plt.plot(x, macd_line,   marker="braille", color="yellow", label="MACD")
    if signal_line: plt.plot(x, signal_line, marker="braille", color="red",    label="Signal")
    plt.horizontal_line(0, color="gray+")
    plt.xticks(xi, xl)

    # ── subplot 3: Histogram only ───────────────────────
    plt.subplot(3, 1)
    plt.plot_size(config.CHART_WIDTH, h_hist)
    plt.title("MACD Histogram  (green = bullish, red = bearish)")
    plt.ylabel("Hist")
    if any(v != 0 for v in hist_pos): plt.bar(x, hist_pos, color="green", label="▲")
    if any(v != 0 for v in hist_neg): plt.bar(x, hist_neg, color="red",   label="▼")
    plt.horizontal_line(0, color="gray+")
    plt.xticks(xi, xl)

    plt.show()


# ── icharts : τρέχει και τα 4 ────────────────────────────

def draw_indicator_charts(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars:
        console.print("[yellow]No bar data available.[/yellow]")
        return

    console.print(Rule(f"[cyan]Chart 1/5 — {symbol} Price[/cyan]"))
    draw_price_chart(symbol, bars, period)

    console.print(Rule(f"[yellow]Chart 2/5 — {symbol} Price + SMA 20[/yellow]"))
    draw_sma20_chart(symbol, bars, period)

    console.print(Rule(f"[magenta]Chart 3/5 — {symbol} Price + SMA 50[/magenta]"))
    draw_sma50_chart(symbol, bars, period)

    console.print(Rule(f"[white]Chart 4/5 — {symbol} Price + RSI[/white]"))
    draw_rsi_chart(symbol, bars, period)

    console.print(Rule(f"[blue]Chart 5/5 — {symbol} Price + MACD[/blue]"))
    draw_macd_chart(symbol, bars, period)