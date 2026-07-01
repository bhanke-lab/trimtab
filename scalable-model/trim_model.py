"""
Trim Decision Pricing Model (scalable-model)
============================================
Reads a Comact TrimExpert AllProducts.xml export and builds, per species + thickness,
a single value ladder of the grades the Comact runs, plus the trim decision matrix.

Everything is done through the PRICES, because the price grid is the only thing the Comact
consumes. There is no decision-side rule: the trim matrix is pure value, exactly what the
Comact does with these prices. So the two protections below are built into the numbers:

- Even-length protection is a consequence of GAP. As long as each one-grade price step stays
  in the safe band, no even board out-values a shorter odd board one grade up, so a 14 or 16
  never trims down to a 13 or 15. See GAP below.
- Freezing the long lengths (13+) is done by flattening their prices: FREEZE_FROM sets every
  grade at those lengths to the top price, so length wins and grade gives no reason to trim.

Each species is one ordered ladder of tiers, highest value first. A tier holds one or more
grades; grades in the same tier are tied (same price), so the Comact never trims between them.
Global rule: Select is tied into the 1 Common tier, so 1 Common never trims up to Select.

Adjustability: tiers are data (order + ties + which lengths carry variance). Tune trims with
GAP, ODD_DISCOUNT, SIX_DISCOUNT, and FREEZE_FROM. Add back an excluded grade by putting its
name in a tier and un-commenting one line in that species' parser.
"""
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict

# ============================ POLICY CONFIG ============================
ODD_DISCOUNT = 0.06   # even/odd lever for variance tiers. MUST stay < 1/15 = 0.0667.
SIX_DISCOUNT = 0.09   # 6' low-point discount on variance tiers
MARGIN       = 0.0    # pure value: any positive gain upgrades. 0 matches the Comact.

# GAP is the one-grade price step: each tier is priced at GAP x the tier above it.
# It is the even-length protection. Keep it in the band below:
#   * GAP >= 0.882  so a 16 (or 14) never out-trims to a shorter odd one grade up.
#   * GAP <= 0.912  so the odd upgrades at 9/11/13/15 still fire.
# 0.89 sits in the middle (about a 12.4% one-grade gap).
GAP = 0.89

# FREEZE_FROM: set to a length (e.g. 13) to flatten every grade at that length and longer to
# the top price. Those lengths then never trim (length wins, grade is equalized). None = off.
FREEZE_FROM = None

LENGTHS = list(range(6, 17))

# Each ladder: list of tiers, HIGHEST value first.  tier = (has_even_odd_variance, [grade names]).
# Same tier = tied price. Prices are generated from GAP, so only the ORDER and the TIES live here.

# ---- Hard maple: no 1W / 2W / FAS Brown (excluded). Sap and unselected on one ladder. ----
HMW = [
    (True,  ['FAS S']),
    (True,  ['1 Common']),                 # 1 Common unselected
    (True,  ['Sap Select', '1 Common Sap']),
    (True,  ['2 Common Sap']),
    (True,  ['3A Sap']),                   # no raw grade in export yet; kept for later
    (True, ['1 Common Brown', '2 Common', '3A Common', '3B Common', 'Subgrade']),
]

# ---- Soft maple: hard maple plus plain Select (tied to 1 Common) and Wormy (between
#      2 Common Sap and 3A Sap). ----
SMA = [
    (True,  ['FAS S']),
    (True,  ['1 Common', 'Select']),
    (True,  ['Sap Select', '1 Common Sap']),
    (True,  ['2 Common Sap']),
    (True,  ['Wormy']),
    (True,  ['3A Sap']),                   # no raw grade in export yet; kept for later
    (True, ['1 Common Brown', '2 Common', '3A Common', '3B Common', 'Subgrade']),
]

# ---- Ash: no color sort. All color grades collapse to their base grade. ----
ASH = [
    (True,  ['FAS']),
    (True,  ['1 Common', 'Select']),
    (True,  ['2 Common']),
    (True,  ['3A Common']),
    (True, ['3B Common']),
    (True, ['Subgrade']),                 # SG
    (True, ['Pallet']),                   # no raw grade in export yet; kept for later
]

# ---- Cherry: heartwood on top. Sap is not wanted, so it prices into the 1 Common tier. ----
CHERRY = [
    (True,  ['FAS 90-50', 'FAS Red']),
    (True,  ['Select 90-50', '1 Common 90-50', '1 Common', 'Select', 'FAS Sap']),
    (True,  ['2 Common']),
    (True,  ['3A Common']),
    (True, ['Subgrade']),                 # SG
    (True, ['3B Common', 'Pallet']),
]

# ---- Red oak: no color sort, no quarter sawn, no fas 10in (excluded). ----
ROK = [
    (True,  ['FAS', 'FAS Stain']),
    (True,  ['1 Common', 'Select']),
    (True,  ['1&2 Common']),
    (True,  ['2 Common']),
    (True,  ['3A Common']),
    (True, ['3B Common', 'Subgrade']),
]

# ---- White oak: like red oak, plus Character between 2 Common and 3A. ----
WOK = [
    (True,  ['FAS', 'FAS Stain']),
    (True,  ['1 Common', 'Select']),
    (True,  ['2 Common']),
    (True,  ['Character']),
    (True,  ['3A Common']),
    (True, ['3B Common', 'Subgrade']),
]

# ---- Walnut: keep everything, do not want to trim. All tiers flat (no even-length trims).
#      No subgrade. ----
WALNUT = [
    # One tied price for every grade: nothing to gain by trimming, so walnut never trims.
    (True, ['FAS', '1 Common', 'Select', '2 Common', '3A Common', '3B Common']),
]

# ---- Basswood / birch / tulip: simple, no subgrade. ----
PLAIN = [
    (True,  ['FAS']),
    (True,  ['1 Common', 'Select']),
    (True,  ['2 Common']),
    (True,  ['3A Common']),
    (True, ['3B Common']),
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
    if g.startswith('SEL') and 'SAP' in g: return 'FAS Sap'   # sap select prices with the sap tier
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
    """Return the present tiers as [{value, variance, names}], highest first. Prices come
    from GAP: the top present tier is 1.0, each lower present tier is GAP x the one above."""
    spec = SPECIES.get(species)
    if not spec: return []
    ladder, canon = spec
    raw = combo.get((species, thick), set())
    name_to_tier = {}
    for i, (var, names) in enumerate(ladder):
        for n in names: name_to_tier[n] = i
    present = defaultdict(list)
    for g in raw:
        nm = canon(g)
        if nm is None or nm not in name_to_tier: continue
        idx = name_to_tier[nm]
        if nm not in present[idx]: present[idx].append(nm)
    tiers, rank = [], 0
    for i, (var, names) in enumerate(ladder):
        if i in present:
            ordered = [n for n in names if n in present[i]]
            tiers.append({'value': GAP ** rank, 'variance': var, 'names': ordered})
            rank += 1
    return tiers

def price(tier, L, scale=1.0):
    if FREEZE_FROM is not None and L >= FREEZE_FROM:
        return 1.0 * scale                            # frozen: flat top price -> length wins, no trim
    base = tier['value'] * scale
    if not tier['variance']: return base              # flat: same $/MBF every length
    if L == 6: return base * (1 - SIX_DISCOUNT)
    if L % 2 == 0: return base
    return base * (1 - ODD_DISCOUNT)

def board_value(tier, L, scale=1.0, width=12, thick_dec=1.0):
    return price(tier, L, scale) / 1000 * thick_dec * width * L / 12

def decision_blocks(tiers, margin=MARGIN, width=12, thick_dec=1.0):
    """Pure value, exactly what the Comact does with these prices: a lower tier climbs to a
    higher tier when the shorter board at the higher tier is worth more."""
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
