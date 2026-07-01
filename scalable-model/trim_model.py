"""
Trim Decision Pricing Model (scalable-model)
============================================
Reads a Comact TrimExpert AllProducts.xml export and builds, per species + thickness,
the list of grades the Comact runs, each with a relative price, plus the trim decision
matrix.

Key points:
- Every grade the Comact runs is its own line (its own price input).
  Grades that should be 'equal' get the SAME price but stay separate grades.
- The Comact upgrades on any positive gain, so the rule is strict > 0.
- Only ratios matter (scale cancels). Tune trims through the prices.
- Color: a board cannot trim across color (brown cannot become sap), so cross-color
  climbs are skipped.
- Flat grades carry no even/odd variance, so they make no even-length trims (the rule
  for the brown/low tier).

Maple, ash, cherry, and oak are each priced from their own canonical grade table
(below), reflecting that species' color or sort streams. The remaining species use a
generic NHLA ladder until their own canonical pricing is set.
"""
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict

# ============================ POLICY CONFIG ============================
ODD_DISCOUNT = 0.06   # even/odd lever for variance grades. MUST stay < 1/15 = 0.0667.
SIX_DISCOUNT = 0.09   # 6' low-point discount on variance grades
MARGIN       = 0.0    # pure value: any positive gain upgrades. 0 matches the Comact.
LENGTHS = list(range(6, 17))

# ---- Maple (HMW, SMA): Nate's canonical grades. Each is its own Comact line. ----
# name: (relative value, has_even/odd_variance, color). Equal value = no trim between.
# Values are relative placeholders; only ratios matter, tune freely. Equalities are real.
MAPLE_BLOCK = 0.50    # the shared bottom block (1C Brown = 2C unsel = 3A = 3B = SG [= Wormy])
# color is the NHLA color class: '1white','2white','sap','brown','unsel'. Trimming climbs
# the standard grade ladder WITHIN one color class only; it never crosses color.
MAPLE = {
    'FAS 1W':         (1.00, True,  '1white'),  # No.1 White FAS, its own color class
    'FAS S':          (0.97, True,  'sap'),     # Sap FAS, top of the sap stream
    'FAS 2W':         (0.95, True,  '2white'),  # No.2 White FAS, its own color class
    'FAS Brown':      (0.90, True,  'brown'),   # top of the brown stream
    'Sap Select':     (0.85, True,  'sap'),     # Sap Select = 1 Common Sap (equal, no trim between)
    '1 Common Sap':   (0.85, True,  'sap'),
    '2 Common Sap':   (0.78, True,  'sap'),
    '1 Common':       (0.70, True,  'unsel'),   # plain / unselected, top of the unselected stream
    '1 Common Brown': (MAPLE_BLOCK, False, 'brown'),  # flat block, brown stream
    '2 Common':       (MAPLE_BLOCK, False, 'unsel'),  # flat block, unselected stream
    '3A Common':      (MAPLE_BLOCK, False, 'unsel'),
    '3B Common':      (MAPLE_BLOCK, False, 'unsel'),
    'Wormy':          (MAPLE_BLOCK, False, 'unsel'),  # soft maple only
    'Subgrade':       (MAPLE_BLOCK, False, 'unsel'),
}
MAPLE_ORDER = ['FAS 1W','FAS S','FAS 2W','FAS Brown','Sap Select','1 Common Sap',
               '2 Common Sap','1 Common','1 Common Brown','2 Common','3A Common',
               '3B Common','Wormy','Subgrade']

def canon_maple(g):
    g = g.upper()
    if 'WORMY' in g: return 'Wormy'
    if 'CHAR' in g or 'STAIN' in g or g.startswith('VENEER'): return None
    if g.startswith('FAS1W'): return 'FAS 1W'
    if g.startswith('FAS2W'): return 'FAS 2W'
    if g.startswith('FASS'):  return 'FAS S'
    if g.startswith('FASB'):  return 'FAS Brown'
    if g.startswith('FAS'):   return 'FAS S'
    if g.startswith('SEL'):   return 'Sap Select'
    if '1COM' in g and 'SAP' in g: return '1 Common Sap'
    if '2COM' in g and 'SAP' in g: return '2 Common Sap'
    if g.startswith('1COMB'): return '1 Common Brown'
    if g.startswith('1COM'):  return '1 Common'
    if g.startswith('2COM'):  return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'):    return '3B Common'
    if g.startswith('SUBG'):  return 'Subgrade'
    return None

# ---- Generic NHLA ladder for non-maple species (collapsed for now) ----
GENERIC_ORDER = ['FAS','Select','1 Common','2 Common','3A Common','3B Common','Below Grade']
GENERIC_LEVEL = {'FAS':1.000,'Select':0.943,'1 Common':0.890,'2 Common':0.840,
                 '3A Common':0.452,'3B Common':0.385,'Below Grade':0.327}
GENERIC_FLATTEN = 'Below Grade'   # only SG/Pallet flat for non-maple

def canon_generic(g):
    g = g.upper()
    if 'WORMY' in g or 'CHAR' in g or 'STAIN' in g or g.startswith('VENEER'): return None
    if g.startswith('FAS'): return 'FAS'
    if g.startswith('SEL'): return 'Select'
    if g.startswith('1COM') or g.startswith('1C/2C'): return '1 Common'
    if g.startswith('2COM'): return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'): return '3B Common'
    if g.startswith('SUBG'): return 'Below Grade'
    return None

# ---- Ash (white-sorted like maple; distinct prices, no equalities for now) ----
ASH = {
    'FAS 1W':     (1.00, True,  '1white'),
    'FAS S':      (0.97, True,  'sap'),
    'FAS 2W':     (0.95, True,  '2white'),
    'Select 1W':  (0.93, True,  '1white'),
    'Sap Select': (0.90, True,  'sap'),
    'Select 2W':  (0.88, True,  '2white'),
    'FAS Brown':  (0.85, True,  'brown'),
    'FAS':        (0.80, True,  'unsel'),
    'Select':     (0.74, True,  'unsel'),
    '1 Common':   (0.68, True,  'unsel'),
    '2 Common':   (0.58, True,  'unsel'),
    '3A Common':  (0.40, True,  'unsel'),
    '3B Common':  (0.34, False, 'unsel'),
    'Subgrade':   (0.29, False, 'unsel'),
}
ASH_ORDER = ['FAS 1W','FAS S','FAS 2W','FAS Brown','Select 1W','Sap Select','Select 2W',
             'FAS','Select','1 Common','2 Common','3A Common','3B Common','Subgrade']

def canon_ash(g):
    g = g.upper()
    if 'CHAR' in g or 'STAIN' in g or g.startswith('VENEER'): return None
    if g.startswith('FAS1W'): return 'FAS 1W'
    if g.startswith('FAS2W'): return 'FAS 2W'
    if g.startswith('FASS'):  return 'FAS S'
    if g.startswith('FASB'):  return 'FAS Brown'
    if g.startswith('SEL1W'): return 'Select 1W'
    if g.startswith('SEL2W'): return 'Select 2W'
    if g.startswith('SEL SAP') or g.startswith('SELSAP'): return 'Sap Select'
    if g.startswith('FAS'):   return 'FAS'
    if g.startswith('SEL'):   return 'Select'
    if g.startswith('1COM'):  return '1 Common'
    if g.startswith('2COM'):  return '2 Common'
    if g.startswith('3ACOM'): return '3A Common'
    if g.startswith('3B'):    return '3B Common'
    if g.startswith('SUBG'):  return 'Subgrade'
    return None

# ---- Cherry (heartwood-premium: Red/90-50 > Sap > Unselected) ----
CHERRY = {
    'FAS Red':        (1.00, True,  'red'),
    'FAS 90-50':      (0.98, True,  'red'),
    'Select 90-50':   (0.90, True,  'red'),
    '1 Common 90-50': (0.80, True,  'red'),
    'FAS Sap':        (0.85, True,  'sap'),
    'Sap Select':     (0.78, True,  'sap'),
    'Select':         (0.72, True,  'unsel'),
    '1 Common':       (0.66, True,  'unsel'),
    '2 Common':       (0.56, True,  'unsel'),
    '3A Common':      (0.40, True,  'unsel'),
    '3B Common':      (0.34, False, 'unsel'),
    'Subgrade':       (0.29, False, 'unsel'),
}
CHERRY_ORDER = ['FAS Red','FAS 90-50','Select 90-50','1 Common 90-50','FAS Sap','Sap Select',
                'Select','1 Common','2 Common','3A Common','3B Common','Subgrade']

def canon_cherry(g):
    g = g.upper()
    if 'CHAR' in g or 'STAIN' in g or g.startswith('VENEER') or '2CHPY' in g: return None
    if g.startswith('FASR'):     return 'FAS Red'
    if g.startswith('FAS9050'):  return 'FAS 90-50'
    if g.startswith('FASSAP'):   return 'FAS Sap'
    if g.startswith('SEL9050'):  return 'Select 90-50'
    if g.startswith('1COM9050'): return '1 Common 90-50'
    if g.startswith('SEL SAP') or g.startswith('SELSAP'): return 'Sap Select'
    if g.startswith('SEL'):      return 'Select'
    if g.startswith('1COM'):     return '1 Common'
    if g.startswith('2COM'):     return '2 Common'
    if g.startswith('3ACOM'):    return '3A Common'
    if g.startswith('3B'):       return '3B Common'
    if g.startswith('SUBG'):     return 'Subgrade'
    return None

# ---- Oak (red & white): plain ladder + parallel sorts (quarter sawn, stain, character) ----
# Streams never trim across: plain is the main grade ladder, quarter sawn is a sawing
# pattern, stain and character are their own lower sorts, '1&2 Common' is a combined sort.
OAK = {
    'FAS Quarter Sawn': (1.10, True,  'qsawn'),
    'FAS':              (1.00, True,  'plain'),
    'FAS 10in':         (1.00, True,  'plain'),
    'Select':           (0.94, True,  'plain'),
    '1 Common':         (0.89, True,  'plain'),
    '2 Common':         (0.80, True,  'plain'),
    '3A Common':        (0.45, True,  'plain'),
    '3B Common':        (0.38, False, 'plain'),
    'Subgrade':         (0.33, False, 'plain'),
    '1&2 Common':       (0.85, True,  'combo'),
    'FAS Stain':        (0.70, True,  'stain'),
    'FAS Stain 2nd':    (0.60, True,  'stain'),
    'Character':        (0.55, True,  'char'),
}
OAK_ORDER = ['FAS Quarter Sawn','FAS','FAS 10in','Select','1 Common','2 Common','3A Common',
             '1&2 Common','FAS Stain','FAS Stain 2nd','Character','3B Common','Subgrade']

def canon_oak(g):
    g = g.upper()
    if g.startswith('VENEER') or '2CHPY' in g: return None
    if 'QUARTER' in g:                return 'FAS Quarter Sawn'
    if 'STAIN' in g and '2ND' in g:   return 'FAS Stain 2nd'
    if 'STAIN' in g:                  return 'FAS Stain'
    if g.startswith('CHAR'):          return 'Character'
    if g.startswith('FAS10'):         return 'FAS 10in'
    if g.startswith('FAS'):           return 'FAS'
    if g.startswith('SEL'):           return 'Select'
    if g.startswith('1C/2C'):         return '1&2 Common'
    if g.startswith('1COM'):          return '1 Common'
    if g.startswith('2COM'):          return '2 Common'
    if g.startswith('3ACOM'):         return '3A Common'
    if g.startswith('3B'):            return '3B Common'
    if g.startswith('SUBG'):          return 'Subgrade'
    return None

SPECIES_TABLES = {
    'HMW':    (MAPLE,  MAPLE_ORDER,  canon_maple),
    'SMA':    (MAPLE,  MAPLE_ORDER,  canon_maple),
    'ASH':    (ASH,    ASH_ORDER,    canon_ash),
    'CHERRY': (CHERRY, CHERRY_ORDER, canon_cherry),
    'ROK':    (OAK,    OAK_ORDER,    canon_oak),
    'WOK':    (OAK,    OAK_ORDER,    canon_oak),
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

def entries_for(combo, species, thick):
    """Return ordered list of grade entries: {name, value, variance, color}."""
    raw = combo[(species, thick)]
    spec = SPECIES_TABLES.get(species)
    if spec:
        table, order_list, canon = spec
        present = {}
        for g in raw:
            name = canon(g)
            if name is None: continue
            if name == 'Wormy' and species != 'SMA': continue
            present[name] = table[name]
        names = [n for n in order_list if n in present]
        return [{'name': n, 'value': present[n][0], 'variance': present[n][1], 'color': present[n][2]} for n in names]
    # generic
    ranks = set()
    for g in raw:
        r = canon_generic(g)
        if r: ranks.add(r)
    order = [r for r in GENERIC_ORDER if r in ranks]
    flat_from = GENERIC_ORDER.index(GENERIC_FLATTEN)
    return [{'name': r, 'value': GENERIC_LEVEL[r],
             'variance': GENERIC_ORDER.index(r) < flat_from, 'color': None} for r in order]

def price(e, L, scale=1.0):
    base = e['value'] * scale
    if not e['variance']: return base            # flat: same $/MBF every length
    if L == 6: return base * (1 - SIX_DISCOUNT)
    if L % 2 == 0: return base
    return base * (1 - ODD_DISCOUNT)

def board_value(e, L, scale=1.0, width=12, thick_dec=1.0):
    return price(e, L, scale) / 1000 * thick_dec * width * L / 12

def decision_blocks(entries, margin=MARGIN, width=12, thick_dec=1.0):
    """Trims climb the standard grade ladder within one color class only (NHLA: trimming
    moves a board up the standard grades, it does not change its color sort)."""
    def bv(e, L): return board_value(e, L, 1.0, width, thick_dec)
    def reds(cur, up):
        return [L for L in range(7, 17) if (bv(up, L-1) - bv(cur, L)) / bv(cur, L) > margin]
    streams = defaultdict(list)
    for e in entries:
        streams[e['color']].append(e)   # entries are already in value order within a class
    res = {'same': {}, 'up1': {}, 'up2': {}}
    for e in entries:
        res['same'][e['name']] = reds(e, e)
    for grp in streams.values():
        for r in range(1, len(grp)):
            res['up1'][f"{grp[r]['name']} -> {grp[r-1]['name']}"] = reds(grp[r], grp[r-1])
        for r in range(2, len(grp)):
            res['up2'][f"{grp[r]['name']} -> {grp[r-2]['name']}"] = reds(grp[r], grp[r-2])
    return res

def write_report_csv(combo, species, thick, path, scale=600.0, width=12):
    es = entries_for(combo, species, thick)
    names = [e['name'] for e in es]
    rows = [[f'{species} {thick} pricing model  (relative, illustrative scale top = {scale:g})'],
            ['grades'] + names, []]
    rows.append(['PRICE / 1000'] + LENGTHS)
    for e in es:
        rows.append([e['name']] + [round(price(e, L, scale)) for L in LENGTHS])
    rows += [[], [f'$ / BOARD (width {width})'] + LENGTHS]
    for e in es:
        rows.append([e['name']] + [round(board_value(e, L, scale, width), 2) for L in LENGTHS])
    res = decision_blocks(es, width=width)
    for title, blk in (('SAME GRADE', 'same'), ('1 GRADE UP', 'up1'), ('2 GRADES UP', 'up2')):
        rows += [[], [title + '  (R = trim fires)'] + list(range(7, 17))]
        for k, r in res[blk].items():
            rows.append([k] + ['R' if L in r else '.' for L in range(7, 17)])
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    return names

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    xml_path = args[0] if len(args) >= 1 else 'allproducts.xml'
    combo = load_raw(xml_path)
    if len(args) >= 3:
        species, thick = args[1], args[2]
    else:
        species, thick = max(combo, key=lambda k: len(combo[k]))
    names = write_report_csv(combo, species, thick, f'sample_{species}_{thick.replace("/", "-")}.csv')
    print(f'{species} {thick} grades: ' + ' | '.join(names))
    print(f'wrote sample_{species}_{thick.replace("/", "-")}.csv')
