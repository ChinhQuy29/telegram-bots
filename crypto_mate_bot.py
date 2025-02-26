import os
from dotenv import load_dotenv
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import sqlite3
import logging

load_dotenv()

#Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("CRYPTO_MATE_BOT_TOKEN")

#SQLite database setup
conn = sqlite3.connect("crypto.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        coin TEXT,
        target_price REAL 
)            
""")
conn.commit()

def get_crypto_price(coin) -> int:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
    response = requests.get(url).json()
    return response[coin]["usd"]

def get_top(top) -> str:
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={top}&page=1"
    response = requests.get(url).json()
    list = "\n".join([f"{coin['market_cap_rank']}. {coin['name']} ({coin['symbol'].upper()})" for coin in response])
    return list

def add_alert(user_id, coin, target_price) -> None:
    cursor.execute("INSERT INTO alerts (user_id, coin, target_price) VALUES (?, ? ,?)", (user_id, coin, target_price))
    conn.commit()

def get_all_alerts(user_id):
    cursor.execute("SELECT id, coin, target_price FROM alerts WHERE user_id = ?", (user_id))
    return cursor.fetchall()

def delete_alert(alert_id, user_id) -> None:
    cursor.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
    conn.commit()

def get_coin_id(symbol) -> str:
    url = "https://api.coingecko.com/api/v3/coins/list"
    response = requests.get(url).json()
    symbol_to_id = {coin['symbol']: coin['id'] for coin in response}
    return symbol_to_id.get(symbol.lower())

async def start(update: Update, context: ContextTypes) -> None:
    await update.message.reply_text(
        "📝 Welcome to CryptoMate Bot!\n\n"
        "Commands:\n"
        "/price [coin] - Get coin's price in USD\n"   
        "/top [quantity] - Retrieve the top cryptocurrencies by market capitalization\n"  
        "/convert [amount] [from_coin] [to_currency] - Convert a specified amount from one cryptocurrency to another\n"
        "/alert [coin] [target_price] - Get notified when your coin reaches a target price\n"
    ) 

async def price(update: Update, context: ContextTypes) -> None:
    coin = " ".join(context.args)

    if not coin:
        await update.message.reply_text("❌ Usage: /get [coin]")
        return

    price = get_crypto_price(coin)
    if not price: 
        await update.message.reply_text("Invalid coin. Try the whole name, i.e. bitcoin or ethereum")
    else:
        await update.message.reply_text(f"{coin}: ${price}")

async def top(update: Update, context: ContextTypes) -> None:
    if not context.args:
        await update.message.reply_text("❌ Usage: /top [quantity]")
        return
    
    top = context.args[0]
    coin_list = get_top(top)
    await update.message.reply_text(f"Top {top} coin:\n{coin_list}")

async def convert(update: Update, context: ContextTypes) -> None:
    if len(context.args) != 3:
        await update.message.reply_text("❌ Usage: /convert [amount] [from] [to]\nExample: /convert 1 bitcoin usd")
        return

    try:
        amount = float(context.args[0])
        from_coin = context.args[1]
        to_currency = context.args[2]

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={from_coin}&vs_currencies={to_currency}"
        response = requests.get(url).json()
        if not response:
            await update.message.reply_text("Invalid source currency.\nExamples: bitcoin, ethereum, binancecoin, etc.")
            return

        if not response[from_coin]:
            await update.message.reply_text("Invalid currency pair.\nExample: bitcoin usd")
            return
    
        await update.message.reply_text(f"{amount} {from_coin.upper()} -> {amount * response[from_coin][to_currency]} {to_currency.upper()}")
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for the amount.")

async def alert(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /alert [coin] [target_price]\nExample: /alert bitcoin 100000")
        return
    
    coin = context.args[0]
    target_price = float(context.args[1])
    add_alert(user_id, coin, target_price)
    await update.message.reply_text(f"🔔 Alert set! You'll be notified when {coin.upper()} reaches ${target_price:.2f}.")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price)) 
    app.add_handler(CommandHandler("top", top))   
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("alert", alert))

    logger.info("Bot is running...")
    app.run_polling(poll_interval=1)