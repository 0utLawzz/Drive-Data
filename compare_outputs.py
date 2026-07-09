"""
compare_outputs.py — Diff two Drive Folders List export files.

Compares OLD vs NEW CSV/Excel output and generates:
  - export/comparison_report.csv  — machine-readable diff
  - export/comparison_report.html — human-readable colour-coded report

Usage:
    python compare_outputs.py export/old_output.csv export/new_output.csv
    python compare_outputs.py export/old_output.xlsx export/new_output.xlsx

Record identity key : CLIENT NUMBER + CASE # + TM NO + CLASS
Columns skipped     : DATE ADDED (timestamps differ between runs)
Duplicate keys      : warned and skipped (first occurrence wins)
"""

import sys
import argparse
import html
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

EXPORT_DIR = str(Path(__file__).parent / "export")
os.makedirs(EXPORT_DIR, exist_ok=True)

KEY_COLS     = ["CLIENT NUMBER", "CASE #", "TM NO", "CLASS"]
SKIP_COMPARE = {"DATE ADDED"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    try:
        if p.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path, engine="openpyxl", dtype=str)
        else:
            df = pd.read_csv(path, dtype=str)
    except Exception as exc:
        print(f"❌ Failed to read {path}: {exc}")
        sys.exit(1)
    return df.fillna("")


def index_rows(df: pd.DataFrame, label: str) -> dict:
    """
    Build a {composite_key: row_dict} index.
    Warns and skips duplicate keys so they don't silently overwrite each other.
    """
    index = {}
    seen  = {}
    dupes = 0

    for i, (_, row) in enumerate(df.iterrows(), start=2):  # row 1 = header
        key = tuple(str(row.get(c, "")).strip() for c in KEY_COLS)
        if key in index:
            if key not in seen:
                seen[key] = []
            seen[key].append(i)
            dupes += 1
        else:
            index[key] = row.to_dict()

    if dupes:
        print(f"   ⚠️  {label}: {dupes} duplicate key(s) found — first occurrence kept.")
        for key, rows in seen.items():
            print(f"      Key {key} duplicated at rows {rows}")

    return index


def compare(old_df: pd.DataFrame, new_df: pd.DataFrame):
    all_cols     = sorted(set(old_df.columns) | set(new_df.columns),
                          key=lambda c: (c not in KEY_COLS, c))
    compare_cols = [c for c in all_cols if c not in SKIP_COMPARE and c not in KEY_COLS]

    old_index = index_rows(old_df, "OLD")
    new_index = index_rows(new_df, "NEW")

    added   = []
    removed = []
    changed = []

    for key, new_row in new_index.items():
        if key not in old_index:
            added.append({"_status": "ADDED",
                          **{c: new_row.get(c, "") for c in all_cols}})

    for key, old_row in old_index.items():
        if key not in new_index:
            removed.append({"_status": "REMOVED",
                            **{c: old_row.get(c, "") for c in all_cols}})
        else:
            new_row = new_index[key]
            diffs   = {}
            for col in compare_cols:
                old_val = str(old_row.get(col, "")).strip()
                new_val = str(new_row.get(col, "")).strip()
                if old_val != new_val:
                    diffs[col] = (old_val, new_val)
            if diffs:
                entry = {"_status": "CHANGED",
                         **{c: new_row.get(c, "") for c in all_cols}}
                entry["_changed_columns"] = "; ".join(
                    f"{c}: [{old}] → [{new}]" for c, (old, new) in diffs.items()
                )
                changed.append(entry)

    return added, removed, changed


def save_csv_report(added, removed, changed, out_path):
    rows = added + removed + changed
    if not rows:
        return
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"📄 CSV report  : {out_path}")


def e(value) -> str:
    """HTML-escape a value and convert newlines to <br> for safe display."""
    escaped = html.escape(str(value) if value else "")
    return escaped.replace("\n", "<br>")


def save_html_report(added, removed, changed, old_path, new_path, out_path):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(added) + len(removed) + len(changed)

    def key_cells(d):
        return "".join(f"<td><b>{e(d.get(c,''))}</b></td>" for c in KEY_COLS)

    rows_html = ""

    for r in added:
        rows_html += (
            f'<tr class="added">'
            f'<td class="status">➕ ADDED</td>'
            f'{key_cells(r)}'
            f'<td colspan="2"><em>New record</em></td>'
            f'</tr>\n'
        )

    for r in removed:
        rows_html += (
            f'<tr class="removed">'
            f'<td class="status">➖ REMOVED</td>'
            f'{key_cells(r)}'
            f'<td colspan="2"><em>Record deleted</em></td>'
            f'</tr>\n'
        )

    for r in changed:
        rows_html += (
            f'<tr class="changed">'
            f'<td class="status">✏️ CHANGED</td>'
            f'{key_cells(r)}'
            f'<td class="changes" colspan="2">{e(r.get("_changed_columns",""))}</td>'
            f'</tr>\n'
        )

    key_headers = "".join(f"<th>{e(c)}</th>" for c in KEY_COLS)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Drive Folders List — Comparison Report</title>
  <style>
    body  {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f9; color: #333; }}
    .header {{ background: #1a3a5c; color: #fff; padding: 24px 32px; }}
    .header h1 {{ margin: 0 0 6px; font-size: 1.5rem; }}
    .header p  {{ margin: 0; font-size: 0.9rem; opacity: .8; }}
    .summary {{ display: flex; gap: 16px; padding: 20px 32px; flex-wrap: wrap; }}
    .card {{ background: #fff; border-radius: 8px; padding: 16px 24px; flex: 1;
             min-width: 140px; box-shadow: 0 1px 4px rgba(0,0,0,.1); text-align: center; }}
    .card .num {{ font-size: 2rem; font-weight: 700; }}
    .card .lbl {{ font-size: .85rem; color: #666; margin-top: 4px; }}
    .card.added   .num {{ color: #2d8a4e; }}
    .card.removed .num {{ color: #c0392b; }}
    .card.changed .num {{ color: #d68910; }}
    .card.total   .num {{ color: #1a3a5c; }}
    .content {{ padding: 0 32px 32px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff;
             box-shadow: 0 1px 4px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; }}
    th {{ background: #1a3a5c; color: #fff; padding: 10px 12px; text-align: left; font-size: .85rem; }}
    td {{ padding: 9px 12px; font-size: .85rem; border-bottom: 1px solid #eee; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    tr.added   {{ background: #eafaf1; }}
    tr.removed {{ background: #fdf2f0; }}
    tr.changed {{ background: #fef9ec; }}
    .status  {{ font-weight: 600; white-space: nowrap; }}
    .changes {{ font-family: monospace; font-size: .8rem; color: #555; }}
    .meta    {{ padding: 0 32px 8px; font-size: .8rem; color: #888; }}
    .no-diff {{ background: #fff; border-radius: 8px; padding: 32px; text-align: center;
                box-shadow: 0 1px 4px rgba(0,0,0,.1); color: #2d8a4e; font-size: 1.1rem; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>&#x1F5C2;&#xFE0F; Drive Folders List &mdash; Comparison Report</h1>
    <p>Generated: {e(now)}</p>
  </div>

  <div class="summary">
    <div class="card total">
      <div class="num">{total}</div>
      <div class="lbl">Total Differences</div>
    </div>
    <div class="card added">
      <div class="num">{len(added)}</div>
      <div class="lbl">&#x2795; Added Records</div>
    </div>
    <div class="card removed">
      <div class="num">{len(removed)}</div>
      <div class="lbl">&#x2796; Removed Records</div>
    </div>
    <div class="card changed">
      <div class="num">{len(changed)}</div>
      <div class="lbl">&#x270F;&#xFE0F; Changed Records</div>
    </div>
  </div>

  <div class="meta">
    <b>OLD:</b> {e(old_path)} &nbsp;|&nbsp; <b>NEW:</b> {e(new_path)}
  </div>

  <div class="content">
"""
    if total == 0:
        html_doc += '    <div class="no-diff">&#x2705; Outputs are identical &mdash; no differences found.</div>\n'
    else:
        html_doc += f"""    <table>
      <thead>
        <tr>
          <th>Status</th>
          {key_headers}
          <th colspan="2">Details / Changed Columns</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
"""
    html_doc += "  </div>\n</body>\n</html>"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"&#x1F310; HTML report : {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare two Drive Folders List export files (CSV or Excel)"
    )
    parser.add_argument("old_file", help="Path to OLD output (CSV or Excel)")
    parser.add_argument("new_file", help="Path to NEW output (CSV or Excel)")
    parser.add_argument(
        "--csv-out",
        default=os.path.join(EXPORT_DIR, "comparison_report.csv"),
        help="Path for the CSV report (default: export/comparison_report.csv)"
    )
    parser.add_argument(
        "--html-out",
        default=os.path.join(EXPORT_DIR, "comparison_report.html"),
        help="Path for the HTML report (default: export/comparison_report.html)"
    )
    args = parser.parse_args()

    print(f"📂 Loading OLD: {args.old_file}")
    old_df = load(args.old_file)
    print(f"   {len(old_df)} records")

    print(f"📂 Loading NEW: {args.new_file}")
    new_df = load(args.new_file)
    print(f"   {len(new_df)} records")

    print("\n🔍 Comparing…")
    added, removed, changed = compare(old_df, new_df)

    print(f"   ➕ Added  : {len(added)}")
    print(f"   ➖ Removed: {len(removed)}")
    print(f"   ✏️  Changed: {len(changed)}")
    print()

    save_csv_report(added, removed, changed, args.csv_out)
    save_html_report(added, removed, changed, args.old_file, args.new_file, args.html_out)

    total = len(added) + len(removed) + len(changed)
    if total == 0:
        print("\n✅ Outputs are IDENTICAL (DATE ADDED timestamps excluded).")
    else:
        print(f"\n⚠️  {total} difference(s) found — see the reports above.")


if __name__ == "__main__":
    main()
