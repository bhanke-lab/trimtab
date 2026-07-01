# Value threshold theory

Why the Comact trims one length to another, and how the pricing model is tuned
to match it.

## The core rule

The Comact optimizer is purely value based. For each board it scores every legal
solution in dollars and keeps the highest. There is no upgrade switch. A board
trims from an odd length to an even length only when the even-length solution is
worth more than the odd-length one.

Trimming usually costs surface measure (board feet), so the upgraded value has to
clear the current value by more than the lost wood is worth.

## Board value

    board value = ($/MBF / 1000) x ThickDec x Width x Length / 12

A higher grade lifts $/MBF and a longer board adds board feet. Trimming shortens
the board, trading board feet for a shot at a better grade or a more saleable length.

## How big the one-grade gap can be

Two forces pull on the one-grade price step in opposite directions.

An upgrade that loses surface measure (a 7 ft chopped to a 6 ft, dropping a full board foot)
only pays if the price jump is large, roughly 20 to 25 percent. A big gap is what would force
those trades.

But a one-grade gap above about 13.5 percent breaks even-length protection: a 16 starts
trimming down to a 15 (see below). So the gap cannot be pushed to 20 to 25 percent without
leaking the long evens.

The model keeps the one-grade step (GAP) around 12 percent. That protects the evens and still
fires the near-even upgrades (9 to 8, 11 to 10, and so on, which lose little or no surface
measure). The heavy surface-measure-losing trades like 7 to 6 do not fire, which is the right
call: you do not want to chop a 7 down to a 6, and you do not want a 16 trimming to a 15.

## The over-pricing trap

Build the gap too big and it flips the other way. A flat 20 percent odd-length
penalty can make an 8 ft 1 Common worth more than a 9 ft 1 Common, even after the
9 footer's extra surface measure. The machine then never makes a 9 ft 1 Common
because the 8 ft version always wins, and you lose that product. The target is a
gap big enough to capture the upgrades you want and small enough to keep
legitimate odd-length grades alive.

## Even-length protection

A good even length should never trim down to a shorter odd one: a 16 should not become a 15,
a 14 should not become a 13. This is done entirely in the prices, because the prices are the
only thing the optimizer reads. There is no rule sitting on top.

The lever is GAP, the one-grade price step (each tier is priced at GAP times the tier above).
A 16 stays put only if the 15 one grade up is worth less, and working that through the board
foot math gives a ceiling: with the odd discount at 0.06, the one-grade step has to be at
least 0.882 (about a 13.5 percent gap or smaller). The step also has to be small enough that
the odd upgrades still fire, which caps it around 0.912. So GAP lives in a band of about 0.882
to 0.912, with 0.89 in the middle. Inside that band every even is protected one grade up and
every odd still upgrades.

Ties help too: grades sharing one price never trim between each other, which is how Select is
kept from being reached by a 1 Common, and how walnut is pinned so it never trims.

The one thing pricing cannot cover is a two-grade jump in a single cut (a 2 Common landing as
FAS). Two steps stack past the ceiling, so a long even can still be pulled by a two-grade gain.
That is what the freeze is for.

## How this maps to the generator

The scalable-model tool puts the same logic in code, all of it in the prices:

- GAP is the one-grade price step (each tier is GAP times the tier above). It is the even
  protection. Keep it in the 0.882 to 0.912 band: tighter and the odd upgrades stop firing,
  looser and the long evens leak. 0.89 is the default.
- ODD_DISCOUNT is the even/odd lever (0.06). It must stay under 1/15 = 0.0667, or a 15 trims
  to 14 inside its own grade.
- SIX_DISCOUNT drops the 6 ft to a low point so nothing wants to become a 6.
- The decision is pure value: a trim fires on any positive gain, exactly like the Comact. No
  decision-side rule, so what the model shows is what the machine does.
- FREEZE_FROM flattens every grade at a length and longer to the top price (set it to 13 to
  lock 13, 14, 15, 16). Grade is equalized, length wins, so those lengths never trim. It is
  the belt-and-suspenders for the two-grade jump that pricing alone cannot stop.
- Tiers can be tied (several grades at one price) so the optimizer never trims between them.

## Only ratios matter

The optimizer compares dollar values, so multiplying every price by a constant changes
no decision. The absolute scale is arbitrary. Set the top grade to any convenient number,
then tune the gaps between grades and the even/odd lever. The ratios and balances are the
whole policy. The reported dollar figures do not affect which board trims.

## Basis

Derived from the Comact TrimExpert optimizer's value-based behavior: every board is
scored in dollars and the highest-value solution wins.
