import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

# --- AYARLAR ---
TOKEN = "8208237413:AAHX1YU-qmqUcMlG3AsKqZa8OoBORqCXNhc"
ADMIN_ID = 7896990912

bot = telebot.TeleBot(TOKEN)

# Render port hatasyny bejermek üçin Flask web serveri
app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Veritabanı Kurulumu
def init_db():
    conn = sqlite3.connect('vpn_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('sponsor', '')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('vpn_code', 'Henüz bir kod eklenmedi.')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('vpn_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def set_setting(key, value):
    conn = sqlite3.connect('vpn_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

user_states = {}
init_db()

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    sponsor = get_setting('sponsor')
    
    if user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_sponsor = types.InlineKeyboardButton("📢 Sponsor Kanal Ekle/Değiştir", callback_data="admin_sponsor")
        btn_code = types.InlineKeyboardButton("🔑 VPN Kodunu Değiştir", callback_data="admin_code")
        btn_show = types.InlineKeyboardButton("📋 Mevcut Ayarları Gör", callback_data="admin_show")
        btn_test = types.InlineKeyboardButton("🎁 Kodu Al (Test)", callback_data="check_sub")
        markup.add(btn_sponsor, btn_code, btn_show, btn_test)
        
        msg_text = f"<b>👑 Admin Paneli</b>\n\nMevcut Sponsor Kanal: <code>{sponsor if sponsor else 'Eklenmedi'}</code>"
        bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=markup)
        return

    check_user_sub(message.chat.id, user_id)

def check_user_sub(chat_id, user_id, message_id=None):
    sponsor = get_setting('sponsor')
    vpn_code = get_setting('vpn_code')

    if not sponsor:
        text = "⚠️ Bot şu anda bakımdadır (Sponsor kanal ayarlanmadı)."
        if message_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
        else:
            bot.send_message(chat_id, text)
        return

    try:
        member = bot.get_chat_member(chat_id=sponsor, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
    except Exception:
        is_member = False

    if is_member:
        text = f"✅ <b>Tebrikler! Kanala katıldığınız doğrulandı.</b>\n\n🔑 <b>VPN Kodunuz / Linkiniz:</b>\n<code>{vpn_code}</code>"
        if message_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="HTML")
        else:
            bot.send_message(chat_id, text, parse_mode="HTML")
    else:
        clean_channel = sponsor.replace("@", "")
        channel_link = f"https://t.me/{clean_channel}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_join = types.InlineKeyboardButton("📢 Sponsor Kanala Katıl", url=channel_link)
        btn_check = types.InlineKeyboardButton("✅ Katıldım, Kodu Ver", callback_data="check_sub")
        markup.add(btn_join, btn_check)
        
        text = "⚠️ <b>Kodu alabilmek için önce sponsor kanalımıza katılmalısınız!</b>\n\nLütfen aşağıdaki butondan kanala katılın ve ardından 'Katıldım' butonuna basın."
        
        if message_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id
    
    if call.data == "check_sub":
        check_user_sub(call.message.chat.id, user_id, call.message.message_id)
    elif call.data == "admin_sponsor" and user_id == ADMIN_ID:
        user_states[user_id] = "WAITING_SPONSOR"
        bot.send_message(call.message.chat.id, "Lütfen yeni sponsor kanalın kullanıcı adını yazın (Örnek: `@kanaladi`):")
    elif call.data == "admin_code" and user_id == ADMIN_ID:
        user_states[user_id] = "WAITING_CODE"
        bot.send_message(call.message.chat.id, "Lütfen kullanıcılara verilecek yeni VPN Kodunu / Linkini yazın:")
    elif call.data == "admin_show" and user_id == ADMIN_ID:
        sponsor = get_setting('sponsor')
        vpn_code = get_setting('vpn_code')
        bot.send_message(call.message.chat.id, f"📌 <b>Mevcut Ayarlar:</b>\n\n<b>Sponsor:</b> <code>{sponsor}</code>\n<b>VPN Kodu:</b> <code>{vpn_code}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def handle_admin_input(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip()
    
    if state == "WAITING_SPONSOR":
        if not text.startswith("@"):
            text = "@" + text
        set_setting('sponsor', text)
        del user_states[user_id]
        bot.send_message(message.chat.id, f"✅ Sponsor kanal güncellendi: <b>{text}</b>\n\n/start yazarak panele dönebilirsiniz.", parse_mode="HTML")
    elif state == "WAITING_CODE":
        set_setting('vpn_code', text)
        del user_states[user_id]
        bot.send_message(message.chat.id, f"✅ VPN Kodu/Link eklendi!\n\n/start yazarak panele dönebilirsiniz.")

if __name__ == '__main__':
    # Web serveri arka planda işledýäris (Render port talabyny ýatyrmak üçin)
    t = Thread(target=run_web)
    t.start()
    
    print("Bot we web server işe girizildi...")
    bot.infinity_polling()
