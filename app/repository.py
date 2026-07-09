"""
Funções de acesso a dados: upsert de Group/Member/Message e registro de eventos.
Mantidas separadas dos endpoints para poderem ser reutilizadas por scripts,
testes e pela camada de ETL.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Group, Member, Message, MessageEvent, EventType
from app.schemas import NormalizedEvent


def get_or_create_group(db: Session, wa_group_id: str, name: str | None) -> Group | None:
    if not wa_group_id:
        return None
    group = db.query(Group).filter_by(wa_group_id=wa_group_id).first()
    if group:
        return group
    group = Group(wa_group_id=wa_group_id, name=name or wa_group_id)
    db.add(group)
    db.flush()
    return group


def get_or_create_member(db: Session, wa_id: str, display_name: str | None) -> Member:
    member = db.query(Member).filter_by(wa_id=wa_id).first()
    if member:
        if display_name and display_name != "Desconhecido" and member.display_name != display_name:
            member.display_name = display_name
        return member
    member = Member(wa_id=wa_id, display_name=display_name or wa_id)
    db.add(member)
    db.flush()
    return member


def get_or_create_message(
    db: Session,
    wa_message_id: str,
    group: Group | None,
    sender_wa_id: str | None,
    message_type: str,
    content_preview: str | None,
    sent_at: datetime | None,
) -> Message:
    message = db.query(Message).filter_by(wa_message_id=wa_message_id).first()
    if message:
        return message
    message = Message(
        wa_message_id=wa_message_id,
        group_id=group.id if group else None,
        sender_wa_id=sender_wa_id,
        message_type=message_type,
        content_preview=content_preview,
        sent_at=sent_at or datetime.utcnow(),
    )
    db.add(message)
    db.flush()
    return message


def register_event(db: Session, event: NormalizedEvent) -> MessageEvent:
    """
    Ponto único de entrada para gravar um evento normalizado no banco.
    Garante que Group / Member / Message existam antes de registrar o evento.
    """
    group = get_or_create_group(db, event.group_wa_id, event.group_name)
    get_or_create_member(db, event.member_wa_id, event.member_name)

    sender_for_message = (
        event.member_wa_id if event.event_type == "sent_by_member" else None
    )
    message = get_or_create_message(
        db,
        wa_message_id=event.message_wa_id,
        group=group,
        sender_wa_id=sender_for_message,
        message_type=event.message_type,
        content_preview=event.content_preview,
        sent_at=event.original_sent_at or event.event_timestamp,
    )

    db_event = MessageEvent(
        message_id=message.id,
        member_wa_id=event.member_wa_id,
        event_type=EventType(event.event_type),
        event_timestamp=event.event_timestamp,
        reaction_emoji=event.reaction_emoji,
    )
    db.add(db_event)
    db.flush()
    return db_event
