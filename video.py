import os
import time
import logging
import asyncio
import aiohttp
import aria2p
from datetime import datetime
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "ARIA2_HOST": "http://localhost",
    "ARIA2_PORT": 6800,
    "ARIA2_SECRET": "",
    "TERABOX_API": "https://terabox-downloader.p.rapidapi.com/get-data",
    "API_HEADERS": {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", "0ec1d5fa9bmsh203fa2fef325774p1bdb48jsnce437790802e"),
        "X-RapidAPI-Host": "terabox-downloader.p.rapidapi.com"
    },
    "MAX_RETRIES": 3,
    "DOWNLOAD_DIR": "downloads"
}

# Initialize aria2
aria2 = aria2p.API(
    aria2p.Client(
        host=CONFIG["ARIA2_HOST"],
        port=CONFIG["ARIA2_PORT"],
        secret=CONFIG["ARIA2_SECRET"]
    )
)

async def get_terabox_direct_link(url: str) -> dict:
    """Get direct download links from Terabox"""
    async with aiohttp.ClientSession() as session:
        for _ in range(CONFIG["MAX_RETRIES"]):
            try:
                async with session.get(
                    CONFIG["TERABOX_API"],
                    headers=CONFIG["API_HEADERS"],
                    params={"url": url},
                    timeout=10
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if data.get("status") and data.get("data"):
                        return {
                            "title": data["data"].get("file_name"),
                            "thumbnail": data["data"].get("thumb"),
                            "links": data["data"].get("links"),
                            "size": data["data"].get("size")
                        }
                    raise Exception("Invalid API response")
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"API request failed: {str(e)}")
                await asyncio.sleep(2)
                
        return {"error": "Failed to fetch download links"}

async def download_file(url: str, reply_msg, user_info: dict) -> str:
    """Handle file download using aria2"""
    try:
        download = aria2.add_uris([url], {"dir": CONFIG["DOWNLOAD_DIR"]})
        start_time = datetime.now()
        
        while not download.is_complete:
            await asyncio.sleep(2)
            download.update()
            
            progress = {
                "percentage": download.progress,
                "done": download.completed_length_string(),
                "total": download.total_length_string(),
                "speed": download.download_speed_string(),
                "eta": download.eta_string(),
                "elapsed": (datetime.now() - start_time).seconds
            }
            
            await update_progress_message(reply_msg, progress, user_info, "Downloading")
        
        return download.files[0].path
        
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        await reply_msg.edit_text("❌ Download failed! Please try again later.")
        return None

async def upload_to_telegram(client: Client, file_path: str, metadata: dict, reply_msg, user_info: dict):
    """Handle Telegram upload"""
    try:
        start_time = datetime.now()
        last_update = time.time()
        
        async def progress_callback(current, total):
            nonlocal last_update
            if time.time() - last_update > 2:
                progress = {
                    "percentage": (current / total) * 100,
                    "done": human_readable_size(current),
                    "total": human_readable_size(total),
                    "speed": human_readable_size(current / (time.time() - start_time.timestamp())),
                    "eta": format_eta((total - current) / (current / (time.time() - start_time.timestamp()))),
                    "elapsed": int(time.time() - start_time.timestamp())
                }
                
                await update_progress_message(reply_msg, progress, user_info, "Uploading")
                last_update = time.time()
        
        await client.send_video(
            chat_id=reply_msg.chat.id,
            video=file_path,
            caption=f"**{metadata['title']}**\n\n✅ Downloaded via Terabox Downloader",
            thumb=metadata.get("thumbnail"),
            progress=progress_callback
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        await reply_msg.edit_text("❌ Upload failed! Please try again later.")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def update_progress_message(message, progress: dict, user_info: dict, status: str):
    """Update progress message with formatted text"""
    text = (
        f"**{status} Progress**\n\n"
        f"🗂 **File:** `{progress.get('title', 'N/A')}`\n"
        f"🧑 **User:** {user_info['mention']}\n"
        f"📈 **Progress:** {progress['percentage']:.1f}%\n"
        f"🔽 **Downloaded:** {progress['done']} / {progress['total']}\n"
        f"⚡ **Speed:** {progress['speed']}/s\n"
        f"⏳ **ETA:** {progress['eta']}\n"
        f"⌛ **Elapsed:** {progress['elapsed']}s"
    )
    
    try:
        await message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to update progress: {str(e)}")

def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format"""
    if not size_bytes:
        return "0B"
        
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size_bytes >= 1024 and index < len(units)-1:
        size_bytes /= 1024
        index += 1
    return f"{size_bytes:.2f}{units[index]}"

def format_eta(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format"""
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

async def handle_terabox_download(client: Client, message, url: str):
    """Main handler for Terabox download requests"""
    user_info = {
        "id": message.from_user.id,
        "mention": message.from_user.mention
    }
    
    reply_msg = await message.reply_text("🔄 Processing your request...")
    
    try:
        # Step 1: Get download links
        await reply_msg.edit_text("🔗 Fetching download links from Terabox...")
        terabox_data = await get_terabox_direct_link(url)
        
        if terabox_data.get("error"):
            return await reply_msg.edit_text("❌ Error: Failed to get download links")
        
        # Step 2: Start download
        best_quality = max(terabox_data["links"], key=lambda x: x.get("quality", 0))
        await reply_msg.edit_text("📥 Starting download...")
        file_path = await download_file(best_quality["url"], reply_msg, user_info)
        
        if not file_path:
            return
            
        # Step 3: Upload to Telegram
        await reply_msg.edit_text("📤 Starting upload...")
        await upload_to_telegram(
            client,
            file_path,
            {
                "title": terabox_data["title"],
                "thumbnail": terabox_data.get("thumbnail")
            },
            reply_msg,
            user_info
        )
        
        await reply_msg.delete()
        await message.reply_sticker("CAACAgIAAxkBAAEZdwRmJhCNfFRnXwR_lVKU1L9F3qzbtAAC4gUAAj-VzApzZV-v3phk4DQE")
        
    except Exception as e:
        logger.error(f"Main handler error: {str(e)}")
        await reply_msg.edit_text("❌ An unexpected error occurred. Please try again later.")
