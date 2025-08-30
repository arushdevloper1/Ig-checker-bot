import os, json, io, time, requests
import telebot
from telebot import types

# ====== CONFIG ======
BOT_TOKEN = "8307730688:AAHMwPKrBN1h5MCFrSLvnqa9Fp1pmU0L1To"
REQUIRED_CHANNEL = "@ARUSHESCROWS"   # bot ko is channel ka admin banao
ADMIN_ID = 0  # <- apna numeric Telegram ID daalo ( @userinfobot se milega )
PASS_KEYS_INITIAL = [
    "XR2J-7Q9M-PA6T-3LZD","V8KJ-2MFR-9TLA-Q5PX","QZ7N-43PM-L2VK-8RJD",
    "H9TB-M4QX-2ZLP-7AVC","P6DY-9QLR-T2XM-8JZW","L7FX-3ZQT-9KPB-2HVM",
    "N4VR-8WZL-5QTA-J2KM","A9QX-7LPM-3ZVD-6TRK","J5MW-2QZN-8VKL-4PRX","T8KV-5MQL-2RZN-9HWD"
]
PASS_KEY_PRICE = 20  # ₹
PASS_KEY_PROMPT = f"🔐 ENTER YOUR PASS KEY\n\nPass key price ₹{PASS_KEY_PRICE} (permanent)\nPurchase/Help: @ARUSH_XY\nLimited users: @arushgc_bot"
WELCOME_NOTE = "Join our channel first: https://t.me/ARUSHESCROWS"

# ====== BOT ======
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ====== PERSISTENCE (json files) ======
DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")     # {key: used_by or None}
USERS_FILE = os.path.join(DATA_DIR, "users.json")   # {user_id: verified_bool}

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return default
    return default

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

keys = load_json(KEYS_FILE, {})
users = load_json(USERS_FILE, {})

# seed initial keys once
if not keys:
    for k in PASS_KEYS_INITIAL:
        keys[k] = None
    save_json(KEYS_FILE, keys)

# ====== HELPERS ======
def is_member_of_required_channel(user_id: int) -> bool:
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["creator","administrator","member"]
    except Exception:
        # if channel check fails, block verification
        return False

def set_typing(chat_id):  # small UX touch
    try: bot.send_chat_action(chat_id, "typing")
    except: pass

def progress_edit(chat_id, msg_id, prefix, cur, total):
    pct = int((cur/total)*100) if total else 100
    bar_len = 12
    filled = int(bar_len * pct / 100)
    bar = "█"*filled + "░"*(bar_len-filled)
    txt = f"{prefix}\n\n{bar}  {pct}%"
    try: bot.edit_message_text(txt, chat_id, msg_id)
    except: pass

def clean_lines(text: str):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]

def instagram_status(username: str) -> str:
    """
    Accurate, username-only check.
    - 200 and NOT 'page isn't available' => active
    - 404 => suspended/deleted/not found
    - 200 + 'Sorry, this page isn't available.' => suspended/deleted
    """
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if r.status_code == 404:
            return "suspended"
        if r.status_code == 200:
            if "Sorry, this page isn't available" in r.text or "Page Not Found" in r.text:
                return "suspended"
            return "active"
        # Too many requests / other
        return "error"
    except:
        return "error"

def summarize_usernames(usernames, chat_id):
    total = len(usernames)
    active = suspended = error = 0

    # send processing message
    msg = bot.send_message(chat_id, "⏳ Processing usernames...\n\n░░░░░░░░░░░░  0%")
    for i, u in enumerate(usernames, start=1):
        set_typing(chat_id)
        status = instagram_status(u)
        if status == "active": active += 1
        elif status == "suspended": suspended += 1
        else: error += 1
        progress_edit(chat_id, msg.message_id, "⏳ Processing usernames...", i, total)
        time.sleep(0.15)  # small animation

    summary = (
        "<b>🎉 All Accounts Info 🎉</b>\n\n"
        "<b>📊 Summary:</b>\n"
        f"✨ Total Accounts Processed: <b>{total}/{total}</b>\n"
        f"✅ Available Accounts: <b>{active}</b>\n"
        f"❌ Suspended Accounts: <b>{suspended}</b>\n"
        f"⏱️ Errors/Unprocessed: <b>{error}</b>\n\n"
        "💡 Thank you for your patience!"
    )
    bot.edit_message_text(summary, chat_id, msg.message_id, parse_mode="HTML")

def extract_usernames_from_text(text: str):
    # allow raw usernames or lines like "id:pass" (we’ll only take the part before colon)
    out = []
    for ln in clean_lines(text):
        if ":" in ln:
            u = ln.split(":", 1)[0].strip()
        else:
            u = ln.strip()
        # strip leading @ and spaces
        u = u.lstrip("@ ")
        if u: out.append(u)
    return out

# ====== UI MARKUP ======
def menu_markup():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add(types.KeyboardButton("🔍 Check Accounts (Suspended/Active)"))
    return mk

# ====== HANDLERS ======
@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.from_user.id
    # Channel gate first
    if not is_member_of_required_channel(uid):
        bot.send_message(
            uid,
            f"🔒 Please join our channel to continue:\n{WELCOME_NOTE}\n\n"
            "After joining, send your pass key again."
        )
        return

    if users.get(str(uid)) is True:
        bot.send_message(uid, "✅ Verified! Choose an option:", reply_markup=menu_markup())
    else:
        bot.send_message(uid, PASS_KEY_PROMPT)

@bot.message_handler(commands=["stats"])
def cmd_stats(m):
    if ADMIN_ID and m.from_user.id == ADMIN_ID:
        total_keys = len(keys)
        used = sum(1 for v in keys.values() if v)
        total_users = sum(1 for v in users.values() if v)
        bot.reply_to(m, f"📈 Stats:\nKeys: {used}/{total_keys} used\nVerified Users: {total_users}")
    else:
        bot.reply_to(m, "❌ Not allowed.")

@bot.message_handler(commands=["addkeys"])
def cmd_addkeys(m):
    if ADMIN_ID and m.from_user.id == ADMIN_ID:
        # /addkeys KEY1 KEY2 ...
        parts = m.text.split()
        if len(parts) < 2:
            bot.reply_to(m, "Usage: <code>/addkeys KEY1 KEY2 ...</code>", parse_mode="HTML")
            return
        added = 0
        for k in parts[1:]:
            if k not in keys:
                keys[k] = None
                added += 1
        save_json(KEYS_FILE, keys)
        bot.reply_to(m, f"✅ Added {added} keys.")
    else:
        bot.reply_to(m, "❌ Not allowed.")

@bot.message_handler(content_types=["text"])
def on_text(m):
    uid = m.from_user.id
    txt = (m.text or "").strip()

    # Channel gate
    if not is_member_of_required_channel(uid):
        bot.send_message(uid, f"🔒 Join channel first:\n{WELCOME_NOTE}")
        return

    # If not verified yet, treat text as pass key
    if users.get(str(uid)) is not True:
        key = txt
        if key in keys and (keys[key] is None or keys[key] == uid):
            # bind key to this user (one-user-permanent)
            keys[key] = uid
            users[str(uid)] = True
            save_json(KEYS_FILE, keys)
            save_json(USERS_FILE, users)
            bot.send_message(uid, "✅ Pass key verified! Choose an option:", reply_markup=menu_markup())
        else:
            bot.send_message(uid, f"❌ Invalid/Already used key.\n{PASS_KEY_PROMPT}")
        return

    # Verified users area
    if txt == "🔍 Check Accounts (Suspended/Active)":
        bot.send_message(uid, "📂 Send usernames (one per line) or a .txt file.\n"
                              "Tip: You can also paste ID:PASS lines; bot will check only usernames.")
        return

    # treat incoming text as list
    usernames = extract_usernames_from_text(txt)
    if usernames:
        summarize_usernames(usernames, uid)
    else:
        bot.send_message(uid, "ℹ️ Send usernames list first or upload a .txt file.")

@bot.message_handler(content_types=["document"])
def on_doc(m):
    uid = m.from_user.id

    # Channel + verification checks
    if not is_member_of_required_channel(uid):
        bot.send_message(uid, f"🔒 Join channel first:\n{WELCOME_NOTE}")
        return
    if users.get(str(uid)) is not True:
        bot.send_message(uid, PASS_KEY_PROMPT)
        return

    # only .txt
    if not (m.document.file_name or "").lower().endswith(".txt"):
        bot.send_message(uid, "❌ Please upload a .txt file.")
        return

    file_info = bot.get_file(m.document.file_id)
    content = bot.download_file(file_info.file_path)
    try:
        text = content.decode("utf-8", errors="ignore")
    except:
        text = io.BytesIO(content).read().decode("utf-8", errors="ignore")

    usernames = extract_usernames_from_text(text)
    if not usernames:
        bot.send_message(uid, "❌ No usernames found in file.")
        return

    summarize_usernames(usernames, uid)

print("🤖 Bot running...")
bot.polling(none_stop=True, interval=0, timeout=20)
