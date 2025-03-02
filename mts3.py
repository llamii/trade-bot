import ccxt
import pandas as pd
import time
import ta
import logging

API_KEY = ""
API_SECRET = ""

symbol = "BTC/USDT"
timeframe = "1m"
THRESHOLD = 0.5
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
LEVERAGE = 5
ORDER_SIZE = 0.01

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "future"},
    "test": True,
    "urls": {
        "api": {
            "public": "https://api-testnet.bybit.com",
            "private": "https://api-testnet.bybit.com"
        }
    }
})

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

initial_balance = None
last_trade = None


def check_balance():
    global initial_balance
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['total']

        if initial_balance is None:
            initial_balance = usdt_balance

        profit_loss = usdt_balance - initial_balance
        pnl_color = "⬆️" if profit_loss >= 0 else "⬇️"

        logging.info(
            f"💰 Current balance: {usdt_balance:.2f} USDT | {pnl_color} P&L: {profit_loss:.2f} USDT")
        return usdt_balance
    except Exception as e:
        logging.error(f"❌ Error fetching balance: {e}")
        return None


def fetch_ohlcv():
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        logging.info(f"📊 New OHLCV data at {df['timestamp'].iloc[-1]}")
        logging.info(
            f"🔎 Last closed prices: {df['close'].tail(5).tolist()}")
        return df
    except Exception as e:
        logging.error(f"❌ Error fetching OHLCV data: {e}")
        return None


def add_indicators(df):
    df["EMA_5"] = ta.trend.ema_indicator(df["close"], window=5)
    df["EMA_10"] = ta.trend.ema_indicator(df["close"], window=10)
    df["RSI"] = ta.momentum.rsi(df["close"], window=14)

    logging.info(
        f"📈 EMA_5: {df['EMA_5'].iloc[-1]:.2f}, EMA_10: {df['EMA_10'].iloc[-1]:.2f}, RSI: {df['RSI'].iloc[-1]:.2f}"
    )
    return df


def check_signals(df):
    global last_trade

    if df is None or df.empty:
        return None

    prev_ema5 = df["EMA_5"].iloc[-2]
    prev_ema10 = df["EMA_10"].iloc[-2]
    current_ema5 = df["EMA_5"].iloc[-1]
    current_ema10 = df["EMA_10"].iloc[-1]
    current_rsi = df["RSI"].iloc[-1]

    if last_trade == df["timestamp"].iloc[-1]:
        logging.info("⏳ Skipping, trade already executed on this candle")
        return None

    if current_rsi < RSI_OVERSOLD and current_ema5 > prev_ema5:
        logging.info(f"🟢 BUY signal detected (RSI: {current_rsi:.2f})")
        last_trade = df["timestamp"].iloc[-1]
        return "buy"

    if current_rsi > RSI_OVERBOUGHT and current_ema5 < prev_ema5:
        logging.info(f"🔴 SELL signal detected (RSI: {current_rsi:.2f})")
        last_trade = df["timestamp"].iloc[-1]
        return "sell"

    return None


def set_leverage():
    try:
        positions = exchange.fetch_positions()
        for position in positions:
            if position["symbol"] == symbol:
                current_leverage = position["leverage"]
                break
        else:
            current_leverage = None

        if current_leverage == LEVERAGE:
            logging.info(
                f"⚙️ Leverage already set to {LEVERAGE}x, skipping")
            return

        exchange.private_post_v5_position_set_leverage({
            "category": "linear",
            "symbol": symbol.replace("/", ""),
            "buyLeverage": str(LEVERAGE),
            "sellLeverage": str(LEVERAGE)
        })
        logging.info(f"⚙️ Leverage successfully set to {LEVERAGE}x")

    except Exception as e:
        logging.error(f"❌ Error setting leverage: {e}")


def place_order(side, amount=ORDER_SIZE):
    try:
        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side=side,
            amount=amount,
            params={"category": "linear", "reduceOnly": False}
        )
        logging.info(f"📌 Order placed: {side.upper()} {amount} BTC")
        check_balance()
        return order
    except Exception as e:
        logging.error(f"❌ Error placing order: {e}")


set_leverage()

while True:
    check_balance()
    df = fetch_ohlcv()
    if df is not None:
        df = add_indicators(df)
        signal = check_signals(df)

        if signal:
            place_order(signal)

    time.sleep(15)
