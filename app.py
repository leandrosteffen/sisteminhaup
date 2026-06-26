"""
Dashboard de Análise de Desempenho Acadêmico
Visualização interativa de dados acadêmicos com pandas + streamlit + plotly
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Análise Acadêmica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CARREGAMENTO E PREPARO DOS DADOS
# ============================================================
@st.cache_data
def carregar_dados(caminho: str) -> pd.DataFrame:
    df = pd.read_csv(caminho)

    # Média vem como string com vírgula decimal (formato BR)
    df["media"] = df["media"].astype(str).str.replace(",", ".").astype(float)

    # Taxa de frequência (mais informativa que faltas/presenças isoladas)
    df["total_aulas"] = df["faltas"] + df["presencas"]
    df["taxa_frequencia"] = df["presencas"] / df["total_aulas"].replace(0, pd.NA)
    df["taxa_frequencia"] = df["taxa_frequencia"].fillna(0)

    # Flag de reprovação (nota OU falta) — útil para várias agregações
    df["reprovado"] = df["status_aluno_classe"].isin(
        ["Reprovado por Nota", "Reprovado por Falta"]
    )
    df["aprovado"] = df["status_aluno_classe"].isin(
        ["Aprovado por Nota", "Aprovado por Convalidação", "Aprovado por Exame de Suficiência"]
    )

    # Período letivo como categoria ordenável (ano + semestre do calendário)
    df["periodo_letivo"] = df["periodo_letivo"].astype(str)

    # Data de fechamento como datetime (10 nulos esperados)
    df["data_fechamento"] = pd.to_datetime(df["data_fechamento"], errors="coerce")

    return df


df_raw = carregar_dados("dados_anonimizados.csv")

# ============================================================
# SIDEBAR — FILTROS
# ============================================================
st.sidebar.title("🎛️ Filtros")
st.sidebar.markdown("Use os filtros abaixo para refinar a análise.")

cursos = sorted(df_raw["curso"].unique())
filtro_curso = st.sidebar.multiselect("Curso", cursos, default=cursos)

periodos = sorted(df_raw["periodo_letivo"].unique())
filtro_periodo = st.sidebar.multiselect("Período letivo", periodos, default=periodos)

semestres = sorted(df_raw["semestre"].unique())
filtro_semestre = st.sidebar.multiselect("Semestre", semestres, default=semestres)

status_classe = sorted(df_raw["status_aluno_classe"].unique())
filtro_status = st.sidebar.multiselect(
    "Situação na disciplina", status_classe, default=status_classe
)

# Disciplina depende do curso selecionado — filtro em cascata
ucs_disponiveis = sorted(
    df_raw[df_raw["curso"].isin(filtro_curso)]["unidade_curricular"].unique()
)
filtro_uc = st.sidebar.multiselect(
    "Unidade curricular (opcional)", ucs_disponiveis, default=[]
)

st.sidebar.markdown("---")
faixa_freq = st.sidebar.slider(
    "Taxa de frequência mínima", 0.0, 1.0, 0.0, step=0.05, format="%.0f%%"
)

# Aplicação dos filtros
df = df_raw[
    df_raw["curso"].isin(filtro_curso)
    & df_raw["periodo_letivo"].isin(filtro_periodo)
    & df_raw["semestre"].isin(filtro_semestre)
    & df_raw["status_aluno_classe"].isin(filtro_status)
    & (df_raw["taxa_frequencia"] >= faixa_freq)
]
if filtro_uc:
    df = df[df["unidade_curricular"].isin(filtro_uc)]

st.sidebar.markdown("---")
st.sidebar.caption(f"📌 {len(df):,} registros após filtro (de {len(df_raw):,} totais)")

# ============================================================
# CABEÇALHO E KPIs
# ============================================================
st.title("📊 Painel de Análise de Desempenho Acadêmico")
st.caption("Explore relações entre frequência, notas, cursos e disciplinas")

if df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Estudantes", f"{df['estudante'].nunique():,}")
col2.metric("Registros (matrícula-disciplina)", f"{len(df):,}")
col3.metric("Média geral", f"{df['media'].mean():.2f}")
col4.metric("Taxa de frequência média", f"{df['taxa_frequencia'].mean()*100:.1f}%")
col5.metric("Taxa de reprovação", f"{df['reprovado'].mean()*100:.1f}%")

st.markdown("---")

# ============================================================
# ABAS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["🔗 Frequência × Desempenho", "🎓 Cursos e Disciplinas", "📈 Evolução Temporal", "🧑‍🎓 Visão por Aluno"]
)

# ------------------------------------------------------------
# TAB 1 — FREQUÊNCIA x DESEMPENHO (a correlação mais forte do dataset)
# ------------------------------------------------------------
with tab1:
    st.subheader("Relação entre frequência e nota final")
    st.markdown(
        "A taxa de frequência é o fator mais correlacionado com a média final "
        "neste conjunto de dados. O gráfico abaixo evidencia essa relação."
    )

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig_scatter = px.scatter(
            df,
            x="taxa_frequencia",
            y="media",
            color="curso",
            opacity=0.55,
            hover_data=["estudante", "unidade_curricular", "status_aluno_classe"],
            labels={"taxa_frequencia": "Taxa de frequência", "media": "Média final"},
            title="Frequência vs. Média (cada ponto = uma disciplina cursada)",
        )
        fig_scatter.update_layout(xaxis_tickformat=".0%", height=480)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_b:
        corr = df[["faltas", "presencas", "taxa_frequencia", "media"]].corr()
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1,
            title="Matriz de correlação",
        )
        fig_corr.update_layout(height=480)
        st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("##### Distribuição de faltas por situação final")
    fig_box = px.box(
        df,
        x="status_aluno_classe",
        y="faltas",
        color="status_aluno_classe",
        points=False,
        labels={"status_aluno_classe": "Situação", "faltas": "Faltas"},
    )
    fig_box.update_layout(showlegend=False, height=420, xaxis_tickangle=-30)
    st.plotly_chart(fig_box, use_container_width=True)

# ------------------------------------------------------------
# TAB 2 — CURSOS E DISCIPLINAS
# ------------------------------------------------------------
with tab2:
    st.subheader("Comparação entre cursos")

    col_a, col_b = st.columns(2)

    with col_a:
        media_curso = (
            df.groupby("curso")["media"].mean().sort_values(ascending=True).reset_index()
        )
        fig_curso_media = px.bar(
            media_curso,
            x="media",
            y="curso",
            orientation="h",
            text_auto=".2f",
            labels={"media": "Média", "curso": "Curso"},
            title="Média final por curso",
            color="media",
            color_continuous_scale="Blues",
        )
        fig_curso_media.update_layout(height=400, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_curso_media, use_container_width=True)

    with col_b:
        repr_curso = (
            df.groupby("curso")["reprovado"].mean().sort_values(ascending=True).reset_index()
        )
        fig_curso_repr = px.bar(
            repr_curso,
            x="reprovado",
            y="curso",
            orientation="h",
            text_auto=".1%",
            labels={"reprovado": "Taxa de reprovação", "curso": "Curso"},
            title="Taxa de reprovação por curso",
            color="reprovado",
            color_continuous_scale="Reds",
        )
        fig_curso_repr.update_layout(
            height=400, showlegend=False, xaxis_tickformat=".0%", coloraxis_showscale=False
        )
        st.plotly_chart(fig_curso_repr, use_container_width=True)

    st.markdown("---")
    st.subheader("Ranking de disciplinas por taxa de reprovação")
    st.caption("Apenas disciplinas com pelo menos N matrículas no recorte filtrado")

    min_matriculas = st.slider("Mínimo de matrículas para considerar a disciplina", 5, 50, 15)

    uc_stats = (
        df.groupby("unidade_curricular")
        .agg(taxa_reprovacao=("reprovado", "mean"), media=("media", "mean"), n=("reprovado", "size"))
        .query("n >= @min_matriculas")
        .sort_values("taxa_reprovacao", ascending=False)
        .head(15)
        .reset_index()
    )

    if uc_stats.empty:
        st.info("Nenhuma disciplina atinge o mínimo de matrículas com os filtros atuais.")
    else:
        fig_uc = px.bar(
            uc_stats,
            x="taxa_reprovacao",
            y="unidade_curricular",
            orientation="h",
            text_auto=".1%",
            hover_data=["media", "n"],
            labels={"taxa_reprovacao": "Taxa de reprovação", "unidade_curricular": "Disciplina"},
            color="taxa_reprovacao",
            color_continuous_scale="Reds",
        )
        fig_uc.update_layout(
            height=500,
            yaxis={"categoryorder": "total ascending"},
            xaxis_tickformat=".0%",
            showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_uc, use_container_width=True)

    st.markdown("---")
    st.subheader("Distribuição de notas por curso")
    fig_violin = px.violin(
        df, x="curso", y="media", color="curso", box=True, points=False,
        labels={"media": "Média final", "curso": "Curso"},
    )
    fig_violin.update_layout(height=450, showlegend=False, xaxis_tickangle=-15)
    st.plotly_chart(fig_violin, use_container_width=True)

# ------------------------------------------------------------
# TAB 3 — EVOLUÇÃO TEMPORAL
# ------------------------------------------------------------
with tab3:
    st.subheader("Evolução do desempenho ao longo dos semestres")
    st.caption(
        "Semestre aqui representa a posição do aluno no curso (1º, 2º, 3º...), "
        "não o calendário civil — útil para ver maturação/afunilamento."
    )

    media_sem = df.groupby("semestre").agg(media=("media", "mean"), n=("media", "size")).reset_index()
    fig_eval = go.Figure()
    fig_eval.add_trace(
        go.Scatter(
            x=media_sem["semestre"], y=media_sem["media"], mode="lines+markers",
            name="Média", line=dict(color="#2563eb", width=3), marker=dict(size=8),
        )
    )
    fig_eval.add_trace(
        go.Bar(
            x=media_sem["semestre"], y=media_sem["n"], name="Nº de registros",
            yaxis="y2", opacity=0.25, marker_color="#94a3b8",
        )
    )
    fig_eval.update_layout(
        title="Média final e volume de registros por semestre do curso",
        xaxis_title="Semestre do curso",
        yaxis=dict(title="Média final"),
        yaxis2=dict(title="Nº de registros", overlaying="y", side="right", showgrid=False),
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_eval, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Comparação entre períodos letivos")
        comp_periodo = (
            df.groupby("periodo_letivo")
            .agg(media=("media", "mean"), reprovacao=("reprovado", "mean"), n=("media", "size"))
            .reset_index()
        )
        fig_periodo = px.bar(
            comp_periodo, x="periodo_letivo", y="media", text_auto=".2f",
            labels={"periodo_letivo": "Período letivo", "media": "Média"},
            color="periodo_letivo",
        )
        fig_periodo.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig_periodo, use_container_width=True)

    with col_b:
        st.markdown("##### Reprovação por semestre do curso")
        repr_sem = df.groupby("semestre")["reprovado"].mean().reset_index()
        fig_repr_sem = px.line(
            repr_sem, x="semestre", y="reprovado", markers=True,
            labels={"semestre": "Semestre do curso", "reprovado": "Taxa de reprovação"},
        )
        fig_repr_sem.update_layout(height=380, yaxis_tickformat=".0%")
        st.plotly_chart(fig_repr_sem, use_container_width=True)

# ------------------------------------------------------------
# TAB 4 — VISÃO POR ALUNO
# ------------------------------------------------------------
with tab4:
    st.subheader("Consulta individual de estudante")

    estudantes = sorted(df["estudante"].unique())
    aluno_sel = st.selectbox("Selecione um estudante", estudantes)

    df_aluno = df[df["estudante"] == aluno_sel].sort_values(["semestre", "unidade_curricular"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Disciplinas cursadas", len(df_aluno))
    col2.metric("Média geral", f"{df_aluno['media'].mean():.2f}")
    col3.metric("Frequência média", f"{df_aluno['taxa_frequencia'].mean()*100:.1f}%")
    col4.metric("Reprovações", int(df_aluno["reprovado"].sum()))

    fig_aluno = px.bar(
        df_aluno,
        x="unidade_curricular",
        y="media",
        color="status_aluno_classe",
        labels={"unidade_curricular": "Disciplina", "media": "Média"},
        title=f"Notas de {aluno_sel} por disciplina",
    )
    fig_aluno.update_layout(height=450, xaxis_tickangle=-40)
    st.plotly_chart(fig_aluno, use_container_width=True)

    st.markdown("##### Detalhamento")
    st.dataframe(
        df_aluno[
            [
                "unidade_curricular", "curso", "semestre", "periodo_letivo",
                "faltas", "presencas", "taxa_frequencia", "media", "status_aluno_classe",
            ]
        ].style.format({"taxa_frequencia": "{:.1%}", "media": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# RODAPÉ — DADOS BRUTOS
# ============================================================
st.markdown("---")
with st.expander("📋 Ver dados filtrados (tabela completa)"):
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Baixar dados filtrados (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        "dados_filtrados.csv",
        "text/csv",
    )
