# Scalable Pricing Model (Python)

<table width="100%">
  <tr>
    <td align="center" width="50%">
      <img src="../docs/images/trim_model_result.png" alt="Trim model result" width="100%"><br>
      <sub><em>Generated price grid and decision matrix for chosen species + thickness</em></sub>
    </td>
    <td align="center" width="50%">
      <img src="../docs/images/trim_model_output.png" alt="Trim model output" width="100%"><br>
      <sub><em>Resultant visualization of trim decisions from model</em></sub>
    </td>
  </tr>
</table>

Reads a Comact TrimExpert AllProducts.xml export and generates the pricing model and
trim decision matrix for any species + thickness, using the grades that combo actually
runs.

Prices are RELATIVE (current $/MBF is outdated and being rebuilt); decisions depend only
on grade spacing + the even/odd lever, so relative structure is enough. Set real values
later by editing each species' tiers.

## Requirements

Python 3.8 or newer. Single-combo CSV mode is standard library only. Batch xlsx
mode needs openpyxl:

    py -m pip install openpyxl

## Run

    python3 scalable-model/trim_model.py path/to/AllProducts.xml      # macOS / Linux
    py scalable-model/trim_model.py path/to/AllProducts.xml           # Windows

Name a species and thickness to target one combo, or omit them to auto-pick the
combo with the most grades:

    py scalable-model/trim_model.py path/to/AllProducts.xml TUL 4/4

Writes a sample CSV and prints every species/thickness grade ladder.

Batch mode writes one formatted workbook, one visualizer-layout sheet per
species + thickness: price/1000 grid, SM row, $/board grid, the three decision
blocks as live formulas with red-positive conditional formatting, Ideal State
Map.

    py scalable-model/trim_model.py path/to/AllProducts.xml --all --max-length 12 --thickness 4/4 6/4

Flags: --max-length 8-16 (default 16), --width inches (default 8), --scale top
even price (default 600), --out (default trim_models.xlsx), --flat-thickness
to skip the thickness multiplier on $/board.

## Pipeline

AllProducts.xml -> per-species value ladder (tiers + ties) -> relative price grid -> decision matrix
