# trim-decision-tools

Three tools that turn a Comact TrimExpert product export into pricing and trim
decisions on a hardwood sawmill floor.

- **value-table/** - Pick a thickness and species; the workbook lists every
  grade for that combo sorted by value, with $/MBF and per-board dollar value
  across lengths 6 to 16. Includes length zones, an even/odd value lever
  system, a Trim Impact Calculator, and a "Should You Trim This Board" helper.
- **scalable-model/** - A Python generator. Reads a Comact TrimExpert AllProducts.xml
  export, derives the real grade ladder for a species and thickness, and generates a
  relative price-by-length grid plus the trim decision matrix.
- **sim-comparison/** - Compares board-foot output between two trimmer simulations,
  grade by grade and length by length, to value a pricing or trim-rule change.

## Why this repo has no .xlsx

Excel workbooks are zipped binaries, so Git cannot diff or version them in any
useful way. Instead this repo ships the **text that the workbook is built from**:
the spill formulas, the RESET Office Script, the Power Query loader, and a
step-by-step rebuild guide. Build the workbook yourself from these and you get a
clean, auditable history. A workbook-builder script is on the roadmap.

## Sample data only

The catalog fixture and every example price in this repo are **synthetic**. Real
production pricing has been stripped.

## Quick start

1. Read `docs/math.md` for the one formula every dollar figure comes from.
2. To build the lookup tool, follow `value-table/README.md`.
3. To build the pricing engine, follow `scalable-model/README.md`.

## Roadmap

- [x] Python generator for the pricing model (scalable-model/trim_model.py).
- [ ] Extend it to emit the value-table RawData.csv and build the workbook with
      openpyxl.
