import asyncio
import nest_asyncio
import ccxt.async_support as ccxt
import datetime
import pytz
import requests
import os
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# Bot pulls from Render Environment Variables first, fallback to your hardcoded ones
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8502307500:AAEXQhcuXFtY6jpcDZSSpRQgxS6E3tz310k')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '6089058395')

EXCHANGES = ['gateio', 'kucoin', 'mexc', 'bitget', 'bybit']
# EXPANDED INTERMEDIARIES: High-liquidity coins used as "bridges"
INTERMEDIARIES = ['BTC', 'ETH', 'BNB', 'SOL', 'USDC', 'DAI', 'XRP', 'ADA', 'TRX', 'DOT', 'KCS', 'GT', 'OKB', 'FDUSD']

MY_TZ = pytz.timezone('Africa/Lagos')
SCAN_INTERVAL = 60  # Updated to 1 Minute to avoid Render memory crashes

# --- KEEP-ALIVE SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

nest_asyncio.apply()

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

async def get_triangular_paths(exchange):
    """Finds all paths where ALT has pairs with both USDT and an INTERMEDIARY"""
    try:
        markets = await exchange.load_markets()
        paths = []
        for symbol in markets:
            if symbol.endswith('/USDT'):
                alt = symbol.split('/')[0]
                if alt in INTERMEDIARIES: continue 
                
                for bridge in INTERMEDIARIES:
                    leg2 = f"{alt}/{bridge}"
                    leg3 = f"{bridge}/USDT"
                    
                    if leg2 in markets and leg3 in markets:
                        paths.append({'p1': symbol, 'p2': leg2, 'p3': leg3, 'alt': alt, 'bridge': bridge})
        return paths
    except:
        return []

async def scan_single_exchange(ex_id):
    """Scans one exchange and sends ALL profitable results to Telegram"""
    print(f"🔄 Scanning {ex_id.upper()}...")
    ex_client = getattr(ccxt, ex_id)({'enableRateLimit': True})
    try:
        paths = await get_triangular_paths(ex_client)
        if not paths: return
        
        tickers = await ex_client.fetch_tickers()
        valid_results = []

        for path in paths:
            try:
                # Calculation: (100 USDT / Ask1) * Bid2 * Bid3
                p1 = tickers[path['p1']]['ask'] # Buy ALT with USDT
                p2 = tickers[path['p2']]['bid'] # Sell ALT for Bridge
                p3 = tickers[path['p3']]['bid'] # Sell Bridge for USDT
                
                if not all([p1, p2, p3]): continue
                
                final_amt = (100.0 / p1) * p2 * p3
                profit = final_amt - 100.0

                if profit > 0:
                    valid_results.append({
                        'label': f"USDT➔{path['alt']}➔{path['bridge']}➔USDT",
                        'profit': profit,
                        'data': f"A:{p1:.6f}, B:{p2:.6f}, B:{p3:.4f}"
                    })
            except:
                continue

        if valid_results:
            # Sort by highest profit
            valid_results = sorted(valid_results, key=lambda x: x['profit'], reverse=True)
            now = datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')
            
            report = f"🏛 *EXCHANGE: {ex_id.upper()}* ({now})\n"
            for res in valid_results:
                line = f"✅ `{res['label']}`: *+{res['profit']:.3f}%*\n"
                # Chunking to prevent Telegram character limit errors
                if len(report) + len(line) > 3900:
                    send_telegram(report)
                    report = f"🏛 *{ex_id.upper()} (Cont.)*\n"
                report += line
            send_telegram(report)
            
    except Exception as e:
        print(f"⚠️ {ex_id} Scan Error: {e}")
    finally:
        await ex_client.close()

async def run_loop():
    """Bulletproof loop that keeps running even if a scan fails"""
    print(f"🚀 Scanner Live. Interval: {SCAN_INTERVAL}s")
    while True:
        try:
            for ex_id in EXCHANGES:
                await scan_single_exchange(ex_id)
        except Exception as e:
            print(f"🔥 Critical Loop Error: {e}")
            await asyncio.sleep(10)
            
        print(f"💤 Cycle Finished. Sleeping {SCAN_INTERVAL}s...")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    # Start Keep-Alive Server
    Thread(target=run_web_server).start()
    # Start Main Bot
    asyncio.run(run_loop())
        
