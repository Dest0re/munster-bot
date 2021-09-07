# -*- coding: utf8 -*- 

import asyncio
import random
import time
import sqlite3
import os

import discord
from loguru import logger as log

from guildeventmanager import BybyrskyEmbedGuildEventManager, BybyrskyEventManager

DISCORD_BOT_TOKEN = os.getenv('TOKEN')
FILE_PATH = './phrases'
SEPARATOR = '$=jopa'
COMMENT = '#'
GROUPS = ('on_ban', 'on_unban', 'on_remove', 'on_return', 'on_join')

GUILD_ID = 785770770869256233

MEMBER_ROLE_ID = 789548860602974209
BOT_ROLE_ID = 785802866077859880

TEXT_CHANNEL_ID = 785790712854609951
RULES_CHANNEL_ID = 785791232122421288
INVITE_CHANNEL_ID = 789561456009543712
SUICIDE_CHANNEL_ID = 785791435093966879
ANNOUNCEMENTS_CHANNEL_ID = 789551174520012830
NOTIFICATIONS_CHANNEL_ID = 785791145191538718
SUGGESTIONS_CHANNEL_ID = 785791296362119190
ADMIN_SUGGESTIONS_CHANNEL_ID = 805081981074931712

BAN_MESSAGE_ID = 789556960516767774

GREETING_MESSAGE = '''{m}, рады приветствовать на сервере Сибирского! Беру на себя ответственность говорить от лица администрации.
Мы надеемся, у тебя не возникнет проблем с тем, чтобы влиться в коллектив.
Можешь разобраться с устройством сервера сам, а можешь нажать на "📕" под этим сообщением, тогда я поясню тебе всё в личных сообщениях. Другой вариант: написать мне в лс первым.'''

GUILD_ANNOTATION = '''В общем, слушай.
Сервер разбит на несколько секций: текстовые каналы для общения и спама, голосовые каналы, секция "интересное" - с ней тебе лучше ознакомиться самостоятельно, - и секция "важное". 
В ней расположены канал с инвайтом на сервер (<#{invite}>), загляни туда, если захочешь позвать друзей, канал с правилами (<#{rules}>), 
ознакомься с ними, если ещё не успел, <#{announcements}> и  <#{notifications}> - каналы с анонсами и с уведомлениями о событиях, соответственно. Если возникнут жалобы или предложения, можно отправить их в канал <#{suggestions}> из той же секции.
Учти, что мы тут придерживаемся политики здорового пренебрежения мнением участников, и отнесись с пониманием, если твоя просьба будет отклонена. Но мы всегда в поисках способов улучшения сервера, и с нетерпением ждём ваших здравых идей. 
Ещё обрати внимание на канал <#{suicide}>. В нём есть сообщение, внимательно прочитай. Если возникнут вопросы - задавай их в основной текстовый канал, тебе ответят или участники, или админы, последних ты сможешь отличить по роли "Угнетающий класс". 
На этом всё, удачного тебе общения!'''

GUILD_ANNOTATION_MESSAGE = GUILD_ANNOTATION.format(invite=INVITE_CHANNEL_ID, 
    rules=RULES_CHANNEL_ID, announcements=ANNOUNCEMENTS_CHANNEL_ID,
    notifications=NOTIFICATIONS_CHANNEL_ID, suggestions=SUGGESTIONS_CHANNEL_ID,
    suicide=SUICIDE_CHANNEL_ID)


class Client(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild = None
        self.ban_message = None
        self.notifications_channel = None
        self.admin_suggestions_channel = None
        self.suggestions_channel = None
        self.text_channel = None
        self.member_role = None
        self.bot_role = None

        self.event_manager: BybyrskyEventManager = None

        self.connection = sqlite3.connect('banned.db')
        self.cur = self.connection.cursor()

        log.info('База данных подключена!')


    def get_strikes(self, author_id):
        t = (author_id, )
        self.cur.execute('select member_id, strikes from trash_suggestions where member_id = ?', t)
        strikes = self.cur.fetchone()
        if strikes:
            return strikes[1]
        return 0

    def generate_embed(self, message):
        embed = discord.Embed(title="Новое предложение", description=message.content)
        embed.set_author(name=str(message.author), icon_url=str(message.author.avatar_url))
        embed.set_footer(text=time.ctime(time.time() -  60 * 60 * 2))
        embed.add_field(name='Штрафы', value=self.get_strikes(message.author.id), inline=False)
        return embed

    def add_messages_to_fetch_list(self, *args):
        for message in args:
            if message not in self._connection._messages:
                self._connection._messages.append(message)

    def remove_messages_from_fetch_list(self, *args):
        for message in args:
            if message in self._connection._messages:
                self._connection._messages.remove(message)

    async def on_ready(self):
        log.info('Инициализируюсь...')
        log.info(f'Авторизовался как {self.user.display_name}.')

        self.guild = self.get_guild(GUILD_ID)
        self.ban_message = await self.get_channel(SUICIDE_CHANNEL_ID).fetch_message(BAN_MESSAGE_ID)
        self.notifications_channel = self.get_channel(NOTIFICATIONS_CHANNEL_ID)
        self.admin_suggestions_channel = self.get_channel(ADMIN_SUGGESTIONS_CHANNEL_ID)
        self.suggestions_channel = self.get_channel(SUGGESTIONS_CHANNEL_ID)
        self.text_channel = self.get_channel(TEXT_CHANNEL_ID)
        self.member_role = self.guild.get_role(MEMBER_ROLE_ID)
        self.bot_role = self.guild.get_role(BOT_ROLE_ID)

        self.event_manager = BybyrskyEmbedGuildEventManager(self.notifications_channel, self.text_channel)

        messages = []
        for row in self.cur.execute('select message_id from suggestion_messages'):
            messages.append(await self.admin_suggestions_channel.fetch_message(row[0]))

        self.add_messages_to_fetch_list(self.ban_message)
        self.add_messages_to_fetch_list(*messages)

        log.info('Инициализация завершена!')

    async def on_member_ban(self, guild, user):
        await self.wait_until_ready()
        if guild.id == GUILD_ID:
            asyncio.get_event_loop().create_task(self.event_manager.send_ban_message(user))

    async def on_member_unban(self, guild, user):
        await self.wait_until_ready()
        if guild.id == GUILD_ID:
            await self.send(user, 'on_unban')

    async def on_member_remove(self, member):
        await self.wait_until_ready()
        if member.guild.id == GUILD_ID:
            bans = await self.guild.bans()
            if not discord.utils.find(lambda e: e.user.id == member.id, bans):
                asyncio.get_event_loop().create_task(self.event_manager.send_leave_message(member))
            
            self.cur.execute('select * from leaved_users where id=?', (member.id,))
            if not self.cur.fetchone():
                t = (member.id, )
                self.cur.execute('insert into leaved_users values (?)', t)
                self.connection.commit()

    async def on_member_join(self, member):
        await self.wait_until_ready()
        if member.guild.id == GUILD_ID:
            if member.bot:
                await member.add_roles(self.bot_role, reason='Это бот')
                log.info(f'{member}: даю роль бота')

            t = (member.id, )
            is_user_leaved = self.cur.execute('select id from leaved_users where id=?', t).fetchone()
            if is_user_leaved:
                asyncio.get_event_loop().create_task(self.event_manager.send_return_message(member))
            else:
                asyncio.get_event_loop().create_task(self.event_manager.send_join_message(member))

                greeting_message = await self.text_channel.send(GREETING_MESSAGE.format(m=member.mention))
                await greeting_message.add_reaction('📕')
                try:
                    reaction, user = await self.wait_for('reaction_add', timeout=300.0, check=lambda r, u: u.id == member.id)
                except asyncio.TimeoutError:
                    log.info('Самостоятельный новичок попался.')
                    await greeting_message.clear_reactions()
                else:
                    await member.send(GUILD_ANNOTATION_MESSAGE)
                    await greeting_message.clear_reactions()
                    log.info('Новичок попросил помочь, отправил ему в лс сообщение.')
    
    async def on_nitro_boost(self, member):
        asyncio.get_event_loop().create_task(self.event_manager.send_boost_message(member))

    async def on_reaction_add(self, reaction, user):
        await self.wait_until_ready()
        if reaction.message == self.ban_message:
            log.info(f'{user}: акт самовыпила')
            await self.ban_message.clear_reactions()
            try:
                await self.guild.ban(user, reason='Самовыпил.', delete_message_days=0)
                asyncio.get_event_loop().create_task(self.event_manager.send_suicide_message(user))
                #await self.notifications_channel.send(f'{user.mention} предпочёл бан. Такова была его реакция: {str(reaction)}.')
                log.info('Желание было исполнено.')
            except discord.errors.Forbidden:
                log.warning('Недостаточно прав для бана!')
                asyncio.get_event_loop().create_task(self.event_manager.send_failed_suicide_message(user))
                # await self.notifications_channel.send(f'{user.mention} попытался покончить с собой, но у него не вышло! \nhttps://www.youtube.com/watch?v=Yic_aU1cmQ4')
        elif row := self.cur.execute('select author_id from suggestion_messages where message_id=?', (reaction.message.id, )).fetchone():
            if user != self.user:
                if reaction.emoji in ('✔', '❌', '♻'):
                    t = (reaction.message.id,)
                    self.remove_messages_from_fetch_list(reaction.message)
                    self.cur.execute('delete from suggestion_messages where message_id=?', t)
                    self.connection.commit()

                    author_id = row[0]
                    author = await self.fetch_user(author_id)
                    embed = reaction.message.embeds[0]
                    if reaction.emoji == '✔':
                        t = (author_id,)
                        action = 'принято'
                        new_color = discord.Colour(0x7fff00)
                        self.cur.execute('update or ignore trash_suggestions set strikes=0 where member_id=?', t)
                        self.connection.commit()
                        await self.suggestions_channel.set_permissions(self.guild.get_member(author_id), overwrite=None)
                    elif reaction.emoji == '❌':
                        action = 'отклонено'
                        new_color = discord.Colour(0xffa500)
                    elif reaction.emoji == '♻':
                        new_color = discord.Colour(0xff0000)
                        t = (author_id,)
                        if self.cur.execute('select * from trash_suggestions where member_id=?', t).fetchone():
                            self.cur.execute('update trash_suggestions set strikes=strikes+1 where member_id=?', t)
                            self.connection.commit()
                            if self.cur.execute('select strikes from trash_suggestions where member_id=?', t).fetchone()[0] >= 3:
                                await self.suggestions_channel.set_permissions(self.guild.get_member(author_id), send_messages=False)
                        else:
                            self.cur.execute('insert into trash_suggestions values (?, ?)', (author_id, 1))
                            self.connection.commit()

                        action = f'признано не подходящим по формату. Напоминаю, что доступ к предложениям блокируется после трёх некорректных обращений подряд'

                    embed.colour = new_color

                    await reaction.message.edit(embed=embed)
                    await reaction.message.clear_reactions()

                    embed.set_field_at(0, name='Штрафы', value=self.get_strikes(author_id))
                    await author.send(f'Обновление по Вашему запросу! Сообщаю, что Ваше предложение было {action}.', embed=embed)

    async def on_message(self, message):
        await self.wait_until_ready()
        if message.channel.type == discord.ChannelType.private:
            if message.author != self.user:
                if message.content != '+':
                    log.info(f'{message.author} поинтересовался, как на сервере всё работает.')
                    await message.channel.send(GUILD_ANNOTATION_MESSAGE)
        elif message.channel == self.suggestions_channel:
            await message.delete()
            embed = self.generate_embed(message)
            sugg_message = await self.admin_suggestions_channel.send(embed=embed)
            t = (sugg_message.id, message.author.id, None)
            self.cur.execute('insert into suggestion_messages values (?, ?, ?)', t)
            self.connection.commit()

            await message.author.send('Ваше предложение / жалоба на рассмотрении. Напоминаю, что три недопустимых обращения подряд влекут за собой блокировку доступа к каналу для жалоб.', embed=embed)
            await sugg_message.add_reaction('✔')
            await sugg_message.add_reaction('❌')
            await sugg_message.add_reaction('♻')
            self.add_messages_to_fetch_list(sugg_message)
        elif message.channel == self.admin_suggestions_channel:
            if message.reference:
                if message.reference.channel_id == self.admin_suggestions_channel.id:
                    if self.cur.execute('select * from suggestion_messages where message_id=?', (message.reference.message_id,)).fetchone():
                        sugg_message = await self.admin_suggestions_channel.fetch_message(message.reference.message_id)
                        embed = sugg_message.embeds[0]
                        if message.content:
                            if len(embed.fields) == 1:
                                embed.add_field(name='Комментарий администратора', value=message.content, inline=False)
                            else:
                                embed.set_field_at(1, name='Комментарий администратора', value=message.content, inline=False)
                        else:
                            if len(embed.fields) > 1:
                                embed.remove_field(1)
                        await message.delete()
                        new_sugg_message = await self.admin_suggestions_channel.send(embed=embed)
                        self.cur.execute('update suggestion_messages set message_id=? where message_id=?', (new_sugg_message.id, sugg_message.id))
                        self.connection.commit()
                        await new_sugg_message.add_reaction('✔')
                        await new_sugg_message.add_reaction('❌')
                        await new_sugg_message.add_reaction('♻')
                        self.add_messages_to_fetch_list(new_sugg_message)

                        await sugg_message.delete()

    async def on_member_update(self, before, after):
        if before.premium_since is None and after.premium_since is not None:
            await self.on_nitro_boost(after)

    def __del__(self):
        self.connection.close()


client = Client(intents=discord.Intents.all())  # Not good
client.run(DISCORD_BOT_TOKEN)
