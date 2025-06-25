from flask import Flask, request, jsonify, send_file
import requests, statistics
from datetime import datetime
import os

app = Flask(__name__)

API_KEY = 'e9032fc3c96b413dbb2ddf88dd599d63'
BASE_URL = 'https://api.twelvedata.com/time_series'

def get_symbol(pair): return pair.replace("/", "")

def fetch_prices(symbol):
    params = {"symbol": symbol, "interval": "1h", "apikey": API_KEY, "outputsize": 60}
    r = requests.get(BASE_URL, params=params).json()
    if "values" not in r:
        return []
    try:
        return [float(c["close"]) for c in r["values"][::-1]]
    except:
        return []

def analyze_ma(prices):
    if len(prices) < 50:
        return "WAIT", "Not enough data for MA"
    ma10 = statistics.mean(prices[-10:])
    ma50 = statistics.mean(prices[-50:])
    if ma10 > ma50:
        return "BUY", f"MA10: {ma10:.4f} > MA50: {ma50:.4f}"
    elif ma10 < ma50:
        return "SELL", f"MA10: {ma10:.4f} < MA50: {ma50:.4f}"
    else:
        return "WAIT", "MAs are equal"

def analyze_rsi(prices):
    if len(prices) < 15:
        return "WAIT", "Not enough data for RSI"
    gains = [prices[-i] - prices[-i-1] for i in range(1,15) if prices[-i] > prices[-i-1]]
    losses = [prices[-i-1] - prices[-i] for i in range(1,15) if prices[-i] < prices[-i-1]]
    if not losses:
        return "WAIT", "No losses - RSI undefined"
    avg_gain = sum(gains)/14 if gains else 0.01
    avg_loss = sum(losses)/14 if losses else 0.01
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    if rsi < 30:
        return "BUY", f"RSI: {rsi:.2f} (Oversold)"
    elif rsi > 70:
        return "SELL", f"RSI: {rsi:.2f} (Overbought)"
    else:
        return "WAIT", f"RSI: {rsi:.2f}"

def analyze_vwap(prices):
    if len(prices) < 20:
        return "WAIT", "Not enough data for VWAP"
    vwap = sum(prices[-20:]) / 20
    last = prices[-1]
    if last > vwap:
        return "BUY", f"Price: {last:.4f} > VWAP: {vwap:.4f}"
    elif last < vwap:
        return "SELL", f"Price: {last:.4f} < VWAP: {vwap:.4f}"
    else:
        return "WAIT", "Price == VWAP"

@app.route('/')
def index(): return send_file('index.html')

@app.route('/analyze')
def analyze():
    pair = request.args.get('pair')
    strategy = request.args.get('strategy', 'ma')
    symbol = get_symbol(pair)
    prices = fetch_prices(symbol)
    if not prices:
        return jsonify({
            "pair": pair,
            "strategy": strategy.upper(),
            "signal": "ERROR",
            "explanation": "No data received. API limit? Wrong symbol?",
            "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        })

    strategy_map = {"ma": analyze_ma, "rsi": analyze_rsi, "vwap": analyze_vwap}
    analyze_func = strategy_map.get(strategy, analyze_ma)
    signal, explanation = analyze_func(prices)
    time = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    return jsonify({
        "pair": pair,
        "strategy": strategy.upper(),
        "signal": signal,
        "explanation": explanation,
        "timestamp": time
    })

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
