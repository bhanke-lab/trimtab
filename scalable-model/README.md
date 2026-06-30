# Scalable Pricing Model (Python)

Reads a Comact TrimExpert AllProducts.xml export and generates the pricing model and
trim decision matrix for any species + thickness, using the grades that combo actually
runs.

Prices are RELATIVE (current $/MBF is outdated and being rebuilt); decisions depend only
on grade spacing + the even/odd lever, so relative structure is enough. Set real $/MBF
later by editing LEVEL.

## Run

    python3 trim_model.py path/to/AllProducts.xml

Writes a sample CSV and prints every species/thickness grade ladder.

## Pipeline

AllProducts.xml -> canonical NHLA grade ladder -> relative price grid -> decision matrix
