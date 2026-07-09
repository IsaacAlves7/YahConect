"""
Modelos de dados (schema) do YahConect.

Estrutura pensada para ETL/BI:
- Group        -> grupos/canais monitorados
- Member       -> pessoas que participam dos grupos
- Message      -> mensagens enviadas (o "fato" de comunicação)
- MessageEvent -> eventos ligados a uma mensagem (entregue, lida, reação, resposta)

MessageEvent é a tabela central para os KPIs: cada linha é um evento atômico
(quem, o quê, quando), no estilo "event log" usado em Data Engineering.
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class EventType(str, enum.Enum):
    SENT = "sent"          # mensagem enviada pelo bot/admin
    DELIVERED = "delivered"  # entregue ao dispositivo do membro
    READ = "read"           # lida (confirmação azul)
    REACTED = "reacted"     # reagiu com emoji
    REPLIED = "replied"     # respondeu (mensagem com contexto/reply)
    SENT_BY_MEMBER = "sent_by_member"  # membro enviou uma mensagem própria (participação)


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    wa_group_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="group")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    wa_id = Column(String(50), unique=True, index=True, nullable=False)  # número/whatsapp id
    display_name = Column(String(150), nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)

    events = relationship("MessageEvent", back_populates="member")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    wa_message_id = Column(String(120), unique=True, index=True, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    sender_wa_id = Column(String(50), nullable=True)
    message_type = Column(String(30), default="text")  # text, image, document, etc.
    content_preview = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="messages")
    events = relationship("MessageEvent", back_populates="message")


class MessageEvent(Base):
    __tablename__ = "message_events"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    member_wa_id = Column(String(50), ForeignKey("members.wa_id"), nullable=False)
    event_type = Column(
        SAEnum(EventType, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    event_timestamp = Column(DateTime, default=datetime.utcnow)
    reaction_emoji = Column(String(10), nullable=True)

    message = relationship("Message", back_populates="events")
    member = relationship("Member", back_populates="events")
