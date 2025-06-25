from flask import Flask, request, jsonify, send_file
import requests, statistics
from datetime import datetime

app = Flask(__name__)

API_KEY = 'e9032fc3c96b413dbb2ddf88dd599d63'
BASE_URL = 'https://api.twelvedata.com/time_series'

PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD",
    "NZD/USD","USD/CAD","EUR/JPY","GBP/JPY","EUR/GBP",
    "XAU/USD","US30/USD","NDX/USD","DE30/EUR"
]

def get_symbol(pair): return pair.replace("/", "")

def fetch_prices(symbol):
    params = {"symbol": symbol, "interval": "1h", "apikey": API_KEY, "outputsize": 60}
    r = requests.get(BASE_URL, params=params).json()
    return [float(c["close"]) for c in r.get("values", [])[::-1]] if "values" in r else []

def analyze_ma(prices):
    if len(prices) < 50: return "WAIT", "Not enough data"
    ma10, ma50 = statistics.mean(prices[-10:]), statistics.mean(prices[-50:])
    return ("BUY" if ma10 > ma50 else "SELL" if ma10 < ma50 else "WAIT", f"MA10: {ma10:.4f}, MA50: {ma50:.4f}")

def analyze_rsi(prices):
    if len(prices) < 15: return "WAIT", "Not enough data"
    gains = [prices[-i] - prices[-i-1] for i in range(1,15) if prices[-i] > prices[-i-1]]
    losses = [prices[-i-1] - prices[-i] for i in range(1,15) if prices[-i] < prices[-i-1]]
    rsi = 100 if not losses else 100 - (100 / (1 + (sum(gains)/14) / (sum(losses)/14)))
    return ("BUY" if rsi < 30 else "SELL" if rsi > 70 else "WAIT", f"RSI: {rsi:.2f}")

def analyze_vwap(prices):
    if len(prices) < 20: return "WAIT", "Not enough data"
    vwap, last = sum(prices[-20:])/20, prices[-1]
    return ("BUY" if last > vwap else "SELL" if last < vwap else "WAIT", f"Price: {last:.4f}, VWAP: {vwap:.4f}")

@app.route('/')
def index(): return send_file('index.html')

@app.route('/analyze')
def analyze():
    pair = request.args.get('pair')
    strategy = request.args.get('strategy', 'ma')
    symbol = get_symbol(pair)
    prices = fetch_prices(symbol)
    if not prices: return jsonify({"error": "No data"}), 500

    strategy_map = {"ma": analyze_ma, "rsi": analyze_rsi, "vwap": analyze_vwap}
    signal, explanation = strategy_map.get(strategy, analyze_ma)(prices)
    time = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    return jsonify({
        "pair": pair,
        "strategy": strategy.upper(),
        "signal": signal,
        "explanation": explanation,
        "timestamp": time
    })

app.run(host="0.0.0.0", port=81)
