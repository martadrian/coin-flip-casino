import asyncio
import nest_asyncio
import ccxt.async_support as ccxt
import datetime
import pytz
import requests
from flask import Flask
from threading import Thread

# --- CONFIGURATION (INSERT YOUR DATA HERE) ---
TELEGRAM_TOKEN = '8502307500:AAEXQhcuXFtY6jpcDZSSpRQgxS6E3tz310k'
TELEGRAM_CHAT_ID = '6089058395'
EXCHANGES = ['gateio', 'kucoin', 'mexc', 'bitget', 'bybit']
MY_TZ = pytz.timezone('Africa/Lagos')
SCAN_INTERVAL = 30  # Seconds between scans

# --- KEEP-ALIVE SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# --- BOT LOGIC ---
nest_asyncio.apply()

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload, timeout=10)
    except Exception as e: print(f"❌ Telegram Error: {e}")

async def get_triangular_paths(exchange):
    try:
        markets = await exchange.load_markets()
        paths = []
        for symbol in markets:
            if symbol.endswith('/USDT'):
                base = symbol.split('/')[0]
                if base == 'BTC': continue 
                leg2, leg3 = f"{base}/BTC", "BTC/USDT"
                if leg2 in markets and leg3 in markets:
                    paths.append({'p1': symbol, 'p2': leg2, 'p3': leg3, 'alt': base})
        return paths
    except: return []

async def scan_single_exchange(ex_id):
    ex_client = getattr(ccxt, ex_id)({'enableRateLimit': True})
    try:
        paths = await get_triangular_paths(ex_client)
        if not paths: return
        tickers = await ex_client.fetch_tickers()
        valid_results = []

        for path in paths:
            try:
                price1, price2, price3 = tickers[path['p1']]['ask'], tickers[path['p2']]['bid'], tickers[path['p3']]['bid']
                if not all([price1, price2, price3]): continue
                
                # Math: Starting with 100 USDT
                final_amount = (100.0 / price1) * price2 * price3
                profit_pct = (final_amount - 100.0)

                if profit_pct > 0: # SHOW ALL PROFITABLE RESULTS
                    valid_results.append({
                        'label': f"USDT➔{path['alt']}➔BTC➔USDT",
                        'profit': profit_pct,
                        'prices': f"A:{price1:.6f}, B:{price2:.8f}, B:{price3:.2f}"
                    })
            except: continue

        if valid_results:
            valid_results = sorted(valid_results, key=lambda x: x['profit'], reverse=True)
            now = datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')
            
            # Send results in chunks if there are many (Telegram has a character limit)
            report = f"🏛 *Exchange: {ex_id.upper()}* ({now})\n"
            for res in valid_results:
                line = f"✅ `{res['label']}`: *+{res['profit']:.4f}%*\n"
                if len(report) + len(line) > 4000:
                    send_telegram(report)
                    report = ""
                report += line
            send_telegram(report)
            
    except Exception as e: print(f"⚠️ Error {ex_id}: {e}")
    finally: await ex_client.close()

async def run_loop():
    print(f"🚀 Bot started. Scanning every {SCAN_INTERVAL} seconds...")
    while True:
        for ex_id in EXCHANGES:
            await scan_single_exchange(ex_id)
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    # Start the web server in a separate thread to keep Render happy
    Thread(target=run_web_server).start()
    # Start the bot loop
    asyncio.run(run_loop())
            
