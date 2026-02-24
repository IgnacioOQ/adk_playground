# ADK Tools Skill — Integrations & Tool Reference Guide
- status: active
- type: agent_skill
- id: skill.adk_tools
- last_checked: 2026-02-24
- label: [agent, guide, infrastructure, backend, tools]
<!-- content -->
This document is the primary reference for all tool types available to ADK agents. It covers the full spectrum: **built-in ADK tools** (zero-setup, import-and-use), **native toolsets** (first-party ADK integrations with dedicated classes), **MCP-backed integrations** (third-party servers connected via `McpToolset`), and **observability plugins**. For each category, the most commonly used tools are catalogued with import paths, setup code, and key notes.

Reference: https://google.github.io/adk-docs/integrations/

Related skills:
- `ADK_MCP_SKILL.md` — deep dive into MCP architecture and connection types
- `ADK_WORKFLOW_SKILL.md` — how to attach any of these tools to workflow pipeline sub-agents
- `ADK_SKILL.md` — foundational ADK agent patterns

## 1. Tool Type Overview
- status: active
- type: guideline
- id: skill.adk_tools.overview
- last_checked: 2026-02-24
<!-- content -->
ADK supports four distinct tool integration mechanisms. Choose the right one based on what you need:

| Type | How it works | Best for |
| :--- | :--- | :--- |
| **Built-in tools** | Single import from `google.adk.tools`; no extra config | Google Search, code execution — instant capability injection |
| **Native ADK toolsets** | Dedicated ADK classes with first-party SDK wrappers | BigQuery, Vertex AI Search, RAG Engine — typed, GCP-native |
| **MCP toolsets** | External server process connected via `McpToolset` | GitHub, Stripe, Atlassian, MongoDB, Pinecone — ecosystem tools |
| **Python tools** | Plain Python functions registered in `tools=[]` | Custom business logic, internal APIs, any hand-written capability |

All four types can coexist in the same agent's `tools` list.

## 2. Built-in Tools
- status: active
- type: guideline
- id: skill.adk_tools.builtin
- last_checked: 2026-02-24
<!-- content -->
Built-in tools are pre-built ADK objects that can be attached to any `LlmAgent` with a single import. No external process, no API key beyond the Gemini key already in `.env`.

### google_search
- status: active
- type: guideline
- id: skill.adk_tools.builtin.google_search
- last_checked: 2026-02-24
<!-- content -->
Enables the agent to perform live Google Search queries using Gemini's grounding capability. The model decides when to call it and what to search for.

```python
from google.adk.tools import google_search

agent = LlmAgent(
    model='gemini-2.5-flash',
    name='search_agent',
    tools=[google_search],
    instruction='Answer questions using up-to-date information from the web.',
)
```

**Notes:**
- Works with Gemini models only (uses Gemini grounding under the hood).
- The agent autonomously decides when to invoke search — no explicit call needed in the instruction.
- Returned results include source URLs for citation.
- Used in `ecosystem/agent.py` to power the parallel research phase.

Reference: https://google.github.io/adk-docs/integrations/

### BuiltInCodeExecutor
- status: active
- type: guideline
- id: skill.adk_tools.builtin.code_executor
- last_checked: 2026-02-24
<!-- content -->
Lets the agent execute Python code snippets during its reasoning turn. The model generates code, executes it, and uses the output to continue its response.

```python
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor

agent = LlmAgent(
    model='gemini-2.0-flash',
    name='calculator_agent',
    code_executor=BuiltInCodeExecutor(),
    instruction='Solve mathematical problems by writing and running Python code.',
)
```

**Notes:**
- Requires Gemini 2.0+ models.
- `BuiltInCodeExecutor` is passed via the `code_executor` parameter, **not** `tools`.
- Single-tool limitation: cannot be combined with other tools in the same agent.
- Handles `executable_code` and `code_execution_result` event parts in the response stream.

Reference: https://google.github.io/adk-docs/integrations/code-execution/

## 3. Native ADK Toolsets
- status: active
- type: guideline
- id: skill.adk_tools.native
- last_checked: 2026-02-24
<!-- content -->
Native toolsets are first-party ADK integrations that ship with `google-adk`. They have dedicated Python classes with typed configuration and GCP-native authentication.

### BigQueryToolset
- status: active
- type: guideline
- id: skill.adk_tools.native.bigquery
- last_checked: 2026-02-24
<!-- content -->
Connects the agent to Google BigQuery for SQL queries, data exploration, schema inspection, and AI-powered forecasting.

**Installation:** No extra install — ships with `google-adk` v1.1.0+.

```python
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
import google.auth

credentials, project = google.auth.default()

bq_toolset = BigQueryToolset(
    credentials_config=BigQueryCredentialsConfig(credentials=credentials),
    bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),  # read-only
)

agent = LlmAgent(
    model='gemini-2.5-flash',
    name='data_analyst_agent',
    tools=[bq_toolset],
    instruction='Answer data questions by querying BigQuery.',
)
```

**Available tools:**

| Tool name | Description |
| :--- | :--- |
| `list_dataset_ids` | List all dataset IDs in a GCP project |
| `get_dataset_info` | Fetch metadata about a dataset |
| `list_table_ids` | List table IDs within a dataset |
| `get_table_info` | Fetch schema and metadata for a table |
| `execute_sql` | Run a SQL query and return results |
| `forecast` | Run a BigQuery AI time-series forecast (`AI.FORECAST`) |
| `ask_data_insights` | Answer natural language questions about table data |

**Notes:**
- Uses Application Default Credentials (ADC) — run `gcloud auth application-default login` locally.
- `WriteMode.BLOCKED` prevents INSERT/UPDATE/DELETE. Use `WriteMode.ALLOWED` to enable writes.

Reference: https://google.github.io/adk-docs/integrations/bigquery/

### VertexAiSearchTool
- status: active
- type: guideline
- id: skill.adk_tools.native.vertex_ai_search
- last_checked: 2026-02-24
<!-- content -->
Enables agents to search private data stores configured in Vertex AI Search and Conversation.

```python
from google.adk.tools import VertexAiSearchTool

DATASTORE_ID = (
    "projects/<PROJECT_ID>/locations/<REGION>"
    "/collections/default_collection/dataStores/<DATASTORE_ID>"
)

search_tool = VertexAiSearchTool(data_store_id=DATASTORE_ID)

agent = LlmAgent(
    model='gemini-2.0-flash',
    name='doc_qa_agent',
    tools=[search_tool],
    instruction='Answer questions using the internal knowledge base.',
)
```

**Notes:**
- Single-tool limitation — cannot be combined with other tools in the same agent.
- Requires a pre-configured Vertex AI Search data store and project IAM permissions.

Reference: https://google.github.io/adk-docs/integrations/vertex-ai-search/

### VertexAiRagRetrieval
- status: active
- type: guideline
- id: skill.adk_tools.native.vertex_ai_rag
- last_checked: 2026-02-24
<!-- content -->
Grounding tool that retrieves private documents from a Vertex AI RAG corpus before the model generates its response.

```python
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag

rag_tool = VertexAiRagRetrieval(
    name='retrieve_rag_documentation',
    description='Retrieve relevant documentation from the internal corpus.',
    rag_resources=[rag.RagResource(rag_corpus='projects/my-proj/locations/us-central1/ragCorpora/my-corpus')],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

agent = LlmAgent(
    model='gemini-2.0-flash-001',
    name='ask_rag_agent',
    tools=[rag_tool],
)
```

**Notes:**
- Single-tool limitation — cannot coexist with other tools.
- `similarity_top_k` controls how many chunks to retrieve; `vector_distance_threshold` filters out weak matches.
- Requires `vertexai` SDK (`pip install vertexai`).

Reference: https://google.github.io/adk-docs/integrations/vertex-ai-rag-engine/

## 4. MCP-Backed Integrations
- status: active
- type: guideline
- id: skill.adk_tools.mcp
- last_checked: 2026-02-24
<!-- content -->
MCP-backed integrations connect an ADK agent to an external tool server via `McpToolset`. The server can run as a local subprocess (stdio) or a remote HTTP service (SSE/Streamable HTTP). See `ADK_MCP_SKILL.md` for full MCP architecture details.

**Common import block for all MCP integrations:**
```python
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
    StreamableHTTPServerParams,  # for modern remote servers
)
from mcp import StdioServerParameters
```

### GitHub
- status: active
- type: guideline
- id: skill.adk_tools.mcp.github
- last_checked: 2026-02-24
<!-- content -->
Full GitHub management via the official GitHub Copilot MCP endpoint: repositories, issues, pull requests, actions, code security, Dependabot, discussions, and organizations.

```python
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"

github_toolset = McpToolset(
    connection_params=StreamableHTTPServerParams(
        url="https://api.githubcopilot.com/mcp/",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-MCP-Toolsets": "all",
            "X-MCP-Readonly": "true",   # remove to allow writes
        },
    ),
)

agent = LlmAgent(
    model='gemini-2.5-pro',
    name='github_agent',
    tools=[github_toolset],
    instruction='Help with GitHub repositories, issues, and pull requests.',
)
```

**Key tools:** list/search repos, read/create/close issues, list/create/merge PRs, list workflows, inspect code security alerts.

**Requirements:** Personal Access Token from GitHub Settings → Developer Settings → Tokens.

Reference: https://google.github.io/adk-docs/integrations/github/

### Stripe
- status: active
- type: guideline
- id: skill.adk_tools.mcp.stripe
- last_checked: 2026-02-24
<!-- content -->
30+ Stripe operations: payments, customers, subscriptions, invoices, refunds, pricing, and business insights.

```python
import os

stripe_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', '@stripe/mcp', '--tools=all'],
            env={**os.environ, 'STRIPE_SECRET_KEY': os.getenv('STRIPE_SECRET_KEY')},
        ),
    ),
    tool_filter=[
        'create_payment_link', 'list_customers', 'create_invoice',
        'retrieve_balance', 'search_payments',
    ],
)
```

**Key tools:** `create_payment_link`, `create_customer`, `create_invoice`, `finalize_invoice`, `create_refund`, `retrieve_balance`, `list_subscriptions`, `search_payments`.

**Requirements:** Restricted API key from the Stripe Dashboard. Enable human confirmation of tool actions before deploying.

Reference: https://google.github.io/adk-docs/integrations/stripe/

### Atlassian (Jira + Confluence)
- status: active
- type: guideline
- id: skill.adk_tools.mcp.atlassian
- last_checked: 2026-02-24
<!-- content -->
Manage Jira issues, Confluence pages, and team content through the official Atlassian remote MCP server.

```python
atlassian_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', 'mcp-remote', 'https://mcp.atlassian.com/v1/mcp'],
        ),
        timeout=30,
    ),
    tool_filter=[
        'jira_create_issue', 'jira_search_issues',
        'confluence_search', 'confluence_create_page',
    ],
)
```

**Key tools:** `jira_create_issue`, `jira_edit_issue`, `jira_search_issues`, `jira_transition_issue`, `confluence_search`, `confluence_get_page`, `confluence_create_page`, `confluence_update_page`.

**Requirements:** Browser-based OAuth authentication on first use. Requires `npx` and an active Atlassian account.

Reference: https://google.github.io/adk-docs/integrations/atlassian/

### MongoDB
- status: active
- type: guideline
- id: skill.adk_tools.mcp.mongodb
- last_checked: 2026-02-24
<!-- content -->
30+ database operations: natural language queries, aggregations, schema analysis, index management, and MongoDB Atlas infrastructure control.

```python
import os

mongodb_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', 'mongodb-mcp-server'],
            env={**os.environ, 'MDB_MCP_CONNECTION_STRING': os.getenv('MONGODB_URI')},
        ),
    ),
    tool_filter=[
        'find', 'aggregate', 'count', 'insert-many', 'update-many',
        'list-collections', 'collection-schema',
    ],
)
```

**Key tools:** `find`, `aggregate`, `count`, `insert-many`, `update-many`, `delete-many`, `list-collections`, `collection-schema`, `explain`, `create-index`.

**Requirements:** MongoDB connection string in `MDB_MCP_CONNECTION_STRING`. Atlas management also needs `MDB_MCP_API_CLIENT_ID` / `MDB_MCP_API_CLIENT_SECRET`.

Reference: https://google.github.io/adk-docs/integrations/mongodb/

### Pinecone
- status: active
- type: guideline
- id: skill.adk_tools.mcp.pinecone
- last_checked: 2026-02-24
<!-- content -->
Semantic search, vector upsert, index management, reranking, and cross-index cascading search for knowledge base and RAG use cases.

```python
import os

pinecone_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', '@pinecone-database/mcp'],
            env={**os.environ, 'PINECONE_API_KEY': os.getenv('PINECONE_API_KEY')},
        ),
    ),
    tool_filter=['search-records', 'upsert-records', 'list-indexes', 'rerank-documents'],
)
```

**Key tools:** `search-records`, `upsert-records`, `list-indexes`, `describe-index`, `describe-index-stats`, `create-index-for-model`, `cascading-search`, `rerank-documents`.

**Requirements:** Pinecone API key. Indexes must be configured with integrated inference for semantic search.

Reference: https://google.github.io/adk-docs/integrations/pinecone/

### Notion
- status: active
- type: guideline
- id: skill.adk_tools.mcp.notion
- last_checked: 2026-02-24
<!-- content -->
12 tools covering Notion workspace search, page/database creation and editing, comments, user management, and teamspace access.

```python
import os

notion_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', '@notionhq/notion-mcp-server'],
            env={**os.environ, 'OPENAPI_MCP_HEADERS': f'{{"Authorization": "Bearer {os.getenv(\"NOTION_TOKEN\")}", "Notion-Version": "2022-06-28"}}'},
        ),
    ),
    tool_filter=[
        'notion-search', 'notion-fetch', 'notion-create-pages',
        'notion-update-page', 'notion-create-database',
    ],
)
```

**Key tools:** `notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page`, `notion-move-pages`, `notion-duplicate-page`, `notion-create-database`, `notion-update-database`, `notion-create-comment`, `notion-get-comments`, `notion-get-teams`, `notion-get-users`.

**Requirements:** Notion integration token from https://www.notion.so/my-integrations. Grant the integration access to the pages you want it to read/edit.

Reference: https://google.github.io/adk-docs/integrations/notion/

## 5. Data & Vector Store Integrations
- status: active
- type: guideline
- id: skill.adk_tools.data
- last_checked: 2026-02-24
<!-- content -->
Tools in this category give agents access to structured data sources, cloud databases, and vector stores for semantic retrieval.

### MCP Toolbox for Databases
- status: active
- type: guideline
- id: skill.adk_tools.data.mcp_toolbox
- last_checked: 2026-02-24
<!-- content -->
Google's open-source database MCP proxy — connects agents to 30+ data sources including PostgreSQL, MySQL, Spanner, AlloyDB, BigQuery, SQLite, and more through a single `McpToolset`.

```python
# Run the toolbox server separately: pip install toolbox-core
# Then connect via SSE:
db_toolset = McpToolset(
    connection_params=SseConnectionParams(
        url='http://localhost:5000/sse',  # default toolbox SSE port
    ),
    tool_filter=['execute_sql', 'list_tables', 'get_schema'],
)
```

Reference: https://google.github.io/adk-docs/integrations/

### Chroma / Qdrant
- status: active
- type: guideline
- id: skill.adk_tools.data.vector_stores
- last_checked: 2026-02-24
<!-- content -->
Open-source vector databases for semantic search, both available as MCP servers via `npx`.

```python
# Chroma
chroma_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx', args=['-y', 'chroma-mcp-server']
        ),
    ),
    tool_filter=['query_collection', 'add_documents', 'list_collections'],
)

# Qdrant
qdrant_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx', args=['-y', 'qdrant-mcp-server'],
            env={**os.environ, 'QDRANT_URL': os.getenv('QDRANT_URL')},
        ),
    ),
    tool_filter=['search_points', 'upsert_points', 'list_collections'],
)
```

Reference: https://google.github.io/adk-docs/integrations/

## 6. Enterprise & SaaS Integrations
- status: active
- type: guideline
- id: skill.adk_tools.enterprise
- last_checked: 2026-02-24
<!-- content -->
Tools that connect agents to enterprise collaboration platforms and SaaS ecosystems.

### Application Integration (Google Cloud)
- status: active
- type: guideline
- id: skill.adk_tools.enterprise.app_integration
- last_checked: 2026-02-24
<!-- content -->
Connects agents to hundreds of enterprise applications (SAP, Salesforce, ServiceNow, etc.) via Google Cloud Application Integration Connectors — no MCP server needed.

```python
from google.adk.tools.application_integration_tool.application_integration_toolset import (
    ApplicationIntegrationToolset,
)

toolset = ApplicationIntegrationToolset(
    project='my-gcp-project',
    location='us-central1',
    integration='my-integration-name',
    triggers=['api_trigger/trigger_1'],
    service_account_credentials='...',
)

agent = LlmAgent(
    model='gemini-2.5-flash',
    name='enterprise_agent',
    tools=[toolset],
)
```

Reference: https://google.github.io/adk-docs/integrations/

### StackOne
- status: active
- type: guideline
- id: skill.adk_tools.enterprise.stackone
- last_checked: 2026-02-24
<!-- content -->
Single MCP connection that gives agents access to 200+ SaaS providers (Workday, Salesforce, HubSpot, Greenhouse, etc.) through StackOne's unified API.

```python
import os

stackone_toolset = McpToolset(
    connection_params=SseConnectionParams(
        url='https://mcp.stackone.com/sse',
        headers={'Authorization': f'Basic {os.getenv("STACKONE_API_KEY")}'},
    ),
)
```

Reference: https://google.github.io/adk-docs/integrations/

## 7. Communication & Media Tools
- status: active
- type: guideline
- id: skill.adk_tools.communication
- last_checked: 2026-02-24
<!-- content -->

### Mailgun
- status: active
- type: guideline
- id: skill.adk_tools.communication.mailgun
- last_checked: 2026-02-24
<!-- content -->
Send emails, track delivery metrics, and manage mailing lists via the Mailgun MCP server.

```python
import os

mailgun_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', 'mailgun-mcp-server'],
            env={**os.environ, 'MAILGUN_API_KEY': os.getenv('MAILGUN_API_KEY')},
        ),
    ),
    tool_filter=['send_email', 'list_mailing_lists', 'get_delivery_stats'],
)
```

Reference: https://google.github.io/adk-docs/integrations/

### ElevenLabs
- status: active
- type: guideline
- id: skill.adk_tools.communication.elevenlabs
- last_checked: 2026-02-24
<!-- content -->
Text-to-speech, voice cloning, audio transcription, and sound effect generation through the ElevenLabs MCP server.

```python
import os

elevenlabs_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', '@elevenlabs/elevenlabs-mcp'],
            env={**os.environ, 'ELEVENLABS_API_KEY': os.getenv('ELEVENLABS_API_KEY')},
        ),
    ),
    tool_filter=['text_to_speech', 'speech_to_text', 'list_voices'],
)
```

Reference: https://google.github.io/adk-docs/integrations/

## 8. Observability & Monitoring
- status: active
- type: guideline
- id: skill.adk_tools.observability
- last_checked: 2026-02-24
<!-- content -->
Observability integrations are **not** attached as tools to agents — they hook into ADK's internal OpenTelemetry tracer. Add them at process startup, before any agent or runner is created.

### AgentOps
- status: active
- type: guideline
- id: skill.adk_tools.observability.agentops
- last_checked: 2026-02-24
<!-- content -->
Session replays, per-agent metrics, LLM cost tracking, tool invocation logs, and performance latency analysis.

```python
# pip install agentops
import agentops
import os

agentops.init(
    api_key=os.getenv('AGENTOPS_API_KEY'),
    trace_name='my-adk-app-trace',
)

# Then build your agents and runners as normal — AgentOps captures everything.
```

**What it captures:**
- Agent execution hierarchies (parent + child spans)
- LLM calls with model, tokens, and latency (e.g. `adk.llm.gemini-2.5-flash`)
- Tool invocations with input arguments (e.g. `adk.tool.google_search`)
- End-to-end session costs and latencies

Reference: https://google.github.io/adk-docs/integrations/agentops/

### MLflow
- status: active
- type: guideline
- id: skill.adk_tools.observability.mlflow
- last_checked: 2026-02-24
<!-- content -->
Ingest ADK OpenTelemetry traces into MLflow for agent run analysis, tool call inspection, and model request logging.

```python
# pip install mlflow
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
mlflow.set_experiment('adk-agent-runs')
# MLflow auto-instruments ADK's OTel tracer.
```

Reference: https://google.github.io/adk-docs/integrations/

### Arize AX / Phoenix / W&B Weave
- status: active
- type: guideline
- id: skill.adk_tools.observability.other
- last_checked: 2026-02-24
<!-- content -->
Production-grade LLM observability platforms. All three integrate via ADK's OpenTelemetry instrumentation with a 2–3 line setup:

```python
# Arize AX
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from arize.otel import register
tracer_provider = register(space_id='...', api_key=os.getenv('ARIZE_API_KEY'))

# Phoenix (self-hosted, open-source)
import phoenix as px
px.launch_app()   # local dashboard at http://localhost:6006

# W&B Weave
import weave
weave.init('my-adk-project')
```

Reference: https://google.github.io/adk-docs/integrations/

## 9. Payment & Financial
- status: active
- type: guideline
- id: skill.adk_tools.payments
- last_checked: 2026-02-24
<!-- content -->

### PayPal
- status: active
- type: guideline
- id: skill.adk_tools.payments.paypal
- last_checked: 2026-02-24
<!-- content -->
Manage PayPal payments, send invoices, and handle subscriptions via the PayPal MCP server.

```python
import os

paypal_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=['-y', '@paypal/mcp-server'],
            env={
                **os.environ,
                'PAYPAL_CLIENT_ID': os.getenv('PAYPAL_CLIENT_ID'),
                'PAYPAL_CLIENT_SECRET': os.getenv('PAYPAL_CLIENT_SECRET'),
            },
        ),
    ),
    tool_filter=['create_invoice', 'send_invoice', 'get_payment', 'list_subscriptions'],
)
```

Reference: https://google.github.io/adk-docs/integrations/

## 10. Choosing the Right Tool Type
- status: active
- type: guideline
- id: skill.adk_tools.decision_guide
- last_checked: 2026-02-24
<!-- content -->
Use this decision table when adding a new capability to an agent:

| Scenario | Recommended approach |
| :--- | :--- |
| Web search or knowledge grounding | `google_search` built-in — zero config |
| Run Python or math code | `BuiltInCodeExecutor` — zero config |
| Query a GCP-managed database or data warehouse | `BigQueryToolset` — native ADK, typed GCP auth |
| Search a private knowledge corpus on GCP | `VertexAiSearchTool` or `VertexAiRagRetrieval` |
| GitHub, Stripe, Atlassian, Notion (popular SaaS) | `McpToolset` with the official MCP server for that service |
| MongoDB, Pinecone, Chroma, Qdrant (data stores) | `McpToolset` with the corresponding npm/npx server |
| 200+ SaaS platforms via one connection | `StackOne` SSE connection |
| Enterprise GCP integrations (SAP, Salesforce) | `ApplicationIntegrationToolset` |
| Custom internal API or business logic | Plain Python function in `tools=[]` |
| Monitoring agent runs | `AgentOps`, `MLflow`, or `Phoenix` — OTel plugins, not tools |

## 11. Combining Multiple Tool Types
- status: active
- type: guideline
- id: skill.adk_tools.combining
- last_checked: 2026-02-24
<!-- content -->
A single `LlmAgent` can hold all tool types simultaneously in its `tools` list, **except** for tools with a single-tool limitation (`VertexAiSearchTool`, `VertexAiRagRetrieval`, `BuiltInCodeExecutor`).

```python
from google.adk.tools import google_search
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

def get_current_time(timezone: str) -> dict:
    """Return current time in the given IANA timezone."""
    import zoneinfo, datetime
    tz = zoneinfo.ZoneInfo(timezone)
    return {"datetime": datetime.datetime.now(tz).isoformat()}

multi_tool_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='full_stack_agent',
    tools=[
        google_search,                              # built-in
        BigQueryToolset(...),                       # native ADK
        McpToolset(                                 # MCP server
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx', args=['-y', 'mongodb-mcp-server']
                )
            ),
            tool_filter=['find', 'aggregate'],
        ),
        get_current_time,                           # plain Python function
    ],
    instruction='You have access to web search, BigQuery, MongoDB, and time lookup.',
)
```

**Single-tool limitation note:** `VertexAiSearchTool`, `VertexAiRagRetrieval`, and `BuiltInCodeExecutor` must each be the only entry in the `tools` / `code_executor` parameter — they cannot be combined with others.

## 12. Quick-Reference Tool Catalogue
- status: active
- type: guideline
- id: skill.adk_tools.catalogue
- last_checked: 2026-02-24
<!-- content -->
All tools from this document in one table, sorted by category.

| # | Tool / Integration | Category | Import / Server | Key capability |
| :- | :--- | :--- | :--- | :--- |
| 1 | `google_search` | Built-in | `google.adk.tools` | Live Google Search with Gemini grounding |
| 2 | `BuiltInCodeExecutor` | Built-in | `google.adk.code_executors` | Execute Python code at runtime |
| 3 | `BigQueryToolset` | Native ADK | `google.adk.tools.bigquery` | SQL queries, schema explore, AI forecast |
| 4 | `VertexAiSearchTool` | Native ADK | `google.adk.tools` | Search private Vertex AI data stores |
| 5 | `VertexAiRagRetrieval` | Native ADK | `google.adk.tools.retrieval` | RAG corpus grounding with similarity thresholds |
| 6 | GitHub | MCP (remote) | `api.githubcopilot.com/mcp/` | Repos, issues, PRs, actions, code security |
| 7 | Stripe | MCP (stdio) | `@stripe/mcp` | Payments, invoices, customers, subscriptions |
| 8 | Atlassian | MCP (stdio→remote) | `mcp-remote + mcp.atlassian.com` | Jira issues, Confluence pages |
| 9 | MongoDB | MCP (stdio) | `mongodb-mcp-server` | Natural language DB queries, aggregations |
| 10 | Pinecone | MCP (stdio) | `@pinecone-database/mcp` | Semantic search, upsert, rerank |
| 11 | Notion | MCP (stdio) | `@notionhq/notion-mcp-server` | Pages, databases, search, comments |
| 12 | MCP Toolbox for DBs | MCP (SSE) | `toolbox-core` proxy | 30+ databases via one SSE endpoint |
| 13 | Chroma | MCP (stdio) | `chroma-mcp-server` | Local vector store, semantic search |
| 14 | Qdrant | MCP (stdio) | `qdrant-mcp-server` | Hosted/local vector store |
| 15 | Application Integration | Native ADK | `google.adk.tools.application_integration_tool` | 400+ enterprise app connectors |
| 16 | StackOne | MCP (SSE) | `mcp.stackone.com` | 200+ SaaS via unified API |
| 17 | Mailgun | MCP (stdio) | `mailgun-mcp-server` | Send email, mailing lists, delivery stats |
| 18 | ElevenLabs | MCP (stdio) | `@elevenlabs/elevenlabs-mcp` | TTS, voice cloning, transcription |
| 19 | PayPal | MCP (stdio) | `@paypal/mcp-server` | Payments, invoices, subscriptions |
| 20 | AgentOps | OTel plugin | `agentops` | Session replays, cost tracking, latency |
| 21 | MLflow | OTel plugin | `mlflow` | Trace ingestion for agent run analysis |
| 22 | Arize AX | OTel plugin | `arize-otel` | Production LLM observability |
| 23 | Phoenix | OTel plugin | `arize-phoenix` | Self-hosted open-source tracing |
| 24 | W&B Weave | OTel plugin | `weave` | Model call visualization and analysis |
