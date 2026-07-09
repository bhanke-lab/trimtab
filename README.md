<p align="center">
  <img src="docs/images/logo.png" alt="trimtab" width="180">
</p>

<h1 align="center">trimtab</h1>

<p align="center">steer the ship</p>

<p align="center">
  <img alt="commits" src="https://img.shields.io/github/commit-activity/t/bhanke-lab/trimtab?label=commits">
  <img alt="last commit" src="https://img.shields.io/github/last-commit/bhanke-lab/trimtab">
  <img alt="license" src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue">
</p>

<p align="center">
  <a href="#value-table">Value Table</a> &bull;
  <a href="#scalable-model">Scalable Model</a> &bull;
  <a href="#sim-comparison">Sim Comparison</a> &bull;
  <a href="docs/value-threshold-theory.md">Theory</a> &bull;
  <a href="docs/species-rules.md">Species rules</a>
</p>

---

Make the right trim decisions for a vertically integrated (forestry + mill + dry + distribution) hardwood operation. Dynamic value tables, Python pricing-model generator, and a simulation comparator.  The catalog fixture and every example price in this repo are synthetic. Real production pricing has been stripped.

Excel workbooks are zipped binaries, so Git can't diff them. This repo ships the text the workbook is built from (spill formulas, the RESET Office Script, the Power Query loader, and a rebuild guide) instead of an .xlsx.

## Value Table

<table width="100%">
  <tr>
    <td align="center" width="33%">
      <img src="docs/images/value-table.png" alt="Value Table" width="90%"><br>
      <sub><em>Plain value table visualization</em></sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/images/lengths-value-table.png" alt="Lengths Value Table" width="100%"><br>
      <sub><em>Add length zones and even/odd levers</em></sub>
    </td>
    <td align="center" width="33%">
      <img src="docs/images/manual-lengths-value-table.png" alt="Manual Lengths Value Table" width="100%"><br>
      <sub><em>Add input for custom even/odd figures</em></sub>
    </td>
  </tr>
</table>

Lookup and decision tool over a Comact TrimExpert export.

### Sheets

| Sheet | Purpose | Visibility |
| --- | --- | --- |
| Value Table | Original lookup; grade list auto-sorts by $/MBF, rest are plain formulas | Visible |
| Lengths Value Table | Dynamic, spill-based; length zones and even/odd levers; hosts the trim helpers | Visible |
| Lengths Value Table (Manual) | Same engine, even/odd block is hand-typeable | Visible |
| RawData | Power Query dump, one row per Board record | Visible |
| Helpers | Thickness decimals, species names, width and length tokens | Visible |
| _Formulas_Backup / _LengthsBackup /_ManualBackup | Golden formula copies for RESET | Hidden |

### Rebuild steps

1. Export AllProducts.xml from TrimExpert, or use fixtures/allproducts_sample.xml.
2. Load it via Power Query (see powerquery.m). Confirm the thick column is text.
3. Build the Helpers sheet (thickness to decimal map, species list).
4. Paste the anchor formulas from formulas.md into each tab.
5. Create the three hidden backup sheets from clean copies of each live tab.
6. Add a button and assign the Office Script in reset.ts.
7. Add conditional formatting and the yellow input cells (B1/B2/B3).

#### *Note

- Thickness must be text in RawData.
- Spill formulas need empty room below and right of the anchor, or you get #SPILL!. RESET clears the spill zones before restoring.
- If you change a tab's formulas on purpose, update its backup or the next RESET reverts your change.
- RESET runs as an Office Script in desktop Excel only, not Excel on the web.

## Scalable Model

<table width="100%">
  <tr>
    <td align="center" width="50%">
      <img src="docs/images/trim_model_result.png" alt="Trim model result" width="100%"><br>
      <sub><em>Generated price grid and decision matrix for chosen species + thickness</em></sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/images/trim_model_output.png" alt="Trim model output" width="100%"><br>
      <sub><em>Resultant visualization of trim decisions from model</em></sub>
    </td>
  </tr>
</table>

A Python generator. It reads a Comact TrimExpert AllProducts.xml export and writes the pricing model and trim decision matrix for any species and thickness, using the grades that combo actually runs.

Prices are relative (current $/MBF is outdated and being rebuilt). Decisions depend only on grade spacing and the even/odd lever, so relative structure is enough. Set real values later by editing each species' tiers.

### Requirements

Python 3.8 or newer, standard library only. No pip packages and no requirements.txt.

### Run

    python3 trim_model.py path/to/AllProducts.xml      # macOS / Linux
    py trim_model.py path/to/AllProducts.xml           # Windows

Name a species and thickness to target one combo, or omit them to auto-pick the combo with the most grades:

    py trim_model.py path/to/AllProducts.xml TUL 4/4

Writes a sample CSV and prints every species and thickness grade ladder.

### Pipeline

    AllProducts.xml -> per-species value ladder (tiers and ties) -> relative price grid -> decision matrix

## Sim Comparison

<p align="center">
  <img src="docs/images/sim-comparison.png" alt="Sim Comparison" width="600"><br>
  <sub><em>Variety of comparison metrics for 2 simulations with up to 10 stored</em></sub>
</p>

Compares board-foot output between two Comact trimmer simulation runs, grade by grade and length by length. Use it to value a pricing or trim-rule change before committing it to the optimizer.

### What it answers

- How does each sim's board-foot output per grade compare to the original (OG) run?
- How much does each sim cut odd-length output, where a trim-to-even policy shows up?
- Which sim wins on odd-length reduction without giving up grade?

### How to use

1. Run the same board sample through the Comact under the original setup and two candidate setups. Paste each run's grade totals and length mix into the two matrices.
2. Pick two sims from the dropdowns.
3. The compare blocks show each sim against OG: grade totals, per-length differences, and the odd-length reduction for each.

### Blocks

- Grade totals: each grade's board feet per run.
- Value block: the board-foot difference between two chosen runs per grade, times a grade transfer price (GTP), summed to a dollar swing.
- Length mix and compare: percent of output at each length per run, the difference vs OG, and the percent change.
- Odd-length reduction: the 7, 9, 11 ft drop per run vs OG, as points, as a percent, and as board feet.
- Top reduction: each run's single biggest odd-length cut.

### Note

This tool reads simulation output. It doesn't price boards itself. Pair it with the Scalable Model (the pricing policy) and the Value Table (the lookup).

### On Trim Tabs

A trim tab is the small rudder bolted to the trailing edge of a ship's main rudder. The main rudder is too heavy to push directly, so you turn the small one. Deflecting the tab generates lift on the tab. That lift is small, but it acts at the trailing edge, the longest moment arm available on the rudder. This produces enough torque about the rudder stock to rotate the whole thing. The rudder then generates the turning force on the hull.

All systems have a trailing edge. Trim tab.
