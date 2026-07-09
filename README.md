> Versículo chave: "Consagre ao Senhor tudo o que você faz, e os seus planos serão bem-sucedidos." - Provérbios 16:3

# 🐑♻️ YahConect

Bot/ETL para coletar eventos de mensagens do WhatsApp (e, futuramente, de outras origens) e transformá-los em KPIs de **engajamento e comunicação** para consumir os dados via API/ dashboards de BI / People Analytics / Community Analytics.

```
Origem do evento → Normalização → Banco de Dados → ETL (Pandas) → Dashboard (Streamlit)
```

## 1. Arquitetura

```
yahconect/
├── app/
│   ├── config.py       # variáveis de ambiente
│   ├── database.py     # engine/sessão SQLAlchemy (SQLite ou Postgres)
│   ├── models.py       # Group, Member, Message, MessageEvent
│   ├── schemas.py       # NormalizedEvent (schema único, agnóstico de origem)
│   ├── repository.py   # upsert de Group/Member/Message + gravação de eventos
│   └── webhook.py       # endpoints FastAPI (webhook Meta + ingestão genérica)
├── etl/
│   ├── load.py          # extração (E): lê o banco e devolve DataFrames
│   └── transform.py     # transformação (T): cálculo dos KPIs em Pandas
├── dashboard/
│   └── streamlit_app.py # dashboard de KPIs
├── scripts/
│   ├── init_db.py
│   └── seed_demo_data.py # gera dados fake para testar sem WhatsApp configurado
├── main.py               # API FastAPI
└── requirements.txt
```

A tabela `message_events` é o coração do sistema: um **event log**, no
estilo usado em Data Engineering, onde cada linha é um evento atômico
(quem, o quê, quando). Todos os KPIs são derivados dela.

### ⚠️ Sobre a fonte dos dados do WhatsApp (importante, sem enrolação)

O **WhatsApp Cloud API oficial (Meta)** — implementado aqui em
`app/webhook.py` — é a via legítima e sustentável para receber eventos de
mensagens (enviada/entregue/lida, reações, respostas), mas ele foi desenhado
para **conversas 1:1 iniciadas por uma empresa (WhatsApp Business)**. O
suporte a **grupos** é limitado/inexistente na API pública da Meta hoje.

Ou seja: para captar eventos de um **grupo de WhatsApp** de verdade (o
cenário descrito no seu briefing), a única forma prática é uma "ponte" não
oficial, como um processo separado em Node.js usando `whatsapp-web.js` ou
`Baileys`, conectado à conta do WhatsApp Web de um administrador do grupo.
Isso funciona bem tecnicamente, mas **não é um uso oficialmente suportado
pelo WhatsApp/Meta** — vale avaliar o risco (bloqueio de número) antes de
usar em produção.

Por isso o projeto foi desenhado com um **endpoint genérico e agnóstico de
origem** (`POST /events/ingest`), que recebe eventos já normalizados
(`NormalizedEvent`). Assim, dá pra plugar:
- o webhook oficial da Meta (1:1 ou futuros grupos oficiais);
- uma ponte não-oficial de grupos (Node.js + whatsapp-web.js/Baileys) que
  chama esse endpoint;
- outras origens completamente diferentes (Telegram, Slack, Discord, e-mail...),
  exatamente como você comentou no fim do seu briefing sobre o Fruzzy.

O pipeline de dados (banco, ETL, KPIs, dashboard) é **o mesmo, não importa a origem**.

### 📜 Nota sobre LGPD/privacidade

Este sistema coleta dados comportamentais (leitura, tempo de resposta,
reações) de pessoas reais. Antes de rodar em um grupo real:
- avise os participantes e obtenha consentimento (LGPD, art. 7º);
- defina uma política de retenção de dados;
- restrinja o acesso ao dashboard a quem realmente precisa ver esses KPIs.

## 2. Instalação

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Por padrão o `.env` usa SQLite (`yahconect.db`), sem precisar instalar nada
além do Python. Para Postgres, troque `DATABASE_URL` no `.env`.

## 3. Testar rapidamente com dados de demonstração

Sem precisar configurar o WhatsApp ainda:

```bash
python -m scripts.init_db
python -m scripts.seed_demo_data
streamlit run dashboard/streamlit_app.py
```

Isso gera 14 dias de eventos simulados (mensagens, leituras, reações,
respostas) para 8 membros fictícios e abre o dashboard com os KPIs.

## 4. Rodando a API (para receber eventos de verdade)

```bash
uvicorn main:app --reload --port 8000
```

- `GET  /` → health check
- `GET  /webhook/whatsapp` → verificação do webhook (usado pela Meta)
- `POST /webhook/whatsapp` → recebe eventos do WhatsApp Cloud API
- `POST /events/ingest` → recebe eventos normalizados de qualquer origem

### Configurando o webhook oficial da Meta

1. Crie um app em https://developers.facebook.com/apps → adicione o produto **WhatsApp**.
2. Em **API Setup**, pegue o `WHATSAPP_ACCESS_TOKEN` e o `WHATSAPP_PHONE_NUMBER_ID` e coloque no `.env`.
3. Exponha sua API publicamente para testes locais (ex.: `ngrok http 8000`).
4. Em **Configuration → Webhook**, aponte para `https://SEU_DOMINIO/webhook/whatsapp`,
   use o mesmo valor de `WHATSAPP_VERIFY_TOKEN` do `.env`, e assine os campos
   `messages`.

### Enviando um evento manualmente (ex.: de uma ponte de grupo)

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "whatsapp_bridge",
    "group_wa_id": "grupo-fruzzy",
    "group_name": "Comunidade Fruzzy",
    "member_wa_id": "5521999990000",
    "member_name": "Isaac",
    "message_wa_id": "wamid.abc123",
    "message_type": "text",
    "content_preview": "Bom dia, pessoal!",
    "event_type": "sent_by_member",
    "event_timestamp": "2026-07-04T10:00:00Z"
  }'
```

## 5. KPIs calculados (`etl/transform.py`)

| KPI | Fórmula |
|---|---|
| Taxa de Leitura | usuários que leram / usuários totais × 100 |
| Tempo Médio de Leitura | média (timestamp da leitura − timestamp de envio) |
| Engajamento | (respostas + reações) / mensagens enviadas × 100 |
| Mensagens/dia | total de mensagens / dias com atividade |
| Ranking de Engajamento | pontuação ponderada: leitura=1, reação=2, resposta=3, mensagem enviada=2 |
| Horário de Pico | distribuição de eventos por hora do dia |

Todas as funções recebem o mesmo `DataFrame` de eventos (`etl/load.load_events()`)
e podem ser chamadas isoladamente, reaproveitadas em notebooks, em outro
dashboard (Grafana/Superset/Metabase apontando direto pro Postgres) ou em
relatórios agendados.

## 6. Próximos passos sugeridos

- Job agendado (cron/Airflow) rodando o ETL e salvando snapshots diários dos KPIs.
- Autenticação no dashboard (Streamlit + senha, ou Superset/Metabase com RBAC).
- Adapters adicionais em `app/schemas.py`/`app/webhook.py` para Telegram, Slack, Discord.
- Alertas automáticos (ex.: "engajamento caiu 20% esta semana") via webhook para o próprio WhatsApp/Slack.


Isso é perfeitamente possível e, na verdade, é uma aplicação muito interessante de Engenharia de Dados, Observabilidade e Business Intelligence aplicada a comunidades.

O fluxo seria algo parecido com: 

```
WhatsApp → Bot → Coleta de Eventos → Banco de Dados → Processamento Python → Dashboard/KPIs
```

Imagine um grupo onde diariamente são enviados comunicados, treinamentos, normas ou conteúdos. O bot poderia registrar eventos como:

* Quem recebeu a mensagem
* Quem visualizou
* Quanto tempo demorou para visualizar
* Quem reagiu
* Quem respondeu
* Quantas mensagens cada pessoa enviou
* Frequência de participação
* Taxa de engajamento
* Horários de maior atividade

Os dados coletados poderiam gerar métricas como:

Taxa de Leitura:

$\text{Taxa de Leitura} = \frac{\text{Usuários que leram}}{\text{Usuários Totais}} \times 100$

Tempo Médio de Leitura:

$\text{Tempo Médio} = \frac{\sum \text{Tempo até leitura}}{\text{Quantidade de leituras}}$

Engajamento:

$\text{Engajamento} = \frac{\text{Respostas + Reações}}{\text{Mensagens Enviadas}}$

Por exemplo:

| Usuário | Leu | Respondeu | Reagiu |
| ------- | --- | --------- | ------ |
| João    | Sim | Sim       | Sim    |
| Maria   | Sim | Não       | Sim    |
| Pedro   | Não | Não       | Não    |

Dessa tabela poderiam surgir indicadores:

* 66% de leitura
* 33% de resposta
* 66% de reação

Em Python você poderia armazenar isso num PostgreSQL:

```python
CREATE TABLE group_events (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(100),
    event_type VARCHAR(50),
    message_id VARCHAR(100),
    event_date TIMESTAMP
);
```

Depois processar com Pandas:

```python
import pandas as pd

df = pd.read_sql(
    "SELECT * FROM group_events",
    connection
)

kpi_leitura = (
    df[df["event_type"] == "read"]["user_name"]
    .nunique()
)

usuarios = df["user_name"].nunique()

taxa = (kpi_leitura / usuarios) * 100

print(f"Taxa de leitura: {taxa:.2f}%")
```

E gerar dashboards com:

* Grafana
* Apache Superset
* Metabase
* Plotly Dash
* Streamlit

Um dashboard poderia mostrar algo semelhante:

```text
━━━━━━━━━━━━━━━━━━━━━━
KPIs DO GRUPO
━━━━━━━━━━━━━━━━━━━━━━

Taxa de Leitura:
92%

Participação:
78%

Mensagens por Dia:
534

Tempo Médio de Resposta:
18 min

Usuário Mais Ativo:
Isaac

Usuário Menos Ativo:
Pedro
━━━━━━━━━━━━━━━━━━━━━━
```

Um ranking de engajamento poderia ser exibido assim:

<img width="768" height="432" alt="Engajamento por membro" src="https://github.com/user-attachments/assets/7906a7c0-67c3-4c3d-8a63-9f4f553a0600" />

O mais interessante é que isso começa a se aproximar de um sistema de People Analytics ou Community Analytics. Você deixa de apenas saber quem está no grupo e passa a medir comportamento, adesão, consumo de informação, participação e impacto das comunicações.

Para um projeto como o Fruzzy, por exemplo, isso poderia ir além do WhatsApp. O mesmo motor poderia coletar eventos de Telegram, Discord, Slack, Teams, E-mail, LMS corporativos, PDFs distribuídos e portais internos, consolidando tudo em uma única plataforma de observabilidade humana, onde os KPIs não monitoram servidores ou aplicações, mas sim o fluxo de conhecimento e comunicação dentro de uma organização. Isso já entra num território bastante próximo de Data Engineering, Analytics Engineering e IA aplicada à análise comportamental.

Engajamento por membro

Exemplo de ranking de participação do grupo.

|membro|pontuacao|
|------|---------|
|Isaac |95       |
|João  |82       |
|Maria |76       |
|Pedro |34       |

Agora o webhook do WhatsApp Cloud API e o endpoint genérico de ingestão:Agora o `main.py` e o módulo de ETL (KPIs em Pandas):Agora o script de dados de demonstração (para testar sem depender do WhatsApp API) e o dashboard Streamlit:Agora os `__init__.py` e o README completo:Agora vou testar se o pipeline realmente funciona de ponta a ponta antes de entregar:Funcionou. Vamos testar o ETL/KPIs também:Tudo funcionando ponta a ponta. Agora a documentação (README) e o script de inicialização do banco:**YahConect** está pronto e testado ponta a ponta (rodei o seed de dados, o ETL e a API de verdade no sandbox antes de te entregar).

**Como está organizado:**

- `app/` — FastAPI: modelos (`Group`, `Member`, `Message`, `MessageEvent`), banco (SQLite por padrão, troca pra Postgres só mudando `DATABASE_URL`), e os endpoints
- `etl/` — `load.py` (extrai do banco pra DataFrame) e `transform.py` (calcula os KPIs: taxa de leitura, tempo médio de leitura, engajamento, ranking, horário de pico)
- `dashboard/streamlit_app.py` — o dashboard visual
- `scripts/seed_demo_data.py` — gera 14 dias de dados fake pra você testar sem precisar de credencial nenhuma

**Um ponto que preciso ser direto sobre:** o WhatsApp Cloud API oficial (Meta) — que é a via legítima e que implementei em `app/webhook.py` — não suporta bem **grupos**, só conversas 1:1 de empresa. Pra captar eventos de um grupo de verdade, na prática só dá com uma ponte não-oficial (Node.js + `whatsapp-web.js`/Baileys rodando numa conta), o que carrega risco de bloqueio de número. Por isso desenhei um endpoint genérico (`POST /events/ingest`) agnóstico de origem — o pipeline de dados (banco → ETL → dashboard) é o mesmo não importa se o evento vem do webhook oficial, de uma ponte de grupo, ou até de Telegram/Slack no futuro, como você mencionou pro Fruzzy. Isso está tudo documentado no README com mais detalhe.

Pra rodar agora:

```bash
pip install -r requirements.txt
python -m scripts.init_db
python -m scripts.seed_demo_data
streamlit run dashboard/streamlit_app.py
```
