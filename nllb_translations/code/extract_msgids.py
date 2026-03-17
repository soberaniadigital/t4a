from pathlib import Path
import argparse
import polib

def main():
    ap = argparse.ArgumentParser(description="Extract msgid strings from .po files")
    ap.add_argument("input_dir", type=Path, help="Folder containing .po files")
    ap.add_argument("output_dir", type=Path, help="Folder to write extracted strings")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    po_files = list(args.input_dir.rglob("*.po"))
    if not po_files:
        raise SystemExit("No .po files found.")

    for po_path in po_files:
        po = polib.pofile(str(po_path))

        rows = []
        for entry in po:
            if entry.obsolete:
                continue
            if entry.msgid == "":  # header
                continue
            rows.append(entry.msgid)

        out_path = args.output_dir / po_path.relative_to(args.input_dir)
        out_path = out_path.with_suffix(".msgids.txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(rows), encoding="utf-8")

        print(f"[OK] {po_path.name} -> {out_path} ({len(rows)} lines)")

if __name__ == "__main__":
    main()