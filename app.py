import os
import asyncio
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
GIFT_ID = "SIMPLE_BEAR_ID"  # ЗАМЕНИТЕ
# ================================

WAITING_FOR_RECIPIENT = 1
purchase_history = []
users = []  # Список ID пользователей для рассылки

SIGNATURES = [
    "Короля не убить",
    "3/2",
    "ебал в рот нижнюю сетку )"
]

logging.basicConfig(level=logging.INFO)

# ========== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ ==========

def load_users():
    """Загружает пользователей из файла"""
    try:
        with open('users.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    user_id = int(line.split('|')[0])
                    if user_id not in users:
                        users.append(user_id)
        print(f"👥 Загружено {len(users)} пользователей")
    except FileNotFoundError:
        print("📁 Файл users.txt не найден, создаю новый...")

def save_user(user_id, username, full_name):
    """Сохраняет нового пользователя"""
    if user_id not in users:
        users.append(user_id)
        try:
            with open('users.txt', 'a', encoding='utf-8') as f:
                f.write(f"{user_id}|{username}|{full_name}|{datetime.now()}\n")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить пользователя: {e}")
        return True
    return False

# ========== КОМАНДЫ ДЛЯ ВЛАДЕЛЬЦА ==========

async def broadcast(update: Update, context: CallbackContext):
    """Рассылка всем пользователям (только для владельца)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text(
            "✏️ **Как использовать:**\n"
            "`/broadcast Текст сообщения`\n\n"
            "📌 Можно использовать Markdown:\n"
            "`/broadcast *Жирный текст*`\n"
            "`/broadcast _Курсив_`\n"
            "`/broadcast [Ссылка](https://t.me/Yatorokale)`",
            parse_mode='Markdown'
        )
        return
    
    if not users:
        await update.message.reply_text("❌ Список пользователей пуст!")
        return
    
    status_msg = await update.message.reply_text(f"⏳ Рассылка {len(users)} пользователям...")
    
    success = 0
    fail = 0
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='Markdown'
            )
            success += 1
        except Exception as e:
            fail += 1
            print(f"❌ Не удалось отправить {user_id}: {e}")
        await asyncio.sleep(0.1)  # Защита от лимитов Telegram
    
    await status_msg.edit_text(
        f"✅ **Рассылка завершена!**\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Не доставлено: {fail}\n"
        f"👥 Всего пользователей: {len(users)}"
    )

async def stats(update: Update, context: CallbackContext):
    """Статистика бота (только для владельца)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    total_profit = sum(p['profit'] for p in purchase_history)
    avg_profit = total_profit / len(purchase_history) if purchase_history else 0
    
    await update.message.reply_text(
        f"📊 **Статистика бота**\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"🎁 Продано подарков: {len(purchase_history)}\n"
        f"⭐️ Общая прибыль: {total_profit} ⭐️\n"
        f"💰 Средняя прибыль: {avg_profit:.1f} ⭐️\n"
        f"📈 Всего продаж: {len(purchase_history)}"
    )

async def users_list(update: Update, context: CallbackContext):
    """Список всех пользователей (только для владельца)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    if not users:
        await update.message.reply_text("📭 Список пользователей пуст.")
        return
    
    # Показываем первых 20 пользователей
    text = "👥 **Список пользователей:**\n\n"
    for i, user_id in enumerate(users[:20], 1):
        text += f"{i}. ID: `{user_id}`\n"
    
    if len(users) > 20:
        text += f"\n... и еще {len(users) - 20} пользователей"
    
    text += f"\n\n📊 Всего: {len(users)} пользователей"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def import_users_file(update: Update, context: CallbackContext):
    """Импортирует пользователей из файла users_old.txt (только для владельца)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    status_msg = await update.message.reply_text("⏳ Импорт пользователей из файла...")
    
    try:
        imported = 0
        already = 0
        invalid = 0
        
        # Проверяем существование файла
        try:
            with open('users_old.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            await status_msg.edit_text(
                "❌ **Файл users_old.txt не найден!**\n\n"
                "Как создать файл:\n"
                "1. Создай файл users_old.txt в папке с ботом\n"
                "2. Вставь ID пользователей (по одному на строку)\n"
                "3. Отправь на GitHub и сделай деплой\n"
                "4. Запусти /import снова"
            )
            return
        
        if not lines:
            await status_msg.edit_text("❌ Файл users_old.txt пуст!")
            return
        
        # Обрабатываем каждую строку
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Проверяем, что это число
            if not line.isdigit():
                invalid += 1
                continue
            
            user_id = int(line)
            
            # Проверяем, есть ли уже в списке
            if user_id not in users:
                users.append(user_id)
                imported += 1
            else:
                already += 1
        
        # Сохраняем в основной файл
        if imported > 0:
            try:
                with open('users.txt', 'a', encoding='utf-8') as f:
                    for user_id in users[-imported:]:
                        f.write(f"{user_id}|imported|imported|{datetime.now()}\n")
            except Exception as e:
                print(f"Ошибка сохранения: {e}")
        
        await status_msg.edit_text(
            f"✅ **Импорт завершен!**\n\n"
            f"📥 Всего строк в файле: {len(lines)}\n"
            f"➕ Добавлено новых: {imported}\n"
            f"⚠️ Уже были в списке: {already}\n"
            f"❌ Неверных ID: {invalid}\n"
            f"👥 Всего пользователей: {len(users)}\n\n"
            f"Теперь используй /broadcast для рассылки!"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def add_user(update: Update, context: CallbackContext):
    """Добавляет одного пользователя по ID (только для владельца)"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "✏️ Использование: /adduser ID\n"
            "Пример: /adduser 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
        if user_id not in users:
            users.append(user_id)
            with open('users.txt', 'a', encoding='utf-8') as f:
                f.write(f"{user_id}|manual|manual|{datetime.now()}\n")
            await update.message.reply_text(f"✅ Пользователь {user_id} добавлен!\n👥 Всего: {len(users)}")
        else:
            await update.message.reply_text(f"⚠️ Пользователь {user_id} уже есть в списке.")
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")

# ========== ОСНОВНОЙ КОД БОТА ==========

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    save_user(user.id, user.username or "нет_username", user.full_name or "Неизвестный")
    await show_main_menu_message(update.message, update.effective_user.id)

async def show_main_menu_message(message, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("📢 Подписаться на новости", callback_data="subscribe")]
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
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("📢 Подписаться на новости", callback_data="subscribe")]
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
    
    if data == "subscribe":
        if user_id not in users:
            users.append(user_id)
            try:
                with open('users.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{user_id}|{update.effective_user.username or 'нет_username'}|{update.effective_user.full_name or 'Неизвестный'}|{datetime.now()}\n")
            except:
                pass
            await query.edit_message_text("✅ Вы подписались на новости бота!")
        else:
            await query.edit_message_text("✅ Вы уже подписаны на новости!")
        return
    
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
    # Загружаем пользователей
    load_users()
    
    application = Application.builder().token(TOKEN).build()
    
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
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Команды для владельца
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("users", users_list))
    application.add_handler(CommandHandler("import", import_users_file))
    application.add_handler(CommandHandler("adduser", add_user))
    
    print("🤖 Бот запущен...")
    print(f"👤 Владелец: {OWNER_ID}")
    print(f"⭐️ Цена: {PRICE_STARS} звёзд")
    print(f"🎁 ID подарка: {GIFT_ID}")
    print(f"📝 Подписей: {len(SIGNATURES)}")
    print(f"👥 Пользователей: {len(users)}")
    print("=" * 50)
    
    # Запускаем бота
    application.run_polling()

# ========== НАСТРОЙКА ДЛЯ RENDER ==========

# Создаем Flask приложение для health check
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Бот работает!"

@flask_app.route('/health')
def health():
    return "OK"

if __name__ == "__main__":
    # Запускаем бота в ГЛАВНОМ потоке
    # Запускаем Flask в отдельном потоке для health check
    import threading
    
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота в главном потоке
    main()