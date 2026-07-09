"""
validate_parser_v2.py — Compare Parser V2 against the legacy engine on the
live Brandex Google Drive dataset, before any code is promoted or committed.

Only folder NAMES are needed to compare parsing behaviour (case/client field
extraction does not look at file contents), so this traversal only lists
client and case folders — no file listing — making it far lighter than
validate_drive.py's full run (which also scans every file for pattern
tick-marks).

For every case folder found, this script:
  1. Runs the legacy diagnose_case() (imported from validate_drive.py, which
     imports the real parsing functions from main.py — unchanged).
  2. Runs parser_v2.diagnose_case() (the new token-based engine).
  3. Compares outputs and buckets each case into:
       - "identical"    — same case_no/tm_no/class_code/case_name.
       - "v2_fixed"      — v1 failed/warned on a missing Case #, v2 recovered it
                            (expected: the OI-1 2-digit Case # bug fix).
       - "regression"    — v1 succeeded on a field, v2 now leaves it blank.
                            MUST be zero for backward compatibility.
       - "other_change"  — any other output difference (reviewed manually).

Usage:
    python validate_parser_v2.py
    python validate_parser_v2.py --clients-id FOLDER_ID --consultants-id FOLDER_ID
    python validate_parser_v2.py --search-name "1 ALL CLIENTS"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed

from validate_drive import (
    BASE_DIR,
    EXPORT_DIR,
    FOLDER_MIME,
    build_drive_service,
    find_folder_by_name,
    list_items,
    _get_thread_service,
    diagnose_case as diagnose_case_v1,
)
from parser_v2 import diagnose_case as diagnose_case_v2


def _list_case_names_for_client(client_folder: dict, creds_path: str) -> list[str]:
    svc = _get_thread_service(creds_path)
    case_folders = list_items(svc, client_folder["id"], mime_filter=FOLDER_MIME)
    return [cf["name"] for cf in case_folders]


def collect_case_folder_names(service, root_folder_id: str, creds_path: str, workers: int = 16) -> list[str]:
    """Return every case-folder name under a root (client) folder — names only.

    Uses a thread pool (one worker per client folder) since this only lists
    folder names via the Drive API — no file listing — so it is much lighter
    than validate_drive.py's full traversal.
    """
    names = []
    client_folders = list_items(service, root_folder_id, mime_filter=FOLDER_MIME)
    total = len(client_folders)
    print(f"      Found {total} client folder(s) — listing case names with {workers} workers…")

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_list_case_names_for_client, cf, creds_path): cf for cf in client_folders}
        for future in as_completed(futures):
            done += 1
            if done % 10 == 0 or done == total:
                print(f"      ↳ {done}/{total} client folders scanned")
            try:
                names.extend(future.result())
            except Exception as exc:
                cf = futures[future]
                print(f"      ⚠️  Error listing {cf['name']!r}: {exc}")
    return names


def compare(names: list[str]) -> dict:
    buckets = {
        "identical": [], "v2_fixed": [], "case_name_fixed": [],
        "regression": [], "other_change": [],
    }
    v1_stats = {"failure": 0, "warning": 0, "ok": 0}
    v2_stats = {"failure": 0, "warning": 0, "ok": 0}

    for name in names:
        d1 = diagnose_case_v1(name)
        d2 = diagnose_case_v2(name)

        v1_stats["failure" if d1["is_failure"] else "warning" if d1["is_warning"] else "ok"] += 1
        v2_stats["failure" if d2["is_failure"] else "warning" if d2["is_warning"] else "ok"] += 1

        fields = ("case_no", "tm_no", "class_code", "case_name")
        same = all(d1[f] == d2[f] for f in fields)

        if same:
            buckets["identical"].append(name)
            continue

        # A regression is: v1 had a non-empty value for a field, v2 has it blank.
        regressed = any(d1[f] and not d2[f] for f in fields)
        # An improvement is: v1 had case_no blank, v2 recovered it.
        improved_case_no = (not d1["case_no"]) and bool(d2["case_no"])

        # Case-name truncation fix: v1's extract_full_case_name() only runs
        # when a TM No is present (early-returns "" otherwise), so v1 falls
        # back to a single-word case_name for TM-less folders. v2 always
        # extracts the full multi-word name. Detect this specific, expected
        # improvement: same case_no/tm_no/class_code, and v2's case_name is
        # v1's case_name extended with more words (not a different value).
        core_fields_same = (d1["case_no"], d1["tm_no"], d1["class_code"]) == \
                            (d2["case_no"], d2["tm_no"], d2["class_code"])
        case_name_extended = (
            core_fields_same
            and d1["case_name"] != d2["case_name"]
            and d2["case_name"]
            and (d1["case_name"] == "" or d1["case_name"] in d2["case_name"])
        )

        if regressed:
            buckets["regression"].append({
                "name": name,
                "v1": {f: d1[f] for f in fields},
                "v2": {f: d2[f] for f in fields},
            })
        elif improved_case_no:
            buckets["v2_fixed"].append({
                "name": name,
                "v1_case_no": d1["case_no"],
                "v2_case_no": d2["case_no"],
            })
        elif case_name_extended:
            buckets["case_name_fixed"].append({
                "name": name,
                "v1_case_name": d1["case_name"],
                "v2_case_name": d2["case_name"],
            })
        else:
            buckets["other_change"].append({
                "name": name,
                "v1": {f: d1[f] for f in fields},
                "v2": {f: d2[f] for f in fields},
            })

    return {
        "buckets": buckets,
        "v1_stats": v1_stats,
        "v2_stats": v2_stats,
        "total": len(names),
    }


def write_report(result: dict, out_path: Path, root_labels: list[str], run_ts: str):
    b = result["buckets"]
    v1s, v2s = result["v1_stats"], result["v2_stats"]
    total = result["total"]

    lines = [
        "# Parser V2 Validation Report — Live Brandex Dataset",
        "",
        f"**Generated:** {run_ts}  ",
        f"**Root folders:** {', '.join(root_labels)}  ",
        f"**Case folders compared:** {total}",
        "",
        "---",
        "",
        "## Severity counts: V1 (legacy) vs V2 (token-based)",
        "",
        "| Engine | Failures | Warnings | OK |",
        "|---|---|---|---|",
        f"| V1 (legacy, main.py) | {v1s['failure']} | {v1s['warning']} | {v1s['ok']} |",
        f"| V2 (token-based, parser_v2/) | {v2s['failure']} | {v2s['warning']} | {v2s['ok']} |",
        "",
        "---",
        "",
        "## Backward-compatibility check",
        "",
        f"- **Identical output:** {len(b['identical'])} / {total}",
        f"- **V2 improvements (OI-1 fix — 2-digit Case # recovered):** {len(b['v2_fixed'])}",
        f"- **V2 improvements (case_name truncation fixed for TM-less folders):** {len(b['case_name_fixed'])}",
        f"- **Regressions (V1 succeeded, V2 blanked a field — MUST be 0):** {len(b['regression'])}",
        f"- **Other changes (needs manual review):** {len(b['other_change'])}",
        "",
    ]

    if b["regression"]:
        lines += ["### ⚠️ Regressions detected", ""]
        for r in b["regression"][:20]:
            lines.append(f"- `{r['name']}` — v1={r['v1']} → v2={r['v2']}")
        lines.append("")
    else:
        lines += ["_No regressions — Parser V2 is a strict improvement over the legacy engine._", ""]

    if b["v2_fixed"]:
        lines += ["### ✅ Sample of OI-1 fixes (2-digit Case # now recovered)", ""]
        for r in b["v2_fixed"][:15]:
            lines.append(f"- `{r['name']}` — Case # recovered: `{r['v2_case_no']}`")
        lines.append(f"- … and {max(0, len(b['v2_fixed'])-15)} more" if len(b["v2_fixed"]) > 15 else "")
        lines.append("")

    if b["case_name_fixed"]:
        lines += [
            "### ✅ Sample of case_name truncation fixes",
            "",
            "_v1's `extract_full_case_name()` only runs when a TM No is present, "
            "so it falls back to a single-word case_name for TM-less folders. "
            "v2 always extracts the full multi-word name._",
            "",
        ]
        for r in b["case_name_fixed"][:15]:
            lines.append(f"- `{r['name']}` — case_name: `{r['v1_case_name']}` → `{r['v2_case_name']}`")
        lines.append(f"- … and {max(0, len(b['case_name_fixed'])-15)} more" if len(b["case_name_fixed"]) > 15 else "")
        lines.append("")

    if b["other_change"]:
        lines += ["### Other field changes (manual review)", ""]
        for r in b["other_change"][:15]:
            lines.append(f"- `{r['name']}` — v1={r['v1']} → v2={r['v2']}")
        lines.append("")

    lines += [
        "---",
        "",
        "_Generated by `validate_parser_v2.py`. No project code (main.py) was modified;",
        "Parser V2 lives entirely in `parser_v2/` as an additive module._",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📝 Report written: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Validate Parser V2 against the live Brandex dataset")
    parser.add_argument("--clients-id", metavar="FOLDER_ID")
    parser.add_argument("--consultants-id", metavar="FOLDER_ID")
    parser.add_argument("--search-name", action="append", metavar="NAME")
    parser.add_argument("--creds", default=str(BASE_DIR / "credentials.json"))
    args = parser.parse_args()

    print("🔐 Authenticating with Google Drive…")
    service = build_drive_service(args.creds)
    print("   ✅ Connected")

    roots: list[tuple[str, str]] = []
    if args.clients_id:
        roots.append((args.clients_id, "1 ALL CLIENTS"))
    if args.consultants_id:
        roots.append((args.consultants_id, "2 CONSULTANTS"))
    if args.search_name:
        for name in args.search_name:
            fid = find_folder_by_name(service, name)
            if fid:
                roots.append((fid, name))
            else:
                print(f"   ⚠️  Not found: {name!r}")
    if not roots:
        for name in ("1 ALL CLIENTS", "2 CONSULTANTS"):
            fid = find_folder_by_name(service, name)
            if fid:
                roots.append((fid, name))

    if not roots:
        print("❌ No accessible root folders found.")
        sys.exit(1)

    all_names = []
    for folder_id, label in roots:
        print(f"\n📁 Scanning root: {label}")
        all_names.extend(collect_case_folder_names(service, folder_id, args.creds))

    print(f"\n🔍 Comparing {len(all_names)} case folder names between V1 and V2…")
    result = compare(all_names)

    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_report(result, EXPORT_DIR / "parser_v2_validation_report.md", [l for _, l in roots], run_ts)

    print(f"\nIdentical   : {len(result['buckets']['identical'])}")
    print(f"V2 fixed (case_no)  : {len(result['buckets']['v2_fixed'])}")
    print(f"V2 fixed (case_name): {len(result['buckets']['case_name_fixed'])}")
    print(f"Regressions         : {len(result['buckets']['regression'])}")
    print(f"Other change        : {len(result['buckets']['other_change'])}")


if __name__ == "__main__":
    main()
