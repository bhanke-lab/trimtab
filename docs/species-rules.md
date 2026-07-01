# Species rules

Each species is one value ladder, highest value first. A tier holds one or more grades; grades
in the same tier are tied (same price), so the optimizer never trims between them. Trimming is
pure value: a board climbs the ladder when the shorter board at a higher tier is worth more.
Flat tiers carry no even/odd variance, so they make no even-length trims. Only ratios matter;
the order and the ties are the policy, the gap sizes are the lever.

Global rule: 1 Common never trims up to Select. Select is tied into the 1 Common tier, so a
Select is only called when the board lays a Select.

## Hard maple

Excludes No.1 White, No.2 White, and FAS Brown.

1. FAS Sap
2. 1 Common (unselected)
3. Sap Select = 1 Common Sap
4. 2 Common Sap
5. 3A Sap
6. Flat bottom, all tied: 1 Common Brown = 2 Common = 3A = 3B = Subgrade

## Soft maple

Hard maple's ladder, plus Wormy between 2 Common Sap and 3A Sap, and a plain Select tied into
the 1 Common tier.

## Ash

No color sort. Every color grade folds to its base grade.

1. FAS
2. 1 Common = Select
3. 2 Common
4. 3A Common
5. 3B Common (flat)
6. Subgrade (flat)
7. Pallet (flat)

## Cherry

Heartwood on top. Sap is priced into the 1 Common tier (sap is not wanted as a premium).

1. FAS 90-50 = FAS Red
2. Select 90-50 = 1 Common 90-50 = 1 Common = Select = FAS Sap
3. 2 Common
4. 3A Common
5. Subgrade (flat)
6. 3B = Pallet (flat)

## Red oak

No color sort, no quarter sawn, no FAS 10in.

1. FAS = FAS Stain
2. 1 Common = Select
3. 1&2 Common
4. 2 Common
5. 3A Common
6. 3B = Subgrade (flat)

## White oak

Red oak's ladder, plus Character between 2 Common and 3A.

1. FAS = FAS Stain
2. 1 Common = Select
3. 2 Common
4. Character
5. 3A Common
6. 3B = Subgrade (flat)

## Walnut

Keep everything, minimal trimming. Every tier is flat, so no even-length trims. No subgrade.

1. FAS
2. 1 Common = Select
3. 2 Common
4. 3A Common
5. 3B Common

## Basswood, birch, tulip

Simple, no subgrade.

1. FAS
2. 1 Common = Select
3. 2 Common
4. 3A Common
5. 3B Common (flat)

## Adjustability

Everything is data in trim_model.py. Change a gap by editing a tier value, move a grade by
moving its name, and add back an excluded grade (quarter sawn, FAS 10in, the white or brown
maple sorts) by putting its name in a tier and un-commenting one line in that species' parser.
The values are relative placeholders pending final tuning.
