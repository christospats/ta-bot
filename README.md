# 📈 Trading Assistant CLI

Ένα CLI trading assistant με AI συμβουλευτικό ρόλο. Χρησιμοποιεί **yfinance** για παγκόσμια δεδομένα και **Ollama** για local AI ανάλυση.

> ⚠️ **Disclaimer:** Αυτό το εργαλείο είναι αποκλειστικά εκπαιδευτικό/πληροφοριακό. Δεν αποτελεί χρηματοοικονομική συμβουλή και δεν εκτελεί αυτόματα αγορές/πωλήσεις.

---

## 📦 Εγκατάσταση

```bash
git clone <repo>
cd trading-assistant

pip install -r requirements.txt
```

## ⚙️ Ρύθμιση

Αντέγραψε το `.env.example` και προσάρμοσε:
```bash
cp .env.example .env
```

Τα μόνα πεδία που χρειάζονται αλλαγή:
```env
OLLAMA_MODEL=qwen2.5:14b   # ή mistral-small3.1, deepseek-r1:14b κλπ
```

> Το Alpaca API key χρειάζεται **μόνο** αν θέλεις να βλέπεις το paper trading portfolio σου από το Alpaca. Για τα υπόλοιπα (τιμές, δείκτες, charts, portfolio manager) δεν χρειάζεται.

## 🚀 Εκκίνηση

```bash
# Ξεκίνα το Ollama (αν δεν τρέχει ήδη)
ollama serve
ollama pull qwen2.5:14b

# Εκκίνηση assistant
python main.py
```

---

## 💻 Εντολές

### Market Data
| Εντολή | Alias | Περιγραφή |
|--------|-------|-----------|
| `quote <SYM>` | `q` | Live quote (τιμή, change %, volume) |
| `info <SYM>` | `i` | Company info (sector, P/E, 52w range) |
| `chart <SYM> [PERIOD]` | `c` | ASCII price chart |
| `icharts <SYM> [PERIOD]` | `ic` | 5 charts: Price / SMA20 / SMA50 / RSI / MACD |
| `volume <SYM> [PERIOD]` | `vol` | Volume chart |
| `ind <SYM> [PERIOD]` | — | Τεχνικοί δείκτες (RSI, MACD, BB, SMA, EMA) |
| `news <SYM>` | `n` | Νέα + keyword sentiment |

**PERIOD:** `1D` `1W` `1M` `3M` `1Y` (default: `1M`)

**Symbols:** US μετοχές (`AAPL`), ελληνικές (`OPAP.AT`), crypto (`BTC`, `ETH`), ETFs (`SPY`) κλπ.

### AI Ανάλυση
| Εντολή | Alias | Περιγραφή |
|--------|-------|-----------|
| `analyze <SYM> [PERIOD]` | `a` | Πλήρης AI ανάλυση (quote + chart + δείκτες + νέα + AI) |
| `compare <SYM_A> <SYM_B>` | `cmp` | AI σύγκριση δύο assets |
| `ai` | — | Ελεύθερη συνομιλία με AI |
| `model <name>` | — | Αλλαγή Ollama model on-the-fly |

### Portfolio Manager
| Εντολή | Περιγραφή |
|--------|-----------|
| `portfolio init` | Αρχικοποίηση: ορισμός κεφαλαίου + assets |
| `portfolio show` | Τρέχουσα κατάσταση με live τιμές + αποτίμηση |
| `portfolio session [DATE]` | Νέα αγοραπωλησία session (DATE: YYYY-MM-DD) |
| `portfolio history` | Ιστορικό όλων των sessions |
| `portfolio add <SYM>` | Προσθήκη νέου asset στο portfolio |
| `portfolio remove <SYM>` | Αφαίρεση asset |
| `portfolio clear` | Διαγραφή portfolio (με confirmation) |

**Λογική portfolio:**
- Ορίζεις αρχικό κεφάλαιο και ποσό προς επένδυση μία φορά
- Κάθε session καταγράφει αγορές/πωλήσεις με αυτόματη σύσταση από RSI/MACD
- Αποτίμηση = `SUMPRODUCT(τιμές × ποσότητες) − συνολικό επενδεδυμένο ποσό`
- Υποστηρίζει fractions (π.χ. `0.003 BTC`)
- Αποθηκεύεται σε `portfolio.json`

---

## 🤖 Ollama Models

Με **RTX 5060 16GB VRAM** προτεινόμενα models:

| Model | VRAM | Ταχύτητα | Ποιότητα |
|-------|------|----------|----------|
| `qwen2.5:14b` | ~10GB | ⚡⚡⚡ | ⭐⭐⭐⭐ |
| `mistral-small3.1` | ~12GB | ⚡⚡⚡ | ⭐⭐⭐⭐ |
| `deepseek-r1:14b` | ~10GB | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| `qwen3-coder-next:cloud ` | ~ | ⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ |

```bash
ollama pull qwen2.5:14b
ollama pull mistral-small3.1
ollama pull deepseek-r1:14b

# Αλλαγή model μέσα στο CLI:
trader> model deepseek-r1:14b
```

---

## 📁 Δομή Project

```
trading-assistant/
├── main.py                  # Entry point, CLI loop
├── config.py                # Settings από .env
├── portfolio.json           # Portfolio data (δημιουργείται αυτόματα)
├── modules/
│   ├── market.py            # yfinance — quotes, bars, company info
│   ├── charts.py            # ASCII charts (plotext)
│   ├── indicators.py        # RSI, MACD, Bollinger Bands, SMA, EMA
│   ├── news.py              # Νέα & sentiment
│   └── portfolio.py         # Portfolio manager
├── ai/
│   ├── assistant.py         # Ollama integration
│   └── prompts.py           # System prompts
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Dependencies

```
yfinance        — market data (παγκόσμιο, δωρεάν, χωρίς API key)
ollama          — local AI (Ollama)
rich            — terminal UI
plotext         — ASCII charts
pandas-ta       — τεχνικοί δείκτες
prompt_toolkit  — CLI με history & autocomplete
python-dotenv   — .env config
alpaca-py       — προαιρετικό, μόνο για Alpaca paper portfolio
pytz
alpaca          — προαιρετικό, μόνο για Alpaca paper portfolio
```