import os
import threading
import logging
from datetime import datetime
from flask import Flask
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ConversationHandler

# ========== НАСТРОЙКИ ==========
# Берем токен из переменных окружения (безопасно!)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден! Добавь его в переменные окружения.")

OWNER_ID = 8619742582  # Твой ID
PRICE_STARS = 20
GIFT_COST = 15
GIFT_ID = "5170233102089322756"  # ЗАМЕНИТЕ
# ================================

WAITING_FOR_RECIPIENT = 1
purchase_history = []

SIGNATURES = [
    "Короля не убить",
    "3/2",
    "ебал в рот нижнюю сетку )"
]

logging.basicConfig(level=logging.INFO)

# ========== ТВОЙ КОД БОТА (без изменений) ==========

async def start(update: Update, context: CallbackContext):
    await show_main_menu_message(update.message, update.effective_user.id)

async def show_main_menu_message(message, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️ всего за {PRICE_STARS} ⭐️!\n\n"
        f"📢 Телеграм канал: https://t.me/Yatorokale\n\n"
        f"Выбери вариант:",
        reply_markup=reply_markup
    )

async def show_main_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️ всего за {PRICE_STARS} ⭐️!\n\n"
        f"📢 Телеграм канал: https://t.me/Yatorokale\n\n"
        f"Выбери вариант:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "show_history":
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ У вас нет доступа.")
            return
        
        if not purchase_history:
            await query.edit_message_text("📜 История пуста.")
            return
        
        history_text = "📜 ИСТОРИЯ ПОКУПОК:\n\n"
        total_profit = 0
        for i, p in enumerate(purchase_history, 1):
            history_text += (
                f"{i}. 👤 Покупатель: {p['buyer_name']} (ID: {p['buyer_id']})\n"
                f"   🎁 Получатель: {p['recipient_name']} (ID: {p['recipient_id']})\n"
                f"   📝 Подпись: {p['signature']}\n"
                f"   ⭐️ {p['price']} звёзд\n"
                f"   📊 Прибыль: {p['profit']} ⭐️\n"
                f"   🕐 {p['time']}\n\n"
            )
            total_profit += p['profit']
        
        history_text += f"📊 ОБЩАЯ ПРИБЫЛЬ: {total_profit} ⭐️"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if data == "back_to_menu":
        await show_main_menu(query, user_id)
        return
    
    if data == "buy_for_self":
        context.user_data['recipient_id'] = user_id
        context.user_data['recipient_name'] = update.effective_user.full_name or "Неизвестный"
        context.user_data['recipient_username'] = update.effective_user.username or "нет_username"
        await show_signature_selection(query, user_id, "для себя")
        return
    
    if data == "buy_for_other":
        await query.edit_message_text(
            "✏️ Введите **ID** пользователя, которому хотите подарить:\n\n"
            "Как узнать ID:\n"
            "1️⃣ Попросите пользователя написать боту: /start\n"
            "2️⃣ Бот пришлет его ID\n"
            "3️⃣ Или используйте бота @userinfobot\n\n"
            "📌 Пример: `8619742582`\n\n"
            "⬇️ Напишите ID в чат и отправьте.\n\n"
            "Или нажмите /cancel для отмены.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_RECIPIENT
    
    if data.startswith("sig_"):
        signature_index = int(data.replace("sig_", ""))
        signature = SIGNATURES[signature_index]
        context.user_data['selected_signature'] = signature
        
        recipient_id = context.user_data.get('recipient_id')
        recipient_name = context.user_data.get('recipient_name', 'Неизвестный')
        
        if not recipient_id:
            await query.edit_message_text("❌ Ошибка: получатель не найден.")
            return
        
        payload = f"gift_{user_id}_{GIFT_ID}"
        
        try:
            await context.bot.send_invoice(
                chat_id=user_id,
                title="🖊️ Роспись от Яторо",
                description=f"Для: {recipient_name}\nПодпись: {signature}",
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Роспись", amount=PRICE_STARS)],
                start_parameter="gift_purchase"
            )
            
            await query.edit_message_text(
                f"✅ Вы выбрали подпись:\n\n"
                f"📝 «{signature}»\n\n"
                f"🎁 Подарок для: {recipient_name}\n"
                f"🆔 ID: {recipient_id}\n"
                f"💰 Стоимость: {PRICE_STARS} ⭐️\n\n"
                f"⬆️ Оплатите счёт выше."
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        return

async def show_signature_selection(query, user_id, mode):
    keyboard = []
    for i, signature in enumerate(SIGNATURES):
        keyboard.append([InlineKeyboardButton(f"📝 {signature}", callback_data=f"sig_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    await query.edit_message_text(
        f"Выбери подпись для подарка ({mode}):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_recipient_input(update: Update, context: CallbackContext):
    input_text = update.message.text.strip()
    
    if not input_text.isdigit():
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="buy_for_other")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        
        await update.message.reply_text(
            f"❌ **Ошибка!**\n\n"
            f"Вы ввели: `{input_text}`\n\n"
            f"⚠️ ID должен быть **числом** (только цифры).\n\n"
            f"📌 Пример правильного ID: `8619742582`\n\n"
            f"Попробуйте снова:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return WAITING_FOR_RECIPIENT
    
    recipient_id = int(input_text)
    
    search_msg = await update.message.reply_text(f"⏳ Поиск пользователя с ID {recipient_id}...")
    
    try:
        recipient = await context.bot.get_chat(recipient_id)
        
        recipient_name = recipient.full_name or "Неизвестный"
        recipient_username = recipient.username or "нет_username"
        
        context.user_data['recipient_id'] = recipient_id
        context.user_data['recipient_name'] = recipient_name
        context.user_data['recipient_username'] = recipient_username
        
        await search_msg.delete()
        
        keyboard = []
        for i, signature in enumerate(SIGNATURES):
            keyboard.append([InlineKeyboardButton(f"📝 {signature}", callback_data=f"sig_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            f"✅ **Пользователь найден!**\n\n"
            f"👤 Имя: {recipient_name}\n"
            f"📱 Username: @{recipient_username if recipient_username != 'нет_username' else 'не указан'}\n"
            f"🆔 ID: `{recipient_id}`\n\n"
            f"Теперь выбери подпись для подарка:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
        
    except Exception as e:
        await search_msg.delete()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="buy_for_other")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        
        await update.message.reply_text(
            f"❌ **Пользователь с ID {recipient_id} не найден.**\n\n"
            f"⚠️ **Возможные причины:**\n"
            f"• Пользователь никогда не писал боту\n"
            f"• Неправильный ID\n"
            f"• Пользователь заблокировал бота\n\n"
            f"💡 **Как исправить:**\n"
            f"1️⃣ Попросите получателя написать боту: /start\n"
            f"2️⃣ После этого бот запомнит пользователя\n"
            f"3️⃣ Попробуйте снова\n\n"
            f"📌 Или используйте бота @userinfobot чтобы узнать свой ID\n\n"
            f"Попробуйте снова:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_FOR_RECIPIENT

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Операция отменена.")
    await show_main_menu_message(update.message, update.effective_user.id)
    return ConversationHandler.END

async def pre_checkout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("gift_") and query.total_amount == PRICE_STARS:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так.")

async def successful_payment(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = update.effective_user
    signature = context.user_data.get('selected_signature', 'Без подписи')
    
    recipient_id = context.user_data.get('recipient_id', user_id)
    recipient_name = context.user_data.get('recipient_name', user.full_name or "Неизвестный")
    recipient_username = context.user_data.get('recipient_username', user.username or "нет_username")
    
    try:
        try:
            test_user = await context.bot.get_chat(recipient_id)
        except Exception as e:
            logging.error(f"Ошибка проверки пользователя {recipient_id}: {e}")
            await update.message.reply_text(
                f"❌ **Ошибка!**\n\n"
                f"Получатель с ID {recipient_id} не найден.\n\n"
                f"⚠️ Возможно, пользователь:\n"
                f"• Никогда не писал боту\n"
                f"• Заблокировал бота\n"
                f"• Удалил аккаунт\n\n"
                f"💰 Деньги будут возвращены на ваш счет.\n"
                f"Свяжитесь с @Yatorokale для решения проблемы."
            )
            return
        
        await context.bot.send_gift(
            user_id=recipient_id,
            gift_id=GIFT_ID,
            text=signature
        )
        
        profit = PRICE_STARS - GIFT_COST
        purchase = {
            'buyer_id': user_id,
            'buyer_name': user.full_name or "Неизвестный",
            'buyer_username': user.username or "нет_username",
            'recipient_id': recipient_id,
            'recipient_name': recipient_name,
            'recipient_username': recipient_username,
            'signature': signature,
            'price': PRICE_STARS,
            'profit': profit,
            'time': datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        }
        purchase_history.append(purchase)
        
        try:
            notification = (
                f"🎁 НОВАЯ ПОКУПКА!\n\n"
                f"👤 Покупатель: {user.full_name or 'Неизвестный'} (ID: {user_id})\n"
                f"🎁 Получатель: {recipient_name} (ID: {recipient_id})\n"
                f"📝 Подпись: {signature}\n"
                f"💰 Стоимость: {PRICE_STARS} ⭐️\n"
                f"📊 Прибыль: {profit} ⭐️\n"
                f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            await context.bot.send_message(chat_id=OWNER_ID, text=notification)
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление: {e}")
        
        context.user_data.clear()
        
        await update.message.reply_text(
            f"✅ **Роспись успешно отправлена!**\n\n"
            f"🎁 Получатель: {recipient_name}\n"
            f"🆔 ID: {recipient_id}\n"
            f"📝 Подпись: «{signature}»\n\n"
            f"⭐️ Оплачено: {PRICE_STARS} звёзд\n\n"
            f"Чтобы купить ещё, нажмите /start"
        )
        
    except Exception as e:
        error = str(e)
        logging.error(f"Ошибка при отправке подарка: {error}")
        
        if "STARGIFT_USAGE_LIMITED" in error:
            await update.message.reply_text(
                f"❌ **Этот подарок уже распродан.**\n\n"
                f"Свяжитесь с @Yatorokale для решения проблемы."
            )
        elif "USER_NOT_FOUND" in error or "user not found" in error.lower():
            await update.message.reply_text(
                f"❌ **Получатель не найден!**\n\n"
                f"Пользователь с ID {recipient_id} не существует или не писал боту.\n\n"
                f"💡 Попросите получателя написать боту: /start\n"
                f"После этого повторите попытку."
            )
        else:
            await update.message.reply_text(f"❌ Ошибка: {error}")

def main():
    """Основная функция запуска бота"""
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern="^buy_for_other$")
        ],
        states={
            WAITING_FOR_RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipient_input)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(button_handler, pattern="^back_to_menu$")
        ],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    print("🤖 Бот запущен...")
    print(f"👤 Владелец: {OWNER_ID}")
    print(f"⭐️ Цена: {PRICE_STARS} звёзд")
    print(f"🎁 ID подарка: {GIFT_ID}")
    print(f"📝 Подписей: {len(SIGNATURES)}")
    print("=" * 50)
    
    # Запускаем бота
    app.run_polling()

# ========== НАСТРОЙКА ДЛЯ RENDER ==========

# Создаем Flask приложение
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Бот работает!"

@flask_app.route('/health')
def health():
    return "OK"

def run_bot():
    """Запускает бота в отдельном потоке"""
    main()

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True  # Поток завершится при остановке главного
    bot_thread.start()
    
    # Запускаем Flask сервер для Render
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port)