#!/usr/bin/env python3
"""
Testes não-paramétricos sobre BLEU por segmento.

Para cada projeto:
  1. Kruskal-Wallis  — ctx-0 vs ctx-1 (pool) vs ctx-2 (pool)
  2. Dunn por nível  — pares (ctx-0, ctx-1, ctx-2) agregados (pool de arquivos)
  3. Dunn por arquivo — ctx-0 + todos os ctx-1/ctx-2 individualmente
  4. Wilcoxon pareado — ctx-0 vs cada arquivo ctx-1/ctx-2 segmento a segmento

Gera:
  estatisticas/testes/kruskal_wallis.csv
  estatisticas/testes/dunn_por_nivel.csv
  estatisticas/testes/dunn_por_arquivo.csv
  estatisticas/testes/wilcoxon_pareado.csv

Uso:
    pip install scikit-posthocs
    python test_nao_parametricos.py
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import scikit_posthocs as sp

warnings.filterwarnings("ignore")

ALPHA      = 0.05
INPUT_DIR  = Path("metrics_csv")
OUTPUT_DIR = Path("estatisticas") / "testes"


def ctx_level(v) -> str:
    cl = str(v).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    if "," not in cl:
        return "ctx-1"
    return "ctx-2"


def load_project(project_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(project_dir.glob("*.csv")):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if "bleu" not in df.columns:
            continue
        df["context_languages"] = df.get("context_languages", "")
        df["ctx_level"] = df["context_languages"].apply(ctx_level)
        df["arquivo"] = path.stem
        frames.append(df[["arquivo", "ctx_level", "bleu"]].dropna(subset=["bleu"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def sig_label(p: float) -> str:
    if p is None or np.isnan(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < ALPHA:
        return "*"
    return "ns"


# ── Kruskal-Wallis por nível ────────────────────────────────────────────────

def run_kruskal(df: pd.DataFrame, project: str) -> dict | None:
    groups = {lvl: grp["bleu"].values for lvl, grp in df.groupby("ctx_level")}
    if len(groups) < 2:
        return None
    stat, p = stats.kruskal(*groups.values())
    return {
        "project": project,
        "grupos": " vs ".join(sorted(groups.keys())),
        "n_total": sum(len(v) for v in groups.values()),
        "kw_stat": round(float(stat), 4),
        "kw_p": round(float(p), 6),
        "significativo": bool(p < ALPHA),
        "sig": sig_label(float(p)),
    }


# ── Dunn por nível (pool de arquivos) ───────────────────────────────────────

def run_dunn_por_nivel(df: pd.DataFrame, project: str) -> list[dict]:
    levels = sorted(df["ctx_level"].unique())
    if len(levels) < 2:
        return []

    # data_list: um vetor de BLEU por nível (ctx-0, ctx-1, ctx-2)
    data_list = [df[df["ctx_level"] == lvl]["bleu"].values for lvl in levels]
    dunn_df = sp.posthoc_dunn(data_list, p_adjust="bonferroni")
    dunn_df.index = levels
    dunn_df.columns = levels

    rows: list[dict] = []
    for i, a in enumerate(levels):
        for b in levels[i + 1 :]:
            p = float(dunn_df.loc[a, b])
            rows.append(
                {
                    "project": project,
                    "grupo_a": a,
                    "grupo_b": b,
                    "comparacao": f"{a} vs {b}",
                    "dunn_p": round(p, 6),
                    "significativo": bool(p < ALPHA),
                    "sig": sig_label(p),
                }
            )
    return rows


# ── Dunn por arquivo ────────────────────────────────────────────────────────

def run_dunn_por_arquivo(df: pd.DataFrame, project: str) -> list[dict]:
    # Cada "grupo" é um arquivo (ctx-0 + todos os ctx-1/ctx-2)
    arquivos = sorted(df["arquivo"].unique())
    if len(arquivos) < 2:
        return []

    data_list = [df[df["arquivo"] == arq]["bleu"].values for arq in arquivos]
    dunn_df = sp.posthoc_dunn(data_list, p_adjust="bonferroni")
    dunn_df.index = arquivos
    dunn_df.columns = arquivos

    ctx_map = df.groupby("arquivo")["ctx_level"].first().to_dict()

    rows: list[dict] = []
    for i, a in enumerate(arquivos):
        for b in arquivos[i + 1 :]:
            p = float(dunn_df.loc[a, b])
            rows.append(
                {
                    "project": project,
                    "arquivo_a": a,
                    "arquivo_b": b,
                    "ctx_a": ctx_map.get(a, ""),
                    "ctx_b": ctx_map.get(b, ""),
                    "dunn_p": round(p, 6),
                    "significativo": bool(p < ALPHA),
                    "sig": sig_label(p),
                }
            )
    return rows


# ── Wilcoxon pareado: ctx-0 vs cada arquivo ctx-1/ctx-2 ─────────────────────

def run_wilcoxon(df: pd.DataFrame, project: str) -> list[dict]:
    ctx0_files = df[df["ctx_level"] == "ctx-0"]["arquivo"].unique()
    if len(ctx0_files) == 0:
        return []

    ref_file = ctx0_files[0]
    bleu_ref = df[df["arquivo"] == ref_file]["bleu"].values

    rows: list[dict] = []
    for arquivo, grp in df[df["ctx_level"] != "ctx-0"].groupby("arquivo"):
        bleu_cmp = grp["bleu"].values
        n = min(len(bleu_ref), len(bleu_cmp))
        if n < 4:
            continue
        a, b = bleu_ref[:n], bleu_cmp[:n]
        if np.all(a == b):
            stat, p = 0.0, 1.0
        else:
            res = stats.wilcoxon(a, b, alternative="two-sided")
            stat, p = float(res.statistic), float(res.pvalue)
        rows.append(
            {
                "project": project,
                "arquivo_ref": ref_file,
                "arquivo_cmp": arquivo,
                "ctx_level_cmp": grp["ctx_level"].iloc[0],
                "n_pares": n,
                "w_stat": round(stat, 4),
                "w_p": round(p, 6),
                "significativo": bool(p < ALPHA),
                "sig": sig_label(p),
            }
        )
    return rows


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    if not INPUT_DIR.exists():
        print(f"[erro] Pasta não encontrada: {INPUT_DIR}")
        sys.exit(1)

    projects = sorted(p for p in INPUT_DIR.iterdir() if p.is_dir())
    if not projects:
        print(f"[erro] Nenhum projeto em {INPUT_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    kw_rows: list[dict] = []
    dunn_nivel_rows: list[dict] = []
    dunn_arq_rows: list[dict] = []
    wilcoxon_rows: list[dict] = []

    for project_dir in projects:
        print(f"\n→ {project_dir.name}")
        df = load_project(project_dir)
        if df.empty:
            print("  [aviso] Sem dados.")
            continue

        # Contagem de segmentos por nível (só para log)
        n_segs_por_nivel = df.groupby("ctx_level")["bleu"].count().to_dict()
        for lvl, n in n_segs_por_nivel.items():
            print(f"  {lvl}: {n} segmentos")

        # 1. Kruskal-Wallis por nível
        kw = run_kruskal(df, project_dir.name)
        if kw:
            kw_rows.append(kw)
            print(f"  KW  stat={kw['kw_stat']}  p={kw['kw_p']}  {kw['sig']}")

        # 2. Dunn por nível (pool)
        d_nivel = run_dunn_por_nivel(df, project_dir.name)
        dunn_nivel_rows.extend(d_nivel)

        # 3. Dunn por arquivo
        d_arq = run_dunn_por_arquivo(df, project_dir.name)
        dunn_arq_rows.extend(d_arq)

        # 4. Wilcoxon pareado
        w_rows = run_wilcoxon(df, project_dir.name)
        wilcoxon_rows.extend(w_rows)
        sig_count = sum(1 for w in w_rows if w["significativo"])
        print(f"  Wilcoxon: {sig_count}/{len(w_rows)} comparações significativas")

    # Salva CSVs
    if kw_rows:
        pd.DataFrame(kw_rows).to_csv(OUTPUT_DIR / "kruskal_wallis.csv", index=False)
        print(f"\n[ok] kruskal_wallis.csv  ({len(kw_rows)} linhas)")
    if dunn_nivel_rows:
        pd.DataFrame(dunn_nivel_rows).to_csv(OUTPUT_DIR / "dunn_por_nivel.csv", index=False)
        print(f"[ok] dunn_por_nivel.csv   ({len(dunn_nivel_rows)} linhas)")
    if dunn_arq_rows:
        pd.DataFrame(dunn_arq_rows).to_csv(OUTPUT_DIR / "dunn_por_arquivo.csv", index=False)
        print(f"[ok] dunn_por_arquivo.csv ({len(dunn_arq_rows)} linhas)")
    if wilcoxon_rows:
        pd.DataFrame(wilcoxon_rows).to_csv(OUTPUT_DIR / "wilcoxon_pareado.csv", index=False)
        print(f"[ok] wilcoxon_pareado.csv ({len(wilcoxon_rows)} linhas)")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
