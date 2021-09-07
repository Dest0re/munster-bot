import random
import asyncio
from enum import Enum
from abc import abstractmethod
from dataclasses import dataclass

import discord


class EventTypeEnum(Enum):
    join = 1
    ret = 2
    leave = 3
    ban = 4
    unban = 5
    boost = 6


@dataclass
class EventType:
    type: EventTypeEnum
    color: int
    title_text: str
    description_text: list[str]
    button_color: discord.ButtonStyle
    button_emoji: str
    reaction_message: str

    def get_description_text(self) -> str:
        return random.choice(self.description_text)


class GuildEventManager:
    @abstractmethod
    async def send_join_message(self, member: discord.Member):
        pass

    @abstractmethod
    async def send_return_message(self, member: discord.Member):
        pass

    @abstractmethod
    async def send_leave_message(self, member: discord.Member):
        pass

    @abstractmethod
    async def send_ban_message(self, member: discord.Member):
        pass

    @abstractmethod
    async def send_unban_message(self, member: discord.Member):
        pass

    @abstractmethod
    async def send_boost_message(self, member: discord.Member):
        pass


class EmbedGuildEventManager(GuildEventManager):
    event_types = {
        EventTypeEnum.join: EventType(
            type=EventTypeEnum.join,
            color=0x5CC67C, 
            title_text='присоединился к серверу', 
            description_text=['Здоровеньки булы!', 'Будь как дома.', 'Прикольный дискриминатор.'],
            button_color=discord.ButtonStyle.green, 
            button_emoji='👋', 
            reaction_message='{a} поприветствовал {m}. \nПривет-привет! 👋'
        ),
        EventTypeEnum.ret: EventType(
            type=EventTypeEnum.ret,
            color=0x78A0C0, 
            title_text='вернулся на сервер', 
            description_text=['Добро пожаловать. Снова.', 'Кого я вижу!', 'И где ты только был?..'],
            button_color=discord.ButtonStyle.grey, 
            button_emoji='👋', 
            reaction_message='{a} рад, что {m} снова с нами. \nПривет-привет! 👋'
        ),
        EventTypeEnum.leave: EventType(
            type=EventTypeEnum.leave,
            color=0xFFE888, 
            title_text='покинул сервер', 
            description_text=['Будем скучать.', 'Интересно, чего это он?', 'Это его личный выбор.'],
            button_color=discord.ButtonStyle.grey, 
            button_emoji='🤨', 
            reaction_message='{a} озадачен уходом {m}. \nЧто ж, будем надеяться, он вернётся!'
        ),
        EventTypeEnum.ban: EventType(
            type=EventTypeEnum.ban,
            color=0xFF7676, 
            title_text='был забанен', 
            description_text=['Вероятно, за дело.', 'Надеюсь, не навсегда.', 'Правила нужно соблюдать.'],
            button_color=discord.ButtonStyle.red, 
            button_emoji='🇫', 
            reaction_message='{a} отдаёт долг уважения забаненному {m}. \nPress :regional_indicator_f:!'
        ),
        EventTypeEnum.unban: EventType(
            type=EventTypeEnum.unban,
            color=0xF4BC1E,
            title_text='был разбанен',
            description_text=['Наконец-то!', 'Я всегда знал, что это должно случиться.', 'Надеюсь, такого больше не повторится'],
            button_color=discord.ButtonStyle.green,
            button_emoji='🥳',
            reaction_message='{a} поздравляет {m} с разбаном. \nДобро пожаловать домой!'
        ),
        EventTypeEnum.boost: EventType(
            type=EventTypeEnum.boost,
            color=0xC49FFF, 
            title_text='забустил сервер!', 
            description_text=['Дружно скажем "Спасибо"!', 'Бустов много не бывает.'],
            button_color=discord.ButtonStyle.blurple, 
            button_emoji='😍', 
            reaction_message='{a} считает, что забустивший сервер {m} - замечательный. \nИ с этим трудно спорить! Спасибо ему!'
        ),
    }

    def __init__(self, notifications_channel: discord.TextChannel, text_channel: discord.TextChannel):
        self._notifications_channel = notifications_channel
        self._text_channel = text_channel

    @classmethod
    def _generate_embed(cls, member: discord.Member, event_type: EventTypeEnum) -> discord.Embed:
        event_type = cls.event_types[event_type]

        description_text = event_type.get_description_text()

        embed = discord.Embed(
            color=event_type.color,
            title=f'{member} {event_type.title_text}',
            description=f'{description_text}\n\n• {member.mention} •'
        )
        embed.set_thumbnail(url=member.avatar.url)

        return embed
    
    @classmethod
    def _generate_button(cls, event_type: EventTypeEnum) -> discord.ui.Button:
        event_type = cls.event_types[event_type]
        return discord.ui.Button(
            style=event_type.button_color,
            emoji=event_type.button_emoji
        )

    @classmethod
    def _get_reaction_text(cls, event_type: EventTypeEnum, author: discord.Member, member: discord.Member) -> str:
        return cls.event_types[event_type].reaction_message.format(a=author.display_name, m=member.display_name)

    def _on_interaction(self, event_type: EventTypeEnum, member: discord.Member):
        already_reacted = []
        async def on_interaction(interaction: discord.Interaction):
            if interaction.user not in already_reacted:
                already_reacted.append(interaction.user)
                await self._text_channel.send(self._get_reaction_text(event_type, interaction.user, member))
            await interaction.response.defer()
        return on_interaction

    def _generate_view(self, event_type: EventTypeEnum, member: discord.Member) -> discord.ui.View:
        button = self._generate_button(event_type)

        view = discord.ui.View()
        view.add_item(button)
        view.interaction_check = self._on_interaction(event_type, member)

        return view

    async def _send_event_message(self, member: discord.Member, event_type: EventTypeEnum):
        embed = self._generate_embed(member, event_type)
        view = self._generate_view(event_type, member)

        message = await self._notifications_channel.send(embed=embed, view=view)

        await asyncio.sleep(60)

        await message.edit(view=None)

    async def send_join_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.join)
    
    async def send_return_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.ret)

    async def send_leave_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.leave)
    
    async def send_ban_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.ban)

    async def send_unban_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.unban)
    
    async def send_boost_message(self, member: discord.Member):
        await self._send_event_message(member, EventTypeEnum.boost)
