"""
Endpoints de ingestão de eventos.

1) /webhook/whatsapp
   Webhook oficial do WhatsApp Cloud API (Meta). Recebe:
   - GET  -> verificação do endpoint (handshake exigido pela Meta)
   - POST -> mensagens e status (sent/delivered/read), que aqui são
             traduzidos para o schema normalizado (NormalizedEvent).

   IMPORTANTE (limitação real, não escondida): o WhatsApp Cloud API
   oficial é voltado principalmente para conversas 1:1 iniciadas pela
   empresa; o suporte a grupos é limitado/inexistente na API pública
   da Meta. Para captar eventos de GRUPOS de WhatsApp (o cenário do
   YahConect), a alternativa usada na prática é uma "ponte" própria
   (ex.: um processo Node.js com whatsapp-web.js/Baileys, escutando o
   WhatsApp Web da conta de um administrador do grupo) que empurra os
   eventos para o endpoint genérico abaixo. Ambas as fontes convergem
   para o MESMO pipeline de dados.

2) /events/ingest
   Endpoint genérico e agnóstico de fonte. Qualquer coletor (ponte de
   WhatsApp, bot de Telegram, integração com Slack, etc.) pode enviar
   eventos já normalizados aqui.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import NormalizedEvent
from app.repository import register_event

router = APIRouter()


# ── Verificação do webhook (Meta) ──────────────────────────────────
@router.get("/webhook/whatsapp")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido")


# ── Recebimento de eventos do WhatsApp Cloud API ───────────────────
@router.post("/webhook/whatsapp")
async def receive_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    events = _parse_cloud_api_payload(payload)

    for event in events:
        register_event(db, event)
    db.commit()

    return {"status": "ok", "events_processed": len(events)}


def _parse_cloud_api_payload(payload: dict) -> list[NormalizedEvent]:
    """Traduz o payload bruto da Meta para uma lista de NormalizedEvent."""
    normalized: list[NormalizedEvent] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            # Mensagens recebidas (texto, reação, resposta)
            for msg in value.get("messages", []):
                ts = datetime.fromtimestamp(int(msg["timestamp"]), tz=timezone.utc)
                sender = msg.get("from")
                sender_name = contacts.get(sender, "Desconhecido")

                if msg.get("type") == "reaction":
                    reaction = msg["reaction"]
                    normalized.append(NormalizedEvent(
                        source="whatsapp_cloud",
                        member_wa_id=sender,
                        member_name=sender_name,
                        message_wa_id=reaction["message_id"],
                        event_type="reacted",
                        event_timestamp=ts,
                        reaction_emoji=reaction.get("emoji"),
                    ))
                elif msg.get("context", {}).get("id"):
                    # resposta a outra mensagem
                    normalized.append(NormalizedEvent(
                        source="whatsapp_cloud",
                        member_wa_id=sender,
                        member_name=sender_name,
                        message_wa_id=msg["context"]["id"],
                        event_type="replied",
                        event_timestamp=ts,
                    ))
                    # a própria resposta também conta como participação
                    normalized.append(NormalizedEvent(
                        source="whatsapp_cloud",
                        member_wa_id=sender,
                        member_name=sender_name,
                        message_wa_id=msg["id"],
                        event_type="sent_by_member",
                        event_timestamp=ts,
                        message_type=msg.get("type", "text"),
                        content_preview=_extract_preview(msg),
                    ))
                else:
                    normalized.append(NormalizedEvent(
                        source="whatsapp_cloud",
                        member_wa_id=sender,
                        member_name=sender_name,
                        message_wa_id=msg["id"],
                        event_type="sent_by_member",
                        event_timestamp=ts,
                        message_type=msg.get("type", "text"),
                        content_preview=_extract_preview(msg),
                    ))

            # Status de mensagens enviadas pela organização (sent/delivered/read)
            for st in value.get("statuses", []):
                ts = datetime.fromtimestamp(int(st["timestamp"]), tz=timezone.utc)
                status_map = {"sent": "sent", "delivered": "delivered", "read": "read"}
                event_type = status_map.get(st.get("status"))
                if not event_type:
                    continue
                normalized.append(NormalizedEvent(
                    source="whatsapp_cloud",
                    member_wa_id=st.get("recipient_id"),
                    message_wa_id=st["id"],
                    event_type=event_type,
                    event_timestamp=ts,
                ))

    return normalized


def _extract_preview(msg: dict) -> str | None:
    if msg.get("type") == "text":
        return msg.get("text", {}).get("body", "")[:200]
    return f"[{msg.get('type')}]"


# ── Ingestão genérica (outras fontes / pontes não-oficiais) ────────
@router.post("/events/ingest")
def ingest_event(event: NormalizedEvent, db: Session = Depends(get_db)):
    db_event = register_event(db, event)
    db.commit()
    return {"status": "ok", "event_id": db_event.id}
