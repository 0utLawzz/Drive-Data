---
name: Drive Folders List — Parser V2 convention
description: Rules for evolving the folder-name parser without breaking the production CLI.
---

`main.py` is the production interactive CLI for this project (a trademark-firm
Drive-folder scanner) and must never be modified except for a confirmed,
narrowly-scoped, reviewed bug fix. New/experimental parsing logic (e.g. a
token-based rewrite) goes in an additive sibling package (`parser_v2/`) that
mirrors `main.py`'s public function signatures, selectable via an opt-in CLI
flag (e.g. `batch_export.py --engine v2`), never as a silent default change.

**Why:** the tool is actively used by the firm; there's no acceptable
mid-session rollback path if a parsing rewrite breaks it. Building additively
lets you validate against the full live dataset with zero production risk
before ever touching the original.

**How to apply:** before trusting a new parsing engine, run a comparator
against the *entire* live dataset (not just the small sample fixture) and
diff **every** output field it produces, not a subset — narrow field
comparisons can hide real regressions/improvements (e.g. this project's
comparator initially skipped `case_name` and looked "clean" while masking
130 real differences). Zero regressions is the hard gate; any other output
delta must be explicitly bucketed/explained, not silently ignored.
