---
date: 2026-03-18
topic: draft-assistant-overhaul
timeline: 1 WEEK TO DRAFT DAY
---

# BATCAVE - Draft Assistant Overhaul

## What We're Building

A complete overhaul of **BATCAVE** (Austin Bats fantasy baseball draft assistant) to become a **live auction companion** that:
1. Provides instant player intelligence via slide-out panels
2. Adjusts all values in real-time as picks happen (inflation + scarcity)
3. Delivers AI-powered bidding advice that synthesizes all data points

**Primary Use:** Second monitor during live ESPN auction draft

## Why This Approach

The current app has:
- Rich data in the database (5 years draft history, projections, historical FPTS)
- Working AI module (Claude Sonnet 4) that's not wired up
- 4 pages that feel disconnected and half-baked
- Inconsistent styling making it hard to scan quickly

The user's pain points during auction:
- **Speed:** Needs instant context without digging
- **Tracking:** Loses sight of roster holes and budget
- **Pivoting:** When targets go too high, needs immediate alternatives

## Key Decisions

### 1. Player Details: Slide-out Panel
- Click any player row → panel slides in from right
- Keeps player list visible for context
- Contains: stats, value analysis, AI synthesis, historical data

### 2. AI Personality: Balanced Analyst
- Synthesizes data + provides mild recommendations
- Example: "Slightly overpriced at $47, but fills your 3B hole and you have budget"
- Not aggressive ("BUY NOW!") but not passive ("here's some numbers")

### 3. Real-time Updates: Full Intelligence
- **Inflation/deflation:** Remaining $ pool changes → all values recalculate
- **Scarcity:** Position thins out → remaining players at that position worth more
- **Competitor tracking:** Deferred to after draft (nice-to-have)

### 4. Target System: Tiered (Deferred)
- MVP: Simple queue with max bids (existing)
- Post-draft: Add "must have" / "nice to have" / "backup" tiers

### 5. UI: Clean and Scannable
- Not Bloomberg terminal density
- Not rough/functional-only
- Middle ground: clean, professional, fast to read under pressure

## Scope: Must-Have for Draft Day (1 week)

| Feature | Priority | Description |
|---------|----------|-------------|
| Fix broken pages | P0 | Budget Strategy showing code, inconsistent fonts |
| Unified styling | P0 | Single color palette, consistent fonts across all pages |
| Player detail panel | P0 | Click → slide-out with stats + AI take |
| Real-time value engine | P0 | Record pick → inflation + scarcity recalculates |
| AI bidding advice | P0 | "Should I bid $X?" → contextual answer |
| Streamlined draft workflow | P0 | One-click record with pre-confirmation stats |

## Scope: Deferred (After Draft)

| Feature | Priority | Description |
|---------|----------|-------------|
| Opponent tendency tracking | P2 | "Cardinal overpays SP" insights |
| Tiered target system | P2 | Must have / nice to have / backup buckets |
| Historical trend charts | P3 | Visualizations of 3-year trajectories |
| Mobile responsiveness | P3 | Desktop-only is fine for draft day |

## Open Questions

1. **API key:** Is Claude API key configured? Need to test ai_assistant.py
2. **Draft platform:** ESPN? Yahoo? Need to know for manual pick entry UX
3. **Keeper handling:** Are keepers already recorded? How do they affect budget?

## Technical Context

**Existing assets to leverage:**
- `model/pb_score.py` - Value calculation engine
- `model/league_calibration.py` - Historical pricing analysis
- `app/ai_assistant.py` - Claude integration (not wired up)
- `data/database.py` - Rich schema with 13 tables
- `02_league/draft_history/` - 5 years of draft CSVs

**Broken things to fix:**
- `02_Budget_Strategy.py` - Showing raw code
- Theme inconsistency - 3 different color palettes
- Missing fonts - IBM Plex Sans not imported
- No `.streamlit/config.toml`

## Branding

- **App Name:** BATCAVE
- **Sidebar Title:** "BATCAVE" at top of left nav
- **Theme:** Clean, scannable, data-forward (not Bloomberg density)

## Success Criteria

Draft day, BATCAVE:
- [ ] Shows me any player's full context in <2 seconds
- [ ] Gives me AI-powered "should I bid?" advice instantly
- [ ] Recalculates all values as picks happen
- [ ] Tracks my roster/budget/needs without manual updating
- [ ] Doesn't have visual bugs or broken pages

## Next Steps

→ Implementation plan with sequential tasks + upfront permissions
