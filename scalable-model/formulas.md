# scalable-model (Python tool)

Python generator that

1) reads AllProducts.xml,
2) derives the canonical NHLA grade ladder for a species + thickness
3) emits the relative pricing model + trim decision matrix.

Files: trim_model.py, README.md. Reads the shared value-table/fixtures/allproducts_sample.xml.

## Model

    price(grade, even L) = LEVEL[grade]
    price(grade, odd L)  = LEVEL[grade] * (1 - ODD_DISCOUNT)
    price(grade, 6 ft)   = LEVEL[grade] * (1 - SIX_DISCOUNT)
    board value = price / 1000 * thick_dec * width * length / 12

A trim fires when the gain from trimming down one foot (optionally landing a
better grade) is >= MARGIN percent of the current board value.

## Knobs (in trim_model.py)

- LEVEL: relative even-length price per NHLA rank (the real pricing policy goes here)
- ODD_DISCOUNT = 0.06  (MUST stay < 1/15 = 0.0667 or the 15'->14' same-grade trim goes positive)
- SIX_DISCOUNT = 0.09
- FLATTEN_AT = 3B Common  (this rank and below go flat)
- SUBGRADE = Below Grade  (the only flat rank allowed to trim, to escape subgrade)
- MARGIN = 0.02

## Policy baked in

- Collapse grade variants to canonical NHLA rank.
- Exclude specialties (Wormy, Char, Stain) and Veneer.
- Flatten at 3B Common and below; flat tier never trims except a Below Grade board escaping subgrade.
- Margin-percent decision rule, not naive > 0.

Full trim_model.py source is on the model spec page and ships in this folder.
