# Pipeline Step 1: Load ADK Framework Components (workflow + built-in search)
from google.adk.tools import google_search

from .imports import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from .tools.loop_control import exit_loop

# ============================================================
# PIPELINE OVERVIEW
# ============================================================
#
# This agent implements a "Research → Draft → Refine" pipeline that
# combines two ADK capability layers:
#
#   1. Workflow Agents    — SequentialAgent, ParallelAgent, LoopAgent
#                           orchestrate the pipeline structure.
#   2. google_search tool — ADK built-in; gives each parallel researcher
#                           live Google Search access with no extra setup.
#
# The full pipeline is orchestrated by a SequentialAgent:
#
#   root_agent  (SequentialAgent: "web_research_pipeline_agent")
#   │
#   ├─ Step 1: research_phase_agent  (ParallelAgent)
#   │   ├─ overview_researcher_agent     (LlmAgent + google_search)
#   │   │    → searches for overview     → session state: "overview"
#   │   ├─ examples_researcher_agent     (LlmAgent + google_search)
#   │   │    → searches for examples     → session state: "examples"
#   │   └─ limitations_researcher_agent  (LlmAgent + google_search)
#   │        → searches for limitations  → session state: "limitations"
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
# ============================================================


# ============================================================
# STEP 1 — PARALLEL RESEARCH PHASE  (with live Google Search)
# Three LlmAgents run concurrently.  Each has google_search and
# writes to a separate output_key in session state.
# ============================================================

overview_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='overview_researcher_agent',
    description='Searches the web and writes a factual overview of the given topic.',
    output_key='overview',      # → session state["overview"]
    tools=[google_search],
    instruction=(
        'You are a research specialist with live Google Search access. '
        'The user will give you a topic. '
        'Use google_search to find reliable information about the topic, '
        'then write a concise, factual overview (3–4 paragraphs) covering: '
        '(1) a clear definition, (2) historical context or origin, and '
        '(3) the current state of the topic today. '
        'Be objective and informative. Do not include examples or limitations.'
    ),
)

examples_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='examples_researcher_agent',
    description='Searches the web for real-world examples and case studies of the given topic.',
    output_key='examples',      # → session state["examples"]
    tools=[google_search],
    instruction=(
        'You are a research specialist with live Google Search access. '
        'The user will give you a topic. '
        'Use google_search to find concrete real-world examples or case studies '
        'of the topic in practice. '
        'Provide 3–5 examples. For each, give a short title and a 2–3 sentence '
        'explanation of what happened and why it matters. '
        'Focus only on examples — do not write an overview or discuss limitations.'
    ),
)

limitations_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='limitations_researcher_agent',
    description='Searches the web for limitations, risks, and open questions about the given topic.',
    output_key='limitations',   # → session state["limitations"]
    tools=[google_search],
    instruction=(
        'You are a critical research specialist with live Google Search access. '
        'The user will give you a topic. '
        'Use google_search to find information about the challenges, limitations, '
        'risks, or open questions surrounding the topic. '
        'Analyse 3–5 key limitations. Be honest and balanced. '
        'Focus only on limitations — do not repeat the overview or examples.'
    ),
)

# ParallelAgent: all three researchers run concurrently.
# Each branch writes to a unique output_key.
research_phase_agent = ParallelAgent(
    name='research_phase_agent',
    description=(
        'Researches a topic from three independent angles simultaneously using '
        'live Google Search: overview, real-world examples, and limitations.'
    ),
    sub_agents=[
        overview_researcher_agent,
        examples_researcher_agent,
        limitations_researcher_agent,
    ],
)


# ============================================================
# STEP 2 — DRAFTING
# Synthesises the three research briefs into a structured report.
# ============================================================

drafting_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='drafting_agent',
    description='Synthesises web-sourced research briefs into a structured first-draft report.',
    output_key='draft',         # → session state["draft"]
    instruction=(
        'You are a professional technical writer. '
        'You have been given three research briefs on the same topic, '
        'each sourced from live Google Search results. '
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
        '\n'
        'Write clearly and professionally. Aim for 400–600 words.'
    ),
)


# ============================================================
# STEP 3 — REFINEMENT LOOP
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
        '  • Clear structure with all five required sections present\n'
        '  • Accurate and well-supported claims\n'
        '  • Smooth flow between sections\n'
        '  • Professional, concise language (no padding)\n'
        '\n'
        'If the draft meets ALL criteria, call the exit_loop tool to approve it.\n'
        'If it does NOT, do NOT call exit_loop. Instead, write a numbered list '
        'of specific, actionable improvements.'
    ),
)

editor_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description="Rewrites the report draft based on the reviewer's notes.",
    output_key='draft',         # overwrites session state["draft"]
    instruction=(
        'You are a skilled editor. Revise the report draft to address every point '
        'in the review notes. '
        '\n\n'
        '--- CURRENT DRAFT ---\n{draft}\n\n'
        '--- REVIEW NOTES ---\n{review_notes}\n\n'
        'Rewrite the full report, incorporating all the feedback. '
        'Keep the five-section structure. '
        'Output ONLY the revised report — no preamble, no commentary.'
    ),
)

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
# ============================================================

root_agent = SequentialAgent(
    name='web_research_pipeline_agent',
    description=(
        'Generates a polished, web-sourced report on any topic using a '
        'three-phase pipeline: concurrent Google Search research, drafting, '
        'and iterative refinement.'
    ),
    sub_agents=[
        research_phase_agent,       # Phase 1: parallel Google Search research
        drafting_agent,             # Phase 2: first-draft synthesis
        refinement_loop_agent,      # Phase 3: quality loop
    ],
)
