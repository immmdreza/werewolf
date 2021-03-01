import asyncio
import json
import random
import re
import os
from collections import namedtuple
from typing import List

from colorama import Back, Fore, Style, init
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message


class WerewolfEvent(object):
    def __init__(self, callback: "Func(event: NewMessage)", pattern: str, allowed_sessions = None):
        self.callback = callback
        self.pattern = pattern
        self.allowed_sessions = allowed_sessions


class WerewolfHandlre:
    def __init__(
        self, 
        api_id: int, 
        api_hash: str, 
        language: str = 'en-normal',
        main_chats: list = None
    ):
        init()

        print( Fore.BLUE + ':: Setting Up Variables ... ::' )
        self.__api_id   = api_id
        self.__api_hash = api_hash

        # Only join in game from here
        self.main_chats = main_chats

        """
        A variable to store all needed inforamtion
        -> in_game:  to know what accounts are in game already
        -> accounts: Every account info with its session name as key
        -> Eg: db['accounts']['anon']['info'] (this is user obj of account)
            db['accounts']['anon']['info'].id (account user id)
            db['accounts']['anon']['session'] (session name in case)
        """
        self._db = {
            'in_game' : [ ],
            'accounts': { }
        }

        self.events = events

        # Setup base handlers
        self._handlers = {
            'ping': {'callback': self.__ping, 'event': events.NewMessage(pattern= r'^/ping$')},
            'werewolf_message': {
                'callback': self.__werewolf_message, 
                'event': events.NewMessage(from_users= ['werewolfbot', 'werewolfbetabot'], incoming= True)
            }
        }

        self.__loop = asyncio.get_event_loop()
        
        self.__on_vote: WerewolfEvent = None
        self.__on_join_message: WerewolfEvent = None
        self.__on_day: WerewolfEvent = None
        self.__on_night: WerewolfEvent = None
        self.__on_new_list: WerewolfEvent = None
        self.__on_finished: WerewolfEvent = None
        self.__on_actions: List[WerewolfEvent] = []

        self.__on_ping = None

        self.__languages = {}
        self.__main_lang = language

        self.reload_languages()


    def reload_languages(self):
        loaded = 0
        files = os.listdir('languages/')
        for x in files:
            try:
                with open(os.path.join('languages/', x), 'r', encoding= 'utf8') as f:
                    read = f.read()
                    data = json.loads(read, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
                    self.__languages[data.identifier] = data
                    loaded += 1
            except:
                continue
        if loaded == 0:
            # Loads default english if not lang files exists
            read = r"""
            {
                "name": "English Normal",
                "identifier": "en-normal",
                "texts": { 
                    "joinButton" : "Join",
                    "voteMessage": "Who do you want to lynch?", 
                    "dayStarted": "It is now day time.",
                    "nightStarted": "Night has fallen.",
                    "newPlayerList": "Players Alive: \\d/\\d",
                    "gameFinished": "Game Length: \\d\\d:\\d\\d:\\d\\d"
                }
            }
            """
            data = json.loads(read, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
            self.__languages[data.identifier] = data
        print( Fore.CYAN + f":: {loaded} Language file loaded! ::" )

    @property
    def languages(self):
        return self.__languages 

    @property
    def current_lang(self):
        return self.__languages[self.__main_lang].texts

    @staticmethod
    def get_session_name(event):
        return event.client.session.filename.split('.')[0]

    def account_info(session: str = None, id: int = None):
        if session:
            return self._db['accounts'][session]['info']
        elif id:
            return [x for x in self._db['accounts'] if self._db['accounts'][x]['info'].id == id][0]

    def on_vote(self, pattern, allowed_sessions: "str|list" = None):
        def wapper(f):
            def decorator():
                self.__on_vote = WerewolfEvent(
                    asyncio.coroutine(f), 
                    pattern or self.current_lang.voteMessage, 
                    allowed_sessions, allowed_sessions
                )
            return decorator()
        return wapper

    def on_action(self, pattern, allowed_sessions: "str|list" = None):
        def wapper(f):
            def decorator():
                self.__on_actions.append(
                    WerewolfEvent(
                        asyncio.coroutine(f), 
                        pattern, 
                        allowed_sessions
                    )
                )
            return decorator()
        return wapper

    def on_join_message(self, pattern, allowed_sessions: "str|list" = None):
        def wapper(f):
            def decorator():
                self.__on_join_message = WerewolfEvent(
                    asyncio.coroutine(f), 
                    pattern or self.current_lang.joinButton, 
                    allowed_sessions
                )
            return decorator()
        return wapper

    def on_ping(self, f):
        def decorator():
            self.__on_ping = asyncio.coroutine(f)
        decorator()

    def add_custom_handler(self, name: str, callback, event: events):
        self._handlers[name] = {
            'callback': callback, 
            'event': event
        }

    @property
    def current_handlers(self):
        return [x for x in self._handlers]

    async def __ping(self, e: Message):
        """Are account alive ?!
        """
        if self.__on_ping:
            await self.__on_ping(e)
        else:
            await e.reply("Pong!")

    async def __werewolf_message(self, e : Message):
        """All incoming messages from werewolf bots comes here ( group, private, channel :| )
        """

        async def report(text):
            """Send report message to main_chat
            """
            await e.client.send_message(e.chat_id, text)

        def get_session():
            return e.client.session.filename.split('.')[0]


        if e.is_group and e.chat_id not in self.main_chats:
            return

        session_name = get_session()

        # Messages with buttons in group chat from werewolf bots
        if e.is_group:
            # Werewolf messages with at least one button
            if e.button_count > 0:
                
                # Check is its the "Join Game" message and join if not 
                if self.__on_join_message:
                    if self.__on_join_message.allowed_sessions and session_name not in self.__on_join_message.allowed_sessions:
                        return
                    if re.match(self.__on_join_message.pattern, e.buttons[0][0].text):
                        return await self.__on_join_message.callback(e)
                elif e.buttons[0][0].text == self.current_lang.joinButton:
                    x = get_session()
                    if x not in self._db['in_game']:
                        code = e.buttons[0][0].url.split('=')[-1]
                        app = e.client
                        # Starts a conversation with werewolf to see if account joined or not
                        async with app.conversation(e.from_id, max_messages = 1) as conv:
                            await conv.send_message("/start " + code)

                            try:
                                # Waiting 3s for ww respond 
                                await conv.get_response(timeout = 5)
                                await report('Joined')
                                self._db['in_game'].append(x)
                            except:
                                await report('No respond from werewolf')
            
            # Messages without buttons in group
            else:
                if self.__on_day:
                    if self.__on_day.allowed_sessions and session_name not in self.__on_day.allowed_sessions:
                        return
                    if re.match(self.__on_day.pattern, e.text):
                        return await self.__on_day.callback(e)
                if re.match(self.current_lang.dayStarted, e.text):
                    # day
                    report('Good morning my friends')
                    return

                if self.__on_night:
                    if self.__on_night.allowed_sessions and session_name not in self.__on_night.allowed_sessions:
                        return
                    if re.match(self.__on_night.pattern, e.text):
                        return await self.__on_night.callback(e)
                elif re.match(self.current_lang.nightStarted, e.text):
                    # night
                    report('The night!')
                    return

                if self.__on_new_list:
                    if self.__on_new_list.allowed_sessions and session_name not in self.__on_new_list.allowed_sessions:
                        return
                    if re.match(self.__on_new_list.pattern, e.text):
                        if self.__on_finished:
                            if self.__on_finished.allowed_sessions and session_name not in self.__on_finished.allowed_sessions:
                                return
                            if re.match(self.__on_finished.pattern, e.text):
                                return await self.__on_finished.callback(e)
                        elif re.match(self.current_lang.gameFinished, e.text):
                            # game finished
                            report('Game finished!')
                            return
                        return await self.__on_new_list.callback(e)
                elif re.match(self.current_lang.newPlayerList, e.text):
                    # player list
                    report('New player list.')
                    if self.__on_finished:
                            if self.__on_finished.allowed_sessions and session_name not in self.__on_finished.allowed_sessions:
                                return
                            if re.match(self.__on_finished.pattern, e.text):
                                return await self.__on_finished.callback(e)
                    elif re.match(self.current_lang.gameFinished, e.text):
                        # game finished
                        report('Game finished!')


        # Should be private
        else:

            # Messages with buttons in private chat with werewolf bots
            if e.button_count:
                # Voting time
                if e.text:
                    if self.__on_vote:
                        if self.__on_vote.allowed_sessions and session_name not in self.__on_vote.allowed_sessions:
                            return
                        if re.match(self.__on_vote.pattern, e.text):
                            return await self.__on_vote.callback(e)
                    elif e.text == self.current_lang.voteMessage:
                        # Click a random button
                        e.click(text= random.choice(e.buttons)[0].text)
                        report("Random Vote!")
                        return

                    for x in self.__on_actions:
                        if x.allowed_sessions and session_name not in x.allowed_sessions:
                            continue
                        if x.pattern:
                            if re.match(x.pattern, e.text): 
                                return await x.callback(e)
                        else:
                            return await x.callback(e)

                    # It should be actions
                    # Click on skip button if exists
                    e.click(text= 'skip')
                report("Skiped")


    def reload_sessions(self):
        """
        Capture all .session files.
        """
        import glob 
        sessions = glob.glob('*.session')
        for x in sessions:
            self._db['accounts'][x.split('.')[0]] = { 'session': x.split('.')[0] }

    def reload_info(self):
        """
        Reload user info for create sessions
        """
        self.__loop.run_until_complete(self.__reload_info())

    async def __reload_info(self):
        for x in self._db['accounts']:
            async with TelegramClient(self._db['accounts'][x]['session'], self.__api_id, self.__api_hash) as app:
                self._db['accounts'][x]['info'] = await app.get_me()

    def start(self, account_count):
        """
        Start all accounts, you should use block() to keep the alive.

        accounts_count ~> Number of account that should add and handle
            you may need to enter phone number and other if you didn't already,
        """
        for x in range(account_count):
            app = TelegramClient(f'anon_{x}', self.__api_id, self.__api_hash)

            for x in self._handlers:
                app.add_event_handler(
                    self._handlers[x]['callback'],
                    self._handlers[x]['event']
                )

            app.start()

    def block(self):
        """
        Run event loop forever
        """
        # I WILL RUN FOR EVER 
        # BUT WHY ARE YOU RUNNING ?
        self.__loop.run_forever()

    def run_forever(self, accounts_count: int):
        """
        Automatically start all account and keep them alive forever

        accounts_count ~> Number of account that should add and handle
            you may need to enter phone number and other if you didn't already,
        """

        print( Fore.BLUE + ':: Watching Session Files ... ::' )
        self.reload_sessions()

        print( Fore.BLUE + ':: Reloading Accuonts Info ... ::' )
        self.reload_info()

        self.start(accounts_count)

        print( Fore.YELLOW + ':: Started Handlers (Running forever) ::' )
        self.block()
