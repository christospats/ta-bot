#!/usr/bin/env python3
"""
Alpaca Trading Assistant — Interactive CLI
Usage: python main.py
"""
from __future__ import annotations
import sys
import os

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter

import config
from modules.market      import get_quote, get_bars, get_portfolio, get_info
from modules.portfolio   import (portfolio_init, portfolio_session, portfolio_show,
                                  portfolio_add_asset, portfolio_remove_asset,
                                  portfolio_history, portfolio_list_symbols)
from modules.charts      import draw_price_chart, draw_volume_chart, draw_indicator_charts
from modules.indicators  import compute_indicators, print_indicators
from modules.news        import get_news, print_news
from ai.assistant        import chat, analyze_stock, compare_stocks

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════╗
║       🦙  Alpaca Trading Assistant  v1.0         ║
║       Advisory mode — no auto-trades             ║
╚══════════════════════════════════════════════════╝[/bold cyan]
"""

HELP_TEXT = """
[bold yellow]Available commands:[/bold yellow]

  [cyan]info   <SYMBOL>[/cyan]              Company info (sector, P/E, 52w range)
  [cyan]quote  <SYMBOL>[/cyan]              Real-time quote
  [cyan]chart  <SYMBOL> [PERIOD][/cyan]     ASCII price chart  (1D 1W 1M 3M 1Y)
  [cyan]icharts <SYMBOL> [PERIOD][/cyan]   4 charts: Price / MA / RSI / MACD  (alias: ic)
  [cyan]volume <SYMBOL> [PERIOD][/cyan]     Volume chart
  [cyan]ind    <SYMBOL> [PERIOD][/cyan]     Technical indicators
  [cyan]news   <SYMBOL>[/cyan]              Latest news + sentiment
  [cyan]portfolio init[/cyan]               Αρχικοποίηση portfolio (κεφάλαιο + assets)
  [cyan]portfolio show[/cyan]               Τρέχουσα κατάσταση + αποτίμηση
  [cyan]portfolio session [DATE][/cyan]     Νέα αγοραπωλησία (DATE: YYYY-MM-DD)
  [cyan]portfolio history[/cyan]            Ιστορικό sessions
  [cyan]portfolio add <SYM>[/cyan]          Προσθήκη asset
  [cyan]portfolio remove <SYM>[/cyan]       Αφαίρεση asset
  [cyan]analyze <SYMBOL> [PERIOD][/cyan]    Full AI analysis (chart + ind + news + AI)
  [cyan]compare <SYM_A> <SYM_B>[/cyan]     AI comparison of two stocks
  [cyan]ai[/cyan]                           Free-form chat with AI assistant
  [cyan]model  <name>[/cyan]               Switch Ollama model on the fly
  [cyan]help[/cyan]                         Show this help
  [cyan]quit / exit[/cyan]                  Exit

[dim]PERIOD defaults to 1M. API keys are loaded from .env[/dim]
"""

_COMMANDS = [
    "quote","chart","volume","ind","icharts","ic","news","info","portfolio","pf",
    "analyze","compare","ai","model","help","quit","exit",
]
_PERIODS  = ["1D","1W","1M","3M","1Y"]

# ── Helpers ──────────────────────────────────────────────

def _require_symbol(parts: list[str], cmd: str) -> str | None:
    if len(parts) < 2:
        console.print(f"[red]Usage: {cmd} <SYMBOL>[/red]")
        return None
    return parts[1].upper()


def _print_quote(symbol: str) -> float | None:
    q = get_quote(symbol)
    if not q:
        return None

    chg_color = "green" if q["change"] >= 0 else "red"
    chg_arrow = "▲" if q["change"] >= 0 else "▼"

    table = Table(title=f"💹 {symbol} — Quote", border_style="cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold white")

    table.add_row("Price",      f"[{chg_color}]${q['price']:.4f}  {chg_arrow} {q['change']:+.4f} ({q['change_pct']:+.2f}%)[/{chg_color}]")
    table.add_row("Prev Close", f"${q['prev_close']:.4f}" if q["prev_close"] else "—")
    table.add_row("Day High",   f"${q['day_high']:.4f}"   if q["day_high"]   else "—")
    table.add_row("Day Low",    f"${q['day_low']:.4f}"    if q["day_low"]    else "—")
    if q["volume"]:
        table.add_row("Volume", f"{q['volume']:,}")
    if q["market_cap"]:
        table.add_row("Market Cap", f"${q['market_cap']:,.0f}")
    table.add_row("Time",       q["time"])

    console.print(table)
    return q["price"]


def _print_portfolio() -> None:
    pf = get_portfolio()
    if not pf:
        return

    summary = Table(title="💼 Portfolio Overview", border_style="green")
    summary.add_column("Metric",  style="dim")
    summary.add_column("Value",   style="bold white", justify="right")
    summary.add_row("Equity",         f"${pf['equity']:,.2f}")
    summary.add_row("Cash",           f"${pf['cash']:,.2f}")
    summary.add_row("Buying Power",   f"${pf['buying_power']:,.2f}")
    summary.add_row("Portfolio Value",f"${pf['portfolio_value']:,.2f}")
    console.print(summary)

    if not pf["positions"]:
        console.print("[yellow]No open positions.[/yellow]")
        return

    pos_table = Table(title="Open Positions", border_style="dim", show_lines=True)
    for col in ["Symbol","Qty","Avg Cost","Current","Market Value","Unrealized P/L","P/L %"]:
        pos_table.add_column(col, justify="right")

    for p in pf["positions"]:
        pl_color = "green" if p["unrealized_pl"] >= 0 else "red"
        pos_table.add_row(
            p["symbol"],
            f"{p['qty']:.2f}",
            f"${p['avg_cost']:.2f}",
            f"${p['current']:.2f}",
            f"${p['market_value']:,.2f}",
            f"[{pl_color}]${p['unrealized_pl']:+,.2f}[/{pl_color}]",
            f"[{pl_color}]{p['unrealized_plpc']:+.2f}%[/{pl_color}]",
        )

    console.print(pos_table)


# ── Command handlers ─────────────────────────────────────



def cmd_portfolio(parts: list[str]) -> None:
    sub = parts[1].lower() if len(parts) > 1 else "show"

    if sub == "init":
        portfolio_init()
    elif sub == "show":
        portfolio_show()
    elif sub == "session":
        date = parts[2] if len(parts) > 2 else None
        portfolio_session(date)
    elif sub == "history":
        portfolio_history()
    elif sub == "add":
        if len(parts) < 3:
            console.print("[red]Usage: portfolio add <SYMBOL>[/red]")
            return
        portfolio_add_asset(parts[2])
    elif sub == "remove":
        if len(parts) < 3:
            console.print("[red]Usage: portfolio remove <SYMBOL>[/red]")
            return
        portfolio_remove_asset(parts[2])
    elif sub == "clear":
        from modules.portfolio import PORTFOLIO_FILE
        if PORTFOLIO_FILE.exists():
            from rich.prompt import Confirm
            if Confirm.ask("Διαγραφή όλου του portfolio;", default=False):
                PORTFOLIO_FILE.unlink()
                console.print("[red]Portfolio διαγράφηκε.[/red]")
        else:
            console.print("[yellow]Το portfolio είναι ήδη κενό.[/yellow]")
    else:
        console.print(f"[red]Άγνωστη εντολή: {sub}[/red]")
        console.print("[dim]init | show | session | history | add | remove | clear[/dim]")

def cmd_info(parts):
    sym = _require_symbol(parts, "info")
    if not sym:
        return
    inf = get_info(sym)
    if not inf:
        return
    table = Table(title=f"🏢 {sym} — Company Info", border_style="magenta")
    table.add_column("Field", style="dim")
    table.add_column("Value", style="white")
    table.add_row("Name",       inf["name"])
    table.add_row("Sector",     inf["sector"])
    table.add_row("Industry",   inf["industry"])
    table.add_row("Country",    inf["country"])
    table.add_row("P/E Ratio",  f"{inf['pe_ratio']:.2f}" if inf["pe_ratio"] else "—")
    table.add_row("EPS",        f"${inf['eps']:.4f}"     if inf["eps"]      else "—")
    table.add_row("52W High",   f"${inf['52w_high']:.4f}" if inf["52w_high"] else "—")
    table.add_row("52W Low",    f"${inf['52w_low']:.4f}"  if inf["52w_low"]  else "—")
    table.add_row("Avg Volume", f"{inf['avg_vol']:,}"     if inf["avg_vol"]  else "—")
    table.add_row("Website",    inf["website"])
    console.print(table)

def cmd_quote(parts):
    sym = _require_symbol(parts, "quote")
    if sym: _print_quote(sym)


def cmd_chart(parts):
    sym    = _require_symbol(parts, "chart")
    if not sym: return
    period = parts[2].upper() if len(parts) > 2 else config.DEFAULT_TIMEFRAME
    bars   = get_bars(sym, period)
    if bars:
        draw_price_chart(sym, bars, period)



def cmd_icharts(parts):
    sym    = _require_symbol(parts, "icharts")
    if not sym: return
    period = parts[2].upper() if len(parts) > 2 else config.DEFAULT_TIMEFRAME
    bars   = get_bars(sym, period)
    if bars:
        draw_indicator_charts(sym, bars, period)

def cmd_volume(parts):
    sym    = _require_symbol(parts, "volume")
    if not sym: return
    period = parts[2].upper() if len(parts) > 2 else config.DEFAULT_TIMEFRAME
    bars   = get_bars(sym, period)
    if bars:
        draw_volume_chart(sym, bars)


def cmd_ind(parts):
    sym    = _require_symbol(parts, "ind")
    if not sym: return
    period = parts[2].upper() if len(parts) > 2 else config.DEFAULT_TIMEFRAME
    bars   = get_bars(sym, period)
    if bars:
        ind = compute_indicators(bars, period)
        if ind:
            print_indicators(sym, ind)


def cmd_news(parts):
    sym = _require_symbol(parts, "news")
    if sym:
        articles = get_news(sym)
        if articles is not None:
            print_news(sym, articles)


def cmd_analyze(parts):
    sym    = _require_symbol(parts, "analyze")
    if not sym: return
    period = parts[2].upper() if len(parts) > 2 else config.DEFAULT_TIMEFRAME

    console.print(f"\n[bold]Fetching data for [cyan]{sym}[/cyan]...[/bold]")

    price    = _print_quote(sym)
    bars     = get_bars(sym, period)
    ind      = None
    if bars:
        draw_price_chart(sym, bars, period)
        ind = compute_indicators(bars, period)
        if ind:
            print_indicators(sym, ind)

    articles = get_news(sym)
    if articles:
        print_news(sym, articles)

    analyze_stock(sym, price or 0.0, period, ind, articles)


def cmd_compare(parts):
    if len(parts) < 3:
        console.print("[red]Usage: compare <SYMBOL_A> <SYMBOL_B>[/red]")
        return
    sym_a, sym_b = parts[1].upper(), parts[2].upper()
    period = "1M"

    console.print(f"\n[bold]Fetching data for [cyan]{sym_a}[/cyan] and [cyan]{sym_b}[/cyan]...[/bold]")

    q_a = get_quote(sym_a); q_b = get_quote(sym_b)
    bars_a = get_bars(sym_a, period); bars_b = get_bars(sym_b, period)
    ind_a  = compute_indicators(bars_a, period) if bars_a else None
    ind_b  = compute_indicators(bars_b, period) if bars_b else None

    if ind_a: print_indicators(sym_a, ind_a)
    if ind_b: print_indicators(sym_b, ind_b)

    compare_stocks(
        sym_a, q_a["price"] if q_a else 0.0, ind_a,
        sym_b, q_b["price"] if q_b else 0.0, ind_b,
    )


def cmd_ai(history: list[dict]) -> list[dict]:
    console.print(Panel(
        "[dim]Free-form chat with AI. Type [bold]back[/bold] or [bold]exit[/bold] to return to main menu.[/dim]",
        title="🤖 AI Chat", border_style="blue"
    ))
    ai_history = InMemoryHistory()
    while True:
        try:
            user_input = ptk_prompt("AI> ", history=ai_history).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("back", "exit", "quit"):
            break
        history = chat(user_input, history)
    return history


# ── Main loop ────────────────────────────────────────────

def check_config() -> bool:
    ok = True
    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        console.print("[red]⚠  ALPACA_API_KEY or ALPACA_SECRET_KEY not set.[/red]")
        console.print("[dim]Create a .env file with:[/dim]")
        console.print("[dim]  ALPACA_API_KEY=your_key[/dim]")
        console.print("[dim]  ALPACA_SECRET_KEY=your_secret[/dim]")
        ok = False
    return ok


def main():
    console.print(BANNER)

    if not check_config():
        console.print("\n[yellow]Continuing without valid keys — some commands will fail.[/yellow]\n")

    console.print(f"[dim]Model: {config.OLLAMA_MODEL}  |  Endpoint: {config.ALPACA_BASE_URL}[/dim]")
    console.print("[dim]Type [bold]help[/bold] for commands.[/dim]\n")

    completer    = WordCompleter(_COMMANDS + _PERIODS, ignore_case=True)
    cmd_history  = InMemoryHistory()
    ai_history: list[dict] = []

    while True:
        try:
            raw = ptk_prompt(
                "trader> ",
                history=cmd_history,
                completer=completer,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye![/dim]")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd   = parts[0].lower()

        if cmd in ("quit", "exit"):
            console.print("[dim]Bye![/dim]")
            break
        elif cmd == "help":
            console.print(HELP_TEXT)
        elif cmd in ("info", "i"):
            cmd_info(parts)
        elif cmd in ("quote", "q"):
            cmd_quote(parts)
        elif cmd in ("chart", "c"):
            cmd_chart(parts)
        elif cmd in ("icharts", "ic"):
            cmd_icharts(parts)
        elif cmd in ("volume", "vol"):
            cmd_volume(parts)
        elif cmd in ("ind", "indicators"):
            cmd_ind(parts)
        elif cmd in ("news", "n"):
            cmd_news(parts)
        elif cmd in ("portfolio", "pf"):
            cmd_portfolio(parts)
        elif cmd in ("analyze", "a"):
            cmd_analyze(parts)
        elif cmd in ("compare", "cmp"):
            cmd_compare(parts)
        elif cmd == "ai":
            ai_history = cmd_ai(ai_history)
        elif cmd == "model":
            if len(parts) < 2:
                console.print(f"[yellow]Current model: {config.OLLAMA_MODEL}[/yellow]")
            else:
                config.OLLAMA_MODEL = parts[1]
                console.print(f"[green]Model switched to: {config.OLLAMA_MODEL}[/green]")
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]  Type [bold]help[/bold] for options.")


if __name__ == "__main__":
    main()