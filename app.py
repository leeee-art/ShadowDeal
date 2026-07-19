import os
import threading
import time
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import re
import io
import random
import secrets
from datetime import datetime, timedelta
from collections import defaultdict

# ==================== КОНФИГ ====================
BOT_TOKEN = "8604759992:AAFkWPhe_5UBblzUJaBjSSXIp0Xoi7E2R8U"
ADMIN_ID = 6988163297
VIP_USER = 6532809507

API_URL = "https://deeptrekapi.onrender.com"
MASTER_KEY = "deeptrek_fjnrndhfrb2947472992gdvsbdh"
ACTIVATE_URL = "https://deeptrekapi.onrender.com/activate"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==================== РЕЖИМ ПОИСКА ====================
search_mode = {"bigbase": True}

# ==================== ВЕЧНАЯ ПОДПИСКА ====================
VIP_USERS = [6988163297, 5292684123]

def is_vip(user_id):
    return user_id in VIP_USERS

# ==================== ДАННЫЕ ====================
user_limits = defaultdict(int)
user_limit_override = {}
last_reset = datetime.now().date()
DEFAULT_LIMIT = 8

referrals = {}
referral_bonus = {}
REFERRAL_REWARD = 3
last_bonus_time = {}

hidden_data = []
promocodes = {}

subscriptions = {}

def generate_secret_key():
    return f"deeptrek_{secrets.token_hex(16)}"

def create_subscription(user_id, days):
    expires = datetime.now() + timedelta(days=days)
    secret_key = generate_secret_key()
    subscriptions[user_id] = {"expires": expires, "secret_key": secret_key, "active": True}
    return secret_key

def get_user_limit(user_id):
    if is_vip(user_id):
        return 999999
    if user_id in subscriptions and subscriptions[user_id]["active"]:
        if datetime.now() < subscriptions[user_id]["expires"]:
            return 999999
        else:
            subscriptions[user_id]["active"] = False
    if user_id == ADMIN_ID:
        return 999999
    if user_id == VIP_USER:
        return 100
    if user_id in user_limit_override:
        return user_limit_override[user_id]
    return DEFAULT_LIMIT + referral_bonus.get(user_id, 0)

def get_user_subscription(user_id):
    if is_vip(user_id):
        return {"active": True, "expires": "Вечная", "secret_key": "deeptrek_fjnrndhfrb2947472992gdvsbdh"}
    if user_id in subscriptions and subscriptions[user_id]["active"]:
        if datetime.now() < subscriptions[user_id]["expires"]:
            return {
                "active": True,
                "expires": subscriptions[user_id]["expires"].strftime('%Y-%m-%d %H:%M'),
                "secret_key": subscriptions[user_id]["secret_key"]
            }
        else:
            subscriptions[user_id]["active"] = False
    return {"active": False}

# ==================== AI-ЧАТ ====================
AI_CHAT_LIMITS = {}
AI_CHAT_LIMIT_DEFAULT = 5

def get_ai_chat_limit(user_id):
    today = datetime.now().date().isoformat()
    if user_id in subscriptions and subscriptions[user_id]["active"]:
        return {"allowed": True, "remaining": float('inf'), "limit": float('inf')}
    if is_vip(user_id):
        return {"allowed": True, "remaining": float('inf'), "limit": float('inf')}
    if user_id not in AI_CHAT_LIMITS or AI_CHAT_LIMITS[user_id]["date"] != today:
        AI_CHAT_LIMITS[user_id] = {"date": today, "count": 0}
    used = AI_CHAT_LIMITS[user_id]["count"]
    remaining = AI_CHAT_LIMIT_DEFAULT - used
    if remaining <= 0:
        return {"allowed": False, "remaining": 0, "limit": AI_CHAT_LIMIT_DEFAULT}
    return {"allowed": True, "remaining": remaining, "limit": AI_CHAT_LIMIT_DEFAULT}

def increment_ai_chat(user_id):
    today = datetime.now().date().isoformat()
    if user_id not in AI_CHAT_LIMITS or AI_CHAT_LIMITS[user_id]["date"] != today:
        AI_CHAT_LIMITS[user_id] = {"date": today, "count": 0}
    AI_CHAT_LIMITS[user_id]["count"] += 1

def get_ai_response(user_id, message):
    try:
        r = requests.post(
            f"{API_URL}/chat",
            headers={"X-API-Secret": MASTER_KEY},
            json={"messages": [{"role": "user", "content": message}]},
            timeout=30
        )
        if r.status_code == 200:
            return r.json().get("response", "❌ Не удалось получить ответ")
        else:
            return f"❌ Ошибка: {r.status_code}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

# ==================== МЕНЮ ====================
def main_menu(user_id=None):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔍 Поиск", callback_data="search"),
        InlineKeyboardButton("🎁 Бонус", callback_data="bonus")
    )
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="stats"),
        InlineKeyboardButton("🔗 Рефералка", callback_data="ref")
    )
    kb.add(
        InlineKeyboardButton("🎫 Промокод", callback_data="promo"),
        InlineKeyboardButton("🔑 Мой API", callback_data="my_api")
    )
    kb.add(
        InlineKeyboardButton("🧠 AI Чат", callback_data="ai_chat"),
        InlineKeyboardButton("📱 ТГ поиск", callback_data="tg_search")
    )
    kb.add(
        InlineKeyboardButton("⚙️ Режим поиска", callback_data="search_mode")
    )
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    )
    kb.add(
        InlineKeyboardButton("➕ Создать промокод", callback_data="admin_add_promo"),
        InlineKeyboardButton("📋 Промокоды", callback_data="admin_list_promos")
    )
    kb.add(
        InlineKeyboardButton("🗑️ Удалить промокод", callback_data="admin_delete_promo"),
        InlineKeyboardButton("👑 Выдать подписку", callback_data="admin_give_sub")
    )
    kb.add(
        InlineKeyboardButton("🎁 Выдать запросы", callback_data="admin_give_requests"),
        InlineKeyboardButton("📈 Топ запросов", callback_data="admin_top")
    )
    kb.add(
        InlineKeyboardButton("🔒 Скрыть данные", callback_data="admin_hide"),
        InlineKeyboardButton("📋 Скрытые данные", callback_data="admin_list_hidden")
    )
    kb.add(
        InlineKeyboardButton("🔓 Открыть данные", callback_data="admin_unhide"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")
    )
    kb.add(
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")
    )
    return kb

# ==================== ОБРАБОТЧИКИ ====================
@bot.message_handler(commands=['start'])
def start(m):
    args = m.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_id = int(args[1].replace("ref_", ""))
        if ref_id != m.chat.id and m.chat.id not in referrals.get(ref_id, []):
            if ref_id not in referrals:
                referrals[ref_id] = []
            referrals[ref_id].append(m.chat.id)
            referral_bonus[ref_id] = referral_bonus.get(ref_id, 0) + REFERRAL_REWARD
            bot.send_message(ref_id, f"🎉 По вашей ссылке зарегистрировался новый пользователь! +{REFERRAL_REWARD} запросов.")
            bot.send_message(m.chat.id, "✅ Вы зарегистрированы по реферальной ссылке!")
    
    bot.send_message(
        m.chat.id,
        "🔍 **DeepTrek Bot v8.0**\n\n"
        "Привет! Я помогаю искать информацию по открытым источникам.\n\n"
        "📱 Телефон — +79123456789\n"
        "✉️ Email — user@mail.ru\n"
        "👤 ФИО — Иванов Иван\n"
        "🏢 Компания — ООО Ромашка\n"
        "🔢 ИНН — 7712345678\n"
        "🔢 ОГРН — 1027700132195\n"
        "🪪 СНИЛС — 12345678900\n"
        "🪪 Паспорт — 1234 567890\n"
        "🚗 Госномер — А123ВС77\n"
        "🌐 IP — 8.8.8.8\n"
        "📱 Telegram — @username\n"
        "🔵 VK — id\n\n"
        "📊 Лимит: 8 запросов/день\n"
        "🎁 Бонус: +0-10 запросов раз в день\n"
        "🔗 Рефералка: +3 запроса за друга\n"
        "🎫 Промокод: увеличивает лимит или даёт подписку\n\n"
        "👇 Выберите действие:",
        parse_mode='Markdown',
        reply_markup=main_menu(m.chat.id)
    )

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.chat.id != ADMIN_ID:
        bot.send_message(m.chat.id, "❌ Доступ запрещён")
        return
    bot.send_message(m.chat.id, "👑 **Админ-панель**", parse_mode='Markdown', reply_markup=admin_menu())

# ==================== РЕЖИМ ПОИСКА ====================
@bot.callback_query_handler(func=lambda call: call.data == "search_mode")
def search_mode_menu(call):
    user_id = call.message.chat.id
    status = "✅ Включён" if search_mode["bigbase"] else "❌ Отключён"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(f"📦 BigBase: {status}", callback_data="toggle_bigbase"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")
    )
    
    bot.edit_message_text(
        "⚙️ **Режим поиска**\n\n"
        "Выбери источник для поиска:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "toggle_bigbase")
def toggle_bigbase(call):
    search_mode["bigbase"] = not search_mode["bigbase"]
    bot.answer_callback_query(call.id, f"BigBase {'включён' if search_mode['bigbase'] else 'отключён'}")
    search_mode_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(
        call.message.chat.id,
        "👑 **Главное меню**",
        parse_mode='Markdown',
        reply_markup=main_menu(call.message.chat.id)
    )

# ==================== ТГ ПОИСК ====================
@bot.callback_query_handler(func=lambda call: call.data == "tg_search")
def tg_search(call):
    bot.send_message(
        call.message.chat.id,
        "📱 **Поиск по Telegram**\n\n"
        "Введи команду:\n"
        "• `тг поиск - @username` — поиск по юзернейму\n"
        "• `тг фанстат - ID` — статистика по ID\n\n"
        "Примеры:\n"
        "`тг поиск - durov`\n"
        "`тг фанстат - 6988163297`",
        parse_mode='Markdown'
    )

# ==================== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ====================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.message.chat.id
    data = call.data
    
    if user_id != ADMIN_ID and data.startswith("admin_"):
        bot.answer_callback_query(call.id, "❌ Доступ запрещён")
        return
    
    # ===== ВЫБОР ДЛЯ НИКА/ФИО/КОМПАНИИ =====
    if data.startswith("username_") or data.startswith("telegram_") or data.startswith("vk_") or data.startswith("company_") or data.startswith("fio_") or data.startswith("passport_") or data.startswith("stats_"):
        parts = data.split("_", 1)
        search_type = parts[0]
        query = parts[1]
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"⏳ Поиск по '{query}' (тип: {search_type})...")
        
        result = search_api(query, search_type)
        
        if result["status"] == "ok":
            user_limits[user_id] += 1
            html = generate_html(result["data"], query, search_type)
            file_data = io.BytesIO(html.encode('utf-8'))
            
            bot.send_document(
                call.message.chat.id,
                (f"deeptrek_{query[:10]}.html", file_data),
                caption=f"📊 Отчёт по запросу: {query} ({search_type})",
                reply_markup=main_menu(user_id)
            )
        else:
            bot.send_message(call.message.chat.id, f"❌ {result['msg']}", reply_markup=main_menu(user_id))
        return
    
    # ===== AI ЧАТ =====
    if data == "ai_chat":
        limit_info = get_ai_chat_limit(user_id)
        
        if not limit_info["allowed"]:
            bot.send_message(
                user_id,
                f"❌ Лимит AI-чата исчерпан ({AI_CHAT_LIMIT_DEFAULT} запросов в день).\n\n"
                "🎫 **Подписка** даёт безлимитный доступ.",
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
            return
        
        remaining = limit_info["remaining"]
        if remaining != float('inf'):
            remaining_text = f"Осталось: {remaining} запросов"
        else:
            remaining_text = "♾️ Безлимит (подписка)"
        
        bot.send_message(
            user_id,
            f"🧠 **AI Чат**\n\n"
            f"📊 {remaining_text}\n\n"
            f"📌 Команды:\n"
            f"`/back` — вернуться в меню",
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
        bot.register_next_step_handler(call.message, process_ai_message)
        return
    
    # ===== ОБЫЧНЫЕ КНОПКИ =====
    if data == "search":
        bot.send_message(
            call.message.chat.id,
            "✏️ Введите данные для поиска:"
        )
        bot.register_next_step_handler(call.message, process_search)
    
    elif data == "bonus":
        now = datetime.now()
        if user_id in last_bonus_time and (now - last_bonus_time[user_id]).days < 1:
            bot.send_message(call.message.chat.id, "⏳ Ты уже получал бонус сегодня. Приходи завтра!")
            return
        bonus = random.randint(0, 10)
        user_limit_override[user_id] = user_limit_override.get(user_id, 0) + bonus
        last_bonus_time[user_id] = now
        bot.send_message(call.message.chat.id, f"🎁 Ты получил бонус: +{bonus} запросов!", reply_markup=main_menu(user_id))
    
    elif data == "stats":
        used = user_limits[user_id]
        limit = get_user_limit(user_id)
        sub_info = ""
        if is_vip(user_id):
            sub_info = "\n🔑 Подписка: Вечная\n📊 Лимит: ∞"
        elif user_id in subscriptions and subscriptions[user_id]["active"]:
            expires = subscriptions[user_id]["expires"].strftime('%Y-%m-%d %H:%M')
            sub_info = f"\n🔑 Подписка до: {expires}\n📊 Лимит: ∞"
        bot.send_message(
            call.message.chat.id,
            f"📊 **Твоя статистика**\n\n"
            f"📌 Запросов сегодня: {used}/{limit if limit != 999999 else '∞'}\n"
            f"👥 Приглашено: {len(referrals.get(user_id, []))}\n"
            f"🎁 Бонус: {referral_bonus.get(user_id, 0)} запросов"
            f"{sub_info}",
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    elif data == "ref":
        link = f"https://t.me/DeepTrekBot?start=ref_{user_id}"
        bot.send_message(
            call.message.chat.id,
            f"🔗 **Твоя реферальная ссылка**\n\n"
            f"`{link}`\n\n"
            f"📊 За каждого приглашённого ты получишь +{REFERRAL_REWARD} запроса!\n"
            f"👥 Приглашено: {len(referrals.get(user_id, []))}\n"
            f"🎁 Бонус: {referral_bonus.get(user_id, 0)} запросов",
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    elif data == "promo":
        bot.send_message(call.message.chat.id, "✏️ Введите промокод:")
        bot.register_next_step_handler(call.message, process_promo)
    
    elif data == "my_api":
        sub_info = get_user_subscription(user_id)
        
        if sub_info["active"]:
            text = f"""🔑 **Твой API доступ**

✅ Подписка активна
📅 Действует до: {sub_info['expires']}

🔐 **Секретный ключ:**
`{sub_info['secret_key']}`

🌐 **Активируй API здесь:**
{ACTIVATE_URL}

📌 После активации ты получишь API-ключ для использования в своих проектах."""
            bot.send_message(
                call.message.chat.id,
                text,
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
        else:
            text = """❌ **У тебя нет активной подписки**

Чтобы получить API доступ, активируй подписку через промокод.

🎫 Введи `.promo` или нажми кнопку «Промокод» в меню.

📌 После активации подписки здесь появится секретный ключ для API."""
            bot.send_message(
                call.message.chat.id,
                text,
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
    
    # ===== АДМИН =====
    if data == "admin_back":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, "👑 **Главное меню**", parse_mode='Markdown', reply_markup=main_menu(user_id))
    
    elif data == "admin_users":
        users_set = set(user_limits.keys()) | set(referral_bonus.keys()) | set(user_limit_override.keys()) | set(subscriptions.keys())
        total = len(users_set)
        with_sub = sum(1 for uid in users_set if uid in subscriptions and subscriptions[uid]["active"])
        vip_count = sum(1 for uid in users_set if is_vip(uid))
        
        text = f"""👥 **ПОЛЬЗОВАТЕЛИ**

📊 Всего: {total}
🔑 С подпиской: {with_sub}
👑 VIP: {vip_count}

📌 Последние 10 пользователей:
"""
        sorted_users = list(users_set)[-10:]
        for uid in sorted_users:
            try:
                user = bot.get_chat(uid)
                name = user.first_name or str(uid)
            except:
                name = str(uid)
            
            sub_status = "🔑" if uid in subscriptions and subscriptions[uid]["active"] else "⬜"
            vip_status = "👑" if is_vip(uid) else ""
            requests_count = user_limits.get(uid, 0)
            
            text += f"\n{sub_status} {vip_status} {name} — {requests_count} запросов"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )
    
    elif data == "admin_stats":
        total_users = len(set(user_limits.keys()) | set(referral_bonus.keys()) | set(user_limit_override.keys()) | set(subscriptions.keys()))
        total_requests = sum(user_limits.values())
        active_subs = sum(1 for sub in subscriptions.values() if sub["active"])
        total_promos = len(promocodes)
        total_hidden = len(hidden_data)
        
        text = f"""📊 **СТАТИСТИКА DeepTrek**

👥 Всего пользователей: {total_users}
📌 Запросов сегодня: {total_requests}
🔑 Активных подписок: {active_subs}
🎫 Промокодов: {total_promos}
🔒 Скрытых данных: {total_hidden}

📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )
    
    elif data == "admin_give_sub":
        bot.send_message(
            call.message.chat.id,
            "✏️ Введите данные для выдачи подписки:\n"
            "`user_id days`\n\n"
            "Пример: `123456789 30` — выдаст подписку на 30 дней"
        )
        bot.register_next_step_handler(call.message, process_give_sub)
    
    elif data == "admin_give_requests":
        bot.send_message(
            call.message.chat.id,
            "✏️ Введите данные для выдачи запросов:\n"
            "`user_id количество`\n\n"
            "Пример: `123456789 50` — выдаст 50 запросов"
        )
        bot.register_next_step_handler(call.message, process_give_requests)
    
    elif data == "admin_top":
        top_users = sorted(user_limits.items(), key=lambda x: x[1], reverse=True)[:10]
        
        if not top_users:
            bot.edit_message_text(
                "📭 Нет данных о запросах.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_menu()
            )
            return
        
        text = "📈 **ТОП-10 ПОЛЬЗОВАТЕЛЕЙ ПО ЗАПРОСАМ**\n\n"
        for i, (uid, count) in enumerate(top_users, 1):
            try:
                user = bot.get_chat(uid)
                name = user.first_name or str(uid)
            except:
                name = str(uid)
            text += f"{i}. {name} — {count} запросов\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )
    
    elif data == "admin_add_promo":
        bot.send_message(
            call.message.chat.id,
            "✏️ Формат промокода:\n"
            "`название тип значение`\n\n"
            "Типы:\n"
            "• `requests` — добавляет запросы (значение — число)\n"
            "• `subscription` — даёт подписку (значение — дни)\n\n"
            "Примеры:\n"
            "`BONUS10 requests 10`\n"
            "`SUBS30 subscription 30`"
        )
        bot.register_next_step_handler(call.message, process_add_promo)
    
    elif data == "admin_list_promos":
        if not promocodes:
            bot.edit_message_text(
                "📭 Нет промокодов.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_menu()
            )
        else:
            text = "📋 **Промокоды:**\n\n"
            for code, data in promocodes.items():
                text += f"🔑 {code} — {data['type']}: {data['value']}, использован: {len(data['users'])} раз\n"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=admin_menu()
            )
    
    elif data == "admin_delete_promo":
        if not promocodes:
            bot.edit_message_text(
                "📭 Нет промокодов.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_menu()
            )
            return
        text = "✏️ Введите название промокода для удаления:\n\n"
        for code in promocodes:
            text += f"• {code}\n"
        bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(call.message, process_delete_promo)
    
    elif data == "admin_hide":
        bot.send_message(call.message.chat.id, "✏️ Введите данные для скрытия:")
        bot.register_next_step_handler(call.message, process_hide_data)
    
    elif data == "admin_list_hidden":
        if not hidden_data:
            bot.edit_message_text(
                "📭 Нет скрытых данных.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_menu()
            )
        else:
            text = "🔒 **Скрытые данные:**\n\n"
            for i, item in enumerate(hidden_data, 1):
                text += f"{i}. {item}\n"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=admin_menu()
            )
    
    elif data == "admin_unhide":
        bot.send_message(call.message.chat.id, "✏️ Введите данные для открытия:")
        bot.register_next_step_handler(call.message, process_unhide_data)
    
    elif data == "admin_broadcast":
        bot.send_message(call.message.chat.id, "✏️ Введите текст для рассылки:")
        bot.register_next_step_handler(call.message, process_broadcast)

# ==================== ОБРАБОТЧИКИ АДМИН ====================
def process_give_sub(m):
    try:
        parts = m.text.strip().split()
        if len(parts) != 2:
            bot.send_message(m.chat.id, "❌ Неверный формат. Используй: `user_id days`")
            return
        
        user_id = int(parts[0])
        days = int(parts[1])
        
        secret_key = create_subscription(user_id, days)
        bot.send_message(
            m.chat.id,
            f"✅ Пользователю `{user_id}` выдана подписка на {days} дней.\n"
            f"🔑 Секретный ключ: `{secret_key}`",
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )
    except:
        bot.send_message(m.chat.id, "❌ Ошибка. Используй: `user_id days`")

def process_give_requests(m):
    try:
        parts = m.text.strip().split()
        if len(parts) != 2:
            bot.send_message(m.chat.id, "❌ Неверный формат. Используй: `user_id количество`")
            return
        
        user_id = int(parts[0])
        amount = int(parts[1])
        
        if amount <= 0:
            bot.send_message(m.chat.id, "❌ Количество должно быть больше 0")
            return
        
        user_limit_override[user_id] = user_limit_override.get(user_id, 0) + amount
        
        bot.send_message(
            m.chat.id,
            f"✅ Пользователю `{user_id}` выдано {amount} запросов.\n"
            f"📊 Теперь у него: {user_limit_override[user_id]} бонусных запросов",
            parse_mode='Markdown',
            reply_markup=admin_menu()
        )
    except ValueError:
        bot.send_message(m.chat.id, "❌ Ошибка. Используй: `user_id количество`")
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Ошибка: {str(e)}")

# ==================== ОБРАБОТЧИК AI СООБЩЕНИЙ ====================
def process_ai_message(m):
    user_id = m.chat.id
    text = m.text.strip()
    
    if text.lower() == "/back":
        bot.send_message(user_id, "👋 Возвращаюсь в меню.", reply_markup=main_menu(user_id))
        return
    
    if not text:
        bot.send_message(user_id, "❌ Введи сообщение.")
        bot.register_next_step_handler(m, process_ai_message)
        return
    
    limit_info = get_ai_chat_limit(user_id)
    if not limit_info["allowed"]:
        bot.send_message(
            user_id,
            f"❌ Лимит AI-чата исчерпан ({AI_CHAT_LIMIT_DEFAULT} запросов в день).",
            reply_markup=main_menu(user_id)
        )
        return
    
    bot.send_message(user_id, "⏳ Думаю...")
    response = get_ai_response(user_id, text)
    increment_ai_chat(user_id)
    
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            bot.send_message(user_id, response[i:i+4000], parse_mode='Markdown')
    else:
        bot.send_message(user_id, response, parse_mode='Markdown')
    
    bot.register_next_step_handler(m, process_ai_message)

# ==================== ПРОМОКОДЫ ====================
def process_promo(m):
    code = m.text.strip()
    user_id = m.chat.id
    
    if code not in promocodes:
        bot.send_message(m.chat.id, "❌ Неверный промокод.", reply_markup=main_menu(user_id))
        return
    
    promo = promocodes[code]
    
    if user_id in promo['users']:
        bot.send_message(m.chat.id, "❌ Вы уже активировали этот промокод.", reply_markup=main_menu(user_id))
        return
    
    promo['users'].append(user_id)
    
    if promo['type'] == 'requests':
        user_limit_override[user_id] = user_limit_override.get(user_id, 0) + promo['value']
        bot.send_message(m.chat.id, f"✅ Промокод активирован! +{promo['value']} запросов.", reply_markup=main_menu(user_id))
    
    elif promo['type'] == 'subscription':
        secret_key = create_subscription(user_id, promo['value'])
        
        text = f"""🎉 **Подписка активирована!**

📅 Действует: {promo['value']} дней
📊 Лимит: безлимит

🔑 **Секретный ключ:**
`{secret_key}`

🌐 **Активируй API здесь:**
{ACTIVATE_URL}

Введи секретный ключ на сайте, чтобы создать API-ключ для бота и сторонних сервисов."""
        
        bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=main_menu(user_id))

def process_add_promo(m):
    try:
        parts = m.text.strip().split()
        if len(parts) != 3:
            bot.send_message(m.chat.id, "❌ Неверный формат. Используй: `название тип значение`")
            return
        
        code, ptype, value = parts[0], parts[1], int(parts[2])
        
        if ptype not in ['requests', 'subscription']:
            bot.send_message(m.chat.id, "❌ Тип должен быть `requests` или `subscription`")
            return
        
        promocodes[code] = {"type": ptype, "value": value, "users": []}
        bot.send_message(m.chat.id, f"✅ Промокод `{code}` создан!\nТип: {ptype}\nЗначение: {value}", parse_mode='Markdown')
    except:
        bot.send_message(m.chat.id, "❌ Неверный формат. Используй: `название тип значение`")
    bot.send_message(m.chat.id, "Админ-панель", reply_markup=admin_menu())

def process_delete_promo(m):
    code = m.text.strip()
    if code in promocodes:
        del promocodes[code]
        bot.send_message(m.chat.id, f"✅ Промокод `{code}` удалён.")
    else:
        bot.send_message(m.chat.id, "❌ Промокод не найден.")
    bot.send_message(m.chat.id, "Админ-панель", reply_markup=admin_menu())

# ==================== СКРЫТИЕ ДАННЫХ ====================
def process_hide_data(m):
    data = m.text.strip()
    if data:
        hidden_data.append(data)
        bot.send_message(m.chat.id, f"✅ Данные `{data}` скрыты.")
    else:
        bot.send_message(m.chat.id, "❌ Неверный ввод.")
    bot.send_message(m.chat.id, "Админ-панель", reply_markup=admin_menu())

def process_unhide_data(m):
    data = m.text.strip()
    if data in hidden_data:
        hidden_data.remove(data)
        bot.send_message(m.chat.id, f"✅ Данные `{data}` открыты.")
    else:
        bot.send_message(m.chat.id, "❌ Таких данных нет.")
    bot.send_message(m.chat.id, "Админ-панель", reply_markup=admin_menu())

def process_broadcast(m):
    text = m.text.strip()
    if not text:
        bot.send_message(m.chat.id, "❌ Пустой текст")
        return
    
    users = set(user_limits.keys()) | set(referral_bonus.keys()) | set(user_limit_override.keys()) | set(subscriptions.keys())
    
    success = 0
    fail = 0
    
    bot.send_message(m.chat.id, f"📢 Начинаю рассылку для {len(users)} пользователей...")
    
    for uid in users:
        try:
            bot.send_message(uid, f"📢 **Объявление от администратора:**\n\n{text}", parse_mode='Markdown')
            success += 1
        except:
            fail += 1
    
    bot.send_message(
        m.chat.id,
        f"✅ Рассылка завершена!\n"
        f"📨 Доставлено: {success}\n"
        f"❌ Не доставлено: {fail}",
        reply_markup=admin_menu()
    )

# ==================== ПОИСК ====================
def search_api(query, search_type):
    headers = {
        "Content-Type": "application/json",
        "X-API-Secret": MASTER_KEY
    }
    data = {"query": query, "type": search_type}
    try:
        r = requests.post(f"{API_URL}/search", headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            return {"status": "ok", "data": r.json()}
        else:
            return {"status": "error", "msg": f"Код: {r.status_code}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def generate_html(data, query, search_type):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DeepTrek — {query}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0b0b1a; color: #e0e0e0; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #151528; border-radius: 16px; padding: 30px; border: 1px solid #2a2a4a; }}
        .header {{ text-align: center; margin-bottom: 25px; }}
        .logo {{ font-size: 32px; font-weight: 700; background: linear-gradient(135deg, #6c5ce7, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .info {{ color: #888; font-size: 14px; margin-top: 5px; }}
        .divider {{ border: none; height: 1px; background: linear-gradient(to right, transparent, #2a2a4a, transparent); margin: 20px 0; }}
        .json-container {{ background: #0e0e20; padding: 20px; border-radius: 12px; overflow-x: auto; border: 1px solid #2a2a4a; }}
        pre {{ font-family: 'Courier New', monospace; font-size: 13px; color: #c0c0c0; white-space: pre-wrap; word-break: break-all; }}
        .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔍 DeepTrek</div>
            <div class="info">Запрос: {query} | Тип: {search_type} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        <hr class="divider">
        <div class="json-container"><pre>{json_str}</pre></div>
        <div class="footer">DeepTrek © 2026 • OSINT инструмент</div>
    </div>
</body>
</html>'''
    return html

def detect_type(query):
    query = query.strip()
    if query.startswith('@'):
        return "telegram"
    if re.search(r'@', query):
        return "email"
    if re.match(r'^[78]\d{10}$', re.sub(r'\D', '', query)):
        return "phone"
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', query):
        return "ip"
    if re.match(r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$', query, re.IGNORECASE):
        return "auto"
    if re.match(r'^\d{10}$|^\d{12}$', query):
        return "inn"
    if re.match(r'^\d{13}$|^\d{15}$', query):
        return "ogrn"
    if re.match(r'^\d{11}$', re.sub(r'\D', '', query)):
        return "snils"
    if re.match(r'^\d+$', query):
        return "vk"
    if re.search(r'[а-яА-Я]', query):
        if len(query.split()) >= 2:
            return "fio"
        else:
            return "company"
    return "username"

def process_search(m):
    query = m.text.strip()
    if not query:
        bot.send_message(m.chat.id, "❌ Пустой запрос", reply_markup=main_menu(m.chat.id))
        return
    
    user_id = m.chat.id
    
    limit = get_user_limit(user_id)
    if user_limits[user_id] >= limit and limit != 999999 and user_id != ADMIN_ID and not is_vip(user_id):
        bot.send_message(m.chat.id, f"❌ Лимит {limit} запросов в день исчерпан.", reply_markup=main_menu(user_id))
        return
    
    search_type = detect_type(query)
    
    # ===== ЕСЛИ ID — предлагаем выбор =====
    if query.isdigit() and len(query) > 5:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🔵 VK", callback_data=f"vk_{query}"),
            InlineKeyboardButton("📱 Telegram", callback_data=f"telegram_{query}"),
            InlineKeyboardButton("🪪 Паспорт", callback_data=f"passport_{query}"),
            InlineKeyboardButton("📊 Funstat", callback_data=f"stats_{query}")
        )
        bot.send_message(
            m.chat.id,
            f"🔍 **{query}** — где ищем?",
            parse_mode='Markdown',
            reply_markup=kb
        )
        return
    
    # ===== ЕСЛИ ФИО — предлагаем выбор =====
    if search_type == "fio":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👤 ФИО", callback_data=f"fio_{query}"),
            InlineKeyboardButton("🏢 Компания", callback_data=f"company_{query}")
        )
        bot.send_message(
            m.chat.id,
            f"🔍 **{query}** — что ищем?",
            parse_mode='Markdown',
            reply_markup=kb
        )
        return
    
    # ===== ЕСЛИ НИК — предлагаем выбор =====
    if search_type == "username":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👤 Ник", callback_data=f"username_{query}"),
            InlineKeyboardButton("📱 Telegram", callback_data=f"telegram_{query}"),
            InlineKeyboardButton("🔵 VK", callback_data=f"vk_{query}")
        )
        bot.send_message(
            m.chat.id,
            f"🔍 **{query}** — что ищем?",
            parse_mode='Markdown',
            reply_markup=kb
        )
        return
    
    bot.send_message(m.chat.id, f"⏳ Поиск по '{query}' (тип: {search_type})...")
    
    result = search_api(query, search_type)
    
    if result["status"] == "ok":
        if user_id != ADMIN_ID and not is_vip(user_id):
            user_limits[user_id] += 1
        html = generate_html(result["data"], query, search_type)
        file_data = io.BytesIO(html.encode('utf-8'))
        bot.send_document(
            m.chat.id,
            (f"deeptrek_{query[:10]}.html", file_data),
            caption=f"📊 Отчёт по запросу: {query} ({search_type})",
            reply_markup=main_menu(user_id)
        )
    else:
        bot.send_message(m.chat.id, f"❌ {result['msg']}", reply_markup=main_menu(user_id))

# ==================== FLASK ДЛЯ RENDER ====================
@app.route('/')
def home():
    return "✅ DeepTrek Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

# ==================== ЗАПУСК БОТА В ФОНЕ ====================
def run_bot():
    print("🤖 DeepTrek Bot запущен")
    bot.infinity_polling()

# ==================== MAIN ====================
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask на порту Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
