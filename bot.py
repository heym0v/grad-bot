import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

SONG_FILE = "songs.txt"
original_songs = []
normalized_songs = set()

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

def normalize_song(song: str) -> str:
    cleaned = re.sub(r'[^\w\s]', '', song.lower())
    words = sorted(cleaned.split())
    return ' '.join(words)

def load_songs():
    if os.path.exists(SONG_FILE):
        with open(SONG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                song = line.strip()
                if song:
                    original_songs.append(song)
                    normalized_songs.add(normalize_song(song))

def save_songs():
    with open(SONG_FILE, "w", encoding="utf-8") as f:
        for song in original_songs:
            f.write(song + "\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📃 Показать все песни", callback_data="show_songs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Отправь сюда песню, а я проверю, есть ли она. Или нажми кнопку, чтобы посмотреть список уже предложенных.",
        reply_markup=reply_markup,
    )

async def handle_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    song = update.message.text.strip()

    if '-' in song:
        await update.message.reply_text("Пожалуйста, не используй тире (-) в названии песни.")
        return

    normalized = normalize_song(song)

    if normalized in normalized_songs:
        await update.message.reply_text("Эта песня уже была предложена. Попробуй другую.")
    else:
        normalized_songs.add(normalized)
        original_songs.append(song)
        save_songs()
        await update.message.reply_text("Спасибо! Песня принята.")
        sender = update.message.from_user
        sender_name = f"@{sender.username}" if sender.username else sender.first_name
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Новая песня от {sender_name}: {song}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_songs":
        if original_songs:
            text = "🎶 Уже предложенные песни:\n\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(original_songs))
        else:
            text = "Пока что нет предложенных песен."
        await query.edit_message_text(text=text)

async def delete_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Удалять песни может только администратор.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи номер песни, которую хочешь удалить.")
        return

    try:
        index = int(context.args[0]) - 1
        if 0 <= index < len(original_songs):
            removed_song = original_songs.pop(index)
            normalized_songs.remove(normalize_song(removed_song))
            save_songs()
            await update.message.reply_text(f"Песня '{removed_song}' удалена.")
        else:
            await update.message.reply_text("Песня с таким номером не найдена.")
    except ValueError:
        await update.message.reply_text("Укажи номер песни (например: /delete 3)")

if __name__ == '__main__':
    load_songs()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("delete", delete_song))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_song))

    print("Бот запущен.")
    app.run_polling()

