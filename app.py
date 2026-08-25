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
TOKEN = "8994853122:AAGQkUeIxC-YN28w_haXSVEZVK2jFRZDgts"
OWNER_ID = 8619742582
PRICE_STARS = 20
STEAM_PRICE_STARS = 350
GIFT_COST = 15
GIFT_ID = "5170233102089322756"  # ЗАМЕНИТЕ НА ПРАВИЛЬНЫЙ ID МЕДВЕДЯ
# ================================

WAITING_FOR_RECIPIENT = 1

purchase_history = []
steam_orders = []  # Список заказов на роспись в Steam

SIGNATURES = [
    "Короля не убить",
    "3/2",
    "ебал в рот нижнюю сетку )"
]

logging.basicConfig(level=logging.INFO)

# ========== РАБОТА С ФАЙЛАМИ ДЛЯ STEAM ==========

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
            "Чтобы заказать, нажмите кнопку **'🎮 Роспись в Steam от Yatoro'** в меню."
        )
        return
    
    if not order.get('paid', False):
        await update.message.reply_text(
            f"⚠️ **У вас есть активный заказ, но он не оплачен!**\n\n"
            f"💰 Стоимость: {STEAM_PRICE_STARS} ⭐️\n\n"
            "Оплатите заказ, чтобы начать обработку.\n"
            "Используйте кнопку **'🎮 Роспись в Steam от Yatoro'** для оплаты."
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

async def handle_steam_link(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    steam_link = update.message.text.strip()
    
    order = next((o for o in steam_orders if o['user_id'] == user_id and o.get('paid', False)), None)
    
    if not order:
        await update.message.reply_text(
            "❌ У вас нет оплаченных заказов.\n\n"
            "Чтобы заказать, нажмите кнопку **'🎮 Роспись в Steam от Yatoro'** в меню."
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

# ========== ОСНОВНОЙ КОД ==========

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("🎮 Роспись в Steam от Yatoro", callback_data="buy_steam")]
    ]
    
    if update.effective_user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️!\n\n"
        f"💰 Обычная роспись: {PRICE_STARS} ⭐️\n"
        f"🎮 Роспись в Steam: {STEAM_PRICE_STARS} ⭐️\n\n"
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
        for i, p in enumerate(purchase_history, 1):
            history_text += (
                f"{i}. 👤 Покупатель: {p['buyer_name']} (@{p['buyer_username']})\n"
                f"   🎁 Получатель: {p['recipient_name']} (@{p['recipient_username']})\n"
                f"   📝 Подпись: {p['signature']}\n"
                f"   ⭐️ {p['price']} звёзд\n"
                f"   📊 Прибыль: {p['profit']} ⭐️\n"
                f"   🕐 {p['time']}\n\n"
            )
        
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
                description=f"Ваша позиция в очереди: {position}",
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Роспись в Steam", amount=STEAM_PRICE_STARS)],
                start_parameter="steam_purchase"
            )
            
            await query.edit_message_text(
                f"✅ **Вы выбрали роспись в Steam!**\n\n"
                f"🎮 Ваша позиция в очереди: **{position}**\n\n"
                f"💰 Стоимость: {STEAM_PRICE_STARS} ⭐️\n\n"
                f"⬆️ Оплатите счёт выше.\n\n"
                f"После оплаты укажите ссылку на ваш профиль Steam."
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        return
    
    # === ОБЫЧНАЯ РОСПИСЬ ===
    if data == "buy_for_self":
        context.user_data['recipient_id'] = user_id
        context.user_data['recipient_name'] = update.effective_user.full_name or "Неизвестный"
        context.user_data['recipient_username'] = update.effective_user.username or "нет_username"
        await show_signature_selection(query, user_id, "для себя")
        return
    
    if data == "buy_for_other":
        await query.edit_message_text(
            "✏️ Введите **username** получателя (с @ или без):\n\n"
            "Пример: `@yatoro` или `yatoro`\n\n"
            "⬇️ Напишите username в чат и отправьте."
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

async def show_main_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другому", callback_data="buy_for_other")],
        [InlineKeyboardButton("🎮 Роспись в Steam от Yatoro", callback_data="buy_steam")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("📜 История покупок", callback_data="show_history")])
    
    await query.edit_message_text(
        f"👋 Привет! Здесь ты можешь купить уникальную роспись от Яторо🖊️!\n\n"
        f"💰 Обычная роспись: {PRICE_STARS} ⭐️\n"
        f"🎮 Роспись в Steam: {STEAM_PRICE_STARS} ⭐️\n\n"
        f"📢 Телеграм канал: https://t.me/Yatorokale\n\n"
        f"Выбери вариант:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_recipient_input(update: Update, context: CallbackContext):
    username_input = update.message.text.strip()
    username_input = username_input.replace('@', '')
    
    search_msg = await update.message.reply_text("⏳ Поиск пользователя @{}...".format(username_input))
    
    try:
        try:
            recipient = await context.bot.get_chat(f"@{username_input}")
        except:
            try:
                recipient = await context.bot.get_chat(username_input)
            except:
                try:
                    recipient = await context.bot.get_chat(username_input)
                except:
                    raise Exception("Пользователь не найден")
        
        recipient_id = recipient.id
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
            f"🆔 ID: {recipient_id}\n\n"
            f"Теперь выбери подпись для подарка:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Ошибка поиска пользователя: {error_msg}")
        
        await search_msg.delete()
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        
        await update.message.reply_text(
            f"❌ **Пользователь @{username_input} не найден.**\n\n"
            f"Возможные причины:\n"
            f"• Такого username не существует\n"
            f"• Пользователь не имеет username\n"
            f"• Пользователь никогда не писал боту\n"
            f"• Пользователь заблокировал бота\n\n"
            f"**Решение:** попросите получателя написать боту любое сообщение (например /start), после этого бот сможет его найти.\n\n"
            f"Попробуйте снова или нажмите «Назад».",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_FOR_RECIPIENT

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Операция отменена.")
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
    
    # === ОБЫЧНАЯ РОСПИСЬ (МЕДВЕДЬ) ===
    if payload.startswith("gift_"):
        signature = context.user_data.get('selected_signature', 'Без подписи')
        recipient_id = context.user_data.get('recipient_id', user_id)
        recipient_name = context.user_data.get('recipient_name', user.full_name or "Неизвестный")
        recipient_username = context.user_data.get('recipient_username', user.username or "нет_username")
        
        try:
            # Отправляем подарок (медведя) с подписью
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
                f"✅ Роспись успешно отправлена!\n\n"
                f"🎁 Получатель: {recipient_name}\n"
                f"📝 Подпись: «{signature}»\n\n"
                f"⭐️ Оплачено: {PRICE_STARS} звёзд"
            )
            
        except Exception as e:
            error = str(e)
            if "STARGIFT_USAGE_LIMITED" in error:
                await update.message.reply_text("❌ Этот подарок уже распродан.")
            else:
                await update.message.reply_text(f"❌ Ошибка: {e}")
        return

def main():
    global steam_orders
    
    # Загружаем Steam заказы
    steam_orders = load_steam_orders()
    print(f"🎮 Загружено Steam заказов: {len(steam_orders)}")
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_for_other$")],
        states={
            WAITING_FOR_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipient_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("steam", steam_status))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_steam_link))
    
    # Запускаем проверку очереди каждую минуту
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_steam_orders, interval=60, first=10)
        print("⏰ Запущена проверка очереди (каждую минуту)")
    
    print("🤖 Бот запущен...")
    print(f"👤 Владелец: {OWNER_ID}")
    print(f"⭐️ Обычная цена: {PRICE_STARS} ⭐️")
    print(f"🎮 Steam цена: {STEAM_PRICE_STARS} ⭐️")
    print(f"🎁 ID подарка: {GIFT_ID}")
    print(f"🎮 Заказов в очереди: {len(steam_orders)}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()