# Phase 5 findings — what the data says about the method itself

Run 2026-09-20 across all 130 members of the 114th General Assembly with money linked.

## 1. The in-session contribution ban dominates everything

Contributions to legislators, 2025, by month:

| Month | Total |
|---|---|
| January | $1,385,084 |
| **February** | **$1,700** |
| **March** | **$2,498** |
| April | $18,804 |
| May | $174,356 |
| June | $687,519 |
| July | $519,084 |
| August | $973,381 |
| September | $921,666 |
| October | $1,186,566 |
| November | $1,017,808 |
| December | $1,280,101 |

An ~800-fold drop from January to February, when the General Assembly convenes.
Tennessee bars contributions while the legislature is in session, so fundraising is
pushed into the interim months and resumes the moment session ends.

## 2. Therefore the pre-introduction total is NOT a signal

Every one of Johnny Garrett's 33 primary-sponsored bills in the 114th GA shows money
in the 90 days before introduction. The totals are nearly identical:

```
HB0170   2025-01-15   $45,250   (40 contributions)
HJR0033  2025-01-14   $45,250   (40)
HB6006   2025-01-24   $44,250   (39)
HB0645   2025-02-03   $42,900   (35)
HB0820   2025-02-04   $40,150   (32)
HB0819   2025-02-04   $40,150   (32)
...
```

These are not different sums. They are **the same contributions**, counted against
every bill, because bills are introduced within a few weeks of each other and their
90-day lookback windows overlap almost completely. The lookback window lands squarely
on the October-January fundraising peak for essentially every legislator.

**The pre-introduction total is a property of the legislative calendar, not of any
individual bill.** Ranking bills by it produces an ordering that reflects introduction
date, nothing more.

### Consequences, which are binding

- **Phase 9's review queue must not rank on pre-introduction totals.** Doing so would
  surface whoever introduced bills closest to the fundraising peak, and present a
  calendar artifact as a finding about a named person.
- The **subject-matched** measure (Phase 6) — money from donors in the same industry
  as the bill's subject — is the primary signal. Timing is at most a secondary filter.
- Any published figure using the lookback window must carry the caveat that nearly
  every member shows the same pattern.

## 3. The baseline, and why everything must be relative

114th General Assembly, members with linked contributions:

| Chamber | N | Median raised | Median PAC share | Median top-10 concentration |
|---|---|---|---|---|
| House | 96 | $258,832 | 44.7% | 27.2% |
| Senate | 34 | $569,306 | 46.7% | 24.8% |

Distribution of each member's ratio to their chamber median:

```
0.0-0.5x  ####################  (20)
0.5-1.0x  #############################################  (45)
1.0-1.5x  #######################################  (39)
1.5-2.0x  ###############  (15)
2.0-2.5x  ###  (3)
2.5-3.0x  #####  (5)
3.0-3.5x  #  (1)
3.5-4.0x  #  (1)
over 4x   #  (1)
```

**Johnny Garrett raised $468,861, a ratio of 1.81x his chamber median.** Above median,
but sharing that band with 14 other members. On fundraising volume alone he is not an
outlier — which is exactly why a baseline is necessary before any figure is published.

## 4. Party differences exist in the data and are not produced by the method

| Party | N | Mean ratio | Median ratio |
|---|---|---|---|
| R | 100 | 1.19 | 1.06 |
| D | 30 | 0.98 | 0.73 |

Republicans hold the majority in both chambers, and with it the leadership and
committee chairmanships that attract money. **The method is party-blind**: party is
never an input to any threshold or ranking (governing principle 1). Both extremes of
the distribution contain both parties — highest include Cameron Sexton (R, 6.38x) and
Bob Freeman (D, 3.92x); lowest include G.A. Hardaway (D, 0.03x) and Monty Fritts
(R, 0.18x).

This table should be published on the methodology page rather than omitted. Stating
the observed difference and showing that the method does not cause it is stronger
than leaving a reader to wonder.

## 5. Known gaps

- **`passed_date` exists for only 3,958 of 5,925 passed bills in the 114th GA.** It is
  derived by scanning LegiScan history text for "signed by governor" or "public
  chapter", which misses other routes to passage. The post-passage measure is
  therefore incomplete and currently returns zero for most bills.
- **Donor classification is provisional**, from a name-pattern function. PAC-share
  figures above should be treated as indicative until Phase 6 does real entity
  resolution.
- **Contributions for 2023 are still missing** — TREF returned HTTP 500 on repeated
  attempts. Any 2023 analysis is incomplete until that is resolved.
- **The Garrett workbook has not been supplied**, so the comparison PLAN.md Phase 5
  asks for has not been done. Note that the pipeline already matches capitol.tn.gov
  exactly on bill counts (D62).
