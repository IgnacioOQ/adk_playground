#!/usr/bin/env python3
"""
RPS Memory MCP Server
---------------------
Tracks Rock-Paper-Scissors game history per session.
Runs as a stdio MCP subprocess — state is persisted to JSON files in ./data/
so it survives across multiple tool calls within the same FastAPI process.

Tools exposed:
  save_agent_choice(session_id, choice)  — lock in agent's choice before player picks
  record_round(session_id, player_choice) — evaluate round, save result, return outcome
  get_history(session_id)                — list all past rounds
  get_stats(session_id)                  — win/loss/draw counts
"""

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Storage — in-memory dict per session (resets when the server process exits)
# ---------------------------------------------------------------------------
_STORE: dict[str, dict] = {}

VALID_CHOICES = {"rock", "paper", "scissors"}
BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}


def _load(session_id: str) -> dict:
    if session_id not in _STORE:
        _STORE[session_id] = {"rounds": [], "pending_choice": None}
    return _STORE[session_id]


def _save(session_id: str, data: dict) -> None:
    _STORE[session_id] = data


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("rps-memory")


@mcp.tool()
def save_agent_choice(session_id: str, choice: str) -> str:
    """
    Lock in the agent's RPS choice BEFORE the player picks.
    choice must be one of: rock, paper, scissors.
    Call this immediately when starting a new round.
    """
    choice = choice.lower().strip()
    if choice not in VALID_CHOICES:
        return f"Invalid choice '{choice}'. Must be rock, paper, or scissors."
    data = _load(session_id)
    data["pending_choice"] = choice
    _save(session_id, data)
    return f"Agent choice '{choice}' saved and sealed."


@mcp.tool()
def record_round(session_id: str, player_choice: str) -> dict:
    """
    Record the player's choice, evaluate the round, and persist the result.
    Returns: { round, player_choice, agent_choice, result }
    result is one of: player_wins, agent_wins, draw.
    Call this when the frontend sends selected_rps_<choice>.
    """
    player = player_choice.lower().strip()
    if player not in VALID_CHOICES:
        return {"error": f"Invalid player choice '{player}'."}

    data = _load(session_id)
    agent = data.get("pending_choice")
    if not agent:
        return {"error": "No agent choice found for this session. Call save_agent_choice first."}

    if player == agent:
        result = "draw"
    elif BEATS.get(player) == agent:
        result = "player_wins"
    else:
        result = "agent_wins"

    round_entry = {
        "round": len(data["rounds"]) + 1,
        "player_choice": player,
        "agent_choice": agent,
        "result": result,
    }
    data["rounds"].append(round_entry)
    data["pending_choice"] = None
    _save(session_id, data)
    return round_entry


@mcp.tool()
def get_history(session_id: str) -> list:
    """Return all past rounds for this session as a list of round objects."""
    return _load(session_id)["rounds"]


@mcp.tool()
def get_stats(session_id: str) -> dict:
    """Return win/loss/draw counts for this session."""
    rounds = _load(session_id)["rounds"]
    stats = {"player_wins": 0, "agent_wins": 0, "draws": 0, "total": len(rounds)}
    for r in rounds:
        stats[r["result"]] = stats.get(r["result"], 0) + 1
    return stats


if __name__ == "__main__":
    mcp.run()
