from pathlib import Path
import argparse
import polib

def flatten_msg(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    return s.replace("\n", "")  
def main():
    ap = argparse.ArgumentParser(description="Extract msgid (.org.txt) and msgstr (.ref.txt) from .po files")
    ap.add_argument("input_dir", type=Path, help="Folder containing .po files")
    ap.add_argument("output_dir", type=Path, help="Folder to write extracted strings")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    po_files = list(args.input_dir.rglob("*.po"))
    if not po_files:
        raise SystemExit("No .po files found.")

    for po_path in po_files:
        po = polib.pofile(str(po_path))

        org_rows = []
        ref_rows = []

        for entry in po:
            if entry.obsolete:
                continue
            if entry.msgid == "":
                continue

            if not (entry.msgstr or "").strip():
                continue

            org_rows.append(flatten_msg(entry.msgid))
            ref_rows.append(flatten_msg(entry.msgstr))

        base_out = args.output_dir / po_path.relative_to(args.input_dir)
        base_out.parent.mkdir(parents=True, exist_ok=True)

        org_path = base_out.with_suffix(".org.txt")
        ref_path = base_out.with_suffix(".ref.txt")

        org_path.write_text("\n".join(org_rows), encoding="utf-8")
        ref_path.write_text("\n".join(ref_rows), encoding="utf-8")

        print(f"[OK] {po_path.name} -> {org_path.name} ({len(org_rows)} lines), {ref_path.name} ({len(ref_rows)} lines)")

if __name__ == "__main__":
    main()
