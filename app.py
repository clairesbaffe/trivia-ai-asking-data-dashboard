import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Configuration de la page ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Trivia — Benchmark LLM",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent / "gold" / "gold.db"

# Palette de couleurs qualitative étendue pour s'adapter dynamiquement à N modèles
EXTENDED_PALETTE = [
    "#6366F1",  # Indigo (LLaMA)
    "#0EA5E9",  # Sky Blue (Gemma)
    "#10B981",  # Émeraude
    "#F59E0B",  # Ambre
    "#EC4899",  # Rose
    "#8B5CF6",  # Violet
    "#14B8A6",  # Sarcelle
    "#F97316",  # Orange
    "#06B6D4",  # Cyan
    "#84CC16",  # Lime
    "#E11D48",  # Rose foncé
    "#64748B",  # Ardoise
]

def get_color_map(models: list[str]) -> dict[str, str]:
    """Attribue des couleurs stables et distinctes quel que soit le nombre de modèles."""
    known = {
        "llama-3.2-3b-instruct": "#6366F1",
        "google/gemma-3-1b": "#0EA5E9",
    }
    mapping = {}
    palette_idx = 0
    for m in models:
        if m in known:
            mapping[m] = known[m]
        else:
            while palette_idx < len(EXTENDED_PALETTE) and EXTENDED_PALETTE[palette_idx] in mapping.values():
                palette_idx += 1
            mapping[m] = EXTENDED_PALETTE[palette_idx % len(EXTENDED_PALETTE)]
            palette_idx += 1
    return mapping

DIFFICULTY_ORDER = ["easy", "medium", "hard"]
DIFFICULTY_LABELS = {
    "easy": "Facile",
    "medium": "Moyen",
    "hard": "Difficile",
}

LENGTH_ORDER = ["Courte (< 80 car.)", "Moyenne (80-130 car.)", "Longue (> 130 car.)"]

QTYPE_LABELS = {
    "boolean": "Vrai / Faux (Boolean)",
    "multiple": "Choix Multiple (QCM)",
}

# ── Helpers de chargement des données ─────────────────────────────────────────

@st.cache_data(ttl=30)
def load_all_marts():
    """Charge tous les marts dbt depuis gold.db et ferme immédiatement la connexion."""
    if not DB_PATH.exists():
        return None

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        def fetch_df(table_name: str) -> pd.DataFrame:
            try:
                return conn.execute(f'SELECT * FROM "{table_name}"').fetchdf()
            except Exception:
                return pd.DataFrame()

        data = {
            "model_acc": fetch_df("mart_model_accuracy"),
            "diff_acc": fetch_df("mart_accuracy_by_difficulty"),
            "qtype_acc": fetch_df("mart_accuracy_by_question_type"),
            "cat_acc": fetch_df("mart_accuracy_by_category"),
            "unformatted": fetch_df("mart_unformatted_answers"),
            "rt_model": fetch_df("mart_response_time_by_model"),
            "rt_length": fetch_df("mart_response_time_by_question_length"),
            "rt_diff": fetch_df("mart_response_time_by_difficulty"),
            "rt_correctness": fetch_df("mart_response_time_by_correctness"),
        }
    finally:
        conn.close()

    return data


# ── Chargement des données ────────────────────────────────────────────────────

marts_data = load_all_marts()

# ── Barre latérale (Filtres & Contrôles) ───────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Contrôles")
    st.caption(f"Source de données : `{DB_PATH.name}`")

    if st.button("🔄 Rafraîchir les données", key="sidebar_btn_refresh_data", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    all_models = []
    if marts_data is not None and not marts_data["model_acc"].empty:
        all_models = sorted(marts_data["model_acc"]["model_name"].unique().tolist())

    selected_models = st.multiselect(
        "Modèles à comparer :",
        options=all_models,
        default=all_models,
        key="sidebar_multiselect_models",
    )

    st.markdown("---")
    st.markdown(
        """
        **Axes d'analyse :**
        - 🎯 **Précision & Taux de Succès** : Modèles, formats, difficultés, 24 catégories et conformité (NULL).
        - ⚡ **Temps de Réponse & Latence** : Vitesse globale, impact de la longueur, de la difficulté et du résultat.
        """
    )

# ── Contrôle de validité des données ──────────────────────────────────────────

if (
    marts_data is None
    or marts_data["model_acc"].empty
    or marts_data["rt_model"].empty
):
    st.warning(
        "⚠️ Données manquantes ou incomplètes dans la base `gold.db`.\n\n"
        "Veuillez exécuter `dbt run` pour compiler et matérialiser l'ensemble des marts.",
        icon="⚠️",
    )
    st.stop()

if not selected_models:
    st.info("Veuillez sélectionner au moins un modèle dans le panneau latéral pour afficher le benchmark.", icon="ℹ️")
    st.stop()

# Génération dynamique des couleurs pour les modèles sélectionnés
ACTIVE_MODEL_COLORS = get_color_map(all_models)

# Filtrage par modèles sélectionnés pour l'Accuracy
filtered_model = marts_data["model_acc"][marts_data["model_acc"]["model_name"].isin(selected_models)].copy()
filtered_diff = marts_data["diff_acc"][marts_data["diff_acc"]["model_name"].isin(selected_models)].copy()
filtered_qtype = marts_data["qtype_acc"][marts_data["qtype_acc"]["model_name"].isin(selected_models)].copy()
filtered_cat = marts_data["cat_acc"][marts_data["cat_acc"]["model_name"].isin(selected_models)].copy()
filtered_unf = (
    marts_data["unformatted"][marts_data["unformatted"]["model_name"].isin(selected_models)].copy()
    if not marts_data["unformatted"].empty
    else pd.DataFrame()
)

# Filtrage par modèles sélectionnés pour le Temps de Réponse
filtered_rt_model = marts_data["rt_model"][marts_data["rt_model"]["model_name"].isin(selected_models)].copy()
filtered_rt_length = marts_data["rt_length"][marts_data["rt_length"]["model_name"].isin(selected_models)].copy()
filtered_rt_diff = marts_data["rt_diff"][marts_data["rt_diff"]["model_name"].isin(selected_models)].copy()
filtered_rt_corr = marts_data["rt_correctness"][marts_data["rt_correctness"]["model_name"].isin(selected_models)].copy()

# Normalisation des libellés et ordres
filtered_diff["difficulty"] = pd.Categorical(filtered_diff["difficulty"], categories=DIFFICULTY_ORDER, ordered=True)
filtered_diff = filtered_diff.sort_values(["model_name", "difficulty"])
filtered_diff["difficulty_label"] = filtered_diff["difficulty"].map(DIFFICULTY_LABELS)

filtered_qtype["type_label"] = filtered_qtype["question_type"].map(QTYPE_LABELS).fillna(filtered_qtype["question_type"])

filtered_rt_diff["difficulty"] = pd.Categorical(filtered_rt_diff["difficulty"], categories=DIFFICULTY_ORDER, ordered=True)
filtered_rt_diff = filtered_rt_diff.sort_values(["model_name", "difficulty"])
filtered_rt_diff["difficulty_label"] = filtered_rt_diff["difficulty"].map(DIFFICULTY_LABELS)

filtered_rt_length["question_length_tier"] = pd.Categorical(
    filtered_rt_length["question_length_tier"], categories=LENGTH_ORDER, ordered=True
)
filtered_rt_length = filtered_rt_length.sort_values(["model_name", "question_length_tier"])

# ── En-tête principal ─────────────────────────────────────────────────────────

st.title("🧠 Benchmark Trivia — Analyse LLM")
st.markdown(
    "Plateforme d'évaluation comparant la **précision** (accuracy) et la **latence** (temps de réponse) "
    "des modèles sur le dataset Open Trivia DB."
)

# ── Séparation des Vues : Précision vs Temps de Réponse ───────────────────────

tab_accuracy_view, tab_latency_view = st.tabs([
    "🎯 Précision & Benchmarks d'Accuracy",
    "⚡ Temps de Réponse & Latence",
])

# ==============================================================================
# ONGLET 1 : PRÉCISION & ACCURACY
# ==============================================================================

with tab_accuracy_view:
    best_acc_row = filtered_model.sort_values("accuracy_pct", ascending=False).iloc[0]
    worst_acc_row = filtered_model.sort_values("accuracy_pct", ascending=True).iloc[0]
    total_q_count = int(filtered_model["total_questions"].iloc[0]) if not filtered_model.empty else 0
    avg_acc_val = round(filtered_model["accuracy_pct"].mean(), 2)
    acc_spread_val = round(best_acc_row["accuracy_pct"] - worst_acc_row["accuracy_pct"], 2)

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric(
            label="🏆 Modèle le plus précis",
            value=best_acc_row["model_name"],
            delta=f"{best_acc_row['accuracy_pct']:.2f}% de précision",
        )
    with col_kpi2:
        st.metric(
            label="🎯 Écart maximal de précision",
            value=f"{acc_spread_val:.2f} pp",
            delta="Écart entre modèles" if len(filtered_model) > 1 else "Modèle unique",
            delta_color="off" if len(filtered_model) <= 1 else "normal",
        )
    with col_kpi3:
        st.metric(
            label="📚 Questions par modèle",
            value=f"{total_q_count:,}".replace(",", " "),
        )
    with col_kpi4:
        st.metric(
            label="📊 Précision moyenne observée",
            value=f"{avg_acc_val:.2f} %",
        )

    st.write("")
    st.markdown("---")

    # ── 1. Performance Globale & Décomposition ──
    st.subheader("1. 🎯 Performance Globale par Modèle")

    col_acc_bar, col_resp_stacked = st.columns(2)

    with col_acc_bar:
        fig_acc = px.bar(
            filtered_model.sort_values("accuracy_pct", ascending=True),
            x="accuracy_pct",
            y="model_name",
            orientation="h",
            text="accuracy_pct",
            color="model_name",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={"accuracy_pct": "Précision (%)", "model_name": "Modèle"},
            title="Taux de réussite global (Accuracy %)",
        )
        fig_acc.update_traces(texttemplate="%{text:.2f} %", textposition="outside", cliponaxis=False)
        fig_acc.add_vline(x=25, line_dash="dash", line_color="#9CA3AF", annotation_text="Hasard QCM (25%)", annotation_position="top right")
        fig_acc.update_layout(showlegend=False, xaxis_range=[0, 105], xaxis_title="Précision (%)", yaxis_title=None, height=360, margin=dict(l=20, r=40, t=50, b=30))
        st.plotly_chart(fig_acc, width='stretch', key="chart_overall_accuracy")

    with col_resp_stacked:
        unf_map = {}
        if not filtered_unf.empty:
            unf_map = dict(zip(filtered_unf["model_name"], filtered_unf["unformatted_answers"]))

        stacked_records = []
        for _, row in filtered_model.iterrows():
            m_name = row["model_name"]
            tot_q = int(row["total_questions"])
            cor_q = int(row["correct_answers"])
            unf_q = int(unf_map.get(m_name, 0))
            wro_q = max(0, tot_q - cor_q - unf_q)

            stacked_records.append({"model_name": m_name, "statut": "Bonnes réponses", "count": cor_q})
            stacked_records.append({"model_name": m_name, "statut": "Mauvaises réponses", "count": wro_q})
            stacked_records.append({"model_name": m_name, "statut": "Format invalide / Null", "count": unf_q})

        df_stacked = pd.DataFrame(stacked_records)
        fig_stacked = px.bar(
            df_stacked,
            x="count",
            y="model_name",
            color="statut",
            orientation="h",
            barmode="stack",
            text_auto=True,
            color_discrete_map={
                "Bonnes réponses": "#10B981",
                "Mauvaises réponses": "#F43F5E",
                "Format invalide / Null": "#F59E0B",
            },
            labels={"count": "Nombre de questions", "model_name": "Modèle", "statut": "Résultat"},
            title="Volume absolu : Bonnes, Mauvaises et Format invalide",
        )
        fig_stacked.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="Nombre total de questions",
            yaxis_title=None,
            height=360,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        st.plotly_chart(fig_stacked, width='stretch', key="chart_correct_incorrect_stacked")

    # Zoom formatage invalide
    if not filtered_unf.empty:
        with st.expander("⚠️ Analyse détaillée des réponses non formatées (ai_answer IS NULL)", expanded=False):
            st.markdown(
                """
                > **Règle métier :** Les réponses non formatées (`ai_answer IS NULL`) sont pénalisées 
                > et comptabilisées comme des **réponses fausses** dans tous les calculs d'accuracy.
                """
            )
            col_u1, col_u2 = st.columns([3, 3])
            with col_u1:
                fig_unf = px.bar(
                    filtered_unf.sort_values("unformatted_answers", ascending=True),
                    x="unformatted_answers",
                    y="model_name",
                    orientation="h",
                    text="unformatted_answers",
                    color="model_name",
                    color_discrete_map=ACTIVE_MODEL_COLORS,
                    title="Questions à format invalide",
                    labels={"unformatted_answers": "Questions non formatées", "model_name": "Modèle"},
                )
                fig_unf.update_traces(texttemplate="%{text} questions", textposition="outside", cliponaxis=False)
                fig_unf.update_layout(showlegend=False, xaxis_title="Questions échouées par format", yaxis_title=None, height=250, margin=dict(l=20, r=40, t=40, b=20))
                st.plotly_chart(fig_unf, width='stretch', key="chart_unformatted_bar")
            with col_u2:
                st.dataframe(
                    filtered_unf.rename(columns={
                        "model_name": "Modèle",
                        "total_questions": "Total",
                        "formatted_answers": "Formatées",
                        "unformatted_answers": "Non formatées",
                        "unformatted_pct": "Taux Erreur (%)",
                        "compliance_pct": "Conformité (%)",
                    }),
                    column_config={
                        "Conformité (%)": st.column_config.ProgressColumn("Conformité (%)", format="%.2f %%", min_value=95, max_value=100),
                        "Taux Erreur (%)": st.column_config.NumberColumn(format="%.2f %%"),
                    },
                    width='stretch',
                    hide_index=True,
                    key="table_unformatted_summary",
                )

    st.markdown("---")

    # ── 2. Format de Question & Difficulté ──
    col_acc_qtype, col_acc_diff = st.columns(2)

    with col_acc_qtype:
        st.subheader("2. 🔀 Précision par Format de Question")
        fig_qtype = px.bar(
            filtered_qtype,
            x="type_label",
            y="accuracy_pct",
            color="model_name",
            barmode="group",
            text="accuracy_pct",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={"accuracy_pct": "Accuracy (%)", "type_label": "Format", "model_name": "Modèle"},
            title="Accuracy (%) : Vrai / Faux vs Choix Multiple",
        )
        fig_qtype.update_traces(texttemplate="%{text:.1f} %", textposition="outside", cliponaxis=False)
        fig_qtype.update_layout(xaxis_title=None, yaxis_range=[0, 105], yaxis_ticksuffix=" %", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=360, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_qtype, width='stretch', key="chart_qtype_bar")

    with col_acc_diff:
        st.subheader("3. 🏔️ Résilience par Difficulté")
        fig_diff_bar = px.bar(
            filtered_diff,
            x="difficulty_label",
            y="accuracy_pct",
            color="model_name",
            barmode="group",
            text="accuracy_pct",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={"accuracy_pct": "Accuracy (%)", "difficulty_label": "Difficulté", "model_name": "Modèle"},
            title="Comparatif par niveau (Easy → Medium → Hard)",
        )
        fig_diff_bar.update_traces(texttemplate="%{text:.1f} %", textposition="outside", cliponaxis=False)
        fig_diff_bar.update_layout(xaxis_title=None, yaxis_range=[0, 105], yaxis_ticksuffix=" %", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=360, margin=dict(l=20, r=20, t=50, b=30))
        st.plotly_chart(fig_diff_bar, width='stretch', key="chart_difficulty_grouped_bar")

    st.markdown("---")

    # ── 4. Analyse par Catégorie ──
    st.subheader("4. 📚 Performance par Catégorie Thématique")
    all_cats = sorted(filtered_cat["category"].unique().tolist())
    col_cat_mode, col_cat_sort = st.columns([3, 2])
    with col_cat_mode:
        cat_view_mode = st.radio(
            "Mode d'affichage :",
            options=["🔥 Matrice comparative (Heatmap)", "🏆 Top & Flop par modèle", "📊 Barres groupées"],
            index=0,
            horizontal=True,
            key="cat_view_mode_radio",
        )
    with col_cat_sort:
        cat_sort_order = st.selectbox(
            "Ordre des catégories :",
            options=["Précision moyenne (décroissante)", "Précision moyenne (croissante)", "Ordre alphabétique"],
            index=0,
            key="cat_sort_order_select",
        )

    with st.expander("🔍 Filtrer les catégories affichées", expanded=False):
        selected_cats = st.multiselect("Sélectionner des domaines spécifiques :", options=all_cats, default=all_cats, key="cat_multiselect_filter")

    if not selected_cats:
        st.info("Veuillez sélectionner au moins une catégorie.", icon="ℹ️")
    else:
        cat_sub = filtered_cat[filtered_cat["category"].isin(selected_cats)].copy()
        cat_mean_acc = cat_sub.groupby("category")["accuracy_pct"].mean()
        if cat_sort_order == "Précision moyenne (décroissante)":
            sorted_cat_list = cat_mean_acc.sort_values(ascending=False).index.tolist()
        elif cat_sort_order == "Précision moyenne (croissante)":
            sorted_cat_list = cat_mean_acc.sort_values(ascending=True).index.tolist()
        else:
            sorted_cat_list = sorted(selected_cats)

        if cat_view_mode == "🔥 Matrice comparative (Heatmap)":
            pivot_heat = cat_sub.pivot(index="category", columns="model_name", values="accuracy_pct")
            heat_cat_order = list(reversed(sorted_cat_list))
            pivot_heat = pivot_heat.reindex(heat_cat_order)
            fig_heat = px.imshow(
                pivot_heat,
                labels=dict(x="Modèle", y="Catégorie", color="Précision (%)"),
                x=pivot_heat.columns.tolist(),
                y=pivot_heat.index.tolist(),
                color_continuous_scale=[[0.0, "#EF4444"], [0.35, "#F97316"], [0.50, "#FBBF24"], [0.65, "#34D399"], [1.0, "#059669"]],
                range_color=[0, 100],
                text_auto=".1f",
                aspect="auto",
            )
            fig_heat.update_traces(textfont=dict(size=12), hovertemplate="<b>%{y}</b><br>Modèle: %{x}<br>Précision: %{z:.2f} %<extra></extra>")
            fig_heat.update_layout(coloraxis_colorbar=dict(title="Précision", ticksuffix=" %"), xaxis_title=None, yaxis_title=None, height=max(450, len(selected_cats) * 26 + 100), margin=dict(l=20, r=20, t=30, b=30))
            st.plotly_chart(fig_heat, width='stretch', key="chart_category_heatmap")

        elif cat_view_mode == "🏆 Top & Flop par modèle":
            focus_model = st.selectbox("Sélectionnez le modèle à détailler :", options=selected_models, key="cat_focus_model_selector")
            model_cat_data = cat_sub[cat_sub["model_name"] == focus_model].sort_values("accuracy_pct", ascending=False)
            top5 = model_cat_data.head(5).sort_values("accuracy_pct", ascending=True)
            flop5 = model_cat_data.tail(5).sort_values("accuracy_pct", ascending=True)
            col_t, col_f = st.columns(2)
            with col_t:
                fig_top = px.bar(top5, x="accuracy_pct", y="category", orientation="h", text="accuracy_pct", color_discrete_sequence=["#10B981"], title=f"🟢 Top 5 — {focus_model}")
                fig_top.update_traces(texttemplate="%{text:.1f} %", textposition="outside", cliponaxis=False)
                fig_top.update_layout(xaxis_range=[0, 105], yaxis_title=None, height=320, margin=dict(l=10, r=30, t=50, b=20))
                st.plotly_chart(fig_top, width='stretch', key=f"chart_top5_{focus_model}")
            with col_f:
                fig_flop = px.bar(flop5, x="accuracy_pct", y="category", orientation="h", text="accuracy_pct", color_discrete_sequence=["#F43F5E"], title=f"🔴 Flop 5 — {focus_model}")
                fig_flop.update_traces(texttemplate="%{text:.1f} %", textposition="outside", cliponaxis=False)
                fig_flop.update_layout(xaxis_range=[0, 105], yaxis_title=None, height=320, margin=dict(l=10, r=30, t=50, b=20))
                st.plotly_chart(fig_flop, width='stretch', key=f"chart_flop5_{focus_model}")
        else:
            bar_cat_order = list(reversed(sorted_cat_list))
            fig_cat = px.bar(cat_sub, y="category", x="accuracy_pct", color="model_name", barmode="group", orientation="h", text="accuracy_pct", category_orders={"category": bar_cat_order}, color_discrete_map=ACTIVE_MODEL_COLORS, title="Taux de réussite (%) par catégorie")
            fig_cat.update_traces(texttemplate="%{text:.1f} %", textposition="outside", cliponaxis=False)
            fig_cat.update_layout(yaxis_title=None, xaxis_range=[0, 105], xaxis_ticksuffix=" %", legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1), height=max(420, len(selected_cats) * 35), margin=dict(l=20, r=40, t=50, b=30))
            st.plotly_chart(fig_cat, width='stretch', key="chart_category_horizontal")

    st.markdown("---")

    # ── 5. Données Chiffrées Détaillées ──
    st.subheader("5. 📋 Données Chiffrées d'Accuracy")
    t_mod, t_dif, t_qty, t_cat, t_unf = st.tabs(["Modèle", "Difficulté", "Format", "Catégories", "Conformité (NULL)"])
    with t_mod:
        st.dataframe(filtered_model.rename(columns={"model_name": "Modèle", "total_questions": "Questions", "correct_answers": "Succès", "accuracy_pct": "Précision (%)"}), column_config={"Précision (%)": st.column_config.ProgressColumn(format="%.2f %%", min_value=0, max_value=100)}, width='stretch', hide_index=True, key="table_model_summary")
    with t_dif:
        st.dataframe(filtered_diff.rename(columns={"model_name": "Modèle", "difficulty_label": "Difficulté", "total_questions": "Questions", "correct_answers": "Succès", "accuracy_pct": "Précision (%)"}), column_config={"Précision (%)": st.column_config.ProgressColumn(format="%.2f %%", min_value=0, max_value=100)}, width='stretch', hide_index=True, key="table_diff_summary")
    with t_qty:
        st.dataframe(filtered_qtype.rename(columns={"model_name": "Modèle", "type_label": "Format", "total_questions": "Questions", "correct_answers": "Succès", "accuracy_pct": "Précision (%)"}), column_config={"Précision (%)": st.column_config.ProgressColumn(format="%.2f %%", min_value=0, max_value=100)}, width='stretch', hide_index=True, key="table_qtype_raw")
    with t_cat:
        st.dataframe(filtered_cat.rename(columns={"model_name": "Modèle", "category": "Catégorie", "total_questions": "Questions", "correct_answers": "Succès", "accuracy_pct": "Précision (%)"}), column_config={"Précision (%)": st.column_config.ProgressColumn(format="%.2f %%", min_value=0, max_value=100)}, width='stretch', hide_index=True, key="table_category_raw")
    with t_unf:
        if not filtered_unf.empty:
            st.dataframe(filtered_unf.rename(columns={"model_name": "Modèle", "total_questions": "Questions", "formatted_answers": "Formatées", "unformatted_answers": "Non formatées", "compliance_pct": "Conformité (%)"}), column_config={"Conformité (%)": st.column_config.ProgressColumn(format="%.2f %%", min_value=95, max_value=100)}, width='stretch', hide_index=True, key="table_unformatted_raw")


# ==============================================================================
# ONGLET 2 : TEMPS DE RÉPONSE & LATENCE (NOUVEAU)
# ==============================================================================

with tab_latency_view:
    fastest_row = filtered_rt_model.sort_values("avg_response_time", ascending=True).iloc[0]
    slowest_row = filtered_rt_model.sort_values("avg_response_time", ascending=False).iloc[0]
    global_median_rt = round(filtered_rt_model["median_response_time"].mean(), 3)
    speedup_ratio = round(slowest_row["avg_response_time"] / fastest_row["avg_response_time"], 1) if fastest_row["avg_response_time"] > 0 else 1.0

    col_rt_kpi1, col_rt_kpi2, col_rt_kpi3, col_rt_kpi4 = st.columns(4)

    with col_rt_kpi1:
        st.metric(
            label="⚡ Modèle le plus véloce",
            value=fastest_row["model_name"],
            delta=f"{fastest_row['avg_response_time']:.3f} s en moyenne",
            delta_color="normal",
        )

    with col_rt_kpi2:
        st.metric(
            label="⏱️ Latence médiane moyenne",
            value=f"{global_median_rt:.3f} s",
        )

    with col_rt_kpi3:
        st.metric(
            label="⚖️ Ratio de vitesse",
            value=f"{speedup_ratio:.1f}x",
            delta=f"{fastest_row['model_name']} plus rapide" if len(filtered_rt_model) > 1 else "Modèle unique",
            delta_color="off" if len(filtered_rt_model) <= 1 else "normal",
        )

    with col_rt_kpi4:
        st.metric(
            label="🐢 Modèle le plus lent",
            value=slowest_row["model_name"],
            delta=f"{slowest_row['avg_response_time']:.3f} s en moyenne",
            delta_color="inverse",
        )

    st.write("")
    st.markdown("---")

    # ── 1. Latence Globale & Dispersion ──
    st.subheader("1. ⚡ Latence Globale : Moyenne vs Médiane")

    col_rt_bar, col_rt_disp = st.columns(2)

    with col_rt_bar:
        # Comparatif Moyenne vs Médiane côte à côte
        rt_melted = filtered_rt_model.melt(
            id_vars=["model_name"],
            value_vars=["avg_response_time", "median_response_time"],
            var_name="metric_type",
            value_name="seconds",
        )
        rt_melted["metric_label"] = rt_melted["metric_type"].map({
            "avg_response_time": "Temps Moyen",
            "median_response_time": "Temps Médian",
        })

        fig_rt_bar = px.bar(
            rt_melted,
            x="seconds",
            y="model_name",
            color="metric_label",
            orientation="h",
            barmode="group",
            text="seconds",
            color_discrete_map={
                "Temps Moyen": "#3B82F6",
                "Temps Médian": "#8B5CF6",
            },
            labels={"seconds": "Temps de réponse (secondes)", "model_name": "Modèle", "metric_label": "Métrique"},
            title="Temps de réponse moyen vs médian (secondes)",
        )
        fig_rt_bar.update_traces(texttemplate="%{text:.3f} s", textposition="outside", cliponaxis=False)
        fig_rt_bar.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="Secondes",
            yaxis_title=None,
            height=360,
            margin=dict(l=20, r=40, t=50, b=30),
        )
        st.plotly_chart(fig_rt_bar, width='stretch', key="chart_rt_overall_bar")

    with col_rt_disp:
        # Étendue de latence (Min - Médiane - Max)
        fig_rt_range = go.Figure()
        for idx, row in filtered_rt_model.iterrows():
            m_col = ACTIVE_MODEL_COLORS.get(row["model_name"], "#6366F1")
            # Barre d'intervalle Min à Max
            fig_rt_range.add_trace(go.Scatter(
                x=[row["min_response_time"], row["max_response_time"]],
                y=[row["model_name"], row["model_name"]],
                mode="lines",
                line=dict(color="#CBD5E1", width=6),
                name=f"Plage Min-Max ({row['model_name']})",
                showlegend=False,
            ))
            # Points pour Min, Médiane, Max
            fig_rt_range.add_trace(go.Scatter(
                x=[row["min_response_time"], row["median_response_time"], row["max_response_time"]],
                y=[row["model_name"], row["model_name"], row["model_name"]],
                mode="markers+text",
                marker=dict(size=[10, 16, 10], color=[m_col, "#10B981", m_col], symbol=["circle", "diamond", "circle"]),
                text=[f"Min: {row['min_response_time']}s", f"Médiane: {row['median_response_time']}s", f"Max: {row['max_response_time']}s"],
                textposition=["bottom center", "top center", "bottom center"],
                name=row["model_name"],
                showlegend=False,
            ))

        fig_rt_range.update_layout(
            title="Étendue des temps de réponse (Min ➔ Médiane ➔ Max)",
            xaxis_title="Temps de réponse (secondes)",
            yaxis_title=None,
            height=360,
            margin=dict(l=20, r=50, t=50, b=30),
        )
        st.plotly_chart(fig_rt_range, width='stretch', key="chart_rt_min_med_max")

    st.markdown("---")

    # ── 2. Impact de la Longueur Totale (Énoncé + Réponses) ──
    st.subheader("2. 📏 Impact de la Longueur Totale (Énoncé + Réponses)")
    st.caption("Évalue comment le temps d'inférence augmente avec la taille globale du prompt (question + l'ensemble des réponses proposées).")

    col_len_chart, col_len_desc = st.columns([3, 2])

    with col_len_chart:
        fig_rt_len = px.bar(
            filtered_rt_length,
            x="question_length_tier",
            y="avg_response_time",
            color="model_name",
            barmode="group",
            text="avg_response_time",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={
                "avg_response_time": "Temps moyen (s)",
                "question_length_tier": "Palier de longueur totale",
                "model_name": "Modèle",
            },
            title="Temps de réponse moyen selon la longueur totale du prompt",
        )
        fig_rt_len.update_traces(texttemplate="%{text:.3f} s", textposition="outside", cliponaxis=False)
        fig_rt_len.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="Temps moyen (secondes)",
            xaxis_title=None,
            height=360,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        st.plotly_chart(fig_rt_len, width='stretch', key="chart_rt_by_length")

    with col_len_desc:
        st.markdown("**Synthèse par palier de longueur totale**")
        st.dataframe(
            filtered_rt_length.rename(columns={
                "model_name": "Modèle",
                "question_length_tier": "Palier Longueur",
                "total_questions": "Questions",
                "avg_prompt_length": "Taille moy.",
                "avg_response_time": "Moyenne (s)",
                "median_response_time": "Médiane (s)",
            }),
            column_config={
                "Taille moy.": st.column_config.NumberColumn(format="%.1f car."),
                "Moyenne (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Médiane (s)": st.column_config.NumberColumn(format="%.3f s"),
            },
            width='stretch',
            hide_index=True,
            key="table_rt_length_summary",
        )

    st.markdown("---")

    # ── 3. Impact de la Difficulté & de l'Issue de Réponse ──
    st.subheader("3. 🏔️ Impact de la Difficulté & de l'Issue de Réponse (Bonne vs Mauvaise)")

    col_diff_rt, col_corr_rt = st.columns(2)

    with col_diff_rt:
        fig_rt_diff = px.bar(
            filtered_rt_diff,
            x="difficulty_label",
            y="avg_response_time",
            color="model_name",
            barmode="group",
            text="avg_response_time",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={
                "avg_response_time": "Temps moyen (s)",
                "difficulty_label": "Difficulté",
                "model_name": "Modèle",
            },
            title="Temps de réponse moyen par niveau de difficulté",
        )
        fig_rt_diff.update_traces(texttemplate="%{text:.3f} s", textposition="outside", cliponaxis=False)
        fig_rt_diff.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="Temps moyen (secondes)",
            xaxis_title=None,
            height=360,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        st.plotly_chart(fig_rt_diff, width='stretch', key="chart_rt_by_diff")

    with col_corr_rt:
        fig_rt_corr = px.bar(
            filtered_rt_corr,
            x="answer_result",
            y="avg_response_time",
            color="model_name",
            barmode="group",
            text="avg_response_time",
            color_discrete_map=ACTIVE_MODEL_COLORS,
            labels={
                "avg_response_time": "Temps moyen (s)",
                "answer_result": "Résultat de la réponse",
                "model_name": "Modèle",
            },
            title="Temps de réponse : Bonne vs Mauvaise réponse",
        )
        fig_rt_corr.update_traces(texttemplate="%{text:.3f} s", textposition="outside", cliponaxis=False)
        fig_rt_corr.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="Temps moyen (secondes)",
            xaxis_title=None,
            height=360,
            margin=dict(l=20, r=20, t=50, b=30),
        )
        st.plotly_chart(fig_rt_corr, width='stretch', key="chart_rt_by_correctness")

    st.markdown("---")

    # ── 4. Données Chiffrées de Latence ──
    st.subheader("4. 📋 Données Chiffrées de Temps de Réponse")
    t_rt_mod, t_rt_len, t_rt_dif, t_rt_cor = st.tabs([
        "Modèle (Global)",
        "Longueur Question",
        "Difficulté",
        "Résultat (Correct / Incorrect)",
    ])

    with t_rt_mod:
        st.dataframe(
            filtered_rt_model.rename(columns={
                "model_name": "Modèle",
                "total_questions": "Questions",
                "avg_response_time": "Moyenne (s)",
                "median_response_time": "Médiane (s)",
                "min_response_time": "Min (s)",
                "max_response_time": "Max (s)",
            }),
            column_config={
                "Moyenne (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Médiane (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Min (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Max (s)": st.column_config.NumberColumn(format="%.3f s"),
            },
            width='stretch',
            hide_index=True,
            key="table_rt_model_tab",
        )

    with t_rt_len:
        st.dataframe(
            filtered_rt_length.rename(columns={
                "model_name": "Modèle",
                "question_length_tier": "Palier de Longueur",
                "total_questions": "Questions",
                "avg_prompt_length": "Taille moy.",
                "avg_response_time": "Moyenne (s)",
                "median_response_time": "Médiane (s)",
            }),
            column_config={
                "Taille moy.": st.column_config.NumberColumn(format="%.1f car."),
                "Moyenne (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Médiane (s)": st.column_config.NumberColumn(format="%.3f s"),
            },
            width='stretch',
            hide_index=True,
            key="table_rt_length_tab",
        )

    with t_rt_dif:
        st.dataframe(
            filtered_rt_diff.rename(columns={
                "model_name": "Modèle",
                "difficulty_label": "Difficulté",
                "total_questions": "Questions",
                "avg_response_time": "Moyenne (s)",
                "median_response_time": "Médiane (s)",
            }),
            column_config={
                "Moyenne (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Médiane (s)": st.column_config.NumberColumn(format="%.3f s"),
            },
            width='stretch',
            hide_index=True,
            key="table_rt_diff_tab",
        )

    with t_rt_cor:
        st.dataframe(
            filtered_rt_corr.rename(columns={
                "model_name": "Modèle",
                "answer_result": "Résultat",
                "total_questions": "Questions",
                "avg_response_time": "Moyenne (s)",
                "median_response_time": "Médiane (s)",
            }),
            column_config={
                "Moyenne (s)": st.column_config.NumberColumn(format="%.3f s"),
                "Médiane (s)": st.column_config.NumberColumn(format="%.3f s"),
            },
            width='stretch',
            hide_index=True,
            key="table_rt_corr_tab",
        )
