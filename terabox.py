from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import logging
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv('config.env', override=True)

logging.basicConfig(level=logging.INFO)

api_id = os.environ.get('TELEGRAM_API', '')
api_hash = os.environ.get('TELEGRAM_HASH', '')
bot_token = os.environ.get('BOT_TOKEN', '')
fsub_id = os.environ.get('FSUB_ID', '')

# Validate environment variables
if not api_id or not api_hash or not bot_token or not fsub_id:
    logging.error("One or more environment variables are missing! Exiting now")
    exit(1)

fsub_id = int(fsub_id)
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Start command handler
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_mention = message.from_user.mention
    reply_message = f"ᴡᴇʟᴄᴏᴍᴇ, {user_mention}.\n\n🌟 ɪ ᴀᴍ ᴀ ᴛᴇʀᴀʙᴏx ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ. sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ ɪ ᴡɪʟʟ ᴅᴏᴡɴʟᴏᴀᴅ ᴡɪᴛʜɪɴ ғᴇᴡ sᴇᴄᴏɴᴅs ᴀɴᴅ sᴇɴᴅ ɪᴛ ᴛᴏ ʏᴏᴜ ✨."
    join_button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/AM_UPLOAD")
    reply_markup = InlineKeyboardMarkup([[join_button]])
    
    await message.reply_text(reply_message, reply_markup=reply_markup)

# Check if user is a member of the channel
async def is_user_member(client, user_id):
    try:
        member = await client.get_chat_member(fsub_id, user_id)
        logging.info(f"User {user_id} membership status: {member.status}")
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logging.error(f"Error checking membership status for user {user_id}: {e}")
        return False

# Function to get stream URL from the API
def get_stream_url(terabox_link):
    api_url = f"https://opabhik.serv00.net/Watch.php?url={terabox_link}"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            return data.get("stream_url")  # Adjust based on actual API response structure
        else:
            logging.error(f"API returned an error: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching stream URL: {e}")
        return None

@app.on_message(filters.text)
async def handle_message(client, message: Message):
    if message.from_user is None:
        logging.error("Message does not contain user information.")
        return

    user_id = message.from_user.id
    user_mention = message.from_user.mention
    is_member = await is_user_member(client, user_id)

    if not is_member:
        join_button = InlineKeyboardButton("ᴊᴏɪɴ ❤️🚀", url="https://t.me/AM_UPLOAD")
        reply_markup = InlineKeyboardMarkup([[join_button]])
        await message.reply_text("ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.", reply_markup=reply_markup)
        return

    valid_domains = ['terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com']  # Add other domains as needed
    terabox_link = message.text.strip()

    if not any(domain in terabox_link for domain in valid_domains):
        await message.reply_text("ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ.")
        return

    stream_url = get_stream_url(terabox_link)
    
    if stream_url:
        stream_button = InlineKeyboardButton("Stream Video 🎥", url=stream_url)
        reply_markup = InlineKeyboardMarkup([[stream_button]])
        await message.reply_text("Here is your stream link:", reply_markup=reply_markup)
    else:
        await message.reply_text("Failed to retrieve the stream URL. Please check the TeraBox link.")

if __name__ == "__main__":
    app.run()
