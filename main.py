import asyncio
import nest_asyncio
import ccxt.async_support as ccxt
import datetime
import pytz
import requests
import os
from aiohttp import web 

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8502307500:AAEXQhcuXFtY6jpcDZSSpRQgxS6E3tz310k')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '6089058395')

EXCHANGES = ['gateio', 'kucoin', 'mexc', 'bitget', 'bybit']
# Comprehensive bridge list for maximum discovery
INTERMEDIARIES = ['BTC', 'ETH', 'BNB', 'SOL', 'USDC', 'DAI', 'XRP', 'ADA', 'TRX', 'DOT', 'KCS', 'GT', 'OKB', 'FDUSD']

MY_TZ = pytz.timezone('Africa/Lagos')
SCAN_INTERVAL = 60 

nest_asyncio.apply()

# --- SYSTEM UTILS ---
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

async def handle_health(request):
    """Answers the doorbell for Render's health check"""
    return web.Response(text="Bot is Active")

# --- BOT LOGIC ---
async def get_triangular_paths(exchange):
    try:
        markets = await exchange.load_markets()
        paths = []
        for symbol in markets:
            if symbol.endswith('/USDT'):
                alt = symbol.split('/')[0]
                if alt in INTERMEDIARIES: continue 
                for bridge in INTERMEDIARIES:
                    leg2, leg3 = f"{alt}/{bridge}", f"{bridge}/USDT"
                    if leg2 in markets and leg3 in markets:
                        paths.append({'p1': symbol, 'p2': leg2, 'p3': leg3, 'alt': alt, 'bridge': bridge})
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
                p1, p2, p3 = tickers[path['p1']]['ask'], tickers[path['p2']]['bid'], tickers[path['p3']]['bid']
                if not all([p1, p2, p3]): continue
                
                # Formula: USDT -> ALT -> BRIDGE -> USDT
                final_amt = (100.0 / p1) * p2 * p3
                profit = final_amt - 100.0
                
                if profit > 0.05: # Only show results above 0.05%
                    # UPDATED LABEL FORMAT: Now shows the full USDT path
                    label = f"USDT➔{path['alt']}➔{path['bridge']}➔USDT"
                    valid_results.append({'text': f"✅ `{label}`: *+{profit:.3f}%*", 'profit': profit})
            except: continue

        if valid_results:
            # Sort so highest profit is at the top
            valid_results = sorted(valid_results, key=lambda x: x['profit'], reverse=True)
            now = datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')
            
            # Extract text lines and join them
            report_lines = [res['text'] for res in valid_results[:20]]
            report = f"🏛 *EXCHANGE: {ex_id.upper()}* ({now})\n" + "\n".join(report_lines)
            send_telegram(report)
            
    except Exception as e: print(f"⚠️ {ex_id} Error: {e}")
    finally: await ex_client.close()

async def run_loop():
    print(f"🚀 Bot Live. Scanning every {SCAN_INTERVAL}s...")
    while True:
        try:
            for ex_id in EXCHANGES:
                await scan_single_exchange(ex_id)
        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            await asyncio.sleep(10)
        await asyncio.sleep(SCAN_INTERVAL)

# --- MAIN ENTRY ---
async def main():
    # 1. Start Web Server for Render
    server = web.Application()
    server.router.add_get('/', handle_health)
    runner = web.AppRunner(server); await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"📡 Web Health Check listening on port {port}")

    # 2. Start the Bot Loop
    await run_loop()

if __name__ == "__main__":
    asyncio.run(main())
    
