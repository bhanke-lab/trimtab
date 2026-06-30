# The board-value formula

Every dollar figure in the pricing tools comes from one formula:

    Board value ($) = ($/MBF / 1000) x ThickDec x Width x Length / 12 x lever

- **$/MBF** is price per 1000 board feet.
- **/ 1000** converts MBF pricing down to a single board-foot basis.
- **ThickDec x Width x Length / 12** is the board-foot content of one piece
  (thickness as a quarter-inch decimal, width in inches, length in feet).
- **lever** is the even/odd zone multiplier (1.0 = no change).

A higher grade lifts $/MBF and a longer board adds board feet. The lever discounts
odd or out-of-favor lengths.

Sanity check at width 10, ThickDec 1.0 (4/4):

- 6 ft at $500/MBF  = 500/1000 * 1 * 10 * 6 / 12  = $2.50/board
- 9 ft at $540/MBF  = 540/1000 * 1 * 10 * 9 / 12  = $4.05/board
