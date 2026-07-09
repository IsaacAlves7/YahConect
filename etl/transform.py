"""
Camada de transformação (o "T" do ETL): recebe o DataFrame de eventos
(vindo de etl/load.py) e calcula os KPIs de People/Community Analytics.

Todas as funções recebem o mesmo df de eventos e devolvem um valor ou
um DataFrame pequeno já pronto para exibir no dashboard.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class KpiSummary:
    total_members: int
    total_messages: int
    read_rate_pct: float
    engagement_rate_pct: float
    avg_time_to_read_minutes: float | None
    messages_per_day: float
    most_active_user: str | None
    least_active_user: str | None


def _messages_df(events: pd.DataFrame) -> pd.DataFrame:
    """Um evento por mensagem (independente de quem viu/reagiu)."""
    return events.drop_duplicates(subset=["message_id"])[
        ["message_id", "wa_message_id", "message_sent_at", "message_sender_wa_id"]
    ]


def total_unique_members(events: pd.DataFrame) -> int:
    return events["member_wa_id"].nunique()


def read_rate(events: pd.DataFrame) -> float:
    """
    % de membros (dentre os que interagiram de alguma forma) que já
    leram pelo menos uma mensagem.
    """
    total = total_unique_members(events)
    if total == 0:
        return 0.0
    leram = events.loc[events["event_type"] == "read", "member_wa_id"].nunique()
    return round((leram / total) * 100, 2)


def avg_time_to_read_minutes(events: pd.DataFrame) -> float | None:
    """
    Tempo médio (minutos) entre o envio da mensagem e a leitura,
    calculado por par (mensagem, membro).
    """
    reads = events[events["event_type"] == "read"].copy()
    if reads.empty:
        return None
    reads["delta_min"] = (
        reads["event_timestamp"] - reads["message_sent_at"]
    ).dt.total_seconds() / 60
    reads = reads[reads["delta_min"] >= 0]  # descarta inconsistências
    if reads.empty:
        return None
    return round(reads["delta_min"].mean(), 2)


def engagement_rate(events: pd.DataFrame) -> float:
    """
    (Respostas + Reações) / Mensagens enviadas, em %.
    Mede o quanto o conteúdo gera interação ativa, não só leitura passiva.
    """
    msgs = _messages_df(events)
    total_msgs = len(msgs)
    if total_msgs == 0:
        return 0.0
    respostas = (events["event_type"] == "replied").sum()
    reacoes = (events["event_type"] == "reacted").sum()
    return round(((respostas + reacoes) / total_msgs) * 100, 2)


def messages_per_day(events: pd.DataFrame) -> float:
    msgs = _messages_df(events)
    if msgs.empty:
        return 0.0
    dias = msgs["message_sent_at"].dt.date.nunique() or 1
    return round(len(msgs) / dias, 2)


def activity_by_hour(events: pd.DataFrame) -> pd.DataFrame:
    """Distribuição de eventos por hora do dia — para achar picos de atividade."""
    if events.empty:
        return pd.DataFrame(columns=["hour", "events"])
    df = events.copy()
    df["hour"] = df["event_timestamp"].dt.hour
    out = df.groupby("hour").size().reset_index(name="events")
    return out.sort_values("hour")


def engagement_ranking(events: pd.DataFrame) -> pd.DataFrame:
    """
    Ranking por membro com pontuação de engajamento, no espírito da
    tabela do briefing (leu / respondeu / reagiu / enviou).

    Pontuação = 1 ponto por leitura + 2 por reação + 3 por resposta
    + 2 por mensagem própria enviada. Pesos arbitrários, fáceis de calibrar.
    """
    if events.empty:
        return pd.DataFrame(columns=["membro", "leu", "respondeu", "reagiu", "enviou", "pontuacao"])

    weights = {
        "read": 1,
        "reacted": 2,
        "replied": 3,
        "sent_by_member": 2,
    }

    pivot = (
        events.groupby(["member_wa_id", "member_name", "event_type"])
        .size()
        .unstack(fill_value=0)
    )

    for col in ("read", "reacted", "replied", "sent_by_member"):
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["pontuacao"] = sum(pivot[col] * w for col, w in weights.items())

    result = pivot.reset_index().rename(columns={
        "member_name": "membro",
        "read": "leu",
        "reacted": "reagiu",
        "replied": "respondeu",
        "sent_by_member": "enviou",
    })

    result = result[["membro", "leu", "respondeu", "reagiu", "enviou", "pontuacao"]]
    return result.sort_values("pontuacao", ascending=False).reset_index(drop=True)


def build_summary(events: pd.DataFrame) -> KpiSummary:
    ranking = engagement_ranking(events)
    most_active = ranking.iloc[0]["membro"] if not ranking.empty else None
    least_active = ranking.iloc[-1]["membro"] if not ranking.empty else None

    return KpiSummary(
        total_members=total_unique_members(events),
        total_messages=len(_messages_df(events)),
        read_rate_pct=read_rate(events),
        engagement_rate_pct=engagement_rate(events),
        avg_time_to_read_minutes=avg_time_to_read_minutes(events),
        messages_per_day=messages_per_day(events),
        most_active_user=most_active,
        least_active_user=least_active,
    )
