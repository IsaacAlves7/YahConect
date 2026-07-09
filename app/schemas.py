"""
Schema normalizado de evento (Pydantic).

A ideia: não importa se o evento vem do WhatsApp Cloud API, de uma ponte
não-oficial (Baileys/whatsapp-web.js), do Telegram, do Slack etc. — tudo
é traduzido para este formato único antes de cair no banco. Isso é o que
permite, no futuro, plugar outras fontes (Discord, Teams, e-mail, LMS...)
sem mexer no restante do pipeline.
"""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

EventTypeLiteral = Literal[
    "sent", "delivered", "read", "reacted", "replied", "sent_by_member"
]


class NormalizedEvent(BaseModel):
    source: str = Field(..., description="Ex.: whatsapp_cloud, whatsapp_bridge, telegram")
    group_wa_id: Optional[str] = Field(None, description="ID do grupo/canal na origem")
    group_name: Optional[str] = None

    member_wa_id: str = Field(..., description="ID único do membro na origem (telefone, etc.)")
    member_name: Optional[str] = "Desconhecido"

    message_wa_id: str = Field(..., description="ID único da mensagem na origem")
    message_type: str = "text"
    content_preview: Optional[str] = None

    event_type: EventTypeLiteral
    event_timestamp: datetime
    reaction_emoji: Optional[str] = None

    # Para eventos de leitura/entrega, é útil saber quando a mensagem original
    # foi enviada, para calcular "tempo até leitura" mesmo que a mensagem já
    # exista no banco.
    original_sent_at: Optional[datetime] = None
