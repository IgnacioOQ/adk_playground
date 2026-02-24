# Pipeline Step 1: Load ADK Framework Components
from .imports import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from .tools.loop_control import exit_loop

# ============================================================
# PIPELINE OVERVIEW
# ============================================================
#
# This agent implements a "Research → Draft → Refine" pipeline for
# generating a polished written report on any user-supplied topic.
#
# The full pipeline is orchestrated by a SequentialAgent:
#
#   root_agent  (SequentialAgent: "report_pipeline_agent")
#   │
#   ├─ Step 1: research_phase_agent  (ParallelAgent)
#   │   ├─ overview_researcher_agent     → session state: "overview"
#   │   ├─ examples_researcher_agent     → session state: "examples"
#   │   └─ limitations_researcher_agent  → session state: "limitations"
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
# Data flows through ADK session state via output_key.
# Each agent's last text response is stored under its output_key and
# can be referenced in subsequent agents' instructions as {key}.
#
# ============================================================


# ============================================================
# STEP 1 — PARALLEL RESEARCH PHASE
# Three LlmAgents research the same topic independently and
# simultaneously.  Their outputs land in separate state keys so
# the drafting agent can combine all three.
# ============================================================

overview_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='overview_researcher_agent',
    description='Writes a broad overview of the given topic.',
    output_key='overview',      # stores output in session state["overview"]
    instruction=(
        'You are a research specialist. The user will give you a topic. '
        'Write a concise, factual overview (3–4 paragraphs) covering: '
        '(1) a clear definition, (2) historical context or origin, and '
        '(3) the current state of the topic today. '
        'Be objective and informative. Do not include examples or limitations.'
    ),
)

examples_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='examples_researcher_agent',
    description='Finds concrete real-world examples or case studies for the given topic.',
    output_key='examples',      # stores output in session state["examples"]
    instruction=(
        'You are a research specialist. The user will give you a topic. '
        'Provide 3–5 concrete, real-world examples or case studies that clearly '
        'illustrate the topic in practice. For each example, give a short title '
        'and a 2–3 sentence explanation of what happened and why it matters. '
        'Focus only on examples — do not write an overview or discuss limitations.'
    ),
)

limitations_researcher_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='limitations_researcher_agent',
    description='Analyses the limitations, challenges, and open questions of the given topic.',
    output_key='limitations',   # stores output in session state["limitations"]
    instruction=(
        'You are a critical research specialist. The user will give you a topic. '
        'Analyse 3–5 key challenges, limitations, risks, or open questions surrounding '
        'the topic. Be honest and balanced — acknowledge both technical and practical '
        'difficulties. Focus only on limitations — do not repeat the overview or examples.'
    ),
)

# ParallelAgent: all three researchers run concurrently.
# There is NO automatic state sharing between branches during execution —
# each agent writes to its own output_key independently.
research_phase_agent = ParallelAgent(
    name='research_phase_agent',
    description=(
        'Researches a topic from three independent angles simultaneously: '
        'overview, real-world examples, and limitations.'
    ),
    sub_agents=[
        overview_researcher_agent,
        examples_researcher_agent,
        limitations_researcher_agent,
    ],
)


# ============================================================
# STEP 2 — DRAFTING
# One LlmAgent reads all three state keys from the parallel
# research phase and synthesises them into a structured report.
# The {key} placeholders are resolved from session state at runtime.
# ============================================================

drafting_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='drafting_agent',
    description='Synthesises parallel research outputs into a structured first-draft report.',
    output_key='draft',         # stores output in session state["draft"]
    instruction=(
        'You are a professional technical writer. '
        'You have been given three research briefs on the same topic. '
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
# A LoopAgent alternates between a reviewer and an editor until
# the reviewer is satisfied (calls exit_loop) or max_iterations
# is reached.
#
# Sub-agent order within each iteration:
#   1. reviewer_agent  — reads current "draft", critiques it.
#      If quality is acceptable, calls exit_loop() → loop terminates.
#      Otherwise, writes actionable notes to session state["review_notes"].
#   2. editor_agent    — reads "draft" + "review_notes", produces an
#      improved draft, overwrites session state["draft"].
# ============================================================

reviewer_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='reviewer_agent',
    description=(
        'Reviews the current report draft for quality. '
        'Calls exit_loop if approved; otherwise writes improvement notes.'
    ),
    output_key='review_notes',  # stores critique in session state["review_notes"]
    tools=[exit_loop],          # gives the LLM the ability to terminate the loop
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
        'If it does NOT meet the criteria, do NOT call exit_loop. Instead, write '
        'a numbered list of specific, actionable improvements. Be precise — point '
        'to exact sections or sentences that need work.'
    ),
)

editor_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='editor_agent',
    description='Rewrites the report draft based on the reviewer\'s notes.',
    output_key='draft',         # overwrites session state["draft"] with the improved version
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

# LoopAgent: alternates reviewer → editor.
# max_iterations=3 is a hard safety cap; the reviewer's exit_loop call
# is the primary (and preferred) termination path.
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
    name='report_pipeline_agent',
    description=(
        'Generates a polished, well-researched report on any topic '
        'using a three-phase pipeline: parallel research, drafting, '
        'and iterative refinement.'
    ),
    sub_agents=[
        research_phase_agent,       # Phase 1: parallel fact-gathering
        drafting_agent,             # Phase 2: first-draft synthesis
        refinement_loop_agent,      # Phase 3: quality loop
    ],
)
