import os
import asyncio
import logging
import json
import random
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ConversationHandler

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    TOKEN = "8994853122:AAGQkUeIxC-YN28w_haXSVEZVK2jFRZDgts"

OWNER_ID = 8619742582
PRICE_STARS = 20  # Обычная роспись
STEAM_PRICE_STARS = 350  # Роспись в Steam
GIFT_COST = 15
GIFT_ID = "5170233102089322756"  # ID медведя

# Каналы для подписки (НЕОБЯЗАТЕЛЬНО)
REQUIRED_CHANNELS = [
    {"name": "Yatorokale", "url": "https://t.me/Yatorokale", "chat_id": "@Yatorokale"},
    {"name": "Team Spirit Official", "url": "https://t.me/Team_Spirit_Official", "chat_id": "@Team_Spirit_Official"}
]
# ================================

WAITING_FOR_RECIPIENT = 1
purchase_history = []
steam_orders = []
users = []

# ========== ПОЛЬЗОВАТЕЛИ ==========
users = [
    1063566670, 1706296392, 6086019488, 818549482, 8179993565,
    5291915479, 1997847677, 5053531607, 7613664425, 1551895486,
    6666249677, 1671727568, 6806681335, 6278658617, 1497318161,
    2004469073, 6682950414, 561123453, 5826934033, 716129320,
    5284725069, 7611609480, 985393449, 2076260534, 8365386325,
    5197774712, 8537366273, 1434031010, 5564666822, 1819861991,
    6765046238, 7351012103, 8684381518
]

SIGNATURES = [
    "Короля не убить",
    "3/2",
    "ебал в рот нижнюю сетку )"
]

logging.basicConfig(level=logging.INFO)

# ========== РАБОТА С ФАЙЛАМИ ==========

def save_users():
    try:
        with open('users.txt', 'w', encoding='utf-8') as f:
            for user_id in users:
                f.write(f"{user_id}|imported|imported|{datetime.now()}\n")
    except:
        pass

def save_steam_orders():
    try:
        with open('steam_orders.json', 'w', encoding='utf-8') as f:
            json.dump(steam_orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения заказов: {e}")

def load_steam_orders():
    try:
        with open('steam_orders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_user(user_id, username, full_name):
    if user_id not in users:
        users.append(user_id)
        try:
            with open('users.txt', 'a', encoding='utf-8') as f:
                f.write(f"{user_id}|{username}|{full_name}|{datetime.now()}\n")
        except:
            pass
        return True
    return False

# ========== ПРОВЕРКА ПОДПИСКИ (НЕОБЯЗАТЕЛЬНАЯ) ==========

async def check_subscription(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    
    if user_id == OWNER_ID:
        return True
    
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(
                chat_id=channel['chat_id'],
                user_id=user_id
            )
            if chat_member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        keyboard = []
        for channel in not_subscribed:
            keyboard.append([InlineKeyboardButton(
                f"📢 Подписаться на {channel['name']} (НЕОБЯЗАТЕЛЬНО)",
                url=channel['url']
            )])
        
        keyboard.append([InlineKeyboardButton(
            "✅ Я подписался! Проверить",
            callback_data="check_subscription"
        )])
        keyboard.append([InlineKeyboardButton(
            "➡️ Пропустить и продолжить",
            callback_data="skip_subscription"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        channels_text = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        
        await update.message.reply_text(
            f"📢 **Подпишись на наши каналы (НЕОБЯЗАТЕЛЬНО)!**\n\n"
            f"🔥 Подпишись на:\n{channels_text}\n\n"
            f"🎁 Подписка даст тебе доступ к эксклюзивным предложениям!\n\n"
            f"Можешь пропустить и продолжить 👇",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return False
    
    return True

async def check_subscription_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id == OWNER_ID:
        try:
            await query.edit_message_text("✅ Вы владелец, доступ открыт!")
        except:
            pass
        return
    
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(
                chat_id=channel['chat_id'],
                user_id=user_id
            )
            if chat_member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        keyboard = []
        for channel in not_subscribed:
            keyboard.append([InlineKeyboardButton(
                f"📢 Подписаться на {channel['name']} (НЕОБЯЗАТЕЛЬНО)",
                url=channel['url']
            )])
        
        keyboard.append([InlineKeyboardButton(
            "✅ Я подписался! Проверить",
            callback_data="check_subscription"
        )])
        keyboard.append([InlineKeyboardButton(
            "➡️ Пропустить и продолжить",
            callback_data="skip_subscription"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        channels_text = "\n".join([f"• {ch['name']}" for ch in not_subscribed])
        
        try:
            await query.edit_message_text(
                f"📢 **Подпишись на наши каналы (НЕОБЯЗАТЕЛЬНО)!**\n\n"
                f"🔥 Подпишись на:\n{channels_text}\n\n"
                f"🎁 Подписка даст тебе доступ к эксклюзивным предложениям!\n\n"
                f"Можешь пропустить и продолжить 👇",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except:
            pass
        return
    
    try:
        await query.edit_message_text(
            "✅ **Спасибо за подписку!**\n\n"
            "🔥 Теперь вам доступны все функции бота!\n"
            "Нажмите /start чтобы продолжить."
        )
    except:
        pass

# ========== КОМАНДЫ ДЛЯ ВЛАДЕЛЬЦА ==========

async def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text(
            "✏️ Использование: /broadcast Текст сообщения",
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
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode='Markdown')
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.1)
    
    await status_msg.edit_text(
        f"✅ **Рассылка завершена!**\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Не доставлено: {fail}\n"
        f"👥 Всего пользователей: {len(users)}"
    )

async def stats(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    total_profit = sum(p['profit'] for p in purchase_history)
    steam_profit = sum(o.get('profit', 0) for o in steam_orders)
    
    await update.message.reply_text(
        f"📊 **Статистика бота**\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"🎁 Обычных росписей: {len(purchase_history)}\n"
        f"🎮 Steam росписей: {len(steam_orders)}\n"
        f"⭐️ Общая прибыль: {total_profit + steam_profit} ⭐️\n"
        f"💰 Steam заказов в очереди: {len(steam_orders)}"
    )

async def users_list(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    if not users:
        await update.message.reply_text("📭 Список пользователей пуст.")
        return
    
    text = "👥 **Список пользователей:**\n\n"
    for i, user_id in enumerate(users[:20], 1):
        text += f"{i}. ID: `{user_id}`\n"
    
    if len(users) > 20:
        text += f"\n... и еще {len(users) - 20} пользователей"
    
    text += f"\n\n📊 Всего: {len(users)} пользователей"
    await update.message.reply_text(text, parse_mode='Markdown')

async def add_user(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text("✏️ Использование: /adduser ID")
        return
    
    try:
        user_id = int(context.args[0])
        if user_id not in users:
            users.append(user_id)
            save_users()
            await update.message.reply_text(f"✅ Пользователь {user_id} добавлен!")
        else:
            await update.message.reply_text(f"⚠️ Пользователь {user_id} уже есть в списке.")
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")

async def add_users_batch(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text("✏️ Использование: /addusers ID1 ID2 ID3 ...")
        return
    
    added = 0
    for arg in context.args:
        try:
            user_id = int(arg)
            if user_id not in users:
                users.append(user_id)
                added += 1
        except:
            pass
    
    if added > 0:
        save_users()
    
    await update.message.reply_text(f"✅ Добавлено {added} пользователей!\n👥 Всего: {len(users)}")

async def test(update: Update, context: CallbackContext):
    await update.message.reply_text(f"✅ Бот работает! Твой ID: {update.effective_user.id}")

# ========== СИСТЕМА ОЧЕРЕДИ ДЛЯ STEAM ==========

def get_initial_position():
    return random.randint(400, 500)

async def check_steam_orders(context: CallbackContext):
    global steam_orders
    
    if not steam_orders:
        return
    
    now = datetime.now()
    orders_to_remove = []
    
    for i, order in enumerate(steam_orders):
        if order.get('paid', False) and order['position'] > 0:
            order['position'] -= 1
        
        if order.get('paid', False):
            created_at = datetime.fromisoformat(order['created_at'])
            if now - created_at >= timedelta(hours=24):
                try:
                    await context.bot.send_message(
                        chat_id=order['user_id'],
                        text="🎉 **РОСПИСЬ ДОСТАВЛЕНА!**\n\n"
                             "✅ Ваша роспись в Steam от Yatoro готова!\n"
                             "🔥 Поздравляем! Вы в числе избранных!"
                    )
                    orders_to_remove.append(i)
                except:
                    pass
    
    for i in sorted(orders_to_remove, reverse=True):
        steam_orders.pop(i)
    
    save_steam_orders()

async def steam_status(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    order = next((o for o in steam_orders if o['user_id'] == user_id), None)
    
    if not order:
        await update.message.reply_text(
            "❌ У вас нет активных заказов.\n\n"
            "Чтобы заказать, нажмите кнопку **'Роспись в Steam от Yatoro'** в меню."
        )
        return
    
    if not order.get('paid', False):
        await update.message.reply_text(
            f"⚠️ **У вас есть активный заказ, но он не оплачен!**\n\n"
            f"💰 Стоимость: {STEAM_PRICE_STARS} ⭐️\n\n"
            "Оплатите заказ, чтобы начать обработку.\n"
            "Используйте кнопку **'Роспись в Steam от Yatoro'** для оплаты."
        )
        return
    
    position = order['position']
    created_at = datetime.fromisoformat(order['created_at'])
    
    if position > 0:
        await update.message.reply_text(
            f"🎮 **Ваша позиция в очереди: {position}**\n\n"
            f"📅 Заказано: {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔥 Ожидайте! Ваша роспись скоро будет готова!"
        )
    else:
        await update.message.reply_text(
            "🎉 **ВАША РОСПИСЬ ГОТОВА!**\n\n"
            "✅ Ожидайте уведомление о доставке!"
        )

# ========== ОСНОВНОЙ КОД БОТА ==========

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    save_user(user.id, user.username or "нет_username", user.full_name or "Неизвестный")
    
    if not await check_subscription(update, context):
        return
    
    await show_main_menu_message(update.message, update.effective_user.id)

async def show_main_menu_message(message, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("🎮 Роспись в Steam от Yatoro", callback_data="buy_steam")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️!\n\n"
        f"💰 Обычная роспись: {PRICE_STARS} ⭐️\n"
        f"🎮 Роспись в Steam: {STEAM_PRICE_STARS} ⭐️\n\n"
        f"📢 Наши каналы (подписка НЕОБЯЗАТЕЛЬНА):\n"
        f"• https://t.me/Yatorokale\n"
        f"• https://t.me/Team_Spirit_Official\n\n"
        f"🔥 Подпишись и получай эксклюзивные предложения!\n\n"
        f"Выбери вариант:",
        reply_markup=reply_markup
    )

async def show_main_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("🎮 Роспись в Steam от Yatoro", callback_data="buy_steam")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️!\n\n"
        f"💰 Обычная роспись: {PRICE_STARS} ⭐️\n"
        f"🎮 Роспись в Steam: {STEAM_PRICE_STARS} ⭐️\n\n"
        f"📢 Наши каналы (подписка НЕОБЯЗАТЕЛЬНА):\n"
        f"• https://t.me/Yatorokale\n"
        f"• https://t.me/Team_Spirit_Official\n\n"
        f"🔥 Подпишись и получай эксклюзивные предложения!\n\n"
        f"Выбери вариант:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # ===== ПРОВЕРКА ПОДПИСКИ =====
    if data == "check_subscription":
        await check_subscription_callback(update, context)
        return
    
    if data == "skip_subscription":
        try:
            await query.edit_message_text(
                "✅ **Пропускаем подписку!**\n\n"
                "🔥 Но помни - подписка даёт доступ к эксклюзивным предложениям!\n"
                "Нажми /start чтобы продолжить."
            )
        except:
            pass
        await show_main_menu(query, user_id)
        return
    
    # ===== ИСТОРИЯ =====
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
                f"{i}. 👤 Покупатель: {p['buyer_name']} (@{p['buyer_username']})\n"
                f"   🎁 Получатель: {p['recipient_name']} (@{p['recipient_username']})\n"
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
    
    # === STEAM РОСПИСЬ ===
    if data == "buy_steam":
        existing = next((o for o in steam_orders if o['user_id'] == user_id), None)
        if existing:
            if existing.get('paid', False):
                await query.edit_message_text(
                    "❌ У вас уже есть оплаченный заказ!\n\n"
                    f"Ваша позиция в очереди: {existing['position']}\n"
                    "Используйте /steam для проверки статуса."
                )
            else:
                await query.edit_message_text(
                    "⚠️ У вас есть неоплаченный заказ!\n\n"
                    f"💰 Стоимость: {STEAM_PRICE_STARS} ⭐️\n\n"
                    "Оплатите его, чтобы начать обработку."
                )
            return
        
        position = get_initial_position()
        order = {
            'user_id': user_id,
            'position': position,
            'created_at': datetime.now().isoformat(),
            'profit': STEAM_PRICE_STARS - GIFT_COST,
            'paid': False,
            'steam_link': None
        }
        steam_orders.append(order)
        save_steam_orders()
        
        payload = f"steam_{user_id}_{GIFT_ID}"
        
        try:
            await context.bot.send_invoice(
                chat_id=user_id,
                title="🎮 Роспись в Steam от Yatoro",
                description="Оплатите заказ",
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Роспись в Steam", amount=STEAM_PRICE_STARS)],
                start_parameter="steam_purchase"
            )
            
            await query.edit_message_text(
                f"✅ **Вы выбрали роспись в Steam!**\n\n"
                f"💰 Стоимость: {STEAM_PRICE_STARS} ⭐️\n\n"
                f"⬆️ Оплатите счёт выше.\n\n"
                f"После оплаты укажите ссылку на ваш профиль Steam."
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        return
    
    # === ОБЫЧНАЯ РОСПИСЬ (из оригинального скрипта) ===
    if data == "buy_for_self":
        context.user_data['recipient_id'] = user_id
        context.user_data['recipient_name'] = update.effective_user.full_name or "Неизвестный"
        context.user_data['recipient_username'] = update.effective_user.username or "нет_username"
        await show_signature_selection(query, user_id, "для себя")
        return
    
    if data == "buy_for_other":
        await query.edit_message_text(
            "✏️ Введите **ID** пользователя, которому хотите подарить:\n\n"
            "📌 Пример: `8619742582`\n\n"
            "⬇️ Напишите ID в чат и отправьте.",
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
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await update.message.reply_text(
            f"❌ ID должен быть числом!\nПопробуйте снова:",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            f"🆔 ID: `{recipient_id}`\n\n"
            f"Теперь выбери подпись:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
        
    except Exception as e:
        await search_msg.delete()
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await update.message.reply_text(
            f"❌ Пользователь с ID {recipient_id} не найден.\nПопробуйте снова:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_FOR_RECIPIENT

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Операция отменена.")
    await show_main_menu_message(update.message, update.effective_user.id)
    return ConversationHandler.END

async def pre_checkout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    
    if query.invoice_payload.startswith("steam_"):
        if query.total_amount == STEAM_PRICE_STARS:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Неверная сумма.")
        return
    
    if query.invoice_payload.startswith("gift_"):
        if query.total_amount == PRICE_STARS:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Неверная сумма.")
        return
    
    await query.answer(ok=False, error_message="Что-то пошло не так.")

async def handle_steam_link(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    steam_link = update.message.text.strip()
    
    order = next((o for o in steam_orders if o['user_id'] == user_id and o.get('paid', False)), None)
    
    if not order:
        await update.message.reply_text(
            "❌ У вас нет оплаченных заказов.\n\n"
            "Чтобы заказать, нажмите кнопку **'Роспись в Steam от Yatoro'** в меню."
        )
        return
    
    order['steam_link'] = steam_link
    save_steam_orders()
    
    position = order['position']
    created_at = datetime.fromisoformat(order['created_at'])
    
    await update.message.reply_text(
        f"✅ **Ссылка на Steam принята!**\n\n"
        f"🎮 Ваша позиция в очереди: **{position}**\n\n"
        f"📅 Заказано: {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🔥 Ожидайте! Ваша роспись будет доставлена автоматически!"
    )

async def successful_payment(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = update.effective_user
    payload = update.message.successful_payment.invoice_payload
    
    # === STEAM РОСПИСЬ ===
    if payload.startswith("steam_"):
        order = next((o for o in steam_orders if o['user_id'] == user_id), None)
        if not order:
            await update.message.reply_text(
                "❌ Ошибка: заказ не найден. Обратитесь к @Yatorokale"
            )
            return
        
        order['paid'] = True
        save_steam_orders()
        
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🎮 НОВЫЙ ЗАКАЗ STEAM!\n\n"
                     f"👤 Покупатель: {user.full_name} (ID: {user_id})\n"
                     f"📊 Позиция: {order['position']}\n"
                     f"💰 {STEAM_PRICE_STARS} ⭐️"
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ **Оплата прошла успешно!**\n\n"
            f"🎮 Теперь отправьте ссылку на ваш профиль Steam:\n\n"
            f"📌 Пример: `https://steamcommunity.com/id/ваш_ник/`\n\n"
            f"Или: `https://steamcommunity.com/profiles/76561198000000000/`"
        )
        return
    
    # === ОБЫЧНАЯ РОСПИСЬ (из оригинального скрипта) ===
    if payload.startswith("gift_"):
        signature = context.user_data.get('selected_signature', 'Без подписи')
        recipient_id = context.user_data.get('recipient_id', user_id)
        recipient_name = context.user_data.get('recipient_name', user.full_name or "Неизвестный")
        recipient_username = context.user_data.get('recipient_username', user.username or "нет_username")
        
        try:
            # Отправляем подарок (медведя)
            await context.bot.send_gift(
                chat_id=recipient_id,
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
            
            # Уведомление владельцу
            try:
                buyer_info = f"@{user.username}" if user.username else f"ID: {user_id}"
                recipient_info = f"@{recipient_username}" if recipient_username != "нет_username" else f"ID: {recipient_id}"
                
                notification = (
                    f"🎁 НОВАЯ ПОКУПКА!\n\n"
                    f"👤 Покупатель: {user.full_name or 'Неизвестный'} ({buyer_info})\n"
                    f"🎁 Получатель: {recipient_name} ({recipient_info})\n"
                    f"📝 Подпись: {signature}\n"
                    f"💰 Стоимость: {PRICE_STARS} ⭐️\n"
                    f"📊 Прибыль: {profit} ⭐️\n"
                    f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                )
                
                await context.bot.send_message(chat_id=OWNER_ID, text=notification)
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление: {e}")
            
            await update.message.reply_text(
                f"✅ **Роспись успешно отправлена!**\n\n"
                f"🎁 Получатель: {recipient_name}\n"
                f"📝 Подпись: «{signature}»\n\n"
                f"⭐️ Оплачено: {PRICE_STARS} звёзд"
            )
            
        except Exception as e:
            error = str(e)
            logging.error(f"Ошибка при отправке подарка: {error}")
            
            if "STARGIFT_USAGE_LIMITED" in error:
                await update.message.reply_text("❌ Этот подарок уже распродан.")
            else:
                await update.message.reply_text(f"❌ Ошибка: {error}")
        return

# ========== ЗАПУСК БОТА ==========

def main():
    global steam_orders
    
    steam_orders = load_steam_orders()
    print(f"🎮 Загружено Steam заказов: {len(steam_orders)}")
    print(f"👥 Загружено пользователей: {len(users)}")
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_for_other$")],
        states={
            WAITING_FOR_RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipient_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(button_handler, pattern="^back_to_menu$")],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("steam", steam_status))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_steam_link))
    
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("users", users_list))
    application.add_handler(CommandHandler("adduser", add_user))
    application.add_handler(CommandHandler("addusers", add_users_batch))
    application.add_handler(CommandHandler("test", test))
    
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_steam_orders, interval=60, first=10)
        print("⏰ Запущена проверка очереди (каждую минуту)")
    
    print("🤖 Бот запущен...")
    print(f"👤 Владелец: {OWNER_ID}")
    print(f"⭐️ Обычная цена: {PRICE_STARS} ⭐️")
    print(f"🎮 Steam цена: {STEAM_PRICE_STARS} ⭐️")
    print(f"🎁 ID подарка: {GIFT_ID}")
    print(f"👥 Пользователей: {len(users)}")
    print(f"🎮 Заказов в очереди: {len(steam_orders)}")
    print("=" * 50)
    
    application.run_polling()

# ========== FLASK ДЛЯ RENDER ==========

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Бот работает!"

@flask_app.route('/health')
def health():
    return "OK"

if __name__ == "__main__":
    import threading
    
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    main()