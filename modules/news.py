"""
News & sentiment via yfinance (no API key needed).
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

_POSITIVE = {"surge", "rally", "beat", "record", "growth", "profit", "gain", "upgrade",
             "bullish", "outperform", "strong", "rise", "rose", "soar", "jumped", "high",
             "boost", "positive", "up", "raises", "exceeds", "wins"}
_NEGATIVE = {"drop", "fall", "loss", "miss", "downgrade", "bearish", "weak", "decline",
             "crash", "plunge", "slump", "concern", "risk", "warn", "cut", "layoff",
             "lawsuit", "investigation", "recall", "down", "low", "below", "fears"}


def _score(text: str) -> tuple[str, str]:
    words = set(text.lower().split())
    pos   = len(words & _POSITIVE)
    neg   = len(words & _NEGATIVE)
    if pos > neg: return "Positive", "green"
    if neg > pos: return "Negative", "red"
    return "Neutral", "yellow"


def get_news(symbol: str, limit: int = 5) -> list[dict] | None:
    try:
        import yfinance as yf
        ticker   = yf.Ticker(symbol.upper())
        raw_news = ticker.news or []

        articles = []
        for item in raw_news[:limit]:
            content   = item.get("content", {})
            headline  = content.get("title", item.get("title", "No title"))
            summary   = content.get("summary", "")
            source    = content.get("provider", {}).get("displayName", "Unknown") \
                        if isinstance(content.get("provider"), dict) \
                        else str(content.get("provider", "Unknown"))
            url       = content.get("canonicalUrl", {}).get("url", "") \
                        if isinstance(content.get("canonicalUrl"), dict) \
                        else ""
            pub_date  = content.get("pubDate", "")[:16] if content.get("pubDate") else "—"

            sentiment, color = _score(headline + " " + summary)
            articles.append({
                "headline" : headline,
                "source"   : source,
                "url"      : url,
                "time"     : pub_date,
                "sentiment": sentiment,
                "color"    : color,
                "summary"  : summary[:200],
            })
        return articles
    except Exception as e:
        console.print(f"[red]News error for {symbol}: {e}[/red]")
        return None


def print_news(symbol: str, articles: list[dict]) -> None:
    if not articles:
        console.print(f"[yellow]No recent news found for {symbol}.[/yellow]")
        return

    table = Table(title=f"📰 News — {symbol}", border_style="dim", show_lines=True)
    table.add_column("Time",      style="dim",  min_width=16)
    table.add_column("Sentiment", min_width=10, justify="center")
    table.add_column("Source",    style="cyan", min_width=12)
    table.add_column("Headline",  min_width=45)

    for a in articles:
        table.add_row(a["time"], Text(a["sentiment"], style=a["color"]), a["source"], a["headline"])

    console.print(table)