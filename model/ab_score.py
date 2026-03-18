"""AB Score v2 - Composite player valuation model."""
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    POSITIONAL_SCARCITY, TEAM_QUALITY, DEFAULT_WEIGHTS,
    SALARY_CAP, KEEPER_TOTAL, FAAB_RESERVE_TARGET
)


class ABScoreCalculator:
    """Calculate AB Score for players based on configurable weights."""

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def _normalize_weights(self):
        """Ensure weights sum to 1.0."""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def update_weights(self, new_weights: dict):
        """Update weights and normalize."""
        self.weights.update(new_weights)
        self._normalize_weights()

    def calculate_scarcity_score(self, positions: list[str]) -> float:
        """Calculate positional scarcity score (0-100).
        Uses the highest-scarcity position the player is eligible for.
        """
        if not positions:
            return 50  # Default

        scores = []
        for pos in positions:
            if pos in POSITIONAL_SCARCITY:
                scores.append(POSITIONAL_SCARCITY[pos]['score'])

        return max(scores) if scores else 50

    def calculate_slot_score(self, lineup_slot: int, team: str, is_pitcher: bool = False) -> float:
        """Calculate lineup/rotation slot score (0-100).

        Args:
            lineup_slot: 1-9 for hitters (batting order), 1-5 for pitchers (rotation spot)
            team: MLB team abbreviation
            is_pitcher: Whether player is a pitcher
        """
        team_quality = TEAM_QUALITY.get(team, 50) / 100

        if is_pitcher:
            # SP1 = 100, SP2 = 85, SP3 = 70, SP4-5 = 40, closer = 40, other = 25
            if lineup_slot == 1:
                base = 100
            elif lineup_slot == 2:
                base = 85
            elif lineup_slot == 3:
                base = 70
            elif lineup_slot <= 5:
                base = 40
            else:
                base = 25
        else:
            # Batting 1-2 = 100, 3-4 = 80, 5-6 = 50, 7+ = 25
            if lineup_slot <= 2:
                base = 100
            elif lineup_slot <= 4:
                base = 80
            elif lineup_slot <= 6:
                base = 50
            else:
                base = 25

        return base * team_quality

    def calculate_fpts_score(self, fpts: float) -> float:
        """Normalize FPTS to 0-100 scale.
        600 FPTS = 100, 400 FPTS = 50, 200 FPTS = 0
        """
        if fpts is None:
            return 0
        return max(0, min(100, (fpts - 200) / 4))

    def calculate_durability_score(
        self,
        games_2025: Optional[int],
        games_2024: Optional[int],
        is_pitcher: bool = False,
        is_rookie: bool = False
    ) -> float:
        """Calculate durability score based on 2-year track record.

        For hitters: based on games played (GP)
        For pitchers: based on games started (GS)
        """
        if is_rookie:
            return 35  # Unknown risk

        g1 = games_2025 or 0
        g2 = games_2024 or 0

        if is_pitcher:
            # Based on games started
            if g1 >= 28 and g2 >= 28:
                return 100  # Iron
            elif g1 >= 25 or g2 >= 25:
                return 75
            elif g1 >= 18 or g2 >= 18:
                return 50
            elif g1 < 10 and g2 < 10:
                return 10  # High risk
            else:
                return 35
        else:
            # Based on games played
            if g1 >= 140 and g2 >= 140:
                return 100  # Iron
            elif (g1 >= 130 or g2 >= 130):
                return 75
            elif g1 >= 100 and g2 >= 100:
                return 50
            elif g1 < 80 and g2 < 80:
                return 10  # High risk
            else:
                return 35

    def calculate_team_quality_score(self, team: str) -> float:
        """Get team quality score (0-100)."""
        return TEAM_QUALITY.get(team, 50)

    def calculate_multi_pos_score(self, positions: list[str]) -> float:
        """Calculate multi-position eligibility score (0-100)."""
        # Remove DH from count (everyone is DH eligible)
        real_positions = [p for p in positions if p != 'DH']
        num_pos = len(real_positions)

        if num_pos >= 4:
            return 100
        elif num_pos == 3:
            return 80
        elif num_pos == 2:
            # Check for SP/RP dual
            if 'SP' in positions and 'RP' in positions:
                return 70
            return 60
        else:
            return 30

    def calculate_value_gap_score(
        self,
        fpts_2025: Optional[float],
        fpts_proj: Optional[float],
        draft_price_2025: Optional[int],
        was_undrafted: bool = False
    ) -> float:
        """Calculate value gap score (market misprice detection).

        - Bad 2025 + good 2026 projection = bounceback (90)
        - Undrafted + low 2025 = hidden value (85)
        - Good 2025 + was cheap = price correcting up (30)
        - Undrafted + 2025 breakout = price correcting (40)
        - Default = 50
        """
        if fpts_2025 is None or fpts_proj is None:
            return 50  # Default

        delta = fpts_proj - fpts_2025

        # Bounceback: underperformed significantly but projected to recover
        if delta > 100 and fpts_2025 < 350:
            return 90

        # Hidden value: wasn't drafted, didn't produce, but has projection
        if was_undrafted and fpts_2025 < 200 and fpts_proj > 300:
            return 85

        # Breakout who's now on radar: undrafted, had good 2025
        if was_undrafted and fpts_2025 > 350:
            return 40  # Price will correct up

        # Was cheap, produced well - price will rise
        if draft_price_2025 and draft_price_2025 <= 5 and fpts_2025 > 400:
            return 30

        return 50  # Default

    def calculate_health_score(
        self,
        is_injured: bool = False,
        days_on_il: int = 0,
        had_surgery: bool = False
    ) -> float:
        """Calculate health status score (0-100).

        100 = Fully healthy
        75 = Minor concern
        50 = Moderate risk
        25 = Major concern (surgery, long IL stint)
        """
        if had_surgery:
            return 25
        if is_injured and days_on_il > 30:
            return 25
        if is_injured and days_on_il > 14:
            return 50
        if is_injured or days_on_il > 0:
            return 75
        return 100

    def calculate_contract_score(
        self,
        is_contract_year: bool = False,
        signed_extension: bool = False
    ) -> float:
        """Calculate contract year motivation score (0-100).

        Contract year players historically slightly outperform.
        Extension signers have stability.
        """
        if is_contract_year:
            return 75  # Motivation boost
        if signed_extension:
            return 60  # Stability
        return 50  # Default

    def calculate_ab_score(
        self,
        positions: list[str],
        fpts_proj: float,
        team: str,
        lineup_slot: int = 5,  # Default to middle of lineup
        games_2025: Optional[int] = None,
        games_2024: Optional[int] = None,
        fpts_2025: Optional[float] = None,
        draft_price_2025: Optional[int] = None,
        is_pitcher: bool = False,
        is_rookie: bool = False,
        was_undrafted: bool = False,
        is_injured: bool = False,
        days_on_il: int = 0,
        had_surgery: bool = False,
        is_contract_year: bool = False,
        signed_extension: bool = False,
    ) -> dict:
        """Calculate full AB Score with component breakdown."""

        components = {
            'scarcity': self.calculate_scarcity_score(positions),
            'slot': self.calculate_slot_score(lineup_slot, team, is_pitcher),
            'fpts': self.calculate_fpts_score(fpts_proj),
            'durability': self.calculate_durability_score(
                games_2025, games_2024, is_pitcher, is_rookie
            ),
            'team_quality': self.calculate_team_quality_score(team),
            'multi_pos': self.calculate_multi_pos_score(positions),
            'value_gap': self.calculate_value_gap_score(
                fpts_2025, fpts_proj, draft_price_2025, was_undrafted
            ),
            'health': self.calculate_health_score(is_injured, days_on_il, had_surgery),
            'contract': self.calculate_contract_score(is_contract_year, signed_extension),
        }

        # Calculate weighted score
        ab_score = sum(
            components[k] * self.weights.get(k, 0)
            for k in components
        )

        return {
            'ab_score': round(ab_score, 1),
            'components': components,
            'weights': self.weights.copy()
        }


def calculate_auction_value(ab_score: float, position: str, league_budget: int = None) -> int:
    """Convert AB Score to auction dollar value.

    Uses position-based multipliers to account for different market dynamics.
    """
    if league_budget is None:
        league_budget = SALARY_CAP - KEEPER_TOTAL - FAAB_RESERVE_TARGET

    # Position multipliers (based on typical market pricing)
    position_multipliers = {
        'C': 0.6,    # Catchers cheaper
        '1B': 0.9,   # 1B slightly cheaper
        '2B': 1.0,   # Average
        '3B': 1.1,   # Premium for scarcity
        'SS': 1.0,   # Average
        'OF': 1.0,   # Average
        'DH': 0.7,   # DH cheap
        'SP': 1.0,   # Average
        'RP': 0.8,   # RP cheaper
    }

    multiplier = position_multipliers.get(position, 1.0)

    # Scale: AB Score 80+ = $30+, 60-80 = $15-30, 40-60 = $5-15, <40 = $1-5
    if ab_score >= 80:
        base_value = 30 + (ab_score - 80) * 1.5
    elif ab_score >= 60:
        base_value = 15 + (ab_score - 60) * 0.75
    elif ab_score >= 40:
        base_value = 5 + (ab_score - 40) * 0.5
    else:
        base_value = max(1, ab_score / 8)

    return max(1, round(base_value * multiplier))


def calculate_bid_range(auction_value: int) -> tuple[int, int, int]:
    """Calculate floor, target, ceiling for bidding.

    Floor: Don't nominate below this
    Target: Happy to pay
    Ceiling: Max bid before passing
    """
    floor = max(1, int(auction_value * 0.7))
    target = auction_value
    ceiling = int(auction_value * 1.3)

    return floor, target, ceiling


if __name__ == "__main__":
    # Test the calculator
    calc = ABScoreCalculator()

    # Test with a top player
    result = calc.calculate_ab_score(
        positions=['OF'],
        fpts_proj=550,
        team='NYM',
        lineup_slot=2,
        games_2025=150,
        games_2024=145,
        fpts_2025=540,
        is_pitcher=False,
    )

    print("Juan Soto test:")
    print(f"  AB Score: {result['ab_score']}")
    print(f"  Components: {result['components']}")

    auction_val = calculate_auction_value(result['ab_score'], 'OF')
    floor, target, ceiling = calculate_bid_range(auction_val)
    print(f"  Auction Value: ${target} (${floor}-${ceiling})")
