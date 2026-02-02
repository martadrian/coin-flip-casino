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

# MAJOR BASES: The bot will try to start and end its journey with any of these
MAJOR_BASES = ['USDT', 'USDC', 'BTC', 'ETH', 'SOL']

# INTERMEDIARIES: All coins that can act as the "middle" or "bridge" steps
INTERMEDIARIES = MAJOR_BASES + [
    'BNB', 'XRP', 'ADA', 'TRX', 'DOT', 'KCS', 'GT', 'OKB', 'FDUSD', 
    'MATIC', 'LINK', 'AVAX', 'LTC', 'BCH', 'SHIB', 'DAI'
]

MY_TZ = pytz.timezone('Africa/Lagos')
SCAN_INTERVAL = 60 # Time to wait between rotating to the next exchange

nest_asyncio.apply()

# --- UTILS ---
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

async def handle_health(request):
    """Keep-alive endpoint for Render"""
    return web.Response(text="Bot is Active")

# --- BOT LOGIC ---
async def get_all_triangular_paths(exchange):
    try:
        markets = await exchange.load_markets()
        paths = []
        for symbol, m in markets.items():
            if not m['active'] or '/' not in symbol: continue
            base, quote = symbol.split('/')
            
            if quote in MAJOR_BASES:
                alt = base
                for bridge in INTERMEDIARIES:
                    if bridge == quote or bridge == alt: continue
                    leg2, leg3 = f"{alt}/{bridge}", f"{bridge}/{quote}"
                    if leg2 in markets and leg3 in markets:
                        paths.append({
                            'start': quote, 'p1': symbol, 'p2': leg2, 
                            'p3': leg3, 'alt': alt, 'bridge': bridge
                        })
        return paths
    except: return []

async def scan_single_exchange(ex_id):
    # Using 'async with' ensures the connection is closed even if an error occurs
    try:
        async with getattr(ccxt, ex_id)({'enableRateLimit': True}) as ex_client:
            paths = await get_all_triangular_paths(ex_client)
            if not paths: return
            
            tickers = await ex_client.fetch_tickers()
            valid_results = []

            for p in paths:
                try:
                    p1, p2, p3 = tickers[p['p1']]['ask'], tickers[p['p2']]['bid'], tickers[p['p3']]['bid']
                    if not all([p1, p2, p3]) or p1 <= 0: continue
                    
                    final_amt = (1.0 / p1) * p2 * p3
                    profit_pct = (final_amt - 1.0) * 100
                    
                    if profit_pct > 0.05:
                        label = f"{p['start']}➔{p['alt']}➔{p['bridge']}➔{p['start']}"
                        valid_results.append({'text': f"✅ `{label}`: *+{profit_pct:.3f}%*", 'profit': profit_pct})
                except: continue

            if valid_results:
                valid_results = sorted(valid_results, key=lambda x: x['profit'], reverse=True)
                now = datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')
                report = f"🏛 *EXCHANGE: {ex_id.upper()}* ({now})\n" + "\n".join([r['text'] for r in valid_results[:20]])
                send_telegram(report)
    except Exception as e:
        print(f"⚠️ {ex_id} Scan Error: {e}")

async def run_loop():
    print(f"🚀 Rotational Bot Live. Interval: {SCAN_INTERVAL}s")
    
    exchange_index = 0
    num_exchanges = len(EXCHANGES)

    while True:
        try:
            # Select the current exchange from the list
            current_ex_id = EXCHANGES[exchange_index]
            print(f"🔄 [{datetime.datetime.now(MY_TZ).strftime('%H:%M:%S')}] Scanning: {current_ex_id.upper()}")
            
            # Execute the scan
            await scan_single_exchange(current_ex_id)
            
            # Update index to move to the next exchange next time
            exchange_index = (exchange_index + 1) % num_exchanges
            
        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            await asyncio.sleep(10)
            
        # Wait for the next minute before rotating
        await asyncio.sleep(SCAN_INTERVAL)

# --- MAIN ENTRY ---
async def main():
    server = web.Application()
    server.router.add_get('/', handle_health)
    runner = web.AppRunner(server); await runner.setup()
    
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"📡 Health check server live on port {port}")
    
    await run_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
