import os
import sys
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UsernameNotOccupiedError, ChannelPrivateError

print("=== SCRIPT STARTED ===")

# خواندن Secrets از فایل
secrets_file = 'secrets.env'
if os.path.exists(secrets_file):
    with open(secrets_file) as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# خواندن از environment variables
API_ID = int(os.environ.get('TG_API_ID', 0))
API_HASH = os.environ.get('TG_API_HASH', '')
STRING_SESSION = os.environ.get('TG_STRING_SESSION', '')
CHAT_TARGET = os.environ.get('CHAT_TARGET', 'me')
START_ID = int(os.environ.get('START_ID', '0'))
END_ID_STR = os.environ.get('END_ID', '')
END_ID = int(END_ID_STR) if END_ID_STR and END_ID_STR.strip() else None

print(f"API_ID: {API_ID}")
print(f"API_HASH: {'*' * 10 if API_HASH else 'MISSING'}")
print(f"STRING_SESSION: {'*' * 10 if STRING_SESSION else 'MISSING'}")
print(f"CHAT_TARGET: {CHAT_TARGET}")
print(f"START_ID: {START_ID}")

if not API_ID or not API_HASH or not STRING_SESSION:
    print("❌ ERROR: Missing required secrets!")
    print("Check that secrets.env file exists with TG_API_ID, TG_API_HASH, TG_STRING_SESSION")
    sys.exit(1)

BASE_DIR = 'saved_files'

def extract_folder_and_filename(text):
    if not text:
        return None, None
    hashtag_match = re.search(r'#(\w+)', text)
    folder_name = hashtag_match.group(1) if hashtag_match else '_no_tag'
    tick_match = re.search(r'✅([^#]+)', text)
    if tick_match:
        raw = tick_match.group(1).strip()
        safe = re.sub(r'[\\/*?:"<>|]', '-', raw).strip()
        return folder_name, safe if safe else None
    return folder_name, None

async def main():
    print("=== Connecting to Telegram ===")
    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        print("✓ Client created")
        
        try:
            me = await client.get_me()
            print(f"✓ Logged in as: {me.first_name} (ID: {me.id})")
        except Exception as e:
            print(f"❌ Failed to get user info: {e}")
            return

        try:
            print(f"Looking for chat: {CHAT_TARGET}")
            entity = await client.get_entity(CHAT_TARGET)
            name = entity.title if hasattr(entity, 'title') else str(entity.id)
            print(f"✅ Connected to: {name}")
        except Exception as e:
            print(f"❌ Error getting entity: {e}")
            return

        os.makedirs(BASE_DIR, exist_ok=True)
        print(f"✓ Base directory: {BASE_DIR}")
        new = 0
        total_messages = 0

        min_id = START_ID if START_ID > 0 else 0
        print(f"Starting from message ID: {min_id}")

        try:
            async for msg in client.iter_messages(entity, min_id=min_id, max_id=END_ID, reverse=True):
                total_messages += 1
                if total_messages % 50 == 0:
                    print(f"📊 Processed {total_messages} messages...")
                
                if END_ID and msg.id > END_ID:
                    break
                if not msg.media:
                    continue

                text = msg.text or msg.caption or ""
                folder, fname = extract_folder_and_filename(text)

                if not fname:
                    orig = getattr(msg.file, 'name', None)
                    if orig:
                        fname = os.path.basename(orig)
                    else:
                        ext = msg.file.ext or '.bin'
                        fname = f"{msg.id}{ext}"

                folder_path = os.path.join(BASE_DIR, folder)
                os.makedirs(folder_path, exist_ok=True)

                ext = msg.file.ext or ''
                if ext and not fname.endswith(ext):
                    fname += ext

                path = os.path.join(folder_path, fname)
                if not os.path.exists(path):
                    try:
                        await msg.download_media(file=path)
                        print(f"✅ {folder}/{fname} (msg {msg.id})")
                        new += 1
                    except Exception as e:
                        print(f"❌ msg {msg.id}: {e}")
                else:
                    print(f"⏩ Already exists: {fname}")

        except Exception as e:
            print(f"❌ Error during iteration: {e}")
            return

        print(f"\n🎉 Done! Total messages checked: {total_messages}, New files: {new}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
