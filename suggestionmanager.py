import datetime
import sqlite3
import time

import discord


class Suggestion:
    def __init__(self, connection: sqlite3.Connection, message: discord.Message):
        self._connection = connection
        self._cursor = self._connection.cursor()
        self._message = message
        self._message_id = message.id

        self._author_id, self._author_name, self._author_avatar_url, self._text, self._admin_response, self._is_active = \
            self._cursor.execute(
                'SELECT author_id, author_name, author_avatar_url, text, admin_response, is_active '
                'FROM suggestion_messages WHERE message_id=?', 
                (self.message_id,)
            ).fetchone()

    @property
    def message_id(self) -> int:
        return self._message_id
    
    @property
    def author_id(self) -> int:
        return self._author_id

    @property
    def admin_response(self) -> str:
        return self._admin_response

    @property
    def author_name(self) -> str:
        return self._author_name

    @property
    def author_avatar_url(self) -> str:
        return self._author_avatar_url

    @property
    def text(self) -> str:
        return self._text

    @property
    def strikes(self) -> int:
        return self._cursor.execute(
            'SELECT strikes FROM trash_suggestion WHERE member_id=?', 
            (self._author_id,)
        ).fetchone()[0]

    @property
    def active(self) -> bool:
        return bool(self._active)
    
    def set_active(self, value):
        self._cursor.execute('UPDATE suggestion_messages SET active=? WHERE message_id=?', (value, self._message_id))
        self._connection.commit()

    def _generate_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Новое предложение", description=self.text, timestamp=datetime.datetime.now())
        embed.set_author(name=self.author_name, icon_url=self.author_avatar_url)
        embed.add_field(name='Штрафы', value=self.strikes, inline=False)
        return embed

    async def set_response(self, respond_message: str):
        pass

    @classmethod
    async def create(cls):
        pass

    @classmethod
    async def dispose(cls, suggestion):
        pass


class SuggestionFactory:
    def __init__(self, db_path: str, suggestion_channel: discord.TextChannel, admin_suggestion_channel: discord.TextChannel):
        self._connection = sqlite3.connect(db_path)
        self._cursor = self._connection.cursor()
        self._suggestion_channel = suggestion_channel
        self._admin_suggestion_channel = admin_suggestion_channel

        self._suggestions = []

        self._load_suggestions

    def _load_suggestions(self):
        for message_id, author_id, admin_response in self._cursor.execute('select message_id, author_id, admin_responce from suggestion_messages'):
            self._suggestions.append(Suggestion(message_id, author_id, admin_response))
    
    async def create_suggestion(self) -> Suggestion:
        pass
