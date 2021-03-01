from werewolf import WerewolfHandlre
from telethon.tl.custom.message import Message

# Place your api hash and api id here
# These gonna use for all accounts
api_id   =  1234567
api_hash = 'API_HASH'

# Only join in game from here
main_chat = [-100112345657]

handler = WerewolfHandlre(api_id, api_hash, main_chats= main_chat)

@handler.on_ping
async def pinged(e: Message):
    await e.reply('OK PINGED!')

@handler.on_join_message(None)
async def join(e):
    await e.reply('I saw join message')

handler.run_forever(1)