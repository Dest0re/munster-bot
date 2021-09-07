from random import random
import discord
from guildeventmanager import EventTypeEnum, GuildEventManager
from loguru import logger


class MessageGuildEventManager(GuildEventManager):
    group_names = {
        EventTypeEnum.join: 'on_join',
        EventTypeEnum.ret: 'on_return',
        EventTypeEnum.leave: 'on_remove',
        EventTypeEnum.ban: 'on_ban',
        EventTypeEnum.unban: 'on_unban',
        EventTypeEnum.boost: 'on_boost'
    }

    def __init__(
        self, 
        phrases_path: str, 
        notifications_channel: discord.TextChannel,
        event_types: list[EventTypeEnum], 
        group_separator: str = '$=jopa', 
        comment_char: str = '#',
    ):
        self._phrases_path = phrases_path
        self._notifications_channel = notifications_channel
        self._event_types = event_types
        self._group_separator = group_separator
        self._comment_char = comment_char

    def get_phrases(self) -> dict:
        logger.info('Получаю фразы...')
        with open(self._phrases_path, encoding='utf-8') as f:
            phrases_dict = {}
            group = 0
            first_line = True

            for line in f.readlines():
                if line == self._group_separator + '\n':
                    group += 1
                    first_line = True
                else:
                    if not line.startswith(self._comment_char) and not line.isspace():
                        if first_line:
                            phrases_dict[self.group_names[self._event_types[group]]] = []
                            first_line = False

                        phrases_dict[self.group_names[self._event_types[group]]].append(
                            line.replace('\\n', '\n'))

            logger.info('Фразы получены!')
            return phrases_dict
    
    async def send(self, user: discord.Member, event_type: EventTypeEnum):
        logger.info(f'{user} | Событие: {self.group_names[event_type]}, отправляю сообщение...')
        phrase = random.choice(self.get_phrases()[self.group_names[event_type]])
        await self.notifications_channel.send(phrase.format(m=user.mention))
        logger.info('Отправлено.')

    async def send_join_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.join)
    
    async def send_return_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.ret)
    
    async def send_leave_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.leave)
    
    async def send_ban_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.ban)
    
    async def send_unban_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.unban)
    
    async def send_boost_message(self, member: discord.Member):
        await self.send(member, EventTypeEnum.boost)
