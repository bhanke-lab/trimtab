"""
Trim Decision Pricing Model (scalable-model)
============================================
Reads a Comact TrimExpert AllProducts.xml export, derives the real grade ladder
for a chosen species + thickness, and generates a relative pricing structure plus
the trim decision matrix that drives the trimmer's keep/trim calls.

WHY RELATIVE: current $/MBF in the XML is outdated and being rebuilt, so this model
ignores the dollar levels and works in relative structure. Trim decisions depend only
on grade spacing + the even/odd length lever, so relative structure is all that matters.
Drop in real $/MBF later by setting LEVEL.

Pipeline:
  XML  ->  canonical NHLA grade ladder  ->  relative price grid  ->  decision matrix
"""
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict

# ======================= POLICY CONFIG (the editable knobs) =======================
RANK_ORDER = ['Veneer','FAS','Select','1 Common','2 Common','3A Common','3B Common','Below Grade']
EXCLUDE_RANKS = {'Veneer'}             # Veneer + specialties (Wormy/Char/Stain) excluded from trim model

# Relative even-length level by canonical rank. THIS is where the real pricing policy lives.
# Values are relative (FAS even = 1.0). Replace with the new $/MBF policy when set.
LEVEL = {'FAS':1.000, 'Select':0.943, '1 Common':0.890, '2 Common':0.840,
         '3A Common':0.452, '3B Common':0.385, 'Below Grade':0.327}

ODD_DISCOUNT = 0.06   # even/odd lever. HARD CEILING: must stay < 1/(max odd length).
                      # For lengths up to 16 (max odd = 15) that is 1/15 = 0.0667.
                      # At/above the ceiling, same-grade odd->even trim (e.g. 15'->14') goes
                      # POSITIVE and the model recommends a mistrim within grade. Do not exceed it.
SIX_DISCOUNT = 0.09   # 6' low-point discount (keeps 7'->6' trims from firing)
FLATTEN_AT  = '3B Common'   # this rank and everything below it goes flat (lever -> 0)
SUBGRADE    = 'Below Grade' # the ONLY flat rank allowed to trim: a board may trim to escape subgrade
MARGIN      = 0.02    # a trim fires only if the gain is >= this % of the current board value
LENGTHS = list(range(6, 17))   # 6..16 ft
# ==================================================================================

def rank_index(label): return RANK_ORDER.index(label)
FLAT_FROM = rank_index(FLATTEN_AT)

def canon(grade):
    """Map a raw TrimExpert grade string to its canonical NHLA rank (variants collapse)."""
    g = grade.upper()
    for k in ('WORMY', 'CHAR', 'STAIN'):
        if k in g: return 'SPECIALTY'
    if g.startswith('VENEER'): return 'Veneer'
    if g.startswith('FAS'): return 'FAS'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1COM') or g.startswith('1C/2C'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return 'Below Grade'
    return 'UNMAPPED:' + grade

def load_ladders(path):
    """Return {(species, thick): set(canonical ranks)} from an AllProducts.xml export."""
    root = ET.parse(path).getroot()
    combo = defaultdict(set)
    for b in root.findall('Board'):
        d = {c.tag: (c.text or '') for c in b}
        species = d['name'].strip().split()[-1]   # species is the last token of <name>
        lab = canon(d['grade'])
        if lab == 'SPECIALTY' or lab in EXCLUDE_RANKS:
            continue
        combo[(species, d['thick'])].add(lab)
    return combo

def ladder_for(combo, species, thick):
    return sorted(combo[(species, thick)], key=rank_index)

def q_for(label):
    return 0.0 if rank_index(label) >= FLAT_FROM else ODD_DISCOUNT

def price(label, L, scale=1.0):
    """Relative price/MBF for a grade at length L (x scale for an illustrative dollar view)."""
    base = LEVEL[label] * scale
    if L == 6: return base * (1 - SIX_DISCOUNT)
    if L % 2 == 0: return base
    return base * (1 - q_for(label))

def board_value(label, L, scale=1.0, width=12, thick_dec=1.0):
    return price(label, L, scale) / 1000 * thick_dec * width * L / 12

def suppressed(source_label, is_same):
    """Flat tier never trims, EXCEPT a subgrade board trimming upward to escape subgrade."""
    if rank_index(source_label) < FLAT_FROM: return False
    if is_same: return True
    return source_label != SUBGRADE

def decision_blocks(ladder, margin=MARGIN, width=12, thick_dec=1.0):
    """Return red (trim-fires) from-lengths for same-grade, 1-grade-up, 2-grade-up."""
    def bv(lab, L): return board_value(lab, L, 1.0, width, thick_dec)
    res = {'same': {}, 'up1': {}, 'up2': {}}
    for lab in ladder:
        res['same'][lab] = ([] if suppressed(lab, True)
            else [L for L in range(7, 17) if (bv(lab, L-1) - bv(lab, L)) / bv(lab, L) >= margin])
    for r in range(1, len(ladder)):
        lab, up = ladder[r], ladder[r-1]
        res['up1'][f'{lab} -> {up}'] = ([] if suppressed(lab, False)
            else [L for L in range(7, 17) if (bv(up, L-1) - bv(lab, L)) / bv(lab, L) >= margin])
    for r in range(2, len(ladder)):
        lab, up = ladder[r], ladder[r-2]
        res['up2'][f'{lab} -> {up}'] = ([] if suppressed(lab, False)
            else [L for L in range(7, 17) if (bv(up, L-1) - bv(lab, L)) / bv(lab, L) >= margin])
    return res

def write_report_csv(combo, species, thick, path, scale=600.0, width=12):
    lad = ladder_for(combo, species, thick)
    rows = [[f'{species} {thick} pricing model  (relative, illustrative scale FAS even = {scale:g})'],
            ['ladder'] + lad, []]
    rows.append(['PRICE / 1000'] + LENGTHS)
    for lab in lad:
        rows.append([lab] + [round(price(lab, L, scale)) for L in LENGTHS])
    rows += [[], [f'$ / BOARD (width {width})'] + LENGTHS]
    for lab in lad:
        rows.append([lab] + [round(board_value(lab, L, scale, width), 2) for L in LENGTHS])
    res = decision_blocks(lad, width=width)
    for title, blk in (('SAME GRADE', 'same'), ('1 GRADE UP', 'up1'), ('2 GRADES UP', 'up2')):
        rows += [[], [title + '  (R = trim fires)'] + list(range(7, 17))]
        for k, reds in res[blk].items():
            rows.append([k] + ['R' if L in reds else '.' for L in range(7, 17)])
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    return lad

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    xml_path = args[0] if len(args) >= 1 else 'allproducts.xml'
    combo = load_ladders(xml_path)
    if len(args) >= 3:
        species, thick = args[1], args[2]
    else:
        # No combo given: pick the species/thickness with the most grades, so any
        # export produces a full example without editing the script.
        species, thick = max(combo, key=lambda k: len(combo[k]))
    lad = ladder_for(combo, species, thick)
    out = f'sample_{species}_{thick.replace("/", "-")}.csv'
    write_report_csv(combo, species, thick, out)
    print(f'{species} {thick} ladder: ' + ' > '.join(lad))
    print(f'wrote {out}')
    print()
    print('all species/thickness ladders:')
    for (s, t) in sorted(combo):
        print(f'  {s:8} {t:5}: ' + ' > '.join(ladder_for(combo, s, t)))
