from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update  
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes  
from bs4 import BeautifulSoup  
import re  
import aiohttp  # Using aiohttp for async HTTP requests  
from web import keep_alive  

BOT_TOKEN = "7334566762:AAFTDty0k5zUhKqmy5H24LurCtGqF-OXbK4"  
BASE_URL = "https://opabhik.serv00.net/Watch.php?url="  
DOWNLOAD_BASE = "https://teradlrobot.cheemsbackup.workers.dev/?url="  
TERABOX_PATTERN = r"https?://(?:\w+\.)?(terabox|1024terabox|freeterabox|teraboxapp|tera|teraboxlink|mirrorbox|nephobox|1024tera|momerybox|tibibox|terasharelink|teraboxshare|terafileshare)\.\w+"  
LOG_CHANNEL_ID = "-1002449524486"  # Replace with your actual log channel's ID  
FSUB_CHANNEL_ID = "-1002574388477"  # Replace with your force subscription channel ID  
FSubLink = "https://t.meam_films"  # Replace with your actual channel link  

async def check_subscription(user_id, bot):  
    """Check if a user is a member of the required channel."""  
    try:  
        member = await bot.get_chat_member(FSUB_CHANNEL_ID, user_id)  
        return member.status in ["member", "administrator", "creator"]  
    except Exception as e:  
        print(f"Error in check_subscription: {e}")  
        return False  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    """Start command to welcome the user with an image and button."""  
    user_id = update.message.from_user.id  
    is_subscribed = await check_subscription(user_id, context.bot)  

    if not is_subscribed:  
        button = InlineKeyboardButton("✨ Join Channel", url=FSubLink)  
        reply_markup = InlineKeyboardMarkup([[button]])  
        await update.message.reply_text(  
            "❌ You must join our channel to use this bot.\n"  
            "Click the button below to join and then try again.",  
            reply_markup=reply_markup,  
        )  
        return  

    image_url = "https://envs.sh/rhi.jpg"  # Replace with your desired image URL  

    button = InlineKeyboardButton("✨ Join Channel", url="https://t.me/am_films")  
    reply_markup = InlineKeyboardMarkup([[button]])  

    await update.message.reply_photo(  
        photo=image_url,  
        caption="👋 Hi! Welcome to the bot! Send a Terabox link, and I’ll create a stream link for you.",  
    )  

async def fetch_file_details(url):  
    """Fetch file name, thumbnail, and size from the provided URL asynchronously."""  
    headers = {  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  
    }  
    try:  
        async with aiohttp.ClientSession() as session:  
            async with session.get(url, headers=headers) as response:  
                response.raise_for_status()  
                page_content = await response.text()  

        soup = BeautifulSoup(page_content, "html.parser")  

        file_name = soup.find("meta", {"property": "og:title"})  
        file_name = file_name["content"] if file_name else "Unknown File"  

        thumbnail = soup.find("meta", {"property": "og:image"})  
        thumbnail_url = thumbnail["content"] if thumbnail else None  

        file_size_tag = soup.find(string=lambda text: "MB" in text or "GB" in text)  
        file_size = file_size_tag.strip() if file_size_tag else "Unknown Size"  

        return {  
            "file_name": file_name,  
            "thumbnail_url": thumbnail_url,  
            "file_size": file_size,  
        }  
    except aiohttp.ClientError as e:  
        return {"error": f"Failed to fetch details: {str(e)}"}  
    except Exception as e:  
        return {"error": f"An unexpected error occurred: {str(e)}"}  

async def process_link(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    """Process a Terabox link, fetch details, and create a new URL with buttons."""  
    user_id = update.message.from_user.id  
    is_subscribed = await check_subscription(user_id, context.bot)  

    if not is_subscribed:  
        button = InlineKeyboardButton("✨ Join Channel", url=FSubLink)  
        reply_markup = InlineKeyboardMarkup([[button]])  
        await update.message.reply_text(  
            "❌ You must join our channel to use this bot.\n"  
            "Click the button below to join and then try again.",  
            reply_markup=reply_markup,  
        )  
        return  

    user_message = update.message.text.strip()  

    if re.search(TERABOX_PATTERN, user_message):  
        file_details = await fetch_file_details(user_message)  

        if "error" in file_details:  
            await update.message.reply_text(f"❌ Error fetching file details: {file_details['error']}")  
            return  

        file_name = file_details["file_name"]  
        file_size = file_details["file_size"]  
        thumbnail_url = file_details["thumbnail_url"]  

        MAX_LENGTH = 100  
        file_name = file_name[:MAX_LENGTH] + "..." if len(file_name) > MAX_LENGTH else file_name  

        watch_url = f"{BASE_URL}{user_message}"  
        download_url = f"{DOWNLOAD_BASE}{user_message}"  

        buttons = [  
            [InlineKeyboardButton("🌐 Watch Online", url=watch_url)],  
            [InlineKeyboardButton("⬇ Download Now", url=download_url)]  
        ]  
        reply_markup = InlineKeyboardMarkup(buttons)  

        reply_text = (  
            f"✅ **Here is your stream Link:**\n\n"  
            f"📄 **File Name:** {file_name}\n\n"  
            f"🔗 Click a button below to open the link.\n\n"
            f"⬇️ Click download button and wait for 5 to 10 seconds to download file.‼️"
        )  

        if thumbnail_url:  
            await update.message.reply_photo(  
                photo=thumbnail_url,  
                caption=reply_text,  
                reply_markup=reply_markup  
            )  
        else:  
            await update.message.reply_text(reply_text, reply_markup=reply_markup)  

        # Logging to channel  
        if thumbnail_url:  
            await context.bot.send_photo(  
                chat_id=LOG_CHANNEL_ID,  
                photo=thumbnail_url,  
                caption=reply_text,  
                reply_markup=reply_markup  
            )  
        else:  
            await context.bot.send_message(  
                chat_id=LOG_CHANNEL_ID,  
                text=reply_text,  
                reply_markup=reply_markup  
            )  
    else:  
        await update.message.reply_text(  
            "❌ That doesn't look like a valid Terabox link.\n"  
            "💡 Please send a link from domains like *terabox.com* or *terabox.co*."  
        )  

def main():  
    """Run the bot."""  
    application = Application.builder().token(BOT_TOKEN).build()  
    application.add_handler(CommandHandler("start", start))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))  

    application.run_polling()  

if __name__ == "__main__":  
    keep_alive()  
    main()
