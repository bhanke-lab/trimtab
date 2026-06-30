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

## The 20 to 25 percent gap

This is the practical threshold the model is tuned around. It is not a setting. It
is the size of the price gap you have to build for an upgrade to win once surface
measure is lost.

Worked example: a 7 ft 1 Common chopped to a 6 ft prime drops a surface measure.
To make that trade pay, the price difference has to sit around 20 to 25 percent.

- No surface measure lost, a small gap triggers the upgrade.
- Surface measure lost, a bigger gap is needed, roughly 20 to 25 percent.

## The over-pricing trap

Build the gap too big and it flips the other way. A flat 20 percent odd-length
penalty can make an 8 ft 1 Common worth more than a 9 ft 1 Common, even after the
9 footer's extra surface measure. The machine then never makes a 9 ft 1 Common
because the 8 ft version always wins, and you lose that product. The target is a
gap big enough to capture the upgrades you want and small enough to keep
legitimate odd-length grades alive.

## Even-length protection

A good even length should never trim down to an odd one. This is baked into the
prices rather than enforced by a rule on top. At 6 in width the pairs 7/8, 9/10, 11/12 tie on
surface measure, so a one-grade gain between them reads the same in both
directions. A grid that pulls 9 ft up to 8 ft will also pull 8 ft down to 7 ft at
that width. You cannot allow one and forbid the other through pricing alone, so
evens are protected: every even out-values the better-grade odd just below it.

## How this maps to the generator

The scalable-model tool puts the same logic in code:

- ODD_DISCOUNT sets the even/odd gap. It has to stay under 1/15 = 0.0667, or a
  15 ft board trims to 14 ft inside its own grade and the even-protection rule
  fails.
- MARGIN is the 20 to 25 percent style threshold. A trim only fires when the gain
  clears MARGIN percent of the current board value, so marginal moves stay dark.
- FLATTEN_AT drops the even/odd gap to zero for the bottom grades. Once into 3B,
  SG, or pallet the price variance goes away and the floor does not trim for even
  lengths.

## Basis

Derived from the Comact TrimExpert optimizer's value-based behavior: every board is
scored in dollars and the highest-value solution wins.
