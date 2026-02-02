import asyncio
import nest_asyncio
import ccxt.async_support as ccxt
import datetime
import pytz
import requests
from flask import Flask
from threading import Thread
import os

# --- CONFIGURATION ---
# Use Environment Variables for Render, or paste directly here for Colab
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8502307500:AAEXQhcuXFtY6jpcDZSSpRQgxS6E3tz310k')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '6089058395')

EXCHANGES = ['gateio', 'kucoin', 'mexc', 'bitget', 'bybit']
# The coins to use as the "Middle" bridge
INTERMEDIARIES = ['BTC', 'ETH', 'BNB', 'SOL'] 
MY_TZ = pytz.timezone('Africa/Lagos')
SCAN_INTERVAL = 60  # Changed to 1 minute

# --- KEEP-ALIVE SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

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
                alt = symbol.split('/')[0]
                if alt in INTERMEDIARIES: continue 
                
                # Check each possible bridge coin
                for bridge in INTERMEDIARIES:
                    leg2 = f"{alt}/{bridge}"
                    leg3 = f"{bridge}/USDT"
                    
                    if leg2 in markets and leg3 in markets:
                        paths.append({'p1': symbol, 'p2': leg2, 'p3': leg3, 'alt': alt, 'bridge': bridge})
        return paths
    except: return []

async def scan_single_exchange(ex_id):
    print(f"🔍 {ex_id.upper()}: Scanning for all {INTERMEDIARIES} triangles...")
    ex_client = getattr(ccxt, ex_id)({'enableRateLimit': True})
    try:
        paths = await get_triangular_paths(ex_client)
        if not paths: return
        tickers = await ex_client.fetch_tickers()
        valid_results = []

        for path in paths:
            try:
                # Execution Logic: 
                # 1. Buy Alt with USDT (Ask)
                # 2. Sell Alt for Bridge (Bid)
                # 3. Sell Bridge for USDT (Bid)
                p1, p2, p3 = tickers[path['p1']]['ask'], tickers[path['p2']]['bid'], tickers[path['p3']]['bid']
                if not all([p1, p2, p3]): continue
                
                final_amount = (100.0 / p1) * p2 * p3
                profit_pct = (final_amount - 100.0)

                if profit_pct > 0: # Shows ALL profitable results
                    valid_results.append({
                        'label': f"USDT ➔ {path['alt']} ➔ {path['bridge']} ➔ USDT",
                        'profit': profit_pct,
                        'prices': f"A1:{p1:.6f}, B2:{p2:.8f}, B3:{p3:.4f}"
                    })
            except: continue

        if valid_results:
            valid_results = sorted(valid_results, key=lambda x: x['profit'], reverse=True)
            now = datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')
            
            report = f"🏛 *EXCHANGE: {ex_id.upper()}* ({now})\n"
            for res in valid_results:
                line = f"✅ `{res['label']}`: *+{res['profit']:.4f}%*\n"
                if len(report) + len(line) > 4000:
                    send_telegram(report)
                    report = f"🏛 *{ex_id.upper()} (Cont.)*\n"
                report += line
            send_telegram(report)
            
    except Exception as e: print(f"⚠️ Error {ex_id}: {e}")
    finally: await ex_client.close()

async def run_loop():
    print(f"🚀 Bot Live. Scanning 5 exchanges every {SCAN_INTERVAL}s...")
    while True:
        for ex_id in EXCHANGES:
            await scan_single_exchange(ex_id)
        print(f"😴 Waiting {SCAN_INTERVAL}s for next cycle...")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    Thread(target=run_web_server).start()
    asyncio.run(run_loop())
    
