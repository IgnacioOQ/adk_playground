"""
MCP-RL Protocol Optimizer
=========================

Core Idea:
    An LLM acts as a fixed policy π for an MDP. We do NOT fine-tune the LLM.
    Instead, we optimize the *protocol layer* — the structured context (system
    prompt, state representation, tool definitions) that the LLM receives via
    MCP. The MDP reward signal drives this optimization.

    Concretely, the LLM sees:
        context = protocol.render(state, history, tool_definitions)
    and returns an action. The protocol has learnable parameters θ that control
    HOW state is rendered, WHICH information is included, and what INSTRUCTIONS
    shape the LLM's reasoning. We optimize θ to maximize expected cumulative
    reward in the MDP.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    MDP Environment                      │
    │   state ──► Protocol(θ) ──► LLM (frozen) ──► action    │
    │     ▲                                           │       │
    │     └───────────── step(action) ◄───────────────┘       │
    │                        │                                │
    │                      reward ──► update θ                │
    └─────────────────────────────────────────────────────────┘

    The Protocol(θ) is the learnable component. It controls:
    1. State representation templates (what the LLM "sees")
    2. Instruction fragments (how the LLM is told to reason)
    3. Tool schemas (which MCP tools are exposed and how)
    4. History windowing (how much past experience is included)
    5. Reward framing (how rewards are communicated back)

    θ is optimized via policy-gradient-style updates, where the "policy"
    is the composition: Protocol(θ) → LLM → action.

Analogy to your RecSys work:
    - LinUCB learns θ_a (per-arm parameters) from context vectors
    - Here, we learn protocol parameters from MDP trajectories
    - The LLM replaces the linear model but is treated as a black box
    - The "context" is not a TF-IDF vector but a structured markdown prompt

Usage:
    See the __main__ block for a complete GridWorld example.

Author: Ignacio (MCMP Architecture)
"""

import random
import math
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional
from abc import ABC, abstractmethod


# =============================================================================
# SECTION 1: MDP Environment Interface
# =============================================================================
# Standard Gym-like interface. Any MDP that implements this can be plugged in.

class MDPEnvironment(ABC):
    """
    Abstract base class for an MDP environment.

    Follows the standard RL interface: reset() -> state, step(action) -> (state, reward, done, info).
    Concrete subclasses define the state space, action space, and transition dynamics.
    """

    @abstractmethod
    def reset(self) -> dict:
        """Reset the environment and return the initial state as a dict."""
        ...

    @abstractmethod
    def step(self, action: str) -> tuple[dict, float, bool, dict]:
        """
        Take an action in the environment.

        Args:
            action: A string action name (MCP tools use string identifiers).

        Returns:
            state: The new state as a dict.
            reward: The scalar reward signal.
            done: Whether the episode has terminated.
            info: Additional metadata (e.g., for logging).
        """
        ...

    @abstractmethod
    def get_available_actions(self) -> list[str]:
        """Return the list of valid action names in the current state."""
        ...


class GridWorldMDP(MDPEnvironment):
    """
    A simple GridWorld MDP for demonstration.

    The agent starts at (0,0) and must reach the goal at (grid_size-1, grid_size-1).
    There is an optional trap at a fixed position that gives negative reward.
    This is intentionally simple so the focus stays on the protocol optimization.

    State: {"x": int, "y": int, "goal_x": int, "goal_y": int, "steps": int}
    Actions: ["up", "down", "left", "right"]
    Rewards:
        +10 for reaching the goal
        -5  for stepping on a trap
        -0.1 per step (encourages efficiency)
    """

    def __init__(self, grid_size: int = 5, max_steps: int = 50):
        self.grid_size = grid_size
        self.max_steps = max_steps
        # Goal is always bottom-right corner
        self.goal = (grid_size - 1, grid_size - 1)
        # Trap is placed roughly in the middle of the grid
        self.trap = (grid_size // 2, grid_size // 2)
        # Agent position and step counter (set properly in reset())
        self.x, self.y, self.steps = 0, 0, 0

    def reset(self) -> dict:
        """Place the agent at (0,0) and reset the step counter."""
        self.x, self.y, self.steps = 0, 0, 0
        return self._get_state()

    def step(self, action: str) -> tuple[dict, float, bool, dict]:
        """
        Move the agent in the specified direction.

        Movement is clipped to stay within the grid boundaries.
        """
        # -- Apply the action (with boundary clipping) --
        if action == "up":
            self.y = max(0, self.y - 1)
        elif action == "down":
            self.y = min(self.grid_size - 1, self.y + 1)
        elif action == "left":
            self.x = max(0, self.x - 1)
        elif action == "right":
            self.x = min(self.grid_size - 1, self.x + 1)

        self.steps += 1

        # -- Compute reward and check termination --
        reward = -0.1  # Small per-step penalty to encourage efficiency
        done = False
        info = {"event": "move"}

        if (self.x, self.y) == self.goal:
            reward = 10.0
            done = True
            info["event"] = "goal_reached"
        elif (self.x, self.y) == self.trap:
            reward = -5.0
            info["event"] = "trap_hit"

        if self.steps >= self.max_steps:
            done = True
            info["event"] = "timeout"

        return self._get_state(), reward, done, info

    def get_available_actions(self) -> list[str]:
        """All four directions are always available (boundary clipping handles edges)."""
        return ["up", "down", "left", "right"]

    def _get_state(self) -> dict:
        """Internal helper to package the current state as a dict."""
        return {
            "x": self.x,
            "y": self.y,
            "goal_x": self.goal[0],
            "goal_y": self.goal[1],
            "trap_x": self.trap[0],
            "trap_y": self.trap[1],
            "grid_size": self.grid_size,
            "steps": self.steps,
            "max_steps": self.max_steps,
        }


# =============================================================================
# SECTION 2: Protocol Components (the learnable θ)
# =============================================================================
# These are the "genes" of the protocol — discrete and continuous parameters
# that control what the LLM sees. Each component has a set of variants that
# can be selected and combined.

@dataclass
class ProtocolComponent:
    """
    A single learnable element of the MCP protocol.

    Each component has a name, a set of discrete variants to choose from,
    and a weight that determines its probability of being included.

    Attributes:
        name:            Human-readable identifier (e.g., "state_format").
        variants:        List of possible realizations (e.g., different templates).
        active_variant:  Index into `variants` for the currently selected one.
        inclusion_weight: Float in [0,1] controlling how likely this component
                         is to appear in the rendered protocol. Optimized by RL.
    """
    name: str
    variants: list[str]
    active_variant: int = 0
    inclusion_weight: float = 1.0  # 1.0 = always included, 0.0 = never


@dataclass
class MCPToolSchema:
    """
    Represents an MCP tool definition exposed to the LLM.

    In standard MCP, tools have a name, description, and input schema.
    Here, the *description* is the learnable part — we can evolve how
    tools are described to the LLM to elicit better action selection.

    Attributes:
        tool_name:         The fixed tool identifier (e.g., "take_action").
        description_variants: Different ways to describe this tool to the LLM.
        active_description:  Index of the currently active description variant.
        input_schema:      JSON schema for the tool's input (fixed).
    """
    tool_name: str
    description_variants: list[str]
    active_description: int = 0
    input_schema: dict = field(default_factory=dict)

    def render(self) -> dict:
        """Render this tool as an MCP-compatible tool definition dict."""
        return {
            "name": self.tool_name,
            "description": self.description_variants[self.active_description],
            "inputSchema": self.input_schema,
        }


# =============================================================================
# SECTION 3: The Evolvable Protocol
# =============================================================================
# This is the main learnable object. It holds all protocol components and
# knows how to render itself into a structured context for the LLM.

class EvolvableProtocol:
    """
    The learnable MCP protocol — this is θ in our optimization.

    The protocol assembles a structured context from its components:
        1. System instruction (role, goal, constraints)
        2. State representation (how the MDP state is formatted)
        3. History window (past transitions shown to the LLM)
        4. Tool definitions (MCP tool schemas)
        5. Reward framing (how past rewards are communicated)

    Each of these is parameterized by ProtocolComponents with discrete
    variants and continuous inclusion weights. The RL optimizer searches
    over this space.

    Design note: this mirrors your RECSYS_AGENT.md structure — each
    "Protocol N" is analogous to a component here, and the agent skill
    document itself is analogous to the system_instruction component.
    """

    def __init__(self):
        # -- System instruction variants --
        # These shape the LLM's "persona" and reasoning approach.
        self.system_instruction = ProtocolComponent(
            name="system_instruction",
            variants=[
                # Variant 0: Minimal — just the goal
                "You are an agent navigating a grid. Reach the goal. Avoid traps.",

                # Variant 1: Analytical — encourages explicit reasoning
                (
                    "You are a strategic agent in a grid environment. "
                    "ALWAYS reason step-by-step about your position relative to the goal "
                    "and any hazards before choosing an action. Prefer the shortest safe path."
                ),

                # Variant 2: Reward-focused — emphasizes optimization
                (
                    "You are a reward-maximizing agent. Your objective is to accumulate "
                    "the highest total reward. Each step costs -0.1, traps cost -5, "
                    "and reaching the goal gives +10. Optimize your path."
                ),

                # Variant 3: Cautious — emphasizes trap avoidance
                (
                    "You are a careful navigation agent. Your PRIMARY concern is avoiding "
                    "the trap. Only after ensuring safety, navigate toward the goal. "
                    "A longer safe path is better than a short dangerous one."
                ),
            ],
            active_variant=0,
            inclusion_weight=1.0,  # System instruction is always included
        )

        # -- State representation variants --
        # These control HOW the MDP state dict is rendered into text.
        self.state_format = ProtocolComponent(
            name="state_format",
            variants=[
                # Variant 0: Raw JSON dump
                "json_raw",
                # Variant 1: Structured markdown (matches your MD_CONVENTIONS)
                "markdown_table",
                # Variant 2: Natural language narrative
                "natural_language",
                # Variant 3: Spatial/visual ASCII grid
                "ascii_grid",
            ],
            active_variant=1,  # Start with markdown (your preferred format)
            inclusion_weight=1.0,
        )

        # -- History window component --
        # Controls how many past transitions are shown to the LLM.
        self.history_window = ProtocolComponent(
            name="history_window",
            variants=[
                "0",   # No history (pure Markov — only current state)
                "3",   # Last 3 transitions
                "5",   # Last 5 transitions
                "10",  # Last 10 transitions (richer context, more tokens)
            ],
            active_variant=1,  # Start with 3-step history
            inclusion_weight=0.8,
        )

        # -- Reward framing variants --
        # Controls how reward information is presented to the LLM.
        self.reward_framing = ProtocolComponent(
            name="reward_framing",
            variants=[
                "none",             # Don't show rewards at all
                "cumulative_only",  # Just show total accumulated reward
                "per_step",         # Show reward for each historical step
                "trend",            # Show whether rewards are improving or declining
            ],
            active_variant=2,  # Start with per-step rewards
            inclusion_weight=0.7,
        )

        # -- MCP Tool definitions --
        # The tool schema is fixed, but the DESCRIPTION is learnable.
        self.tools = [
            MCPToolSchema(
                tool_name="take_action",
                description_variants=[
                    # Variant 0: Minimal
                    "Move the agent in a direction.",
                    # Variant 1: Informative
                    (
                        "Move the agent one step in the specified direction. "
                        "The agent cannot move outside the grid boundaries."
                    ),
                    # Variant 2: Strategic
                    (
                        "Choose a movement direction. Consider your distance to "
                        "the goal and proximity to hazards before deciding."
                    ),
                ],
                active_description=1,
                input_schema={
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down", "left", "right"],
                            "description": "Direction to move",
                        }
                    },
                    "required": ["direction"],
                },
            ),
            MCPToolSchema(
                tool_name="get_state",
                description_variants=[
                    "Get the current environment state.",
                    "Retrieve full state including position, goal, and hazard locations.",
                    "Query the environment for a complete situational assessment.",
                ],
                active_description=1,
                input_schema={"type": "object", "properties": {}},
            ),
        ]

        # -- Gather all components for the optimizer --
        self.components: list[ProtocolComponent] = [
            self.system_instruction,
            self.state_format,
            self.history_window,
            self.reward_framing,
        ]

    # -------------------------------------------------------------------------
    # State rendering methods
    # -------------------------------------------------------------------------

    def _render_state_json(self, state: dict) -> str:
        """Render state as raw JSON (compact, machine-readable)."""
        return f"```json\n{json.dumps(state, indent=2)}\n```"

    def _render_state_markdown(self, state: dict) -> str:
        """
        Render state as a markdown table.

        This follows the structured format from RECSYS_AGENT.md — tabular,
        typed, and easy for the LLM to parse.
        """
        lines = [
            "| Property | Value |",
            "|----------|-------|",
            f"| Position | ({state['x']}, {state['y']}) |",
            f"| Goal     | ({state['goal_x']}, {state['goal_y']}) |",
            f"| Trap     | ({state['trap_x']}, {state['trap_y']}) |",
            f"| Grid Size | {state['grid_size']}x{state['grid_size']} |",
            f"| Steps    | {state['steps']}/{state['max_steps']} |",
        ]
        return "\n".join(lines)

    def _render_state_natural(self, state: dict) -> str:
        """Render state as natural language narrative."""
        # Compute distances for richer description
        dx_goal = state["goal_x"] - state["x"]
        dy_goal = state["goal_y"] - state["y"]
        dx_trap = abs(state["trap_x"] - state["x"])
        dy_trap = abs(state["trap_y"] - state["y"])
        return (
            f"You are at position ({state['x']}, {state['y']}) on a "
            f"{state['grid_size']}x{state['grid_size']} grid. "
            f"The goal is {dx_goal} steps right and {dy_goal} steps down. "
            f"There is a trap {dx_trap + dy_trap} steps away (Manhattan distance). "
            f"You have taken {state['steps']} of {state['max_steps']} allowed steps."
        )

    def _render_state_ascii(self, state: dict) -> str:
        """
        Render state as an ASCII grid.

        This gives the LLM a spatial/visual representation:
            A = Agent, G = Goal, X = Trap, . = empty
        """
        grid = []
        for row in range(state["grid_size"]):
            line = []
            for col in range(state["grid_size"]):
                if (col, row) == (state["x"], state["y"]):
                    line.append("A")  # Agent
                elif (col, row) == (state["goal_x"], state["goal_y"]):
                    line.append("G")  # Goal
                elif (col, row) == (state["trap_x"], state["trap_y"]):
                    line.append("X")  # Trap
                else:
                    line.append(".")
            grid.append(" ".join(line))
        return "```\n" + "\n".join(grid) + "\n```\nA=Agent, G=Goal, X=Trap"

    def render_state(self, state: dict) -> str:
        """Dispatch to the active state format variant."""
        fmt = self.state_format.variants[self.state_format.active_variant]
        renderers = {
            "json_raw": self._render_state_json,
            "markdown_table": self._render_state_markdown,
            "natural_language": self._render_state_natural,
            "ascii_grid": self._render_state_ascii,
        }
        return renderers[fmt](state)

    # -------------------------------------------------------------------------
    # History rendering
    # -------------------------------------------------------------------------

    def render_history(self, history: list[dict]) -> str:
        """
        Render the trajectory history according to the active window and reward framing.

        Args:
            history: List of dicts with keys {state, action, reward, next_state}.

        Returns:
            Formatted string showing recent experience.
        """
        # Determine how many past steps to show
        window = int(self.history_window.variants[self.history_window.active_variant])
        if window == 0 or not history:
            return ""

        recent = history[-window:]
        framing = self.reward_framing.variants[self.reward_framing.active_variant]

        lines = ["## Recent History"]

        if framing == "none":
            # Show actions only, no rewards
            for i, h in enumerate(recent):
                lines.append(f"- Step {h['step']}: moved **{h['action']}**")

        elif framing == "cumulative_only":
            # Show actions and a running total
            total = sum(h["reward"] for h in history)
            for i, h in enumerate(recent):
                lines.append(f"- Step {h['step']}: moved **{h['action']}**")
            lines.append(f"\n**Cumulative reward so far:** {total:.1f}")

        elif framing == "per_step":
            # Show each action with its immediate reward
            for h in recent:
                lines.append(
                    f"- Step {h['step']}: moved **{h['action']}** → reward: {h['reward']:.1f}"
                )

        elif framing == "trend":
            # Show actions and whether rewards are improving
            for h in recent:
                lines.append(f"- Step {h['step']}: moved **{h['action']}**")
            if len(recent) >= 2:
                recent_avg = sum(h["reward"] for h in recent[len(recent)//2:]) / max(1, len(recent)//2)
                older_avg = sum(h["reward"] for h in recent[:len(recent)//2]) / max(1, len(recent)//2)
                trend = "improving 📈" if recent_avg > older_avg else "declining 📉"
                lines.append(f"\n**Reward trend:** {trend}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Full context assembly
    # -------------------------------------------------------------------------

    def render_full_context(self, state: dict, history: list[dict]) -> dict:
        """
        Assemble the complete MCP-style context for the LLM.

        This is the main output — it produces a dict with:
            - "system":  The system prompt (instruction + protocol)
            - "user":    The current state + history (the "user message")
            - "tools":   List of MCP tool schemas

        This mirrors how you'd structure an actual Anthropic API call
        with system prompt, user message, and tool definitions.
        """
        # -- System prompt (always included) --
        system = self.system_instruction.variants[
            self.system_instruction.active_variant
        ]

        # -- State representation --
        state_text = self.render_state(state)

        # -- History (conditionally included based on inclusion_weight) --
        history_text = ""
        if random.random() < self.history_window.inclusion_weight:
            history_text = self.render_history(history)

        # -- Compose the user message --
        user_parts = ["## Current State", state_text]
        if history_text:
            user_parts.append(history_text)

        # -- Available actions reminder --
        user_parts.append(
            "\n**Available actions:** up, down, left, right\n"
            "Choose the best action by calling the `take_action` tool."
        )

        # -- Tool schemas --
        tool_schemas = [tool.render() for tool in self.tools]

        return {
            "system": system,
            "user": "\n\n".join(user_parts),
            "tools": tool_schemas,
        }

    # -------------------------------------------------------------------------
    # Genome: encode/decode for the optimizer
    # -------------------------------------------------------------------------

    def get_genome(self) -> dict:
        """
        Extract the current protocol configuration as a flat "genome" dict.

        This is what the RL optimizer manipulates. It captures all the
        discrete choices (variant indices) and continuous parameters
        (inclusion weights) that define this protocol instance.
        """
        genome = {}
        for comp in self.components:
            genome[f"{comp.name}_variant"] = comp.active_variant
            genome[f"{comp.name}_weight"] = comp.inclusion_weight
        for i, tool in enumerate(self.tools):
            genome[f"tool_{tool.tool_name}_desc"] = tool.active_description
        return genome

    def set_genome(self, genome: dict):
        """
        Apply a genome dict to configure this protocol.

        This is the inverse of get_genome() — the optimizer proposes a
        genome, and we apply it before running an episode.
        """
        for comp in self.components:
            variant_key = f"{comp.name}_variant"
            weight_key = f"{comp.name}_weight"
            if variant_key in genome:
                comp.active_variant = genome[variant_key]
            if weight_key in genome:
                comp.inclusion_weight = max(0.0, min(1.0, genome[weight_key]))
        for tool in self.tools:
            desc_key = f"tool_{tool.tool_name}_desc"
            if desc_key in genome:
                tool.active_description = genome[desc_key]

    def get_genome_hash(self) -> str:
        """Return a short hash of the current genome for caching/logging."""
        genome_str = json.dumps(self.get_genome(), sort_keys=True)
        return hashlib.md5(genome_str.encode()).hexdigest()[:8]


# =============================================================================
# SECTION 4: Simulated LLM (for testing without API calls)
# =============================================================================
# In production, this would call the Anthropic API. For demonstration and
# rapid prototyping, we simulate an LLM that responds differently depending
# on the protocol context it receives — which is the whole point.

class SimulatedLLM:
    """
    A simulated LLM that responds to protocol context.

    This is a stand-in for the real Anthropic API. The key property we
    simulate is that the LLM's action quality DEPENDS ON THE PROTOCOL:
        - Better state representations → better actions
        - Richer history → more informed decisions
        - Clearer instructions → more strategic behavior

    This makes the protocol optimization meaningful even in simulation.
    In production, you'd replace this with actual API calls to Claude.

    The simulation uses heuristics to model how an LLM would respond to
    different context qualities, with added stochasticity to simulate the
    nondeterministic nature of LLM sampling.
    """

    def __init__(self, noise_level: float = 0.15):
        """
        Args:
            noise_level: Probability of taking a random action instead of
                        the heuristic-optimal one. Models LLM imperfection.
        """
        self.noise_level = noise_level

    def _compute_context_quality(self, context: dict) -> float:
        """
        Score how "good" the protocol context is for decision-making.

        This models the intuition that some protocol configurations help
        the LLM more than others. Returns a float in [0, 1].

        Higher quality → lower noise → better actions.
        """
        quality = 0.0
        system = context["system"]
        user = context["user"]

        # -- Instruction quality: longer, more specific instructions help --
        if "step-by-step" in system.lower() or "reason" in system.lower():
            quality += 0.2  # Analytical prompts improve LLM reasoning
        if "reward" in system.lower() or "cost" in system.lower():
            quality += 0.1  # Reward awareness helps optimization

        # -- State quality: spatial representations are most informative --
        if "A=Agent" in user:  # ASCII grid
            quality += 0.3
        elif "Position" in user and "|" in user:  # Markdown table
            quality += 0.2
        elif "steps right" in user:  # Natural language with distances
            quality += 0.25
        else:  # Raw JSON
            quality += 0.1

        # -- History quality: more context generally helps --
        if "Recent History" in user:
            quality += 0.15
            if "reward:" in user:  # Per-step rewards shown
                quality += 0.1

        return min(1.0, quality)

    def choose_action(
        self, context: dict, state: dict, available_actions: list[str]
    ) -> str:
        """
        Choose an action given the protocol context and raw state.

        The action quality depends on context quality (simulating how
        better prompts lead to better LLM outputs).

        Args:
            context: The full rendered protocol context dict.
            state: The raw MDP state dict (for the heuristic).
            available_actions: List of valid action strings.

        Returns:
            The chosen action string.
        """
        quality = self._compute_context_quality(context)

        # -- Effective noise: better context → less noise --
        effective_noise = self.noise_level * (1.0 - quality * 0.7)

        # -- With probability effective_noise, take a random action --
        if random.random() < effective_noise:
            return random.choice(available_actions)

        # -- Otherwise, use a quality-dependent heuristic --
        return self._heuristic_action(state, quality)

    def _heuristic_action(self, state: dict, quality: float) -> str:
        """
        Compute a heuristic action, with quality affecting trap avoidance.

        Low quality  → greedy movement toward goal (may hit trap)
        High quality → aware of trap, navigates around it
        """
        x, y = state["x"], state["y"]
        gx, gy = state["goal_x"], state["goal_y"]
        tx, ty = state["trap_x"], state["trap_y"]

        # -- High quality: check if we're about to walk into the trap --
        if quality > 0.4:
            # If moving toward goal would put us on the trap, detour
            if x < gx and (x + 1, y) == (tx, ty):
                return "down" if y < gy else "up"  # Go around
            if y < gy and (x, y + 1) == (tx, ty):
                return "right" if x < gx else "left"  # Go around

        # -- Default: greedy movement toward goal --
        dx = gx - x
        dy = gy - y

        # Prefer the axis with larger distance
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"


# =============================================================================
# SECTION 5: Protocol Optimizers (the RL algorithms)
# =============================================================================
# These optimize the protocol genome θ using MDP reward signals.
# We provide two approaches:
#   1. Evolutionary (genetic algorithm style) — good for discrete choices
#   2. Bandit-based (connects to your LinUCB work) — good for component selection

class ProtocolOptimizer(ABC):
    """Abstract base class for protocol optimizers."""

    @abstractmethod
    def suggest_genome(self) -> dict:
        """Propose a protocol genome to evaluate."""
        ...

    @abstractmethod
    def report_reward(self, genome: dict, total_reward: float):
        """Report the total episode reward for a genome."""
        ...


class EvolutionaryOptimizer(ProtocolOptimizer):
    """
    Evolutionary / genetic algorithm optimizer for protocol genomes.

    Maintains a population of protocol configurations. Each generation:
    1. Evaluate each genome by running episodes in the MDP
    2. Select the top-k performers (elitism)
    3. Create new genomes via mutation of the elite
    4. Repeat

    This is well-suited for the discrete nature of protocol components
    (variant indices) combined with continuous inclusion weights.

    Connection to your work:
        - This is analogous to evolving the "agent skill document" itself
        - Each genome is a different RECSYS_AGENT.md configuration
        - Reward signal tells us which documentation style works best
    """

    def __init__(
        self,
        protocol: EvolvableProtocol,
        population_size: int = 10,
        elite_fraction: float = 0.3,
        mutation_rate: float = 0.3,
    ):
        """
        Args:
            protocol:        The protocol template (defines the search space).
            population_size: Number of genomes to maintain.
            elite_fraction:  Top fraction to keep each generation.
            mutation_rate:   Probability of mutating each gene.
        """
        self.protocol = protocol
        self.population_size = population_size
        self.elite_count = max(1, int(population_size * elite_fraction))
        self.mutation_rate = mutation_rate

        # -- Build the search space from the protocol's components --
        self.search_space = {}
        for comp in protocol.components:
            self.search_space[f"{comp.name}_variant"] = list(range(len(comp.variants)))
            self.search_space[f"{comp.name}_weight"] = "continuous"  # [0, 1]
        for tool in protocol.tools:
            key = f"tool_{tool.tool_name}_desc"
            self.search_space[key] = list(range(len(tool.description_variants)))

        # -- Initialize population with random genomes --
        self.population: list[dict] = [self._random_genome() for _ in range(population_size)]
        # -- Track fitness (reward) for each genome --
        self.fitness: list[float] = [float("-inf")] * population_size
        self._eval_index = 0  # Which genome to evaluate next
        # -- Track the best genome ever seen --
        self.best_genome: Optional[dict] = None
        self.best_fitness: float = float("-inf")

    def _random_genome(self) -> dict:
        """Generate a random genome within the search space."""
        genome = {}
        for key, space in self.search_space.items():
            if space == "continuous":
                genome[key] = random.random()  # Uniform [0, 1]
            else:
                genome[key] = random.choice(space)  # Random variant index
        return genome

    def _mutate(self, genome: dict) -> dict:
        """
        Create a mutated copy of a genome.

        Each gene is independently mutated with probability mutation_rate.
        Discrete genes: randomly re-sampled from their variant space.
        Continuous genes: perturbed by Gaussian noise, clipped to [0, 1].
        """
        mutant = genome.copy()
        for key, space in self.search_space.items():
            if random.random() < self.mutation_rate:
                if space == "continuous":
                    # Gaussian perturbation
                    mutant[key] = max(0.0, min(1.0, mutant[key] + random.gauss(0, 0.2)))
                else:
                    # Random variant re-sample
                    mutant[key] = random.choice(space)
        return mutant

    def suggest_genome(self) -> dict:
        """
        Return the next genome to evaluate.

        Cycles through the population. After all have been evaluated,
        triggers a new generation via selection + mutation.
        """
        if self._eval_index >= self.population_size:
            self._evolve()  # Create next generation
            self._eval_index = 0
        genome = self.population[self._eval_index]
        return genome

    def report_reward(self, genome: dict, total_reward: float):
        """Record the fitness of the most recently suggested genome."""
        self.fitness[self._eval_index] = total_reward
        self._eval_index += 1

        # Track global best
        if total_reward > self.best_fitness:
            self.best_fitness = total_reward
            self.best_genome = genome.copy()

    def _evolve(self):
        """
        Create the next generation via elitism + mutation.

        Steps:
        1. Rank genomes by fitness
        2. Keep the top elite_count genomes unchanged
        3. Fill the rest by mutating randomly chosen elites
        """
        # -- Sort population by fitness (descending) --
        ranked = sorted(
            zip(self.population, self.fitness),
            key=lambda x: x[1],
            reverse=True,
        )

        # -- Elites survive unchanged --
        elites = [genome for genome, _ in ranked[:self.elite_count]]

        # -- Fill remaining slots with mutated elites --
        new_population = list(elites)
        while len(new_population) < self.population_size:
            parent = random.choice(elites)
            child = self._mutate(parent)
            new_population.append(child)

        self.population = new_population
        self.fitness = [float("-inf")] * self.population_size


class ComponentBanditOptimizer(ProtocolOptimizer):
    """
    Bandit-based optimizer that treats each protocol component as an arm.

    This directly connects to your LinUCB work in RECSYS_AGENT.md:
        - Each component variant is an "arm" in a multi-armed bandit
        - The reward signal from MDP episodes updates arm estimates
        - UCB-style exploration balances trying new variants vs. exploiting known good ones

    Key difference from the evolutionary approach:
        - Evolutionary: optimizes the FULL genome jointly
        - Bandit: optimizes each component INDEPENDENTLY (faster, but misses interactions)

    For the inclusion weights, we use a simple exponential moving average.
    """

    def __init__(self, protocol: EvolvableProtocol, exploration: float = 1.5):
        """
        Args:
            protocol:    The protocol template.
            exploration: UCB exploration parameter (like α in LinUCB).
        """
        self.protocol = protocol
        self.exploration = exploration

        # -- Per-component bandit statistics --
        # For each component, track counts and reward sums per variant.
        self.arm_stats: dict[str, dict[str, Any]] = {}
        for comp in protocol.components:
            n_variants = len(comp.variants)
            self.arm_stats[comp.name] = {
                "counts": [0] * n_variants,       # N(variant)
                "total_rewards": [0.0] * n_variants,  # Sum of rewards
                "n_variants": n_variants,
            }
        for tool in protocol.tools:
            n_desc = len(tool.description_variants)
            self.arm_stats[f"tool_{tool.tool_name}"] = {
                "counts": [0] * n_desc,
                "total_rewards": [0.0] * n_desc,
                "n_variants": n_desc,
            }

        # -- For inclusion weights: exponential moving average of reward --
        self.weight_ema: dict[str, float] = {
            comp.name: 0.0 for comp in protocol.components
        }

        self._current_genome: Optional[dict] = None
        self._current_selections: dict[str, int] = {}
        self.total_rounds = 0  # Global counter for UCB denominator

    def _ucb_select(self, stats: dict) -> int:
        """
        Select a variant using Upper Confidence Bound (UCB1).

        UCB1 score = mean_reward + c * sqrt(ln(N) / n_i)

        This balances exploitation (high mean reward) with exploration
        (under-sampled variants), exactly like the alpha parameter
        in your LinUCB implementation.
        """
        n_variants = stats["n_variants"]
        self.total_rounds += 1

        scores = []
        for i in range(n_variants):
            count = stats["counts"][i]
            if count == 0:
                # Never tried → infinite UCB score → explore it
                scores.append(float("inf"))
            else:
                mean_reward = stats["total_rewards"][i] / count
                # UCB exploration bonus
                bonus = self.exploration * math.sqrt(
                    math.log(self.total_rounds) / count
                )
                scores.append(mean_reward + bonus)

        return scores.index(max(scores))

    def suggest_genome(self) -> dict:
        """
        Propose a genome by independently selecting each component's variant via UCB.
        """
        genome = {}
        self._current_selections = {}

        for comp in self.protocol.components:
            stats = self.arm_stats[comp.name]
            variant = self._ucb_select(stats)
            genome[f"{comp.name}_variant"] = variant
            genome[f"{comp.name}_weight"] = comp.inclusion_weight
            self._current_selections[comp.name] = variant

        for tool in self.protocol.tools:
            key = f"tool_{tool.tool_name}"
            stats = self.arm_stats[key]
            desc = self._ucb_select(stats)
            genome[f"tool_{tool.tool_name}_desc"] = desc
            self._current_selections[key] = desc

        self._current_genome = genome
        return genome

    def report_reward(self, genome: dict, total_reward: float):
        """
        Update bandit statistics for each selected component variant.

        Each component that was active in this episode gets credited with
        the full episode reward. This is a simplification — in practice
        you might want credit assignment per component.
        """
        for comp_name, variant in self._current_selections.items():
            stats = self.arm_stats[comp_name]
            stats["counts"][variant] += 1
            stats["total_rewards"][variant] += total_reward

        # -- Update inclusion weight EMAs --
        alpha = 0.1  # EMA smoothing factor
        for comp in self.protocol.components:
            old = self.weight_ema.get(comp.name, 0.0)
            self.weight_ema[comp.name] = (1 - alpha) * old + alpha * total_reward
            # Map EMA to a weight in [0.3, 1.0] via sigmoid-like scaling
            comp.inclusion_weight = 0.3 + 0.7 / (
                1 + math.exp(-self.weight_ema[comp.name])
            )

    def get_best_variants(self) -> dict:
        """Return the highest-mean-reward variant for each component."""
        best = {}
        for comp_name, stats in self.arm_stats.items():
            best_variant = -1
            best_mean = float("-inf")
            for i in range(stats["n_variants"]):
                if stats["counts"][i] > 0:
                    mean = stats["total_rewards"][i] / stats["counts"][i]
                    if mean > best_mean:
                        best_mean = mean
                        best_variant = i
            best[comp_name] = {
                "variant": best_variant,
                "mean_reward": best_mean,
                "times_selected": stats["counts"][best_variant] if best_variant >= 0 else 0,
            }
        return best


# =============================================================================
# SECTION 6: Training Loop
# =============================================================================
# Brings everything together: MDP + Protocol + LLM + Optimizer.

@dataclass
class EpisodeResult:
    """Container for the outcome of a single MDP episode."""
    total_reward: float
    steps: int
    reached_goal: bool
    hit_trap: bool
    trajectory: list[dict]
    genome_hash: str


def run_episode(
    env: MDPEnvironment,
    protocol: EvolvableProtocol,
    llm: SimulatedLLM,
    genome: dict,
) -> EpisodeResult:
    """
    Run a single MDP episode with a given protocol genome.

    This is the core evaluation function:
    1. Configure the protocol with the proposed genome
    2. Reset the environment
    3. At each step: render context → LLM chooses action → environment steps
    4. Accumulate rewards and trajectory data
    5. Return the episode result

    Args:
        env:      The MDP environment.
        protocol: The evolvable protocol (will be configured with genome).
        llm:      The (simulated) LLM acting as the frozen policy.
        genome:   The protocol configuration to evaluate.

    Returns:
        EpisodeResult with total reward, trajectory, and metadata.
    """
    # -- Configure the protocol --
    protocol.set_genome(genome)
    genome_hash = protocol.get_genome_hash()

    # -- Reset environment --
    state = env.reset()
    history: list[dict] = []
    total_reward = 0.0
    reached_goal = False
    hit_trap = False
    step_count = 0

    done = False
    while not done:
        # 1. Protocol renders the context for the LLM
        context = protocol.render_full_context(state, history)

        # 2. LLM chooses an action based on the rendered context
        available = env.get_available_actions()
        action = llm.choose_action(context, state, available)

        # 3. Environment processes the action
        next_state, reward, done, info = env.step(action)
        total_reward += reward
        step_count += 1

        # 4. Record this transition in history
        history.append({
            "step": step_count,
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state,
        })

        # 5. Track events
        if info.get("event") == "goal_reached":
            reached_goal = True
        if info.get("event") == "trap_hit":
            hit_trap = True

        state = next_state

    return EpisodeResult(
        total_reward=total_reward,
        steps=step_count,
        reached_goal=reached_goal,
        hit_trap=hit_trap,
        trajectory=history,
        genome_hash=genome_hash,
    )


def train_protocol(
    env: MDPEnvironment,
    protocol: EvolvableProtocol,
    llm: SimulatedLLM,
    optimizer: ProtocolOptimizer,
    n_generations: int = 20,
    episodes_per_genome: int = 3,
    verbose: bool = True,
) -> list[dict]:
    """
    Main training loop: optimize the protocol using RL reward signals.

    For each generation:
        1. Optimizer suggests a genome
        2. Run multiple episodes to estimate its expected reward
        3. Report average reward back to the optimizer
        4. Optimizer updates its internal state (evolves / updates UCB)

    Args:
        env:                 The MDP environment.
        protocol:            The evolvable protocol.
        llm:                 The frozen LLM policy.
        optimizer:           The protocol optimizer (evolutionary or bandit).
        n_generations:       Number of optimization iterations.
        episodes_per_genome: Episodes to average over per genome evaluation.
        verbose:             Whether to print progress.

    Returns:
        List of per-generation log dicts for analysis.
    """
    training_log = []

    for gen in range(n_generations):
        # -- Get a genome proposal from the optimizer --
        genome = optimizer.suggest_genome()

        # -- Evaluate it over multiple episodes (reduce variance) --
        results = []
        for _ in range(episodes_per_genome):
            result = run_episode(env, protocol, llm, genome)
            results.append(result)

        # -- Compute average metrics --
        avg_reward = sum(r.total_reward for r in results) / len(results)
        avg_steps = sum(r.steps for r in results) / len(results)
        goal_rate = sum(r.reached_goal for r in results) / len(results)
        trap_rate = sum(r.hit_trap for r in results) / len(results)

        # -- Report reward to optimizer --
        optimizer.report_reward(genome, avg_reward)

        # -- Log this generation --
        gen_log = {
            "generation": gen,
            "avg_reward": avg_reward,
            "avg_steps": avg_steps,
            "goal_rate": goal_rate,
            "trap_rate": trap_rate,
            "genome": genome,
            "genome_hash": results[0].genome_hash,
        }
        training_log.append(gen_log)

        if verbose and gen % 5 == 0:
            print(
                f"Gen {gen:3d} | "
                f"Avg Reward: {avg_reward:7.2f} | "
                f"Goal Rate: {goal_rate:.0%} | "
                f"Trap Rate: {trap_rate:.0%} | "
                f"Avg Steps: {avg_steps:.1f}"
            )

    return training_log


# =============================================================================
# SECTION 7: Analysis Utilities
# =============================================================================

def analyze_results(training_log: list[dict], protocol: EvolvableProtocol) -> str:
    """
    Produce a human-readable analysis of the training run.

    Returns a formatted string summarizing what the optimizer learned
    about which protocol components work best.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("PROTOCOL OPTIMIZATION RESULTS")
    lines.append("=" * 60)

    # -- Reward trajectory --
    rewards = [g["avg_reward"] for g in training_log]
    first_5 = sum(rewards[:5]) / min(5, len(rewards))
    last_5 = sum(rewards[-5:]) / min(5, len(rewards))
    best_gen = max(training_log, key=lambda g: g["avg_reward"])

    lines.append(f"\nReward trajectory:")
    lines.append(f"  First 5 generations avg:  {first_5:.2f}")
    lines.append(f"  Last 5 generations avg:   {last_5:.2f}")
    lines.append(f"  Improvement:              {last_5 - first_5:+.2f}")
    lines.append(f"  Best generation:          {best_gen['generation']} "
                 f"(reward: {best_gen['avg_reward']:.2f})")

    # -- Decode best genome into human-readable protocol choices --
    best_genome = best_gen["genome"]
    lines.append(f"\nBest protocol configuration:")

    for comp in protocol.components:
        variant_idx = best_genome.get(f"{comp.name}_variant", 0)
        weight = best_genome.get(f"{comp.name}_weight", 1.0)
        variant_text = comp.variants[variant_idx]
        # Truncate long variant text for display
        if len(str(variant_text)) > 80:
            variant_text = str(variant_text)[:77] + "..."
        lines.append(f"  {comp.name}:")
        lines.append(f"    Variant {variant_idx}: {variant_text}")
        lines.append(f"    Inclusion weight: {weight:.2f}")

    for tool in protocol.tools:
        desc_idx = best_genome.get(f"tool_{tool.tool_name}_desc", 0)
        desc_text = tool.description_variants[desc_idx]
        if len(desc_text) > 80:
            desc_text = desc_text[:77] + "..."
        lines.append(f"  tool_{tool.tool_name}:")
        lines.append(f"    Description {desc_idx}: {desc_text}")

    # -- Goal/trap rates over time --
    lines.append(f"\nGoal reach rate:")
    lines.append(f"  First 5: {sum(g['goal_rate'] for g in training_log[:5]) / 5:.0%}")
    lines.append(f"  Last 5:  {sum(g['goal_rate'] for g in training_log[-5:]) / 5:.0%}")

    lines.append(f"\nTrap hit rate:")
    lines.append(f"  First 5: {sum(g['trap_rate'] for g in training_log[:5]) / 5:.0%}")
    lines.append(f"  Last 5:  {sum(g['trap_rate'] for g in training_log[-5:]) / 5:.0%}")

    return "\n".join(lines)


# =============================================================================
# SECTION 8: Main — Run the full experiment
# =============================================================================

if __name__ == "__main__":
    random.seed(42)

    print("MCP-RL Protocol Optimizer")
    print("=" * 60)
    print("LLM is FROZEN. Only the protocol (context) is optimized.\n")

    # -- Setup --
    env = GridWorldMDP(grid_size=5, max_steps=50)
    protocol = EvolvableProtocol()
    llm = SimulatedLLM(noise_level=0.15)

    # -------------------------------------------------------------------------
    # Experiment 1: Evolutionary Optimizer
    # -------------------------------------------------------------------------
    print("\n--- Experiment 1: Evolutionary Optimizer ---\n")
    evo_optimizer = EvolutionaryOptimizer(
        protocol=protocol,
        population_size=12,
        elite_fraction=0.3,
        mutation_rate=0.3,
    )

    evo_log = train_protocol(
        env=env,
        protocol=protocol,
        llm=llm,
        optimizer=evo_optimizer,
        n_generations=50,
        episodes_per_genome=5,
        verbose=True,
    )

    print(analyze_results(evo_log, protocol))

    # -------------------------------------------------------------------------
    # Experiment 2: Component Bandit Optimizer
    # -------------------------------------------------------------------------
    print("\n\n--- Experiment 2: Component Bandit Optimizer ---\n")
    bandit_optimizer = ComponentBanditOptimizer(
        protocol=protocol,
        exploration=1.5,
    )

    bandit_log = train_protocol(
        env=env,
        protocol=protocol,
        llm=llm,
        optimizer=bandit_optimizer,
        n_generations=50,
        episodes_per_genome=5,
        verbose=True,
    )

    print(analyze_results(bandit_log, protocol))

    # -- Show what the bandit learned per-component --
    print("\n\nComponent-level bandit analysis:")
    best_variants = bandit_optimizer.get_best_variants()
    for comp_name, info in best_variants.items():
        print(
            f"  {comp_name}: best variant={info['variant']} "
            f"(mean reward={info['mean_reward']:.2f}, "
            f"selected {info['times_selected']} times)"
        )

    # -------------------------------------------------------------------------
    # Show what an actual rendered protocol looks like
    # -------------------------------------------------------------------------
    print("\n\n" + "=" * 60)
    print("EXAMPLE: Best protocol rendering for a sample state")
    print("=" * 60)

    # Apply the best genome from the evolutionary run
    if evo_optimizer.best_genome:
        protocol.set_genome(evo_optimizer.best_genome)

    sample_state = env.reset()
    sample_history = [
        {"step": 1, "state": sample_state, "action": "right", "reward": -0.1,
         "next_state": sample_state},
        {"step": 2, "state": sample_state, "action": "down", "reward": -0.1,
         "next_state": sample_state},
    ]

    context = protocol.render_full_context(sample_state, sample_history)
    print(f"\n[SYSTEM PROMPT]\n{context['system']}")
    print(f"\n[USER MESSAGE]\n{context['user']}")
    print(f"\n[TOOLS]\n{json.dumps(context['tools'], indent=2)}")
