"""
Gera dados de demonstração para você testar o dashboard sem precisar
ter o WhatsApp Cloud API configurado ainda.

Uso:
    python -m scripts.seed_demo_data
"""
import random
from datetime import datetime, timedelta

from faker import Faker

from app.database import init_db, get_session
from app.schemas import NormalizedEvent
from app.repository import register_event

fake = Faker("pt_BR")
random.seed(42)

GROUP_WA_ID = "grupo-demo-001"
GROUP_NAME = "Comunidade Fruzzy"

NOMES = ["Isaac", "João", "Maria", "Pedro", "Ana", "Lucas", "Beatriz", "Rafael"]


def gerar_membros(n=8):
    return [
        {"wa_id": f"55219{1000000 + i}", "name": nome}
        for i, nome in zip(range(n), NOMES[:n])
    ]


def main():
    init_db()
    membros = gerar_membros()

    with get_session() as db:
        base_date = datetime.utcnow() - timedelta(days=14)

        for dia in range(14):
            n_mensagens = random.randint(1, 5)
            for _ in range(n_mensagens):
                sent_at = base_date + timedelta(days=dia, hours=random.randint(7, 22))
                autor = random.choice(membros)
                message_wa_id = f"wamid.demo.{dia}.{random.randint(1000,9999)}"

                # mensagem enviada pelo membro (participação)
                with_db_event = NormalizedEvent(
                    source="whatsapp_bridge",
                    group_wa_id=GROUP_WA_ID,
                    group_name=GROUP_NAME,
                    member_wa_id=autor["wa_id"],
                    member_name=autor["name"],
                    message_wa_id=message_wa_id,
                    message_type="text",
                    content_preview=fake.sentence(),
                    event_type="sent_by_member",
                    event_timestamp=sent_at,
                )
                register_event(db, with_db_event)

                # demais membros leem / reagem / respondem com probabilidades diferentes
                for membro in membros:
                    if membro["wa_id"] == autor["wa_id"]:
                        continue

                    if random.random() < 0.85:  # leu
                        delay = timedelta(minutes=random.randint(1, 240))
                        register_event(db, NormalizedEvent(
                            source="whatsapp_bridge",
                            group_wa_id=GROUP_WA_ID,
                            group_name=GROUP_NAME,
                            member_wa_id=membro["wa_id"],
                            member_name=membro["name"],
                            message_wa_id=message_wa_id,
                            event_type="read",
                            event_timestamp=sent_at + delay,
                            original_sent_at=sent_at,
                        ))

                    if random.random() < 0.25:  # reagiu
                        register_event(db, NormalizedEvent(
                            source="whatsapp_bridge",
                            group_wa_id=GROUP_WA_ID,
                            group_name=GROUP_NAME,
                            member_wa_id=membro["wa_id"],
                            member_name=membro["name"],
                            message_wa_id=message_wa_id,
                            event_type="reacted",
                            event_timestamp=sent_at + timedelta(minutes=random.randint(1, 60)),
                            reaction_emoji=random.choice(["👍", "❤️", "😂", "🙏"]),
                        ))

                    if random.random() < 0.15:  # respondeu
                        register_event(db, NormalizedEvent(
                            source="whatsapp_bridge",
                            group_wa_id=GROUP_WA_ID,
                            group_name=GROUP_NAME,
                            member_wa_id=membro["wa_id"],
                            member_name=membro["name"],
                            message_wa_id=message_wa_id,
                            event_type="replied",
                            event_timestamp=sent_at + timedelta(minutes=random.randint(1, 120)),
                        ))

    print("Dados de demonstração gerados com sucesso em yahconect.db ✅")


if __name__ == "__main__":
    main()
