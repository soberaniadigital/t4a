from __future__ import annotations

from pathlib import Path
import argparse
import csv
from typing import Dict, List, Tuple

import polib
import sacrebleu


def load_tsv_file(tsv_path: Path) -> Dict[str, str]:

    m: Dict[str, str] = {}
    for line in tsv_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or "\t" not in line:
            continue
        k, v = line.split("\t", 1)
        k = k.strip()
        v = v.strip()
        if k:
            m[k] = v
    return m


def load_all_tsvs(tsv_dir: Path) -> Dict[str, str]:
   
    files = list(tsv_dir.rglob("*.tsv"))
    if not files:
        raise SystemExit(f"No .tsv files found in: {tsv_dir}")
    merged: Dict[str, str] = {}
    for fp in files:
        merged.update(load_tsv_file(fp))
    return merged


def find_matching_tsv(po_path: Path, po_root: Path, tsv_root: Path) -> Path | None:
    
    rel = po_path.relative_to(po_root)
    candidate = (tsv_root / rel).with_suffix(".tsv")
    return candidate if candidate.exists() else None


def collect_pairs_for_po(po_path: Path, hyp_map: Dict[str, str]) -> Tuple[List[str], List[str], int, int]:
    
    po = polib.pofile(str(po_path))
    refs: List[str] = []
    hyps: List[str] = []
    missing_hyp = 0
    missing_ref = 0

    for e in po:
        if e.obsolete or e.msgid == "":
            continue

        msgid = e.msgid.strip()
        hyp = hyp_map.get(msgid)
        if hyp is None:
            missing_hyp += 1
            continue

        ref = (e.msgstr or "").strip()
        if not ref:
            missing_ref += 1
            continue

        refs.append(ref)
        hyps.append(hyp)

    return refs, hyps, missing_hyp, missing_ref


def bleu_score(refs: List[str], hyps: List[str]) -> float:
    return sacrebleu.corpus_bleu(hyps, [refs]).score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--po-dir", type=Path, required=True, help="Folder with .po (msgstr filled)")
    ap.add_argument("--tsv-dir", type=Path, required=True, help="Folder with .tsv hypotheses (msgid<TAB>translation)")
    ap.add_argument("--out-csv", type=Path, default=None, help="Optional CSV output path")
    args = ap.parse_args()

    po_files = list(args.po_dir.rglob("*.po"))
    if not po_files:
        raise SystemExit(f"No .po files found in: {args.po_dir}")

    global_map = None
    rows = []

    for po_path in po_files:
        tsv_path = find_matching_tsv(po_path, args.po_dir, args.tsv_dir)
        if tsv_path is not None:
            hyp_map = load_tsv_file(tsv_path)
        else:
            if global_map is None:
                global_map = load_all_tsvs(args.tsv_dir)
            hyp_map = global_map

        refs, hyps, miss_h, miss_r = collect_pairs_for_po(po_path, hyp_map)

        if not refs:
            rows.append({
                "file": str(po_path.relative_to(args.po_dir)),
                "segments": 0,
                "missing_hyp": miss_h,
                "missing_ref": miss_r,
                "BLEU": None,
            })
            continue

        bleu = bleu_score(refs, hyps)
        rows.append({
            "file": str(po_path.relative_to(args.po_dir)),
            "segments": len(refs),
            "missing_hyp": miss_h,
            "missing_ref": miss_r,
            "BLEU": bleu,
        })

    
    print("\n=== Per-file BLEU (TSV vs PO msgstr) ===")
    header = f"{'file':60}  {'seg':>5}  {'BLEU':>7}  {'miss_h':>6}  {'miss_r':>6}"
    print(header)
    print("-" * len(header))

    for r in sorted(rows, key=lambda x: x["file"]):
        bleu_str = "-" if r["BLEU"] is None else f"{r['BLEU']:.2f}"
        print(
            f"{r['file'][:60]:60}  "
            f"{r['segments']:5d}  "
            f"{bleu_str:>7}  "
            f"{r['missing_hyp']:6d}  "
            f"{r['missing_ref']:6d}"
        )

    # Optional: write CSV
    if args.out_csv:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["file", "segments", "BLEU", "missing_hyp", "missing_ref"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nSaved CSV: {args.out_csv}")


if __name__ == "__main__":
    main()