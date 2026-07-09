"""
Camada de extração (o "E" do ETL): lê as tabelas do banco e devolve
DataFrames prontos para o processamento em etl/transform.py.
"""
import pandas as pd
from sqlalchemy import text

from app.database import engine


def load_events(group_wa_id: str | None = None) -> pd.DataFrame:
    """
    Retorna um DataFrame "wide" com uma linha por evento, já com o join
    de member, message e group feito no SQL (mais eficiente que juntar em pandas).
    """
    query = """
        SELECT
            me.id               AS event_id,
            me.event_type       AS event_type,
            me.event_timestamp  AS event_timestamp,
            me.reaction_emoji   AS reaction_emoji,
            m.wa_id             AS member_wa_id,
            m.display_name      AS member_name,
            msg.id              AS message_id,
            msg.wa_message_id   AS wa_message_id,
            msg.sent_at         AS message_sent_at,
            msg.sender_wa_id    AS message_sender_wa_id,
            g.wa_group_id       AS group_wa_id,
            g.name              AS group_name
        FROM message_events me
        JOIN members m   ON m.wa_id = me.member_wa_id
        JOIN messages msg ON msg.id = me.message_id
        LEFT JOIN groups g ON g.id = msg.group_id
    """
    if group_wa_id:
        query += " WHERE g.wa_group_id = :group_wa_id"
        params = {"group_wa_id": group_wa_id}
    else:
        params = {}

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    for col in ("event_timestamp", "message_sent_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


def load_members() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM members"), conn)
