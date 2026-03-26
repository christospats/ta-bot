# 🦙 Alpaca Trading Assistant

Ένα CLI trading assistant που χρησιμοποιεί:
- **Alpaca Markets API** για real-time δεδομένα & portfolio
- **Ollama** για local AI ανάλυση (qwen2.5:14b ή όποιο model θέλεις)
- **Rich** για όμορφο terminal UI
- **plotext** για ASCII charts

## 📦 Εγκατάσταση

```bash
cd alpaca-assistant
pip install -r requirements.txt

# Αντέγραψε το .env.example και βάλε τα keys σου
cp .env.example .env
```

## ⚙️ Ρύθμιση

Επεξεργάσου το `.env`:
```
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
OLLAMA_MODEL=qwen2.5:14b   # ή mistral-small3.1, deepseek-r1:14b κλπ
```

## 🚀 Εκκίνηση

```bash
# Πρώτα ξεκίνα το Ollama (αν δεν τρέχει ήδη)
ollama serve
ollama pull qwen2.5:14b

# Μετά ξεκίνα το assistant
python main.py
```

## 💻 Εντολές

| Εντολή | Περιγραφή |
|--------|-----------|
| `quote AAPL` | Real-time quote |
| `chart AAPL 3M` | ASCII chart (1D/1W/1M/3M/1Y) |
| `volume AAPL` | Volume chart |
| `ind AAPL` | Τεχνικοί δείκτες (RSI, MACD, BB, MA) |
| `news AAPL` | Νέα + sentiment ανάλυση |
| `portfolio` | Portfolio overview |
| `analyze AAPL` | Πλήρης AI ανάλυση |
| `compare AAPL MSFT` | AI σύγκριση δύο μετοχών |
| `ai` | Ελεύθερη συνομιλία με AI |
| `model llama3` | Αλλαγή Ollama model on-the-fly |

## ⚠️ Disclaimer

Αυτό το εργαλείο είναι **αποκλειστικά εκπαιδευτικό/πληροφοριακό**. Δεν αποτελεί χρηματοοικονομική συμβουλή. Δεν εκτελεί αυτόματα αγορές/πωλήσεις.