# MannKaMeet - Telegram Dating/Friendship Bot (Text-only Profiles)
# Author: Divya (with ChatGPT)

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import os

# ====== SETUP =======
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
MONGO_URI = os.getenv("MONGO_URI") or "YOUR_MONGODB_URI_HERE"

bot = telebot.TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['mannkameet']
users = db['users']
likes = db['likes']

# ====== UTILITIES =======
def get_user(user_id):
    return users.find_one({"_id": user_id})

def save_user_step(user_id, data):
    users.update_one({"_id": user_id}, {"$set": data}, upsert=True)

def find_match(user):
    query = {
        "_id": {"$ne": user["_id"]},
        "gender": {"$in": user.get("interested_in", ["M", "F", "Other"])}
    }
    return users.find_one(query)

# ====== BOT HANDLERS =======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "\U0001F3F3 Welcome to *MannKaMeet*!\n\nLet's set up your profile.", parse_mode='Markdown')
    bot.send_message(message.chat.id, "What's your name?")
    bot.register_next_step_handler(message, ask_gender)

def ask_gender(message):
    name = message.text.strip()
    save_user_step(message.from_user.id, {"_id": message.from_user.id, "name": name})
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Male", callback_data="gender_M"))
    markup.add(InlineKeyboardButton("Female", callback_data="gender_F"))
    markup.add(InlineKeyboardButton("Other", callback_data="gender_Other"))
    bot.send_message(message.chat.id, "Select your gender:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("gender_"))
def set_gender(call):
    gender = call.data.split("_")[1]
    users.update_one({"_id": call.from_user.id}, {"$set": {"gender": gender}})
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Male", callback_data="interested_M"))
    markup.add(InlineKeyboardButton("Female", callback_data="interested_F"))
    markup.add(InlineKeyboardButton("All", callback_data="interested_All"))
    bot.edit_message_text("Who are you interested in?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("interested_"))
def set_interest(call):
    val = call.data.split("_")[1]
    val = [val] if val != "All" else ["M", "F", "Other"]
    users.update_one({"_id": call.from_user.id}, {"$set": {"interested_in": val}})
    bot.send_message(call.message.chat.id, "What is your age?")
    bot.register_next_step_handler(call.message, ask_age)

def ask_age(message):
    try:
        age = int(message.text.strip())
        users.update_one({"_id": message.from_user.id}, {"$set": {"age": age}})
        bot.send_message(message.chat.id, "Which city/state are you from?")
        bot.register_next_step_handler(message, ask_location)
    except:
        bot.send_message(message.chat.id, "Please enter a valid number for age.")
        bot.register_next_step_handler(message, ask_age)

def ask_location(message):
    loc = message.text.strip()
    users.update_one({"_id": message.from_user.id}, {"$set": {"location": loc}})
    bot.send_message(message.chat.id, "Write a short bio about yourself:")
    bot.register_next_step_handler(message, ask_bio)

def ask_bio(message):
    bio = message.text.strip()
    users.update_one({"_id": message.from_user.id}, {"$set": {"bio": bio}})
    bot.send_message(message.chat.id, "\u2705 Profile created successfully!\n\nUse /startmatch to meet people.")

# ====== MATCH SYSTEM =======
@bot.message_handler(commands=['startmatch'])
def start_match(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "Please set up your profile using /start")
        return
    match = find_match(user)
    if not match:
        bot.send_message(message.chat.id, "No matches found right now. Please try again later.")
        return

    msg = f"👤 *{match['name']}*\n🎂 {match['age']} yrs\n📍 {match['location']}\n📝 {match['bio']}"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👍 Like", callback_data=f"like_{match['_id']}"))
    markup.add(InlineKeyboardButton("👎 Skip", callback_data="skip"))
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("like_"))
def handle_like(call):
    liked_id = int(call.data.split("_")[1])
    liker_id = call.from_user.id
    likes.insert_one({"from": liker_id, "to": liked_id})
    # Check if mutual
    if likes.find_one({"from": liked_id, "to": liker_id}):
        liked_user = get_user(liked_id)
        liker_user = get_user(liker_id)
        bot.send_message(liker_id, f"💞 It's a Match! You can chat now: @{liked_user.get('username', 'unknown')}")
        bot.send_message(liked_id, f"💞 It's a Match! You can chat now: @{liker_user.get('username', 'unknown')}")
    else:
        bot.send_message(call.from_user.id, "Liked! Looking for more? Use /startmatch again.")

@bot.callback_query_handler(func=lambda call: call.data == "skip")
def handle_skip(call):
    bot.send_message(call.from_user.id, "Skipped. Use /startmatch again for more matches.")

# ====== START BOT =======
bot.polling()
