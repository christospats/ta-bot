"""
Portfolio manager με session-based λογική.
Αποθηκεύεται σε portfolio.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.rule import Rule

console = Console()

PORTFOLIO_FILE = Path(os.getenv("PORTFOLIO_FILE", "portfolio.json"))

_CRYPTO = {"BTC","ETH","SOL","ADA","XRP","DOGE","BNB","AVAX","DOT","MATIC","LTC","LINK"}

def _normalize(symbol: str) -> str:
    s = symbol.upper()
    return s + "-USD" if s in _CRYPTO else s


# ── Persistence ──────────────────────────────────────────

def _load() -> dict:
    if PORTFOLIO_FILE.exists():
        try:
            return json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save(data: dict) -> None:
    PORTFOLIO_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ── Price fetch ──────────────────────────────────────────

def _fetch_price(yf_symbol: str) -> float | None:
    try:
        price = getattr(yf.Ticker(yf_symbol).fast_info, "last_price", None)
        return float(price) if price else None
    except Exception:
        return None


# ── Signal από RSI/MACD ──────────────────────────────────

def _compute_signal(symbol: str) -> str:
    try:
        import pandas as pd
        import pandas_ta as ta
        df = yf.Ticker(_normalize(symbol)).history(period="3mo", interval="1d")
        if df.empty or len(df) < 26:
            return "ΟΥΔΕΤΕΡΟ"
        closes = df["Close"]

        rsi = ta.rsi(closes, length=14)
        rsi_val = float(rsi.iloc[-1]) if rsi is not None and pd.notna(rsi.iloc[-1]) else 50.0

        macd_df = ta.macd(closes)
        macd_hist = 0.0
        if macd_df is not None:
            hist_col = next((c for c in macd_df.columns if c.startswith("MACDh_")), None)
            if hist_col and pd.notna(macd_df[hist_col].iloc[-1]):
                macd_hist = float(macd_df[hist_col].iloc[-1])

        # Λογική: RSI < 40 ή MACD hist > 0 → ΑΓΟΡΑ, RSI > 60 ή MACD hist < 0 → ΠΩΛΗΣΗ
        buy_signals  = (rsi_val < 40) + (macd_hist > 0)
        sell_signals = (rsi_val > 60) + (macd_hist < 0)

        if buy_signals >= 2:   return "ΑΓΟΡΑ"
        if sell_signals >= 2:  return "ΠΩΛΗΣΗ"
        if buy_signals > sell_signals: return "ΑΓΟΡΑ"
        if sell_signals > buy_signals: return "ΠΩΛΗΣΗ"
        return "ΟΥΔΕΤΕΡΟ"
    except Exception:
        return "ΟΥΔΕΤΕΡΟ"


# ── Init portfolio ───────────────────────────────────────

def portfolio_init() -> None:
    """Αρχικοποίηση portfolio — ορισμός κεφαλαίου και assets."""
    data = _load()

    if data.get("initialized"):
        console.print("[yellow]Portfolio already initialized.[/yellow]")
        console.print(f"[dim]Αρχικό κεφάλαιο: ${data['initial_capital']:,.2f}  |  "
                      f"Διαθέσιμα: ${data['available_cash']:,.2f}[/dim]")
        if not Confirm.ask("Θέλεις να το επανεκκινήσεις;", default=False):
            return

    console.print(Panel("[bold cyan]Αρχικοποίηση Portfolio[/bold cyan]", border_style="cyan"))

    try:
        capital = float(Prompt.ask("Αρχικό κεφάλαιο ($)"))
        invest  = float(Prompt.ask("Ποσό προς επένδυση ($)", default=str(capital)))
    except ValueError:
        console.print("[red]Μη έγκυρο ποσό.[/red]")
        return

    if invest > capital:
        console.print("[red]Το ποσό επένδυσης δεν μπορεί να υπερβαίνει το κεφάλαιο.[/red]")
        return

    # Προσθήκη assets
    assets: dict = {}
    console.print("\n[dim]Πρόσθεσε τα assets σου. Πάτα Enter με κενό σύμβολο για να τελειώσεις.[/dim]")
    while True:
        sym = Prompt.ask("Σύμβολο (π.χ. BTC, AAPL, OPAP.AT)").strip()
        if not sym:
            break
        yf_sym = _normalize(sym.upper())
        console.print(f"[dim]Fetching price για {yf_sym}...[/dim]")
        price = _fetch_price(yf_sym)
        if price is None:
            console.print(f"[red]Δεν βρέθηκε τιμή για {yf_sym}. Δοκίμασε ξανά.[/red]")
            continue
        console.print(f"[green]Τρέχουσα τιμή {sym.upper()}: ${price:,.4f}[/green]")
        assets[sym.upper()] = {
            "yf_symbol"  : yf_sym,
            "total_qty"  : 0.0,
        }

    data = {
        "initialized"      : True,
        "initial_capital"  : capital,
        "invest_amount"    : invest,
        "total_invested"   : 0.0,
        "available_cash"   : capital,
        "assets"           : assets,
        "sessions"         : [],
        "created_at"       : datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    _save(data)
    console.print(f"\n[green]✓ Portfolio initialized — κεφάλαιο: ${capital:,.2f}, "
                  f"προς επένδυση: ${invest:,.2f}[/green]")


# ── New session ──────────────────────────────────────────

def portfolio_session(date_str: str | None = None) -> None:
    """Νέα αγοραπωλησία session."""
    data = _load()
    if not data.get("initialized"):
        console.print("[red]Πρώτα τρέξε: portfolio init[/red]")
        return

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    console.print(Panel(
        f"[bold cyan]Νέα Session — {date_str}[/bold cyan]\n"
        f"[dim]Διαθέσιμα μετρητά: ${data['available_cash']:,.2f}  |  "
        f"Συνολικά επενδεδυμένα: ${data['total_invested']:,.2f}[/dim]",
        border_style="cyan"
    ))

    assets   = data["assets"]
    if not assets:
        console.print("[yellow]Δεν υπάρχουν assets. Τρέξε: portfolio init[/yellow]")
        return

    # Fetch τιμές και signals
    console.print("[dim]Φόρτωση τιμών και σημάτων...[/dim]")
    prices  : dict[str, float] = {}
    signals : dict[str, str]   = {}
    for sym, info in assets.items():
        p = _fetch_price(info["yf_symbol"])
        prices[sym]  = p or 0.0
        console.print(f"  [dim]{sym}: ${p:,.4f}  — computing signal...[/dim]")
        signals[sym] = _compute_signal(sym)

    # Εμφάνιση πίνακα προτάσεων
    tbl = Table(title=f"📋 Session {date_str}", border_style="cyan", show_lines=True)
    tbl.add_column("Σύμβολο",        style="cyan bold", min_width=10)
    tbl.add_column("Τιμή",           justify="right",   min_width=12)
    tbl.add_column("Υπάρχ. Qty",     justify="right",   min_width=12)
    tbl.add_column("Αξία Θέσης",     justify="right",   min_width=14)
    tbl.add_column("Σύσταση",        justify="center",  min_width=12)
    tbl.add_column("Νέα Qty (+/-)",  justify="right",   min_width=14)

    for sym, info in assets.items():
        price     = prices[sym]
        total_qty = info["total_qty"]
        pos_value = total_qty * price
        sig       = signals[sym]
        sig_color = "green" if sig == "ΑΓΟΡΑ" else ("red" if sig == "ΠΩΛΗΣΗ" else "yellow")

        tbl.add_row(
            sym,
            f"${price:,.4f}",
            f"{total_qty:.4f}",
            f"${pos_value:,.2f}",
            Text(sig, style=sig_color),
            "[dim]— θα εισαχθεί —[/dim]",
        )

    console.print(tbl)

    # Εισαγωγή νέων ποσοτήτων
    console.print("\n[bold]Εισαγωγή αλλαγών ποσοτήτων:[/bold]")
    console.print("[dim]Θετικό = αγορά, Αρνητικό = πώληση, 0 = χωρίς αλλαγή[/dim]\n")

    session_trades: list[dict] = []
    session_cost   = 0.0

    for sym, info in assets.items():
        price = prices[sym]
        try:
            raw = Prompt.ask(f"  {sym} (τιμή ${price:,.4f}, υπάρχ: {info['total_qty']:.4f})",
                             default="0")
            delta_qty = float(raw)
        except ValueError:
            delta_qty = 0.0

        new_total_qty = info["total_qty"] + delta_qty
        trade_value   = delta_qty * price   # θετικό = αγορά (κόστος), αρνητικό = πώληση (έσοδο)

        session_cost += trade_value

        session_trades.append({
            "symbol"       : sym,
            "price"        : price,
            "delta_qty"    : delta_qty,
            "new_total_qty": new_total_qty,
            "position_value": new_total_qty * price,
            "signal"       : signals[sym],
        })

        # Ενημέρωση assets
        assets[sym]["total_qty"] = new_total_qty

    # Υπολογισμοί session
    new_total_invested = data["total_invested"] + session_cost
    new_available_cash = data["initial_capital"] - new_total_invested

    # Αποτίμηση: SUMPRODUCT(τιμές × συν.ποσότητες) − συνολικό ποσό επένδυσης
    sumproduct = sum(t["position_value"] for t in session_trades)
    apotimisi  = sumproduct - new_total_invested

    # Εμφάνιση αποτελεσμάτων session
    console.print(Rule(f"[cyan]Αποτελέσματα Session {date_str}[/cyan]"))

    res_tbl = Table(border_style="green", show_lines=True)
    res_tbl.add_column("Σύμβολο",      style="cyan bold", min_width=10)
    res_tbl.add_column("Τιμή",         justify="right",   min_width=12)
    res_tbl.add_column("Νέα Qty",      justify="right",   min_width=10)
    res_tbl.add_column("Συν. Qty",     justify="right",   min_width=10)
    res_tbl.add_column("Αξία Θέσης",  justify="right",   min_width=14)
    res_tbl.add_column("Σύσταση",     justify="center",  min_width=12)
    res_tbl.add_column("Κόστος",      justify="right",   min_width=14)

    for t in session_trades:
        sig_color   = "green" if t["signal"] == "ΑΓΟΡΑ" else ("red" if t["signal"] == "ΠΩΛΗΣΗ" else "yellow")
        cost_color  = "red" if t["delta_qty"] > 0 else ("green" if t["delta_qty"] < 0 else "dim")
        res_tbl.add_row(
            t["symbol"],
            f"${t['price']:,.4f}",
            f"{t['delta_qty']:+.4f}" if t["delta_qty"] != 0 else "—",
            f"{t['new_total_qty']:.4f}",
            f"${t['position_value']:,.2f}",
            Text(t["signal"], style=sig_color),
            Text(f"${t['delta_qty'] * t['price']:+,.2f}", style=cost_color) if t["delta_qty"] != 0 else Text("—", style="dim"),
        )

    console.print(res_tbl)

    # Summary panel
    ap_color = "green" if apotimisi >= 0 else "red"
    summary = (
        f"[dim]Ποσό session (αγ/πωλ):      [/dim][white]${session_cost:+,.2f}[/white]\n"
        f"[dim]Συνολικό ποσό επένδυσης:    [/dim][white]${new_total_invested:,.2f}[/white]\n"
        f"[dim]Διαθέσιμα μετρητά:          [/dim][white]${new_available_cash:,.2f}[/white]\n"
        f"[dim]Αξία χαρτοφυλακίου:         [/dim][white]${sumproduct:,.2f}[/white]\n"
        f"[dim]Αποτίμηση (P/L):            [/dim][{ap_color}]${apotimisi:+,.2f}[/{ap_color}]"
    )
    console.print(Panel(summary, title=f"📊 Σύνοψη Session {date_str}",
                        border_style=ap_color, padding=(0, 2)))

    # Save session
    data["assets"]         = assets
    data["total_invested"] = new_total_invested
    data["available_cash"] = new_available_cash
    data["sessions"].append({
        "date"           : date_str,
        "trades"         : session_trades,
        "session_cost"   : session_cost,
        "total_invested" : new_total_invested,
        "available_cash" : new_available_cash,
        "portfolio_value": sumproduct,
        "apotimisi"      : apotimisi,
    })
    _save(data)
    console.print(f"\n[green]✓ Session αποθηκεύτηκε.[/green]")


# ── Show portfolio ───────────────────────────────────────

def portfolio_show() -> None:
    data = _load()
    if not data.get("initialized"):
        console.print("[red]Πρώτα τρέξε: portfolio init[/red]")
        return

    assets = data["assets"]
    if not assets:
        console.print("[yellow]Δεν υπάρχουν assets.[/yellow]")
        return

    console.print("[dim]Φόρτωση τιμών...[/dim]")

    tbl = Table(title="💼 Portfolio — Τρέχουσα Κατάσταση",
                border_style="green", show_lines=True)
    tbl.add_column("Σύμβολο",    style="cyan bold", min_width=10)
    tbl.add_column("Τιμή",       justify="right",   min_width=12)
    tbl.add_column("Συν. Qty",   justify="right",   min_width=12)
    tbl.add_column("Αξία Θέσης", justify="right",   min_width=14)
    tbl.add_column("Σύσταση",    justify="center",  min_width=12)

    total_value = 0.0
    for sym, info in assets.items():
        price     = _fetch_price(info["yf_symbol"]) or 0.0
        pos_value = info["total_qty"] * price
        total_value += pos_value
        sig       = _compute_signal(sym)
        sig_color = "green" if sig == "ΑΓΟΡΑ" else ("red" if sig == "ΠΩΛΗΣΗ" else "yellow")
        tbl.add_row(
            sym,
            f"${price:,.4f}",
            f"{info['total_qty']:.4f}",
            f"${pos_value:,.2f}",
            Text(sig, style=sig_color),
        )
    console.print(tbl)

    apotimisi = total_value - data["total_invested"]
    ap_color  = "green" if apotimisi >= 0 else "red"
    summary = (
        f"[dim]Αρχικό κεφάλαιο:          [/dim][white]${data['initial_capital']:,.2f}[/white]\n"
        f"[dim]Συνολικά επενδεδυμένα:    [/dim][white]${data['total_invested']:,.2f}[/white]\n"
        f"[dim]Διαθέσιμα μετρητά:        [/dim][white]${data['available_cash']:,.2f}[/white]\n"
        f"[dim]Αξία χαρτοφυλακίου:       [/dim][white]${total_value:,.2f}[/white]\n"
        f"[dim]Αποτίμηση (P/L):          [/dim][{ap_color}]${apotimisi:+,.2f}[/{ap_color}]"
    )
    console.print(Panel(summary, title="📊 Σύνοψη", border_style=ap_color, padding=(0, 2)))

    # Ιστορικό sessions
    sessions = data.get("sessions", [])
    if sessions:
        console.print(f"\n[dim]Ιστορικό: {len(sessions)} session(s)[/dim]")
        hist = Table(border_style="dim", show_lines=False)
        hist.add_column("Ημερομηνία", style="dim",   min_width=12)
        hist.add_column("Κόστος",     justify="right", min_width=14)
        hist.add_column("Συν. Επενδ.",justify="right", min_width=14)
        hist.add_column("Αξία",       justify="right", min_width=14)
        hist.add_column("Αποτίμηση",  justify="right", min_width=14)
        for s in sessions:
            ap    = s["apotimisi"]
            color = "green" if ap >= 0 else "red"
            hist.add_row(
                s["date"],
                f"${s['session_cost']:+,.2f}",
                f"${s['total_invested']:,.2f}",
                f"${s['portfolio_value']:,.2f}",
                Text(f"${ap:+,.2f}", style=color),
            )
        console.print(hist)


# ── Add/Remove assets ────────────────────────────────────

def portfolio_add_asset(symbol: str) -> None:
    data = _load()
    if not data.get("initialized"):
        console.print("[red]Πρώτα τρέξε: portfolio init[/red]")
        return
    sym    = symbol.upper()
    yf_sym = _normalize(sym)
    if sym in data["assets"]:
        console.print(f"[yellow]{sym} υπάρχει ήδη στο portfolio.[/yellow]")
        return
    price = _fetch_price(yf_sym)
    if price is None:
        console.print(f"[red]Δεν βρέθηκε τιμή για {yf_sym}.[/red]")
        return
    data["assets"][sym] = {"yf_symbol": yf_sym, "total_qty": 0.0}
    _save(data)
    console.print(f"[green]✓ Προστέθηκε {sym} (${price:,.4f})[/green]")


def portfolio_remove_asset(symbol: str) -> None:
    data = _load()
    sym  = symbol.upper()
    if sym not in data.get("assets", {}):
        console.print(f"[yellow]{sym} δεν υπάρχει στο portfolio.[/yellow]")
        return
    del data["assets"][sym]
    _save(data)
    console.print(f"[red]Αφαιρέθηκε το {sym}.[/red]")


def portfolio_history() -> None:
    data = _load()
    sessions = data.get("sessions", [])
    if not sessions:
        console.print("[yellow]Δεν υπάρχουν sessions ακόμα.[/yellow]")
        return
    for s in sessions:
        ap    = s["apotimisi"]
        color = "green" if ap >= 0 else "red"
        console.print(Rule(f"[cyan]Session {s['date']}[/cyan]"))
        tbl = Table(border_style="dim", show_lines=True)
        tbl.add_column("Σύμβολο");  tbl.add_column("Τιμή", justify="right")
        tbl.add_column("Νέα Qty", justify="right"); tbl.add_column("Συν. Qty", justify="right")
        tbl.add_column("Αξία Θέσης", justify="right"); tbl.add_column("Σύσταση", justify="center")
        for t in s["trades"]:
            sig_color = "green" if t["signal"] == "ΑΓΟΡΑ" else ("red" if t["signal"] == "ΠΩΛΗΣΗ" else "yellow")
            tbl.add_row(
                t["symbol"], f"${t['price']:,.4f}",
                f"{t['delta_qty']:+.4f}" if t["delta_qty"] != 0 else "—",
                f"{t['new_total_qty']:.4f}", f"${t['position_value']:,.2f}",
                Text(t["signal"], style=sig_color),
            )
        console.print(tbl)
        console.print(f"  Αποτίμηση: [{color}]${ap:+,.2f}[/{color}]  |  "
                      f"Διαθέσιμα: ${s['available_cash']:,.2f}\n")


def portfolio_list_symbols() -> list[str]:
    return list(_load().get("assets", {}).keys())