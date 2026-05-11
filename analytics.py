"""
analytics.py
Pipeline de análise para experimentos com 3 agentes.

Uso:
    python analytics.py --data_dir data --outdir analysis_output
"""

import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

sns.set(style="whitegrid")
PALETTE = {"random": "#e74c3c", "bfs": "#3498db", "item_hunter": "#2ecc71"}
AGENTS  = ["random", "bfs", "item_hunter"]


# =====================================================
# UTIL
# =====================================================
def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def safe_read_csv(path):
    if not os.path.exists(path):
        print(f"⚠️  Arquivo não encontrado: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path, on_bad_lines="skip")
    print(f"📄 Carregado {path}: {df.shape}")
    return df


def save_fig(fig, outdir, name):
    fig.savefig(os.path.join(outdir, name), dpi=150, bbox_inches="tight")
    plt.close(fig)


# =====================================================
# 1. SUMMARY GLOBAL POR AGENTE
# =====================================================
def summary_by_agent(matches_df, outdir):
    if matches_df.empty:
        return

    summary = (
        matches_df.groupby("agent")
        .agg(
            total_matches = ("match_id",      "count"),
            win_rate      = ("win",            "mean"),
            avg_steps     = ("steps",          "mean"),
            avg_score     = ("score",          "mean"),
            avg_hp_final  = ("hp_final",       "mean"),
            avg_kills     = ("enemies_killed", "mean"),
            median_score  = ("score",          "median"),
            std_score     = ("score",          "std"),
        )
        .reset_index()
    )

    summary.to_csv(os.path.join(outdir, "summary_by_agent.csv"), index=False)
    print("✅ summary_by_agent.csv salvo.")
    return summary


# =====================================================
# 2. COMPARATIVOS ENTRE AGENTES
# =====================================================
def comparative_plots(matches_df, outdir):
    if matches_df.empty:
        return

    order = [a for a in AGENTS if a in matches_df["agent"].unique()]

    # --- Win rate ---
    win_rate = matches_df.groupby("agent")["win"].mean().reindex(order)
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(win_rate.index, win_rate.values,
                  color=[PALETTE.get(a, "gray") for a in win_rate.index])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Win Rate")
    ax.set_title("Win Rate por Agente")
    for bar, val in zip(bars, win_rate.values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.02,
                f"{val:.2f}", ha="center", fontsize=10)
    save_fig(fig, outdir, "winrate_by_agent.png")

    # --- Score boxplot ---
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=matches_df, x="agent", y="score", hue="agent",
                order=order, palette=PALETTE, ax=ax, legend=False)
    ax.set_title("Distribuição de Score por Agente")
    save_fig(fig, outdir, "score_boxplot.png")

    # --- Steps boxplot ---
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=matches_df, x="agent", y="steps", hue="agent",
                order=order, palette=PALETTE, ax=ax, legend=False)
    ax.set_title("Distribuição de Steps por Agente")
    save_fig(fig, outdir, "steps_boxplot.png")

    # --- HP final violin ---
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.violinplot(data=matches_df, x="agent", y="hp_final", hue="agent",
                   order=order, palette=PALETTE, ax=ax, inner="quartile", legend=False)
    ax.set_title("HP Final por Agente")
    save_fig(fig, outdir, "hp_violin.png")

    # --- Kills (média ± SE) ---
    kills = matches_df.groupby("agent")["enemies_killed"].agg(["mean","sem"]).reindex(order)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(kills.index, kills["mean"],
           yerr=kills["sem"], capsize=4,
           color=[PALETTE.get(a, "gray") for a in kills.index])
    ax.set_ylabel("Inimigos Mortos (média ± SE)")
    ax.set_title("Kills por Agente")
    save_fig(fig, outdir, "kills_by_agent.png")

    print("✅ Gráficos comparativos salvos.")


# =====================================================
# 3. DISTRIBUIÇÃO DE AÇÕES (global + por agente)
# =====================================================
def analyze_actions(actions_df, matches_df, outdir):
    if actions_df.empty:
        return

    # Injeta coluna agent via matches
    if "agent" not in actions_df.columns and not matches_df.empty:
        agent_map = matches_df.drop_duplicates("match_id").set_index("match_id")["agent"]
        actions_df = actions_df.copy()
        actions_df["agent"] = actions_df["match_id"].map(agent_map)

    # Global
    actions_df["action"].value_counts().to_csv(
        os.path.join(outdir, "action_distribution_global.csv")
    )

    # Por agente
    for agent in actions_df["agent"].dropna().unique():
        sub    = actions_df[actions_df["agent"] == agent]
        counts = sub["action"].value_counts()
        counts.to_csv(os.path.join(outdir, f"action_distribution_{agent}.csv"))

        fig, ax = plt.subplots(figsize=(6, 4))
        counts.plot(kind="bar", ax=ax, color=PALETTE.get(agent, "steelblue"))
        ax.set_title(f"Distribuição de Ações — {agent}")
        ax.set_xlabel("")
        save_fig(fig, outdir, f"action_distribution_{agent}.png")

    print("✅ Distribuição de ações salva.")


# =====================================================
# 4. HEATMAP DE POSIÇÕES (global + por agente)
# =====================================================
def heatmap_positions(positions_df, matches_df, outdir):
    if positions_df.empty:
        return

    if "agent" not in positions_df.columns and not matches_df.empty:
        agent_map = matches_df.drop_duplicates("match_id").set_index("match_id")["agent"]
        positions_df = positions_df.copy()
        positions_df["agent"] = positions_df["match_id"].map(agent_map)

    def _make_heatmap(df, title, filename):
        if df.empty:
            return
        heat = df.groupby(["x","y"]).size().reset_index(name="count")
        xmax, ymax = int(heat["x"].max()), int(heat["y"].max())
        grid = np.zeros((ymax+1, xmax+1))
        for _, row in heat.iterrows():
            grid[int(row["y"]), int(row["x"])] = row["count"]
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(grid, cmap="magma", ax=ax)
        ax.set_title(title)
        save_fig(fig, outdir, filename)

    player_pos = positions_df[positions_df["entity"] == "player"]

    _make_heatmap(player_pos,
                  "Heatmap de Posições — player (global)",
                  "heatmap_player_global.png")

    for agent in player_pos["agent"].dropna().unique():
        sub = player_pos[player_pos["agent"] == agent]
        _make_heatmap(sub,
                      f"Heatmap de Posições — {agent}",
                      f"heatmap_player_{agent}.png")

    enemy_pos = positions_df[positions_df["entity"].str.contains("enemy", na=False)]
    if not enemy_pos.empty:
        _make_heatmap(enemy_pos,
                      "Heatmap de Posições — inimigos (global)",
                      "heatmap_enemy_global.png")

    print("✅ Heatmaps salvos.")


# =====================================================
# 5. FEATURE ENGINEERING + CLUSTERING (global + por agente)
# =====================================================
def build_feature_matrix(matches_df, actions_df, events_df=None):
    """
    Duas camadas de features:

    DESCRITIVAS (clustering — incluem outcomes):
      steps, score, hp_final, kills, attack_rate

    COMPORTAMENTAIS PURAS (modelo preditivo — sem leakage):
      kills, attack_rate, collected_maca, got_sword, times_hit, explored_cells

    Excluídas do modelo preditivo:
      score    -> +1000 ao vencer (leakage direto)
      steps    -> 2000 = timeout = derrota (leakage indireto)
      hp_final -> <=0 = morte = derrota (leakage indireto)
    """
    if matches_df.empty:
        return pd.DataFrame()

    if not actions_df.empty and "agent" not in actions_df.columns:
        agent_map = matches_df.drop_duplicates("match_id").set_index("match_id")["agent"]
        actions_df = actions_df.copy()
        actions_df["agent"] = actions_df["match_id"].map(agent_map)

    # Pré-indexa events por match_id
    events_by_match = {}
    if events_df is not None and not events_df.empty:
        for mid, grp in events_df.groupby("match_id"):
            events_by_match[mid] = grp

    rows = []
    for _, m in matches_df.iterrows():
        mid = m["match_id"]
        a   = actions_df[actions_df["match_id"] == mid] if not actions_df.empty else pd.DataFrame()
        ev  = events_by_match.get(mid, pd.DataFrame())

        attack_rate    = (a["action"] == "ATTACK").mean() if not a.empty else 0.0
        collected_maca = int((ev["type"] == "COLLECT_MACA").sum())  if not ev.empty else 0
        got_sword      = int((ev["type"] == "COLLECT_ESPADA").any()) if not ev.empty else 0
        times_hit      = int((ev["type"] == "PLAYER_HIT").sum())    if not ev.empty else 0
        explored_cells = int((ev["type"] == "MOVE_PLAYER").sum())   if not ev.empty else 0

        rows.append({
            "match_id":       mid,
            "agent":          m.get("agent", "unknown"),
            "win":            int(m["win"]),
            "steps":          m["steps"],
            "score":          m["score"],
            "hp_final":       m["hp_final"],
            "kills":          m["enemies_killed"],
            "attack_rate":    attack_rate,
            "collected_maca": collected_maca,
            "got_sword":      got_sword,
            "times_hit":      times_hit,
            "explored_cells": explored_cells,
        })

    return pd.DataFrame(rows)


def cluster_playstyles(features, outdir):
    if features is None or features.empty:
        return features

    feat_cols = ["steps", "score", "hp_final", "kills", "attack_rate"]
    Xs = StandardScaler().fit_transform(features[feat_cols])

    features = features.copy()
    features["cluster"] = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(Xs)
    features.to_csv(os.path.join(outdir, "feature_matrix_with_clusters.csv"), index=False)

    # Scatter global (colorido por cluster)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.scatterplot(x=Xs[:,0], y=Xs[:,1],
                    hue=features["cluster"].astype(str),
                    palette="tab10", ax=ax)
    ax.set_title("Clusters de Estilo de Jogo (global)")
    ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
    save_fig(fig, outdir, "clusters_global.png")

    # Scatter por agente (subplots lado a lado)
    present_agents = [a for a in AGENTS if a in features["agent"].unique()]
    fig, axes = plt.subplots(1, len(present_agents), figsize=(5*len(present_agents), 4),
                             sharey=True)
    if len(present_agents) == 1:
        axes = [axes]
    for ax, agent in zip(axes, present_agents):
        sub = features[features["agent"] == agent]
        if sub.empty:
            ax.set_title(f"{agent}\n(sem dados)")
            continue
        idx = sub.index
        sns.scatterplot(x=Xs[idx, 0], y=Xs[idx, 1],
                        hue=sub["cluster"].astype(str),
                        palette="tab10", ax=ax, legend=(agent == present_agents[-1]))
        ax.set_title(f"Clusters — {agent}")
        ax.set_xlabel("PC1")
    fig.suptitle("Clusters por Agente")
    save_fig(fig, outdir, "clusters_by_agent.png")

    print("✅ Clustering concluído.")
    return features


# =====================================================
# 6. MODELO DE VITÓRIA (global com agent dummies + por agente)
# =====================================================
def model_victory(features, outdir):
    if features is None or features.empty:
        return

    # Features comportamentais puras — sem leakage.
    # score/steps/hp_final excluídos pois são proxies diretos do outcome:
    #   score    -> +1000 ao vencer
    #   steps    -> 2000 == timeout == derrota
    #   hp_final -> <=0 == morte == derrota
    feat_cols = ["kills", "attack_rate", "collected_maca", "got_sword",
                 "times_hit", "explored_cells"]

    # --- Modelo global: inclui dummies de agente como feature ---
    dummies  = pd.get_dummies(features["agent"], prefix="agent")
    X_global = pd.concat([features[feat_cols], dummies], axis=1)
    y_global = features["win"]

    if y_global.nunique() >= 2:
        Xtr, Xte, ytr, yte = train_test_split(
            X_global, y_global, test_size=0.25, random_state=42, stratify=y_global
        )
        clf = RandomForestClassifier(n_estimators=200, random_state=42,
                                     class_weight="balanced")
        clf.fit(Xtr, ytr)

        pd.DataFrame(
            classification_report(yte, clf.predict(Xte), output_dict=True)
        ).T.to_csv(os.path.join(outdir, "victory_classification_report.csv"))

        importances = pd.Series(clf.feature_importances_, index=X_global.columns)\
                        .sort_values(ascending=False)
        importances.to_csv(os.path.join(outdir, "feature_importances.csv"))

        fig, ax = plt.subplots(figsize=(7, 4))
        importances.plot(kind="bar", ax=ax, color="steelblue")
        ax.set_title("Feature Importances — Modelo Global de Vitória\n(score excluído para evitar leakage)")
        save_fig(fig, outdir, "feature_importances.png")

    # --- Modelo por agente ---
    for agent in features["agent"].dropna().unique():
        sub = features[features["agent"] == agent]
        Xa, ya = sub[feat_cols], sub["win"]

        if ya.nunique() < 2 or len(sub) < 10:
            continue

        Xtr, Xte, ytr, yte = train_test_split(
            Xa, ya, test_size=0.25, random_state=42, stratify=ya
        )
        clf_a = RandomForestClassifier(n_estimators=100, random_state=42,
                                       class_weight="balanced")
        clf_a.fit(Xtr, ytr)

        pd.DataFrame(
            classification_report(yte, clf_a.predict(Xte), output_dict=True)
        ).T.to_csv(os.path.join(outdir, f"victory_report_{agent}.csv"))

        imp_a = pd.Series(clf_a.feature_importances_, index=feat_cols)\
                  .sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(6, 3))
        imp_a.plot(kind="bar", ax=ax, color=PALETTE.get(agent, "steelblue"))
        ax.set_title(f"Feature Importances — {agent}")
        save_fig(fig, outdir, f"feature_importances_{agent}.png")

    print("✅ Modelo de vitória treinado.")


# =====================================================
# PIPELINE PRINCIPAL
# =====================================================
def run_analysis(data_dir, outdir):
    ensure_dir(outdir)

    matches   = safe_read_csv(os.path.join(data_dir, "matches.csv"))
    events    = safe_read_csv(os.path.join(data_dir, "events.csv"))
    positions = safe_read_csv(os.path.join(data_dir, "positions.csv"))
    actions   = safe_read_csv(os.path.join(data_dir, "actions.csv"))

    if matches.empty:
        print("❌ matches.csv vazio ou ausente. Abortando.")
        return

    matches["win"] = matches["win"].astype(str).str.lower().isin(["true", "1"])

    summary_by_agent(matches, outdir)
    comparative_plots(matches, outdir)
    analyze_actions(actions, matches, outdir)
    heatmap_positions(positions, matches, outdir)

    features = build_feature_matrix(matches, actions, events)
    features = cluster_playstyles(features, outdir)
    model_victory(features, outdir)

    print(f"\n🎯 Análise concluída! Resultados em: {outdir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="data")
    parser.add_argument("--outdir",   default="analysis_output")
    args = parser.parse_args()

    run_analysis(args.data_dir, args.outdir)
