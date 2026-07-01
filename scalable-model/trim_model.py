"""
Trim Decision Pricing Model (scalable-model)
============================================
Reads a Comact TrimExpert AllProducts.xml export and builds, per species + thickness,
a single value ladder of the grades the Comact runs, plus the trim decision matrix.

How it works:
- Each species is one ordered ladder of TIERS, highest value first.
- A tier holds one or more grades. Grades in the same tier are TIED: same price, so
  the Comact never trims between them.
- The Comact is pure value: a trim fires on any positive gain (rule is strict > 0).
- Only ratios matter (scale cancels). The ORDER and the TIES are the policy; the gap
  sizes are just the lever you tune to place the trims.
- Flat tiers carry no even/odd variance, so they make no even-length trims.

Global rule: 1 Common never trims up to Select. Select is tied into the 1 Common tier
(you only get a Select if the board lays a Select), so no trim fires between them.

Adjustability: everything is data. To change a price gap, edit a tier value. To move a
grade, move its name to another tier. To add back an excluded grade (quarter sawn, fas
10in, the white/brown maple sorts, etc.), put its name in a tier and un-comment the
matching line in that species' parser.
"""
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict

# ============================ POLICY CONFIG ============================
ODD_DISCOUNT = 0.06   # even/odd lever for variance tiers. MUST stay < 1/15 = 0.0667.
SIX_DISCOUNT = 0.09   # 6' low-point discount on variance tiers
MARGIN       = 0.0    # pure value: any positive gain upgrades. 0 matches the Comact.
LENGTHS = list(range(6, 17))

# Each ladder: list of tiers, HIGHEST value first.
# tier = (relative_value, has_even_odd_variance, [grade names]).  Same tier = tied price.
# Values are relative placeholders; tune the gaps. Order + ties are the canonical policy.

# ---- Hard maple: no 1W / 2W / FAS Brown (excluded). Sap and unselected on one ladder. ----
HMW = [
    (1.00, True,  ['FAS S']),
    (0.88, True,  ['1 Common']),                 # 1 Common unselected
    (0.78, True,  ['Sap Select', '1 Common Sap']),
    (0.68, True,  ['2 Common Sap']),
    (0.60, True,  ['3A Sap']),                   # no raw grade in export yet; kept for later
    (0.48, False, ['1 Common Brown', '2 Common', '3A Common', '3B Common', 'Subgrade']),
]

# ---- Soft maple: same as hard maple, plus plain Select (tied to 1 Common) and Wormy
#      (between 2 Common Sap and 3A Sap). ----
SMA = [
    (1.00, True,  ['FAS S']),
    (0.88, True,  ['1 Common', 'Select']),
    (0.78, True,  ['Sap Select', '1 Common Sap']),
    (0.68, True,  ['2 Common Sap']),
    (0.63, True,  ['Wormy']),
    (0.60, True,  ['3A Sap']),                   # no raw grade in export yet; kept for later
    (0.48, False, ['1 Common Brown', '2 Common', '3A Common', '3B Common', 'Subgrade']),
]

# ---- Ash: no color sort. All color grades collapse to their base grade. ----
ASH = [
    (1.00, True,  ['FAS']),
    (0.88, True,  ['1 Common', 'Select']),
    (0.72, True,  ['2 Common']),
    (0.56, True,  ['3A Common']),
    (0.48, False, ['3B Common']),
    (0.42, False, ['Subgrade']),                 # SG
    (0.36, False, ['Pallet']),                   # no raw grade in export yet; kept for later
]

# ---- Cherry: heartwood on top. Sap is not wanted, so sap prices into the 1 Common tier. ----
CHERRY = [
    (1.00, True,  ['FAS 90-50', 'FAS Red']),
    (0.85, True,  ['Select 90-50', '1 Common 90-50', '1 Common', 'Select', 'FAS Sap', 'Sap Select']),
    (0.70, True,  ['2 Common']),
    (0.56, True,  ['3A Common']),
    (0.48, False, ['Subgrade']),                 # SG
    (0.42, False, ['3B Common', 'Pallet']),
]

# ---- Red oak: no color sort, no quarter sawn, no fas 10in (excluded). ----
ROK = [
    (1.00, True,  ['FAS', 'FAS Stain']),
    (0.87, True,  ['1 Common', 'Select']),
    (0.80, True,  ['1&2 Common']),
    (0.72, True,  ['2 Common']),
    (0.56, True,  ['3A Common']),
    (0.46, False, ['3B Common', 'Subgrade']),
]

# ---- White oak: like red oak, plus Character between 2 Common and 3A. ----
WOK = [
    (1.00, True,  ['FAS', 'FAS Stain']),
    (0.87, True,  ['1 Common', 'Select']),
    (0.72, True,  ['2 Common']),
    (0.64, True,  ['Character']),
    (0.56, True,  ['3A Common']),
    (0.46, False, ['3B Common', 'Subgrade']),
]

# ---- Walnut: keep everything, do not want to trim. All tiers flat (no even-length trims).
#      No subgrade. ----
WALNUT = [
    (1.00, False, ['FAS']),
    (0.90, False, ['1 Common', 'Select']),
    (0.80, False, ['2 Common']),
    (0.70, False, ['3A Common']),
    (0.62, False, ['3B Common']),
]

# ---- Basswood / birch / tulip: simple, no subgrade. ----
PLAIN = [
    (1.00, True,  ['FAS']),
    (0.87, True,  ['1 Common', 'Select']),
    (0.72, True,  ['2 Common']),
    (0.56, True,  ['3A Common']),
    (0.48, False, ['3B Common']),
]


# ---- Parsers: raw grade string -> ladder grade name, or None to exclude. ----
def canon_hmw(g):
    g = g.upper()
    if g.startswith('VENEER') or 'WORMY' in g: return None
    if g.startswith('FAS1W') or g.startswith('FAS2W') or g.startswith('FASB'): return None  # excluded: re-add to a tier to restore
    if g.startswith('FASS'): return 'FAS S'
    if g.startswith('FAS'):  return None
    if '1COM' in g and 'SAP' in g: return '1 Common Sap'
    if '2COM' in g and 'SAP' in g: return '2 Common Sap'
    if g.startswith('SEL') and 'SAP' in g: return 'Sap Select'
    if g.startswith('SEL'): return None
    if g.startswith('1COMB'): return '1 Common Brown'
    if g.startswith('1COM'):  return '1 Common'
    if g.startswith('2COM'):  return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'):    return '3B Common'
    if g.startswith('SUBG'):  return 'Subgrade'
    return None

def canon_sma(g):
    g = g.upper()
    if g.startswith('VENEER'): return None
    if 'WORMY' in g: return 'Wormy'
    if g.startswith('FAS1W') or g.startswith('FAS2W') or g.startswith('FASB'): return None  # excluded
    if g.startswith('FASS'): return 'FAS S'
    if g.startswith('FAS'):  return None
    if '1COM' in g and 'SAP' in g: return '1 Common Sap'
    if '2COM' in g and 'SAP' in g: return '2 Common Sap'
    if g.startswith('SEL') and 'SAP' in g: return 'Sap Select'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1COMB'): return '1 Common Brown'
    if g.startswith('1COM'):  return '1 Common'
    if g.startswith('2COM'):  return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'):    return '3B Common'
    if g.startswith('SUBG'):  return 'Subgrade'
    return None

def canon_ash(g):
    g = g.upper()
    if g.startswith('VENEER'): return None
    if g.startswith('FAS'): return 'FAS'        # no color sort: FAS1W/FAS2W/FASS/FASB all fold to FAS
    if g.startswith('SEL'): return 'Select'     # SEL/SEL1W/SEL2W/SEL SAP all fold to Select
    if g.startswith('1COM'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return 'Subgrade'
    return None

def canon_cherry(g):
    g = g.upper()
    if '2CHPY' in g or g.startswith('VENEER'): return None
    if g.startswith('FASR'):     return 'FAS Red'
    if g.startswith('FAS9050'):  return 'FAS 90-50'
    if g.startswith('FASSAP'):   return 'FAS Sap'
    if g.startswith('FAS'):      return None
    if g.startswith('SEL9050'):  return 'Select 90-50'
    if g.startswith('SEL') and 'SAP' in g: return 'Sap Select'
    if g.startswith('SEL'):      return 'Select'
    if g.startswith('1COM9050'): return '1 Common 90-50'
    if g.startswith('1COM'):     return '1 Common'
    if g.startswith('2COM'):     return '2 Common'
    if g.startswith('3ACOM'):    return '3A Common'
    if g.startswith('3B'):       return '3B Common'
    if g.startswith('SUBG'):     return 'Subgrade'
    return None

def canon_rok(g):
    g = g.upper()
    if 'QUARTER' in g: return None              # excluded: no quarter sawn
    if g.startswith('FAS10'): return None       # excluded: no fas 10in
    if '2CHPY' in g or g.startswith('VENEER'): return None
    if 'STAIN' in g: return 'FAS Stain'
    if g.startswith('FAS'): return 'FAS'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1C/2C'): return '1&2 Common'
    if g.startswith('1COM'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return 'Subgrade'
    return None

def canon_wok(g):
    g = g.upper()
    if 'QUARTER' in g: return None              # excluded: no quarter sawn
    if '2CHPY' in g or g.startswith('VENEER'): return None
    if 'STAIN' in g: return 'FAS Stain'
    if g.startswith('CHAR'): return 'Character'
    if g.startswith('FAS'): return 'FAS'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1C/2C'): return '1 Common'
    if g.startswith('1COM'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return 'Subgrade'
    return None

def canon_walnut(g):
    g = g.upper()
    if g.startswith('VENEER'): return None
    if g.startswith('FAS'): return 'FAS'        # incl FAS OPT 6-7' (short FAS prices as FAS)
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1COM'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return None        # no subgrade
    return None

def canon_plain(g):
    g = g.upper()
    if g.startswith('VENEER') or 'WORMY' in g or 'CHAR' in g or 'STAIN' in g: return None
    if g.startswith('FAS'): return 'FAS'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1C/2C'): return '1 Common'
    if g.startswith('1COM'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return None        # no subgrade
    return None

SPECIES = {
    'HMW':      (HMW,    canon_hmw),
    'SMA':      (SMA,    canon_sma),
    'ASH':      (ASH,    canon_ash),
    'CHERRY':   (CHERRY, canon_cherry),
    'ROK':      (ROK,    canon_rok),
    'WOK':      (WOK,    canon_wok),
    'WALNUT':   (WALNUT, canon_walnut),
    'BASSWOOD': (PLAIN,  canon_plain),
    'BIRCH':    (PLAIN,  canon_plain),
    'TUL':      (PLAIN,  canon_plain),
}
# =======================================================================

def load_raw(path):
    """Return {(species, thick): set(raw grade strings)}."""
    root = ET.parse(path).getroot()
    combo = defaultdict(set)
    for b in root.findall('Board'):
        d = {c.tag: (c.text or '') for c in b}
        species = d['name'].strip().split()[-1]
        combo[(species, d['thick'])].add(d['grade'])
    return combo

def tiers_for(combo, species, thick):
    """Return the present tiers as [{value, variance, names:[present grades]}], highest first."""
    spec = SPECIES.get(species)
    if not spec: return []
    ladder, canon = spec
    raw = combo.get((species, thick), set())
    name_to_tier = {}
    for i, (v, var, names) in enumerate(ladder):
        for n in names: name_to_tier[n] = i
    present = defaultdict(list)
    for g in raw:
        nm = canon(g)
        if nm is None or nm not in name_to_tier: continue
        idx = name_to_tier[nm]
        if nm not in present[idx]: present[idx].append(nm)
    tiers = []
    for i, (v, var, names) in enumerate(ladder):
        if i in present:
            ordered = [n for n in names if n in present[i]]
            tiers.append({'value': v, 'variance': var, 'names': ordered})
    return tiers

def price(tier, L, scale=1.0):
    base = tier['value'] * scale
    if not tier['variance']: return base          # flat: same $/MBF every length
    if L == 6: return base * (1 - SIX_DISCOUNT)
    if L % 2 == 0: return base
    return base * (1 - ODD_DISCOUNT)

def board_value(tier, L, scale=1.0, width=12, thick_dec=1.0):
    return price(tier, L, scale) / 1000 * thick_dec * width * L / 12

def decision_blocks(tiers, margin=MARGIN, width=12, thick_dec=1.0):
    """Pure-value trims along the single ladder: a lower tier climbs to a higher tier
    when the shorter board at the higher tier is worth more."""
    def bv(t, L): return board_value(t, L, 1.0, width, thick_dec)
    def reds(cur, up):
        return [L for L in range(7, 17) if (bv(up, L-1) - bv(cur, L)) / bv(cur, L) > margin]
    def label(t): return ' / '.join(t['names'])
    res = {'same': {}, 'up1': {}, 'up2': {}}
    for t in tiers:
        res['same'][label(t)] = reds(t, t)
    for i in range(1, len(tiers)):
        res['up1'][f"{label(tiers[i])} -> {label(tiers[i-1])}"] = reds(tiers[i], tiers[i-1])
    for i in range(2, len(tiers)):
        res['up2'][f"{label(tiers[i])} -> {label(tiers[i-2])}"] = reds(tiers[i], tiers[i-2])
    return res

def write_report_csv(combo, species, thick, path, scale=600.0, width=12):
    tiers = tiers_for(combo, species, thick)
    labels = [' / '.join(t['names']) for t in tiers]
    rows = [[f'{species} {thick} pricing model  (relative, illustrative scale top = {scale:g})'],
            ['tiers'] + labels, []]
    rows.append(['PRICE / 1000'] + LENGTHS)
    for t in tiers:
        rows.append([' / '.join(t['names'])] + [round(price(t, L, scale)) for L in LENGTHS])
    rows += [[], [f'$ / BOARD (width {width})'] + LENGTHS]
    for t in tiers:
        rows.append([' / '.join(t['names'])] + [round(board_value(t, L, scale, width), 2) for L in LENGTHS])
    res = decision_blocks(tiers, width=width)
    for title, blk in (('SAME TIER', 'same'), ('1 TIER UP', 'up1'), ('2 TIERS UP', 'up2')):
        rows += [[], [title + '  (R = trim fires)'] + list(range(7, 17))]
        for k, r in res[blk].items():
            rows.append([k] + ['R' if L in r else '.' for L in range(7, 17)])
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    return labels

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    xml_path = args[0] if len(args) >= 1 else 'allproducts.xml'
    combo = load_raw(xml_path)
    if len(args) >= 3:
        species, thick = args[1], args[2]
    else:
        species, thick = max((k for k in combo if k[0] in SPECIES),
                             key=lambda k: len(combo[k]), default=(None, None))
    if species is None:
        print('No known species found in export.'); sys.exit(0)
    out = f'sample_{species}_{thick.replace("/", "-")}.csv'
    labels = write_report_csv(combo, species, thick, out)
    print(f'{species} {thick} tiers: ' + ' | '.join(labels))
    print(f'wrote {out}')
