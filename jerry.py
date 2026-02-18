import asyncio
import os
import logging
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = int(os.getenv("API_ID", "22792918"))
API_HASH = os.getenv("API_HASH", "ff10095d2bb96d43d6eb7a7d9fc85f81")
SESSION = "BQFi2MYAM4dR-6mKuV2Xgg6QaqaC-uQq9F_ijYFuJhY5KihO4SYthbC3lZ4ry64kB2XmunPsyaj8fFaSnlccubMcTWMo0hsJNTQAU-Fj_8LFH5ZVfzGn7rsnjx8JMBmrQruJkO_KMo7QEzSodCrfy-GYIgC4v35fqV8kA_lGF99tU5L0kNuwZyZLj7vKSoXIqlkoVQY8lhZcCdFEL53iMY8QTZp7dMYMO3FQ1khDF8fe_jCUwzcNgmMY_fNCdGoEoNAFj1QjjhfPV8CvE8ndufiwQjOW0M_ISBej2K3g1PlGDIyUFyfC4f3dbti8GJkZe5Tj3kVQpAkSxsA_Hm9izeHLtfhaigAAAAHX23EJAA"  # Move to environment variable

TARGET_GROUP_IDS = [-1003811011870]
ALLOWED_FORWARD_CHANNEL_ID = -1003811011870
ADMIN_ID = -1003811011870  # Your user ID for notifications

# Timing configuration (in seconds)
POST_INTERVAL = 600  # 15 minutes
BATCH_SIZE = 20

app = Client("word9", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)

# Store the last posted message ID
last_shayari_message_id = None

async def notify_admin(text: str):
    """Send notification to admin"""
    try:
        await app.send_message(ADMIN_ID, text)
        logger.info(f"Notification sent to admin: {text}")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")


async def post_trending_shayari():
    """Post a new trending shayari message to all groups"""
    global last_shayari_message_id
    shayari_text = "⚡"

    for group_id in TARGET_GROUP_IDS:
        try:
            message = await app.send_message(group_id, shayari_text)
            last_shayari_message_id = message.id
            logger.info(f"Posted new shayari in {group_id} with ID: {message.id}")
            await message.delete()
        except Exception as e:
            error_msg = f"Error posting shayari in {group_id}: {str(e)}"
            logger.error(error_msg)
            await notify_admin(f"❌ {error_msg}")


async def clean_group_messages():
    """Delete all media messages except text/allowed forwards in all groups"""
    global last_shayari_message_id
    
    for group_id in TARGET_GROUP_IDS:
        try:
            to_delete = []
            deleted_count = 0
            preserved_count = 0

            logger.info(f"Starting media cleanup for {group_id}")
            
            async for message in app.get_chat_history(group_id):
                preserve = False

                if message.id == last_shayari_message_id:
                    preserve = True
                if message.text:
                    preserve = True
                if (message.forward_from_chat and 
                    message.forward_from_chat.id == ALLOWED_FORWARD_CHANNEL_ID):
                    preserve = True

                if preserve:
                    preserved_count += 1
                    continue

                if (message.photo or message.sticker or message.animation or 
                    message.video or message.audio or message.voice or 
                    message.document or message.video_note or message.contact or
                    message.location or message.venue or message.poll):
                    to_delete.append(message.id)

            if not to_delete:
                logger.info(f"No media messages to delete in {group_id}")
                continue

            for i in range(0, len(to_delete), BATCH_SIZE):
                batch = to_delete[i:i + BATCH_SIZE]
                try:
                    await app.delete_messages(group_id, batch)
                    deleted_count += len(batch)
                    logger.info(f"Deleted {len(batch)} messages in {group_id}")
                    await asyncio.sleep(2)
                except FloodWait as e:
                    logger.warning(f"Flood wait triggered. Sleeping {e.value}s")
                    await asyncio.sleep(e.value)
                except RPCError as e:
                    logger.error(f"Error deleting in {group_id}: {str(e)}")
                    continue

            stats = (
                f"🧹 Cleanup for {group_id} done:\n"
                f"• Deleted Media: {deleted_count}\n"
                f"• Preserved: {preserved_count}\n"
                f"• Last Shayari ID: {last_shayari_message_id}"
            )
            await notify_admin(stats)
            logger.info(stats)

        except Exception as e:
            error_msg = f"Error in cleanup for {group_id}: {str(e)}"
            logger.error(error_msg)
            await notify_admin(f"❌ {error_msg}")


async def periodic_operation():
    """Run periodic posting and cleaning"""
    logger.info("Starting periodic operations")
    while True:
        try:
            # Step 1: Post new shayari
            await post_trending_shayari()
            
            # Step 2: Clean the group
            await clean_group_messages()
            
        except Exception as e:
            logger.error(f"Periodic operation error: {str(e)}")
            await notify_admin(f"⚠️ Periodic operation failed: {str(e)}")
            
        await asyncio.sleep(POST_INTERVAL)

async def main():
    """Main function to start the bot"""
    try:
        await app.start()
        logger.info("Bot started successfully")
        await notify_admin("🤖 Bot started and running")
        await periodic_operation()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        await notify_admin(f"💀 Fatal error: {str(e)}")
    finally:
        await app.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
