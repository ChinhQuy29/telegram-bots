import asyncio
import logging
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TASKY_BOT_TOKEN")

# SQLite Database Setup
conn = sqlite3.connect("todolist.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    task TEXT
)
""")

conn.commit()

def add_task(user_id, task):
    cursor.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (user_id, task))
    conn.commit()

def get_tasks(user_id):
    cursor.execute("SELECT id, task FROM tasks WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def delete_tasks(task_id, user_id):
    cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Welcome to To-Do Bot!\n\n"
        "Commands:\n"
        "/add [task] - Add a task\n"
        "/list - Show tasks\n"
        "/delete [task_id] - Delete a task"        
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    task_text = " ".join(context.args)

    if not task_text:
        await update.message.reply_text("X Usage: /add [task]")
        return  
    
    add_task(user_id, task_text)
    await update.message.reply_text(f"Task added: {task_text}")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id   
    tasks = get_tasks(user_id)

    if tasks:
        task_list = "\n".join([f"{task[0]}. {task[1]}" for task in tasks])
        await update.message.reply_text(f"Your To-Do List: \n{task_list}")
    else:
        await update.message.reply_text("No tasks found. Use /add to add a task.")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("X Usage: /delete [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
        delete_tasks(task_id, user_id)
        await update.message.reply_text(f"Task {task_id} deleted.")
    except ValueError:
        await update.message.reply_text("Invalid task ID.")

# async def main():


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("delete", delete))

    # Start
    logger.info("Bot is running...")
    app.run_polling(poll_interval=1)