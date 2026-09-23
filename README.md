# AFS Compiler

[![Tests](https://github.com/paulojorge1963/afs-compiler/actions/workflows/tests.yml/badge.svg)](https://github.com/paulojorge1963/afs-compiler/actions/workflows/tests.yml)

A local tool for compiling Annual Financial Statements (AFS) for small South African
companies, in the style of a compilation-engagement AFS pack prepared under the
**IFRS for SME's** and the **Companies Act of South Africa, 71 of 2008**.

This is a **compilation aid**, not an audit or review tool. It assembles a full AFS
pack from figures you provide, on the basis of ISRS 4410 (Revised) compilation
engagements. Every generated pack carries a "FOR REVIEW BEFORE ISSUE" banner/footer -
it does not replace your accounting practitioner's review before the pack is issued.

All data stays on your machine in a single SQLite file (`data/afs_compiler.db`).

## Running it

```bash
./run.sh
```

This creates a virtual environment on first run, installs dependencies, and starts
the app at http://127.0.0.1:8420.

## Getting started

1. Fill in `AFS-Compiler-Input-Template.xlsx` (the companion workbook) for an entity's
   financial year, or use the worked Example Photography Studio FY2026 example as-is.
2. Open the app and go to **Import Workbook**. Every sheet is parsed into the database.
3. Open the financial year and check the **Validation** tab - every check must tie to
   zero before you can generate the document.
4. Use **Generate** to download the `.docx` AFS pack.
5. Next year, use **Create Next Year** from the Generate tab to roll closing balances
   forward into a new financial year and export a pre-filled workbook.

Everything the workbook captures is also directly editable in the app (Trial Balance,
PPE Register, Loans, Tax Computation, Policy Elections) - the workbook is a convenience
for offline data capture, not the only way in.

## Running the tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

The calc-engine tests use the Example Photography Studio FY2026 figures as fixtures and
assert every cross-check in the workbook's Validation Summary sheet ties to zero,
independently of document generation.

## Architecture

- `app/models.py` - SQLAlchemy models mirroring the input workbook's sheets exactly.
- `app/calc.py` - pure calculation-engine functions (Section 6). Every figure is
  computed here once and reused by both the on-screen preview and the document
  generator - never recomputed independently.
- `app/reporting.py` - orchestrates calc.py into one consistent `ReportData` object
  per financial year, including note auto-numbering.
- `app/importer.py` / `app/exporter.py` - workbook <-> database round trip.
- `app/rollforward.py` - "Create Next Year".
- `app/docgen.py` - generates the `.docx` AFS pack.
- `app/policy_library/` - the library of standard IFRS for SME's accounting policy
  paragraphs, one per section, gated by each financial year's Policy Elections.
- `app/routers/` - FastAPI routes; `app/templates/` - server-rendered Jinja2 pages.

## Known limitations of the generated .docx

- **Page numbering is deterministic by construction, not measured.** The generator
  forces one hard page break per statement/note/section and counts pages by
  construction, so the Contents page and the "pages X to Y" references in the
  Director's Responsibilities/Report and Practitioner's Report are only correct as
  long as no single section's content overflows one physical page. For a small
  entity like the worked example this holds; a much larger trial balance, PPE
  register or loan book may push a section onto a second page and the numbers after
  it will drift by that many pages. Reflow the document in Word if that happens.
- The Independent Review Report and Independent Auditor's Report wording are left as
  placeholders (see Section 10) - only the Compilation Report is fully drafted.

## Explicitly out of scope for v1

- Deferred tax, VAT reconciliation/VAT201 support, provisional tax (IRP6) calculations.
- Audit or independent review procedures/evidence - only the report *wording*
  branches on report type; no assurance work is performed by the tool.
- Multi-currency, group/consolidated accounts, XBRL/CIPC iXBRL submission.
- User accounts/authentication - this is a single-user local tool.

## A note on tax rates

The Small Business Corporation (SBC) tax bracket table on each financial year's Tax
Computation tab is a per-year, user-editable input, never a constant baked into the
app - SARS revises the brackets annually. A new financial year's bracket table is
pre-populated by copying the prior year's as a starting point; check SARS's current
published rates before relying on the output.

## Development workflow

`main` is protected, including for the repo owner: direct pushes are rejected, and
every change has to come in through a pull request with a passing `test` check
(GitHub Actions, see `.github/workflows/tests.yml`).

```bash
git checkout -b my-change
# ...edit, commit...
git push -u origin my-change
gh pr create --fill
# wait for the "test" check to go green, then:
gh pr merge --squash
```
