import json
import sqlite3
import asyncio
import os

import discord
from loguru import logger as log

DISCORD_BOT_TOKEN = os.getenv('TOKEN')


class HostRoom:
    def __init__(self, client: discord.Client, connection, room):
        self.client = client
        self.room = room
        self.text_channel: discord.TextChannel = None
        self.thread = None
        self.owner = None
        self.valid = False

        self.connection = connection
        self.cursor = self.connection.cursor()

        self._load()

    def _load(self):
        row = self.cursor.execute('select guild_id, owner_id, thread_id from host_rooms where channel_id=?', (self.room.id,)).fetchone()
        if not row:
            raise KeyError()
        guild_id, owner_id, thread_id = row
        if not self.client.get_guild(guild_id):
            raise
        if not self.room:
            self.valid = False
            self.client.loop.create_task(self.delete())
            return
        self.owner = self.room.guild.get_member(owner_id)
        if not self.owner:
            self.valid = False
            self.client.loop.create_task(self.delete())
            return
        if self.owner not in self.room.members:
            self.valid = False
            self.client.loop.create_task(self.delete())
            return
        
        row = self.cursor.execute('SELECT host_text_channel_id FROM guilds WHERE guild_id=?', (self.room.guild.id,)).fetchone()
        host_text_channel_id = row[0]
        if host_text_channel_id:
            self.text_channel = self.client.get_channel(host_text_channel_id)

            if self.text_channel:
                row = self.cursor.execute('SELECT thread_id FROM host_rooms WHERE channel_id=?', (self.room.id,)).fetchone()
                thread_id = row[0]
                self.thread = self.text_channel.get_thread(thread_id)

        self.valid = True

    @property
    def id(self):
        return self.channel.id if self.channel else None

    @classmethod
    async def create(cls, client, connection, room: discord.VoiceChannel, owner: discord.Member):
        cursor = connection.cursor()

        allow_perms = discord.Permissions(2147483647)
        deny_perms = discord.Permissions(268435457)
        perms_overwrite = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
        await room.edit(name=owner.display_name, reason='temp',
                        overwrites={owner: perms_overwrite})

        row = cursor.execute('SELECT host_text_channel_id FROM guilds WHERE guild_id=?', (room.guild.id,)).fetchone()
        host_text_channel_id = row[0]
        if host_text_channel_id:
            text_channel = client.get_channel(host_text_channel_id)
        thread = await text_channel.create_thread(name=f'{owner.display_name}\'s thread', type=discord.enums.ChannelType.public_thread)

        await thread.send(f"{owner.mention}, вау, это твой новый тред! Я тут что-то типа прислуги, зови если что.")
        
        r = (room.id, owner.guild.id, owner.id, thread.id)
        cursor.execute("insert into host_rooms (channel_id, guild_id, owner_id, thread_id) values (?, ?, ?, ?)", r)
        connection.commit()
        return cls(client, connection, room)

    async def delete(self):
        remove_instantly = False
        if self.room:
            row = self.cursor.execute('select * from host_rooms where channel_id=?', (self.room.id,)).fetchone()
        remove_instantly = False if row else True
        if not remove_instantly:
            if self.room:
                if self.owner:
                    await asyncio.sleep(10)
                    if self.owner in self.room.members:
                        return False
            self.cursor.execute('delete from host_rooms where channel_id=?', (self.room.id,))
            self.connection.commit()
        if self.room:
            await self.room.delete()
        if self.thread:
            counter = 0
            async for message in self.thread.history(limit=5):
                #if not message.author.bot:
                #print('efef')
                counter += 1
            
            if counter <= 3:
                await self.thread.delete()
            else:
                await self.thread.edit(archived=True)
        self.valid = False
        return True

    async def on_member_connect(self, member):
        if self.thread:
            await self.thread.send(f'{member.mention}, добро пожаловать в тред {self.owner.display_name}! Не мусори тут, пожалуйста!')

    async def on_member_disconnect(self, member):
        if self.thread:
            await self.thread.send(f'{member.mention} нас покинул. Дружно скажите "пока-пока"!')
            await self.thread.remove_user(member)


class VoiceState:
    def __init__(self, client):
        self.client = client
        self.loop = self.client.loop

    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel:
            if not (before.channel and after.channel):
                if before.channel:
                    self.loop.create_task(self.on_member_remove(member, before))
                elif after.channel:
                    self.loop.create_task(self.on_member_join(member, after))
            else:
                self.loop.create_task(self.on_member_move(member, before, after))

    async def on_member_join(self, member, state):
        pass

    async def on_member_remove(self, member, state):
        pass

    async def on_member_move(self, member, before, after):
        pass


class HostRooms(VoiceState):
    def __init__(self, client, connection=None):
        super().__init__(client)
        self._host_rooms = []

        if connection != None:
            self.connection = connection
        else:
            self.connection = sqlite3.connect('./host_rooms.db')
            # huita

        self.cursor = self.connection.cursor()

    def get_room(self, room_id):
        f = filter(lambda r: r.room.id == room_id, self._host_rooms)
        f = list(f)
        if len(f) > 0:
            return f[0]

    async def on_ready(self):
        for channel_id in self.cursor.execute('select channel_id from host_rooms'):
            channel = self.client.get_channel(channel_id[0])
            if channel:
                room = HostRoom(self.client, self.connection, channel)
            else:
                continue
            if room.valid:
                self._host_rooms.append(room)

        for channel_id in self.cursor.execute('select host_channel_id from guilds'):
            channel_id = channel_id[0]
            channel = self.client.get_channel(channel_id)
            for member in channel.members:
                self.client.loop.create_task(self.room_create(member, channel))

    async def room_create(self, member, host_channel):
        if len(host_channel.members) > 1:
            return
        old_name = host_channel.name
        new_channel = await member.guild.create_voice_channel(
            name=old_name, category=host_channel.category)
        t = (new_channel.id, member.guild.id)
        self.cursor.execute('update guilds set host_channel_id=? where guild_id=?', t)
        self.connection.commit()

        room = await HostRoom.create(self.client, self.connection, host_channel, member)
        if room.valid:
            self._host_rooms.append(room)
        return room

    async def room_delete(self, room):
        if await room.delete():
            if room in self._host_rooms:
                self._host_rooms.remove(room)

    async def create_text_channel(self, host_room):
        owner_perms = discord.Permissions(523328)
        guest_perms = discord.Permissions(515136)
        overwrites = {}

        text_room = await host_room.guild.create_text_channel(
            name=host_room.name, position=host_room.position+1,
            overwrites=overwrites)

    async def create_channel(self, member, channel):
        if self.cursor.execute('select * from guilds where host_channel_id=?', (channel.id,)).fetchone():
            return await self.room_create(member, channel)

    async def proceed_join(self, member, channel):
        await self.client.wait_until_ready()
        room = await self.create_channel(member, channel)
        if room:
            if member != room.owner:
                await room.on_member_connect(member)
        else:
            room = self.get_room(channel.id)
            if room:
                await room.on_member_connect(member)
        

    async def delete_room(self, member, room):
        if member.id == room.owner.id:
            self.loop.create_task(self.room_delete(room))

    async def proceed_disconnect(self, member, channel):
        await self.client.wait_until_ready()

        room = self.get_room(channel.id)
        if room:
            await room.on_member_disconnect(member)
            await self.delete_room(member, room)

    async def on_member_join(self, member, state):
        log.info(f'{member}: join')
        self.loop.create_task(self.proceed_join(member, state.channel))

    async def on_member_move(self, member, before, after):
        log.info(f'{member}: move')
        self.loop.create_task(self.proceed_join(member, after.channel))

        room_t = self.cursor.execute('select owner_id from host_rooms where channel_id=?', (before.channel.id,)).fetchone()
        if room_t:
            if member.id == room_t[0]:
                room = self.get_room(before.channel.id)
                if room:
                    self.loop.create_task(self.proceed_disconnect(member, before.channel))
    
    async def on_member_remove(self, member, state):
        log.info(f'{member}: remove')
        self.loop.create_task(self.proceed_disconnect(member, state.channel))


if __name__ == '__main__':
    client = discord.Client(intents=discord.Intents.all())
    host_rooms = HostRooms(client)


    @client.event
    async def on_ready():
        await host_rooms.on_ready()
        print(f'Logged in Discord as {client.user}')
    

    @client.event
    async def on_voice_state_update(member, before, after):
        asyncio.get_event_loop().create_task(host_rooms.on_voice_state_update(member, before, after))
    

    client.run(DISCORD_BOT_TOKEN)
