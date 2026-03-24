from pathlib import Path
import argparse
import pandas as pd
import sacrebleu


def sentence_bleu(hyp: str, ref: str) -> float:
    return sacrebleu.sentence_bleu(hyp, [ref]).score


def base_name_from_csv(csv_name: str) -> str:
    name = csv_name
    suffix = ".org.translated.csv"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return Path(csv_name).stem


def find_ref_file(ref_dir: Path, csv_file: Path) -> Path:
    base = base_name_from_csv(csv_file.name)
    exact = ref_dir / f"{base}.ref.txt"
    if exact.exists():
        return exact

    candidates = list(ref_dir.rglob(f"{base}.ref.txt"))
    if candidates:
        return candidates[0]

    candidates = list(ref_dir.rglob(f"{base}*.ref.txt"))
    if candidates:
        candidates.sort(key=lambda p: len(p.name))
        return candidates[0]

    raise FileNotFoundError(
        f"Reference file not found for CSV '{csv_file.name}'. "
        f"Expected something like '{base}.ref.txt' under {ref_dir}"
    )


def load_ref_lines(ref_path: Path) -> list[str]:
    return [ln.rstrip("\n") for ln in ref_path.read_text(encoding="utf-8").splitlines()]


def make_output_path(output_dir: Path, input_dir: Path, in_path: Path, df: pd.DataFrame) -> Path:

    base = base_name_from_csv(in_path.name)

    out_name = f"{base}.nllb.ctx-0.po.meta.csv"

    
    rel_parent = in_path.relative_to(input_dir).parent
    return output_dir / rel_parent / out_name


def process_file(in_path: Path, input_dir: Path, output_dir: Path, ref_dir: Path) -> None:
    df = pd.read_csv(in_path)

    required = {"original", "translated"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"{in_path.name}: missing required columns: {sorted(missing)}")

    if "reference" not in df.columns:
        df["reference"] = None
    if "context_languages" not in df.columns:
        df["context_languages"] = ""
    if "strategy" not in df.columns:
        df["strategy"] = "NLLB"
    if "bleu" not in df.columns:
        df["bleu"] = None

    ref_path = find_ref_file(ref_dir, in_path)
    ref_lines = load_ref_lines(ref_path)

    if len(ref_lines) != len(df):
        raise SystemExit(
            f"Row mismatch for {in_path.name}:\n"
            f"  CSV rows      = {len(df)}\n"
            f"  ref.txt lines = {len(ref_lines)}\n"
            f"  ref file      = {ref_path}"
        )

    df["reference"] = ref_lines


    scores = []
    for _, row in df.iterrows():
        hyp = "" if pd.isna(row["translated"]) else str(row["translated"]).strip()
        ref = "" if pd.isna(row["reference"]) else str(row["reference"]).strip()
        if not hyp or not ref:
            scores.append(None)
        else:
            scores.append(sentence_bleu(hyp, ref))
    df["bleu"] = scores

    out_path = make_output_path(output_dir, input_dir, in_path, df)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[OK] {in_path.name} -> {out_path.name} (ref: {ref_path.name})")


def main():
    ap = argparse.ArgumentParser(description="Fill reference from .ref.txt and compute per-row BLEU for CSVs")
    ap.add_argument("input_dir", type=Path, help="Folder containing input .csv files")
    ap.add_argument("ref_dir", type=Path, help="Folder containing *.ref.txt files")
    ap.add_argument("output_dir", type=Path, help="Folder to write output .csv files")
    args = ap.parse_args()

    if not args.input_dir.exists():
        raise SystemExit(f"Input dir not found: {args.input_dir}")
    if not args.ref_dir.exists():
        raise SystemExit(f"Ref dir not found: {args.ref_dir}")

    csv_files = list(args.input_dir.rglob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No .csv files found under: {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for in_path in csv_files:
        process_file(in_path, args.input_dir, args.output_dir, args.ref_dir)

    print("Done.")


if __name__ == "__main__":
    main()
