# Austin Bats — Composite Draft Value Formula (AB Score)

## The Formula

**AB Score = (Scarcity × 0.25) + (Slot × 0.20) + (FPTS × 0.18) + (Durability × 0.14) + (Team × 0.10) + (Multi × 0.08) + (Gap × 0.05)**

Each component is scored 0–100, producing a composite score of 0–100.

---

## Component Definitions

### 1. Positional Scarcity (25%)
Gap between #1 and replacement level at each position. Measures how much value you lose by waiting.

| Position | Scarcity Score | Gap (FPTS) | Replacement FPTS |
|----------|---------------|------------|-----------------|
| 3B | 100 | 248 | 309 |
| OF | 95 | 234 | 334 |
| SP | 94 | 233 | 354 |
| 2B | 83 | 206 | 270 |
| SS | 60 | 148 | 383 |
| 1B | 51 | 127 | 355 |
| DH | 40 | 98 | 476 |
| C | 39 | 96 | 248 |
| RP | 35 | 87 | 290 |

Player gets the score of their highest-scarcity eligible position.

### 2. Lineup / Rotation Slot (20%)
Where the player bats or pitches, weighted by team quality.

**Hitters:**
- Bats 1st–2nd in lineup: base score = 100
- Bats 3rd–4th: base score = 80
- Bats 5th–6th: base score = 50
- Bats 7th+: base score = 25
- Not in projected top 4: base score = 20

**Pitchers:**
- SP1 (ace): base score = 100
- SP2: base score = 85
- SP3: base score = 70
- SP4–5: base score = 40
- Closer/RP: base score = 40
- Not in top 3: base score = 25

**Final slot score = base score × (team quality score / 100)**
Example: Batting 2nd on the Dodgers (team quality 100) = 100. Batting 2nd on the Rockies (team quality 25) = 25.

### 3. Projected FPTS (18%)
Normalized: `score = min(100, max(0, (FPTS - 200) / 4))`
- 600 FPTS = 100
- 400 FPTS = 50
- 200 FPTS = 0

### 4. Durability (14%)
Based on games played in 2024 AND 2025.

**Hitters:**
| Condition | Score |
|-----------|-------|
| 140+ GP both years | 100 (IRON) |
| 130+ GP one year, other decent | 75 |
| 100+ GP both years | 50 |
| <80 GP one year, other OK | 35 |
| <80 GP BOTH years | 10 (HIGH RISK) |
| Rookie / no track record | 35 |

**Pitchers:**
| Condition | Score |
|-----------|-------|
| 28+ GS both years | 100 |
| 25+ GS one year | 75 |
| 18+ GS | 50 |
| <10 GS both years | 10 |
| Rookie | 35 |

### 5. Team Quality (10%)
Scale 0–100 based on projected 2026 competitiveness.

| Tier | Teams | Score Range |
|------|-------|------------|
| Contender | LAD, NYM, BAL, PHI, BOS, HOU, SEA, ATL, KC, SF, DET, CLE, MIL, ARI, SD, NYY | 73–100 |
| Mid-tier | TOR, CIN, MIN, TEX, CHC, PIT, STL, LAA, TB | 55–68 |
| Rebuilder | WAS, MIA, ATH, CHW, COL | 25–45 |

### 6. Multi-Position Eligibility (8%)
| Positions (excluding DH) | Score |
|--------------------------|-------|
| 4+ positions | 100 |
| 3 positions | 80 |
| 2 positions | 60 |
| SP/RP dual | 70 |
| 1 position | 30 |

### 7. Value Gap (5%)
Estimates whether the player will be underpriced at auction based on 2025 performance vs 2026 projection.

| Condition | Score |
|-----------|-------|
| Produced well in 2025 AND was cheap → price will correct up | 30 |
| Bad 2025 but good 2026 projection (bounceback) | 90 |
| Undrafted + low 2025 production (hidden) | 85 |
| Undrafted but broke out in 2025 → price will correct | 40 |
| Default / average | 50 |

---

## League Context: Dedeaux Field 4.0

### League Settings
- **Platform:** CBS Sports
- **Format:** 10-team, H2H Total Points (FPTS wins the week)
- **Auction Budget:** $320 per team
- **Unspent dollars become FAAB** (waiver budget for in-season pickups)
- **Roster:** 15 starters (9 hitters / 6 pitchers), 10 reserves, 2 prospects, 2 DL
- **Pitching config:** 5 SP + 1 RP (7 start cap) OR 4 SP + 2 RP (6 start cap)
- **Keepers:** Up to 3 players, combined salary ≤ $30, kept for 1 year at same salary

### Your Keepers (Austin Bats)
| Player | Position | Salary | Projected FPTS |
|--------|----------|--------|---------------|
| Nico Hoerner | 2B (CHC) | $11 | ~340 |
| CJ Abrams | SS (WAS) | $5 | ~375 |
| Joe Misirowski | SP (MIL) | $5 | ~330 |
| **TOTAL** | | **$21** | |

**Available budget: $299** ($320 - $21)
**FAAB target: $35-50 unspent**
**Spending target: $250-265 at auction**

### Positions Locked vs Needed
- ✅ 2B — Hoerner
- ✅ SS — Abrams
- ✅ SP (1 slot) — Misirowski
- ❌ C, 1B, 3B, 3×OF, DH — NEED
- ❌ 4-5 more SP, 1-2 RP — NEED

---

## Opponent Scouting (2025 Auction Data)

| Team | Total Spent | Style | Key Tendency |
|------|------------|-------|-------------|
| Austin Bats (YOU) | $261 | Stars & scrubs, punt pitching | 89% on hitters, big FAAB reserve |
| Bushwood CC | $274 | Balanced | Spreads $20+ across 6 players |
| Cardinal and Gold | $269 | Pitching whale | 50% budget on pitching, will drive up SP |
| Ireland | $275 | Upside chaser | Pays premium for young SS/OF |
| MeShe | $275 | Elite bat + arm | Anchors with 1 stud hitter + 1 stud SP |
| Moneyball Dos | $241 | Value hunter | Smartest drafter, finds $1 steals |
| Sarre | $212 | Pitching heavy, FAAB warrior | Buys 3-4 SP aggressively, huge FAAB |
| Sofa Kings | $274 | Star-chaser | Spends $50 on elite SS |
| Swing and a Miss 2020 | $273 | Stars & scrubs, name chaser | $50 on Elly, $41 Tatis, 12 players at $1 |
| The Mike Uhlenkamp Experience | $270 | OF chaser | Chases elite OF ceiling regardless of injury |

### League-Wide Trends
- Top 10 salaries average $49
- 26% of all picks are $1
- SP spending varies wildly (11% to 50% of budget)
- League total spend: ~$2,624 of $3,200 possible (18% kept as FAAB on average)

---

## Nomination Strategy

### Early (drain other budgets):
1. Elly De La Cruz → Swing and a Miss will push to $50+
2. Ronald Acuña Jr. → Uhlenkamp chases injured OF
3. Tarik Skubal → Cardinal and Gold will fight MeShe/Sarre
4. Luis Robert Jr. → Name value exceeds projection
5. Yordan Alvarez → Uhlenkamp may chase redemption ($44 for 110 FPTS last year)

### Mid-auction:
- Nominate SP you don't want (Glasnow, McClanahan, Snell)
- Nominate catchers (Cal Raleigh, William Contreras)

### Late (your targets, budgets should be thinner):
- Hitters: Springer, Burleson, Suzuki, Aranda
- SP: Rogers, Sheehan, Gore, Horton
- IL stashes: Wheeler, Cole, Rodón

---

## Budget Allocation Plan

### Hitting ($160-175):
| Role | Budget | Targets |
|------|--------|---------|
| Elite Hitter #1 (OF) | $45-55 | Soto, Ramirez, Tucker |
| Mid Hitter #2 (3B/1B) | $20-30 | Caminero, Machado, Devers |
| Mid Hitter #3 (OF) | $12-18 | Springer, Rooker, Chourio |
| Value OF #4 | $5-10 | Burleson, Suzuki, Frelick, Duran |
| Catcher | $3-8 | Goodman, Kirk, Ben Rice |
| DH/UTIL | $3-8 | Aranda, Yandy Diaz, Ballesteros |
| Bench hitters (x3-4) | $1 each | |

### Pitching ($80-100):
| Role | Budget | Targets |
|------|--------|---------|
| Elite SP #1 | $25-35 | Skenes, Woo, Crochet, Boyd |
| Mid SP #2 | $12-20 | Rogers, Eovaldi, Ragans |
| Mid SP #3 | $8-15 | Gore, Sheehan, Horton, Pepiot |
| Value SP #4 | $3-8 | Taillon, Flaherty, Bassitt |
| Closer/RP | $3-10 | Diaz, Palencia ($1), Cade Smith |
| IL stashes | $5-12 total | Wheeler ($5-8), Cole ($1-3), Rodón ($3-5) |
| Bench SP (x2-3) | $1 each | |

### FAAB Reserve: $40-50

---

## Key Injury Intel

| Player | Issue | Timeline | Draft Impact |
|--------|-------|----------|-------------|
| Zack Wheeler (PHI SP) | Shoulder surgery | Late April return | IL stash at $5-8 |
| Gerrit Cole (NYY SP) | Tommy John | May/June return | IL stash at $1-3 |
| Carlos Rodón (NYY SP) | Elbow surgery | April/May return | IL stash at $3-5 |
| Corbin Carroll (ARI OF) | Hamate fracture | May miss Opening Day | Possible discount |
| Jackson Holliday (BAL 2B) | Broken hamate | Starts on IL | $1 stash |
| Blake Snell (LAD SP) | Shoulder issues | Unclear timeline | Risky at cost |
| Josh Hader (HOU RP) | Biceps inflammation | Unclear | Avoid at closer prices |
| Anthony Santander (TOR) | Shoulder surgery | Most of season | Do not draft |
| Pablo Lopez (MIN SP) | Tommy John | Full season | Do not draft |

---

## Data Files

The spreadsheet `dedeaux_final_draft_2026.xlsx` contains:
- **DRAFT BOARD tab:** 200 players with AB Score, projected FPTS, 2025 FPTS, YoY delta, GP 2024, GP 2025, health flag, dollar value, 2025 auction price, 2025 owner, 2024 auction price, bid range, intel flags, target/avoid tags, and full CBS positional eligibility
- **League Intel tab:** Full opponent scouting reports, nomination strategy, budget plan, keeper value targets, prospect draft notes
