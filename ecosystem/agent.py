# Pipeline Step 1: Load ADK Framework Components (workflow + MCP)
from .imports import (
    LlmAgent, SequentialAgent, ParallelAgent, LoopAgent,
    McpToolset, StdioConnectionParams, StdioServerParameters,
)
from .tools.loop_control import exit_loop

# ============================================================
# PIPELINE OVERVIEW
# ============================================================
#
# This agent implements a "Research → Draft → Refine" pipeline that
# combines two ADK capability layers:
#
#   1. Workflow Agents  — SequentialAgent, ParallelAgent, LoopAgent
#                         orchestrate the pipeline structure.
#   2. MCP Tools        — Each parallel researcher has a live internet
#                         fetch capability via mcp-server-fetch.
#
# The full pipeline is orchestrated by a SequentialAgent:
#
#   root_agent  (SequentialAgent: "web_research_pipeline_agent")
#   │
#   ├─ Step 1: research_phase_agent  (ParallelAgent)
#   │   ├─ overview_researcher_agent     (LlmAgent + McpToolset[fetch])
#   │   │    → fetches an overview page  → session state: "overview"
#   │   ├─ examples_researcher_agent     (LlmAgent + McpToolset[fetch])
#   │   │    → fetches examples/case studies  → session state: "examples"
#   │   └─ limitations_researcher_agent  (LlmAgent + McpToolset[fetch])
#   │        → fetches limitations/critique   → session state: "limitations"
#   │
#   ├─ Step 2: drafting_agent  (LlmAgent)
#   │   └─ Synthesises the three parallel outputs  → session state: "draft"
#   │
#   └─ Step 3: refinement_loop_agent  (LoopAgent, max_iterations=3)
#       ├─ reviewer_agent  — critiques "draft"; calls exit_loop() if approved
#       │                    → session state: "review_notes"
#       └─ editor_agent    — rewrites "draft" using "review_notes"
#                            → session state: "draft"  (updated in-place)
#
# Key difference from workflow_agents/:
#   Each parallel researcher now calls fetch via MCP to pull live web
#   content before synthesising its research angle.  The pipeline
#   structure (Sequential → Parallel → Draft → Loop) is identical.
#
# ============================================================


# ============================================================
# MCP TOOLSET FACTORY
# Each LlmAgent that uses MCP tools needs its OWN McpToolset instance —
# MCP connections are per-agent.  Call _fetch_toolset() once per agent.
# ============================================================

def _fetch_toolset() -> McpToolset:
    """Return a new McpToolset instance backed by mcp-server-fetch."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command='uvx',
                args=['mcp-server-fetch'],
            ),
        ),
        tool_filter=['fetch'],
    )


# ============================================================
# STEP 1 — PARALLEL RESEARCH PHASE  (with live internet access)
# Three LlmAgents run concurrently.  Each has its own MCP fetch
# connection and writes to a separate output_key in session state.
# ============================================================

overview_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='overview_researcher_agent',
    description='Fetches and summarises a factual overview of the topic from the web.',
    output_key='overview',      # → session state["overview"]
    tools=[_fetch_toolset()],   # live internet fetch via MCP
    instruction=(
        'You are a research specialist with live internet access via the fetch tool. '
        'The user will give you a topic. '
        '\n\n'
        'Steps:\n'
        '1. Construct the Wikipedia URL for the topic '
        '   (e.g. https://en.wikipedia.org/wiki/Transformer_(machine_learning_model) '
        '   for "transformer neural networks").\n'
        '2. Call fetch with that URL to retrieve the page content.\n'
        '3. Using the fetched content, write a concise, factual overview '
        '   (3–4 paragraphs) covering: (1) a clear definition, '
        '   (2) historical context or origin, and (3) the current state today.\n'
        '4. End your response with: Source: <the URL you fetched>\n'
        '\n'
        'Be objective and informative. Do not include examples or limitations.'
    ),
)

examples_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='examples_researcher_agent',
    description='Fetches real-world examples and case studies for the topic from the web.',
    output_key='examples',      # → session state["examples"]
    tools=[_fetch_toolset()],
    instruction=(
        'You are a research specialist with live internet access via the fetch tool. '
        'The user will give you a topic. '
        '\n\n'
        'Steps:\n'
        '1. Construct a URL that is likely to contain concrete examples or '
        '   applications of the topic.  Good choices: a Wikipedia "Applications" '
        '   or "Examples" section, or the main Wikipedia article for the topic.\n'
        '2. Call fetch with that URL.\n'
        '3. Using the fetched content, provide 3–5 concrete, real-world examples '
        '   or case studies.  For each, give a short title and a 2–3 sentence '
        '   explanation of what happened and why it matters.\n'
        '4. End your response with: Source: <the URL you fetched>\n'
        '\n'
        'Focus only on examples — do not write an overview or discuss limitations.'
    ),
)

limitations_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='limitations_researcher_agent',
    description='Fetches limitations, risks, and open questions for the topic from the web.',
    output_key='limitations',   # → session state["limitations"]
    tools=[_fetch_toolset()],
    instruction=(
        'You are a critical research specialist with live internet access via the fetch tool. '
        'The user will give you a topic. '
        '\n\n'
        'Steps:\n'
        '1. Construct a URL likely to discuss criticism, limitations, or challenges '
        '   of the topic.  Good choices: the Wikipedia article (look for "Criticism", '
        '   "Limitations", or "Challenges" sections), or a relevant overview page.\n'
        '2. Call fetch with that URL.\n'
        '3. Using the fetched content, analyse 3–5 key challenges, limitations, '
        '   risks, or open questions.  Be honest and balanced.\n'
        '4. End your response with: Source: <the URL you fetched>\n'
        '\n'
        'Focus only on limitations — do not repeat the overview or examples.'
    ),
)

# ParallelAgent: all three researchers run concurrently, each with their own
# MCP fetch connection.  Each branch writes to a unique output_key.
research_phase_agent = ParallelAgent(
    name='research_phase_agent',
    description=(
        'Researches a topic from three independent angles simultaneously using '
        'live web data: overview, real-world examples, and limitations.'
    ),
    sub_agents=[
        overview_researcher_agent,
        examples_researcher_agent,
        limitations_researcher_agent,
    ],
)


# ============================================================
# STEP 2 — DRAFTING
# Synthesises the three web-sourced research briefs into a structured
# first-draft report, preserving cited sources.
# ============================================================

drafting_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='drafting_agent',
    description='Synthesises web-sourced research briefs into a structured first-draft report.',
    output_key='draft',         # → session state["draft"]
    instruction=(
        'You are a professional technical writer. '
        'You have been given three research briefs on the same topic, each sourced '
        'from the web via live fetch calls. '
        'Synthesise them into a single, coherent, well-structured report. '
        '\n\n'
        '--- OVERVIEW ---\n{overview}\n\n'
        '--- EXAMPLES ---\n{examples}\n\n'
        '--- LIMITATIONS ---\n{limitations}\n\n'
        'Structure the report with the following sections:\n'
        '1. Introduction\n'
        '2. Key Concepts\n'
        '3. Real-World Examples\n'
        '4. Challenges & Limitations\n'
        '5. Conclusion\n'
        '6. Sources\n'
        '\n'
        'In the Sources section, list every URL cited by the researchers. '
        'Write clearly and professionally. Aim for 400–600 words.'
    ),
)


# ============================================================
# STEP 3 — REFINEMENT LOOP
# Identical pattern to workflow_agents/: a reviewer critiques the draft
# and either approves (exit_loop) or requests changes, then an editor
# rewrites.  Runs up to 3 iterations.
# ============================================================

reviewer_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='reviewer_agent',
    description=(
        'Reviews the current report draft for quality. '
        'Calls exit_loop if approved; otherwise writes improvement notes.'
    ),
    output_key='review_notes',  # → session state["review_notes"]
    tools=[exit_loop],
    instruction=(
        'You are a strict but fair editor reviewing a report draft. '
        '\n\n'
        '--- CURRENT DRAFT ---\n{draft}\n\n'
        'Evaluate the draft against these criteria:\n'
        '  • All six required sections present (including Sources)\n'
        '  • Claims supported by the cited web sources\n'
        '  • Smooth flow between sections\n'
        '  • Professional, concise language (no padding)\n'
        '\n'
        'If the draft meets ALL criteria, call the exit_loop tool to approve it.\n'
        'If it does NOT, do NOT call exit_loop. Instead, write a numbered list '
        'of specific, actionable improvements. Be precise — point to exact '
        'sections or sentences that need work.'
    ),
)

editor_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description="Rewrites the report draft based on the reviewer's notes.",
    output_key='draft',         # overwrites session state["draft"] with the improved version
    instruction=(
        'You are a skilled editor. Revise the report draft to address every point '
        'in the review notes. '
        '\n\n'
        '--- CURRENT DRAFT ---\n{draft}\n\n'
        '--- REVIEW NOTES ---\n{review_notes}\n\n'
        'Rewrite the full report, incorporating all the feedback. '
        'Keep the six-section structure (including Sources). '
        'Output ONLY the revised report — no preamble, no commentary.'
    ),
)

# LoopAgent: reviewer → editor, max 3 iterations.
# exit_loop (set by reviewer_agent) is the primary termination path.
# max_iterations=3 is the safety cap.
refinement_loop_agent = LoopAgent(
    name='refinement_loop_agent',
    description=(
        'Iteratively refines the report draft through reviewer–editor cycles '
        'until quality standards are met or the iteration limit is reached.'
    ),
    sub_agents=[reviewer_agent, editor_agent],
    max_iterations=3,
)


# ============================================================
# ROOT AGENT — Sequential Pipeline
# Ties all three steps together in strict order:
#   research_phase_agent → drafting_agent → refinement_loop_agent
# ============================================================

root_agent = SequentialAgent(
    name='web_research_pipeline_agent',
    description=(
        'Generates a polished, web-sourced report on any topic using a '
        'three-phase pipeline: concurrent internet research (via MCP fetch), '
        'drafting, and iterative refinement.'
    ),
    sub_agents=[
        research_phase_agent,       # Phase 1: parallel web research
        drafting_agent,             # Phase 2: first-draft synthesis
        refinement_loop_agent,      # Phase 3: quality loop
    ],
)
