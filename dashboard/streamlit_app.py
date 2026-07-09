"""
Dashboard de KPIs do YahConect (Streamlit).

Rodar com:
    streamlit run dashboard/streamlit_app.py
"""
import sys
from pathlib import Path

# permite rodar `streamlit run dashboard/streamlit_app.py` a partir da raiz do projeto
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from etl.load import load_events
from etl.transform import (
    build_summary, engagement_ranking, activity_by_hour,
)

st.set_page_config(page_title="YahConect — KPIs", page_icon="🐑", layout="wide")

st.title("🐑♻️ YahConect — KPIs do Grupo")
st.caption("Observabilidade de comunicação e engajamento em comunidades")

events = load_events()

if events.empty:
    st.warning(
        "Nenhum evento encontrado ainda. Rode `python -m scripts.seed_demo_data` "
        "para gerar dados de demonstração, ou configure o webhook do WhatsApp."
    )
    st.stop()

summary = build_summary(events)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Taxa de Leitura", f"{summary.read_rate_pct}%")
col2.metric("Engajamento", f"{summary.engagement_rate_pct}%")
col3.metric("Mensagens/dia", summary.messages_per_day)
col4.metric(
    "Tempo Médio de Leitura",
    f"{summary.avg_time_to_read_minutes} min" if summary.avg_time_to_read_minutes else "—",
)

col5, col6, col7 = st.columns(3)
col5.metric("Membros ativos", summary.total_members)
col6.metric("Usuário Mais Ativo", summary.most_active_user or "—")
col7.metric("Usuário Menos Ativo", summary.least_active_user or "—")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("📊 Ranking de Engajamento")
    ranking = engagement_ranking(events)
    st.dataframe(ranking, use_container_width=True, hide_index=True)

    fig_ranking = px.bar(
        ranking, x="membro", y="pontuacao", color="pontuacao",
        color_continuous_scale="Blues", title="Pontuação por membro",
    )
    st.plotly_chart(fig_ranking, use_container_width=True)

with right:
    st.subheader("🕒 Horários de Maior Atividade")
    hourly = activity_by_hour(events)
    fig_hour = px.line(hourly, x="hour", y="events", markers=True, title="Eventos por hora do dia")
    st.plotly_chart(fig_hour, use_container_width=True)

st.divider()
st.subheader("📄 Eventos brutos (amostra)")
st.dataframe(
    events.sort_values("event_timestamp", ascending=False).head(200),
    use_container_width=True, hide_index=True,
)
