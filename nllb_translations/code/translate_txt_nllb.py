from pathlib import Path
import argparse
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_DEFAULT = "facebook/nllb-200-distilled-600M"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path, help="Folder with .txt files (extracted msgids)")
    ap.add_argument("output_dir", type=Path, help="Folder to write translated .txt files")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--src-lang", default="eng_Latn")
    ap.add_argument("--tgt-lang", default="por_Latn")
    ap.add_argument("--batch-size", type=int, default=16)
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")

    print("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(device).eval()

    forced_id = tokenizer.convert_tokens_to_ids(args.tgt_lang)

    txt_files = list(args.input_dir.rglob("*.txt"))
    if not txt_files:
        raise SystemExit("No .txt files found in input_dir.")

    for txt_path in txt_files:
        lines = txt_path.read_text(encoding="utf-8").splitlines()

        to_translate = []
        map_idx = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            to_translate.append(line)
            map_idx.append(i)

        if not to_translate:
            out_path = args.output_dir / txt_path.relative_to(args.input_dir)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("", encoding="utf-8")
            print(f"[SKIP] {txt_path.name} (empty) -> {out_path}")
            continue

        # Translate in batches
        translations = [""] * len(to_translate)
        tokenizer.src_lang = args.src_lang

        for start in range(0, len(to_translate), args.batch_size):
            batch = to_translate[start:start + args.batch_size]

            inputs = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(device)

            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    forced_bos_token_id=forced_id,
                    max_new_tokens=256,
                    num_beams=4,
                    do_sample=False,
                )

            decoded = tokenizer.batch_decode(out, skip_special_tokens=True)
            translations[start:start + len(decoded)] = decoded

        out_lines = []
        for src, tgt in zip(to_translate, translations):
            out_lines.append(f"{src}\t{tgt}")

        out_path = args.output_dir / txt_path.relative_to(args.input_dir)
        out_path = out_path.with_suffix(".translated.tsv")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(out_lines), encoding="utf-8")

        print(f"[OK] {txt_path.name} -> {out_path} ({len(to_translate)} lines)")

if __name__ == "__main__":
    main()