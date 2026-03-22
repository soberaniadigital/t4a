#!/usr/bin/env python3
"""
Transform per-segment CSV files from metrics_csv/ into a single
experiment_data.csv suitable for R mixed-effects model analysis.

Input:  metrics_csv/<project>/*.csv  (29 CSVs per project, one per condition)
Output: estatisticas/experiment_data.csv

Usage:
    python estatisticas/generate_experiment_csv.py
"""

import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

METRICS_DIR = Path(__file__).resolve().parent.parent / "metrics_csv"
OUTPUT_FILE = Path(__file__).resolve().parent / "experiment_data.csv"

# All 7 pivot languages used in the experiment
ALL_LANGUAGES = ["de", "es", "fr", "id", "ru", "vi", "zh_cn"]

# Expected 29 conditions: 1 direct + 7 single + 21 dual
EXPECTED_CONDITIONS = 29


def parse_filename(filename):
    """Parse a CSV filename to extract context level and languages.

    Filename pattern: {name}.pt_BR.llama.ctx-{level}[.{lang1}[-{lang2}]].po.meta.csv

    Returns:
        (treatment_type, context_config) tuple
    """
    match = re.search(r'\.ctx-(\d+)(?:\.([^.]+(?:-[^.]+)?))?\.po\.meta\.csv$', filename)
    if not match:
        return None, None

    level = int(match.group(1))
    langs_str = match.group(2)  # None for ctx-0, "es" for ctx-1, "de-es" for ctx-2

    if level == 0:
        return "direct", "none"
    elif level == 1:
        lang = langs_str.lower()
        return "single_context", lang
    elif level == 2:
        parts = sorted(langs_str.lower().split("-"))
        return "dual_context", "_".join(parts)
    else:
        return None, None


def load_csv(filepath):
    """Load a CSV file and return list of row dicts."""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main():
    if not METRICS_DIR.is_dir():
        print(f"ERROR: metrics_csv directory not found at {METRICS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Collect all project directories
    projects = sorted(
        d for d in METRICS_DIR.iterdir()
        if d.is_dir()
    )

    print(f"Found {len(projects)} projects")

    all_rows = []
    global_sentence_counter = 0
    validation_issues = []

    for project_dir in projects:
        project_name = project_dir.name
        csv_files = sorted(f for f in project_dir.iterdir() if f.suffix == ".csv")

        # Filter to only metric CSVs (exclude boxplot PNGs etc that snuck in)
        metric_csvs = [f for f in csv_files if ".po.meta.csv" in f.name]

        num_conditions = len(metric_csvs)
        if num_conditions < EXPECTED_CONDITIONS:
            validation_issues.append(
                f"  {project_name}: {num_conditions}/{EXPECTED_CONDITIONS} conditions"
            )

        # Load the direct translation (ctx-0) first to establish sentence order
        ctx0_files = [f for f in metric_csvs if ".ctx-0." in f.name]
        if not ctx0_files:
            validation_issues.append(f"  {project_name}: MISSING ctx-0 (baseline)! Skipping.")
            continue

        baseline_data = load_csv(ctx0_files[0])
        # Build sentence key list from baseline
        sentence_keys = [row["original"] for row in baseline_data]
        num_sentences = len(sentence_keys)

        # Assign sentence IDs for this project
        sentence_id_map = {}
        for i, key in enumerate(sentence_keys):
            global_sentence_counter += 1
            sentence_id_map[key] = f"s{global_sentence_counter:05d}"

        # Process each condition CSV
        for csv_file in metric_csvs:
            treatment_type, context_config = parse_filename(csv_file.name)
            if treatment_type is None:
                validation_issues.append(
                    f"  {project_name}: Could not parse filename {csv_file.name}"
                )
                continue

            data = load_csv(csv_file)

            # Validate sentence alignment
            file_keys = [row["original"] for row in data]
            if file_keys != sentence_keys:
                if set(file_keys) == set(sentence_keys) and len(file_keys) == len(sentence_keys):
                    validation_issues.append(
                        f"  {project_name}/{csv_file.name}: sentences in different order than baseline"
                    )
                else:
                    missing = set(sentence_keys) - set(file_keys)
                    extra = set(file_keys) - set(sentence_keys)
                    validation_issues.append(
                        f"  {project_name}/{csv_file.name}: sentence mismatch "
                        f"(missing={len(missing)}, extra={len(extra)})"
                    )

            for row in data:
                original = row["original"]
                sid = sentence_id_map.get(original)
                if sid is None:
                    # Sentence not in baseline — skip
                    continue

                bleu = row.get("bleu", "")
                if bleu == "":
                    continue

                all_rows.append({
                    "sentence_id": sid,
                    "source_project": project_name,
                    "treatment_type": treatment_type,
                    "context_config": context_config,
                    "score": bleu,
                })

    # Print validation report
    print(f"\nTotal sentences across all projects: {global_sentence_counter}")
    print(f"Total output rows: {len(all_rows)}")

    if validation_issues:
        print(f"\nValidation issues ({len(validation_issues)}):")
        for issue in validation_issues:
            print(issue)
    else:
        print("\nNo validation issues found.")

    # Write output CSV
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sentence_id", "source_project", "treatment_type", "context_config", "score"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nOutput written to: {OUTPUT_FILE}")

    # Summary statistics
    print("\n--- Summary Statistics ---")

    # Count by treatment_type
    type_counts = defaultdict(int)
    for row in all_rows:
        type_counts[row["treatment_type"]] += 1
    print("\nRows by treatment_type:")
    for t in sorted(type_counts):
        print(f"  {t}: {type_counts[t]}")

    # Count unique sentence_ids
    unique_sentences = set(row["sentence_id"] for row in all_rows)
    print(f"\nUnique sentence_ids: {len(unique_sentences)}")

    # Count conditions per sentence
    conditions_per_sentence = defaultdict(int)
    for row in all_rows:
        conditions_per_sentence[row["sentence_id"]] += 1
    cond_counts = defaultdict(int)
    for sid, count in conditions_per_sentence.items():
        cond_counts[count] += 1
    print("\nConditions per sentence distribution:")
    for count in sorted(cond_counts):
        print(f"  {count} conditions: {cond_counts[count]} sentences")

    # Cross-tabulation: treatment_type x pivot_config
    cross_tab = defaultdict(lambda: defaultdict(int))
    for row in all_rows:
        cross_tab[row["treatment_type"]][row["context_config"]] += 1
    print("\nCross-tabulation (treatment_type x context_config):")
    for ttype in ["direct", "single_context", "dual_context"]:
        configs = sorted(cross_tab[ttype].keys())
        print(f"  {ttype}:")
        for config in configs:
            print(f"    {config}: {cross_tab[ttype][config]}")

    # Check for duplicates
    seen = set()
    duplicates = 0
    for row in all_rows:
        key = (row["sentence_id"], row["context_config"])
        if key in seen:
            duplicates += 1
        seen.add(key)
    if duplicates:
        print(f"\nWARNING: {duplicates} duplicate sentence_id x context_config combinations!")
    else:
        print("\nNo duplicate sentence_id x context_config combinations.")


if __name__ == "__main__":
    main()
