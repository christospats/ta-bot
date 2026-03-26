"""
AI assistant router — uses Ollama (local) with graceful fallback message.
"""
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

import config
from ai.prompts import SYSTEM_PROMPT, ANALYZE_PROMPT, COMPARE_PROMPT

console = Console()


def _ollama_chat(messages: list[dict]) -> str | None:
    try:
        import ollama
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            stream=False,
        )
        return response["message"]["content"]
    except ImportError:
        console.print("[red]ollama package not installed. Run: pip install ollama[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Ollama error: {e}[/red]")
        console.print(f"[dim]Is Ollama running? Try: ollama serve[/dim]")
        return None


def _print_response(text: str, title: str = "🤖 AI Assistant") -> None:
    console.print(Panel(Markdown(text), title=title, border_style="blue", padding=(1, 2)))


# ── Public API ───────────────────────────────────────────

def chat(user_message: str, history: list[dict] | None = None) -> list[dict]:
    """Free-form chat. Returns updated history."""
    history = history or []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": user_message}
    ]

    console.print(f"[dim]Using model: {config.OLLAMA_MODEL}[/dim]")
    with console.status("[bold blue]Thinking...[/bold blue]", spinner="dots"):
        response = _ollama_chat(messages)

    if response:
        _print_response(response)
        history.append({"role": "user",      "content": user_message})
        history.append({"role": "assistant", "content": response})

    return history


def analyze_stock(symbol: str, price: float, period: str,
                  indicators: dict | None, news: list[dict] | None) -> None:
    """AI analysis of a single stock."""
    ind_text  = "\n".join(f"  {k}: {v}" for k, v in (indicators or {}).items())
    news_text = "\n".join(
        f"  [{a['sentiment']}] {a['headline']} ({a['source']}, {a['time']})"
        for a in (news or [])
    ) or "  No recent news available."

    prompt = ANALYZE_PROMPT.format(
        symbol=symbol, price=price, period=period,
        indicators=ind_text, news=news_text,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    console.print(f"[dim]Using model: {config.OLLAMA_MODEL}[/dim]")
    with console.status(f"[bold blue]Analyzing {symbol}...[/bold blue]", spinner="dots"):
        response = _ollama_chat(messages)

    if response:
        _print_response(response, title=f"🤖 AI Analysis — {symbol}")


def compare_stocks(sym_a: str, price_a: float, ind_a: dict | None,
                   sym_b: str, price_b: float, ind_b: dict | None) -> None:
    """AI comparison of two stocks."""
    def fmt(ind): return "\n".join(f"  {k}: {v}" for k, v in (ind or {}).items())

    prompt = COMPARE_PROMPT.format(
        symbol_a=sym_a, price_a=price_a, indicators_a=fmt(ind_a),
        symbol_b=sym_b, price_b=price_b, indicators_b=fmt(ind_b),
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    console.print(f"[dim]Using model: {config.OLLAMA_MODEL}[/dim]")
    with console.status(f"[bold blue]Comparing {sym_a} vs {sym_b}...[/bold blue]", spinner="dots"):
        response = _ollama_chat(messages)

    if response:
        _print_response(response, title=f"🤖 AI Comparison — {sym_a} vs {sym_b}")