"""Austin Bats Analytics Department - AI Draft Assistant

Claude-powered draft advice for fantasy baseball auction drafts.
Integrates with the Dedeaux Field 4.0 league configuration.
"""

import os
import json
from typing import Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Model configuration
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 500

# System prompt establishing the AI persona
SYSTEM_PROMPT = """You are the Austin Bats Analytics Department - an elite fantasy baseball analysis team
supporting the Dedeaux Field 4.0 auction draft.

Your communication style:
- Concise and data-driven. No fluff.
- Lead with the recommendation, then support with numbers.
- Think in terms of value over replacement player and positional scarcity.
- Focus on winning. Every dollar matters.

You understand auction dynamics:
- Budget management is survival. Running out of money loses drafts.
- Positional scarcity creates value. 3B and OF are scarce; DH and C run deep.
- Opponent tendencies create opportunities. Let others overpay.
- FAAB reserves matter. In-season moves win championships.

Format responses for quick draft decisions:
- Use bullet points for key stats
- Bold the recommendation
- Include a confidence level (High/Medium/Low)
- Keep explanations under 3 sentences when possible."""


def _check_api_available() -> tuple[bool, Optional[str]]:
    """Check if the Anthropic API is available and configured."""
    if not ANTHROPIC_AVAILABLE:
        return False, "Anthropic SDK not installed. Run: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY environment variable not set."

    return True, None


def _format_context(context: dict) -> str:
    """Format draft context for the AI prompt."""
    sections = []

    if "budget" in context:
        sections.append(f"**Remaining Budget:** ${context['budget']}")

    if "needs" in context and context["needs"]:
        sections.append(f"**Positions Needed:** {', '.join(context['needs'])}")

    if "roster" in context and context["roster"]:
        roster_str = ", ".join(
            f"{p['name']} ({p.get('position', '?')}, ${p.get('salary', '?')})"
            for p in context["roster"]
        )
        sections.append(f"**Current Roster:** {roster_str}")

    if "league_info" in context:
        league = context["league_info"]
        if isinstance(league, dict):
            league_str = ", ".join(f"{k}: {v}" for k, v in league.items())
            sections.append(f"**League Context:** {league_str}")
        else:
            sections.append(f"**League Context:** {league}")

    if "round" in context:
        sections.append(f"**Draft Round/Phase:** {context['round']}")

    if "opponents_remaining_budget" in context:
        sections.append(f"**Opponent Budget Levels:** {context['opponents_remaining_budget']}")

    return "\n".join(sections) if sections else "No additional context provided."


def _format_player(player: dict) -> str:
    """Format player data for the AI prompt."""
    name = player.get("name", "Unknown")
    position = player.get("position", "?")
    team = player.get("team", "?")
    fpts = player.get("fpts_proj", player.get("fpts", "?"))
    value = player.get("model_value", player.get("value", "?"))
    ab_score = player.get("ab_score", "?")

    parts = [f"**{name}** ({position}, {team})"]
    parts.append(f"- Projected FPTS: {fpts}")

    if value != "?":
        parts.append(f"- Model Value: ${value}")
    if ab_score != "?":
        parts.append(f"- AB Score: {ab_score}")

    # Add any additional stats
    for key in ["avg", "hr", "rbi", "sb", "era", "whip", "k", "w", "sv"]:
        if key in player:
            parts.append(f"- {key.upper()}: {player[key]}")

    return "\n".join(parts)


def _call_claude(user_message: str, system: str = SYSTEM_PROMPT) -> str:
    """Make a call to the Claude API."""
    available, error = _check_api_available()
    if not available:
        return f"[Analytics Offline] {error}"

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text
    except anthropic.APIConnectionError:
        return "[Analytics Offline] Unable to connect to Claude API. Check your internet connection."
    except anthropic.RateLimitError:
        return "[Analytics Offline] API rate limit exceeded. Please wait a moment and try again."
    except anthropic.APIStatusError as e:
        return f"[Analytics Offline] API error: {e.message}"
    except Exception as e:
        return f"[Analytics Offline] Unexpected error: {str(e)}"


def get_draft_advice(context: dict, question: str) -> str:
    """Get AI advice for draft decisions.

    Args:
        context: Draft context including:
            - budget: remaining budget
            - needs: list of positions still needed
            - roster: current roster (list of player dicts)
            - league_info: league tendencies or notes
        question: The specific question to ask

    Returns:
        AI-generated advice string
    """
    formatted_context = _format_context(context)

    prompt = f"""Draft Context:
{formatted_context}

Question: {question}

Provide actionable advice for this draft situation."""

    return _call_claude(prompt)


def compare_players(player1: dict, player2: dict, context: dict) -> str:
    """Compare two players for draft decision.

    Args:
        player1: First player data dict
        player2: Second player data dict
        context: Draft context (budget, needs, roster, etc.)

    Returns:
        AI comparison and recommendation
    """
    p1_str = _format_player(player1)
    p2_str = _format_player(player2)
    context_str = _format_context(context)

    prompt = f"""Compare these two players for my draft:

PLAYER 1:
{p1_str}

PLAYER 2:
{p2_str}

MY DRAFT CONTEXT:
{context_str}

Who should I target, and at what price? Consider my roster needs and budget."""

    return _call_claude(prompt)


def get_value_alert(player: dict, current_bid: int) -> str:
    """Get alert if player is going below/above model value.

    Args:
        player: Player data dict (must include model_value or value)
        current_bid: Current bid amount

    Returns:
        Quick alert/recommendation
    """
    name = player.get("name", "Unknown")
    position = player.get("position", "?")
    model_value = player.get("model_value", player.get("value", 0))
    fpts = player.get("fpts_proj", player.get("fpts", "?"))

    if model_value == 0:
        return f"[No model value for {name}]"

    diff = model_value - current_bid
    diff_pct = (diff / model_value) * 100 if model_value > 0 else 0

    prompt = f"""Quick value check needed:

Player: {name} ({position})
Projected FPTS: {fpts}
Model Value: ${model_value}
Current Bid: ${current_bid}
Difference: ${diff:+d} ({diff_pct:+.0f}%)

Is this a buy, pass, or let go? One sentence max."""

    return _call_claude(prompt)


def summarize_draft_state(context: dict) -> str:
    """Generate summary of current draft position and recommendations.

    Args:
        context: Full draft context including:
            - budget: remaining budget
            - needs: positions still needed
            - roster: current roster
            - league_info: any league notes
            - Optional: round, players_left, opponent_budgets

    Returns:
        Strategic summary and next-move recommendations
    """
    formatted_context = _format_context(context)

    # Add roster summary if available
    roster_summary = ""
    if "roster" in context and context["roster"]:
        roster = context["roster"]
        total_spent = sum(p.get("salary", 0) for p in roster)
        roster_summary = f"\n**Players Drafted:** {len(roster)} (${total_spent} spent)"

    prompt = f"""Provide a draft status report and recommendations:

{formatted_context}{roster_summary}

Include:
1. Current position assessment (strong/weak)
2. Priority positions to target
3. Budget strategy for remaining picks
4. Key watch items or risks

Keep it actionable and under 200 words."""

    return _call_claude(prompt)


# Utility function for testing
def test_connection() -> str:
    """Test the Claude API connection."""
    available, error = _check_api_available()
    if not available:
        return f"Connection failed: {error}"

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'Austin Bats Analytics Online' and nothing else."}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Connection failed: {str(e)}"
