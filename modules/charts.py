"""
ASCII charts using plotext.
"""
from __future__ import annotations
import plotext as plt
from rich.console import Console
from rich.panel import Panel

import config

console = Console()


def draw_price_chart(symbol: str, bars: list[dict], period: str = "1M") -> None:
    if not bars:
        console.print("[yellow]No bar data available.[/yellow]")
        return

    closes = [b["close"] for b in bars]
    labels = [b["time"]  for b in bars]

    # Thin out x labels so they don't overlap
    step   = max(1, len(labels) // 8)
    x_vals = list(range(len(closes)))

    plt.clf()
    plt.theme("dark")
    plt.plot_size(config.CHART_WIDTH, config.CHART_HEIGHT)
    plt.title(f"{symbol}  [{period}]  — Close Price")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")

    plt.plot(x_vals, closes, marker="braille", color="cyan")

    # Mark min / max
    min_i = closes.index(min(closes))
    max_i = closes.index(max(closes))
    plt.scatter([x_vals[min_i]], [closes[min_i]], marker="x", color="red",   label=f"Low  ${closes[min_i]:.2f}")
    plt.scatter([x_vals[max_i]], [closes[max_i]], marker="x", color="green", label=f"High ${closes[max_i]:.2f}")

    # X-tick labels
    tick_positions = x_vals[::step]
    tick_labels    = labels[::step]
    plt.xticks(tick_positions, tick_labels)

    plt.show()


def draw_volume_chart(symbol: str, bars: list[dict]) -> None:
    if not bars:
        return
    volumes = [b["volume"] for b in bars]
    x_vals  = list(range(len(volumes)))

    plt.clf()
    plt.theme("dark")
    plt.plot_size(config.CHART_WIDTH, config.CHART_HEIGHT // 2)
    plt.title(f"{symbol}  — Volume")
    plt.bar(x_vals, volumes, color="blue")
    plt.show()