# AegisAI MCP Server

The AegisAI MCP (Model Context Protocol) server enables AI-assisted coding tools and language models to call AegisAI endpoints as native tools. This allows seamless integration of AegisAI's compliance, guard, and regulatory intelligence features into your AI workflows.

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is a standardized protocol that lets AI assistants (like Claude in VS Code, or other AI coding tools) call external services as structured tools. MCP provides a clean abstraction over HTTP APIs, enabling AI tools to safely and reliably interact with backend services.

## Getting Started

### 1. Install Dependencies

```bash
cd mcp
pip install -r requirements.txt
```

### 2. Set Environment Variables

The MCP server requires two environment variables:

- **AEGISAI_BASE_URL**: The base URL of your AegisAI backend (default: `http://localhost:8000`)
- **AEGISAI_API_TOKEN**: Bearer token for authentication (required)

```bash
# On macOS/Linux
export AEGISAI_BASE_URL="http://localhost:8000"
export AEGISAI_API_TOKEN="your-api-token-here"

# On Windows PowerShell
$env:AEGISAI_BASE_URL = "http://localhost:8000"
$env:AEGISAI_API_TOKEN = "your-api-token-here"

# On Windows cmd
set AEGISAI_BASE_URL=http://localhost:8000
set AEGISAI_API_TOKEN=your-api-token-here
```

### 3. Start the MCP Server

```bash
python mcp/server.py
```

If successful, you'll see the server start listening for MCP client connections via stdin/stdout.

## Available Tools

The MCP server exposes three tools that AI assistants can call:

### 1. `scan_prompt`

Scan a prompt for injection risks using AegisAI Guard.

**Input:**
```json
{
  "prompt": "Your prompt text here"
}
```

**Output:**
```json
{
  "decision": "allow",
  "confidence": 0.95,
  "reasoning": "No injection patterns detected",
  "matched_patterns": [],
  "sanitized_prompt": null
}
```

**Decision Values:**
- `allow` — Prompt is safe to process
- `sanitize` — Prompt contains suspicious patterns that should be sanitized
- `block` — Prompt contains injection attempts and should be blocked

### 2. `classify_ai_system`

Classify an AI system's risk level according to EU AI Act criteria and provide compliance requirements.

**Input:**
```json
{
  "use_case_category": "hr_recruitment",
  "is_safety_component": false,
  "affects_fundamental_rights": true,
  "hr_recruitment_screening": true,
  "makes_automated_decisions": true
}
```

**Output:**
```json
{
  "risk_level": "HIGH",
  "confidence": 0.9,
  "reasons": [
    "AI systems used for recruitment, CV screening, or employment decisions are classified as HIGH risk under Annex III"
  ],
  "requirements": [
    "Implement risk management system (Article 9)",
    "Ensure data governance and quality (Article 10)",
    "Enable human oversight (Article 14)"
  ],
  "next_steps": [
    "Complete the full risk assessment questionnaire",
    "Document your AI system's technical specifications",
    "Implement a risk management system"
  ]
}
```

**Available Parameters:**
- `use_case_category` (required): Category of AI system (e.g., `hr_recruitment`, `credit_scoring`, `healthcare`)
- `is_safety_component`: Whether the AI is part of a safety component
- `affects_fundamental_rights`: Whether the AI affects fundamental rights (employment, education, essential services)
- `hr_recruitment_screening`: HR/CV screening
- `hr_promotion_termination`: Promotion/termination decisions
- `credit_worthiness`: Credit assessment
- `insurance_risk_assessment`: Insurance risk assessment
- `law_enforcement`: Used in law enforcement
- `border_control`: Used for border control
- `justice_system`: Used in the justice system
- `interacts_with_humans`: Directly interacts with humans (chatbots, etc.)
- `generates_synthetic_content`: Generates synthetic/deepfake content
- `emotion_recognition`: Uses emotion recognition
- `biometric_categorization`: Uses biometric categorization

### 3. `query_regulations`

Query the AegisAI regulatory knowledge base to get answers about compliance and regulatory requirements.

**Input:**
```json
{
  "question": "Does my CV-screening tool qualify as high-risk under the EU AI Act?"
}
```

**Output:**
```json
{
  "answer": "Yes, CV-screening tools that make automated decisions about recruitment are classified as high-risk under Annex III of the EU AI Act...",
  "sources": [
    "EU AI Act - Annex III",
    "EU AI Act - Article 6"
  ],
  "answer_id": "abc123"
}
```

## Configuring MCP Clients

### Claude for VS Code

To use the AegisAI MCP server with Claude in VS Code:

1. Open Claude for VS Code settings
2. Navigate to MCP Servers configuration
3. Add a new MCP server entry:

```json
{
  "name": "AegisAI",
  "command": "python",
  "args": ["path/to/mcp/server.py"],
  "env": {
    "AEGISAI_BASE_URL": "http://localhost:8000",
    "AEGISAI_API_TOKEN": "your-api-token-here"
  }
}
```

### Node.js / Other MCP Clients

To connect any MCP client to the server:

```bash
python mcp/server.py
```

The server communicates via stdin/stdout using the MCP protocol. Clients should spawn the server as a subprocess and communicate via JSON-RPC over these streams.

## Error Handling

### Missing API Token

If `AEGISAI_API_TOKEN` is not set, the server will exit with an error:

```
ERROR: AEGISAI_API_TOKEN environment variable is not set.
Please set AEGISAI_API_TOKEN before running the MCP server.
```

### Backend Connection Errors

If the server cannot reach the AegisAI backend, tool calls will return error messages:

```json
{
  "error": "API error (503): RAG module not ready: Run POST /rag/ingest first."
}
```

### Rate Limiting

The `/guard/scan` endpoint has rate limiting (60 requests per minute per user). If exceeded:

```json
{
  "error": "API error (429): Rate limit exceeded: 60 requests per minute per user."
}
```

## Development

### Testing the Server

You can test the server manually using MCP's Python client:

```python
import subprocess
import json

# Start server
proc = subprocess.Popen(
    ["python", "mcp/server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={"AEGISAI_API_TOKEN": "test-token"}
)

# Send MCP request to list tools
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}

proc.stdin.write(json.dumps(request).encode() + b"\n")
response = json.loads(proc.stdout.readline().decode())
print(response)
```

### Debugging

Enable verbose logging by running:

```bash
RUST_LOG=debug python mcp/server.py
```

## Architecture

The MCP server:

1. **Validates Configuration**: Checks that `AEGISAI_API_TOKEN` is set on startup
2. **Maintains HTTP Client**: Uses `httpx` to communicate with the AegisAI backend
3. **Exposes Tools**: Implements three MCP tools with proper input/output schemas
4. **Handles Errors**: Catches and formats errors from the backend API
5. **Communicates via stdio**: Uses MCP's stdio transport for client communication

## Troubleshooting

### Server won't start

- Ensure `AEGISAI_API_TOKEN` is set: `echo $AEGISAI_API_TOKEN`
- Check that Python 3.8+ is installed: `python --version`
- Verify dependencies: `pip list | grep mcp`

### MCP client can't connect

- Ensure the server is running: `ps aux | grep mcp/server.py`
- Check the base URL is correct: `curl http://localhost:8000/api/v1/health` (or your configured URL)
- Verify the API token has permissions for the required endpoints

### Tool calls failing

- Check AegisAI backend logs: `tail -f backend/logs/app.log`
- Verify the backend is running: `ps aux | grep uvicorn`
- Test endpoints manually: `curl -H "Authorization: Bearer $AEGISAI_API_TOKEN" http://localhost:8000/api/v1/guard/scan -d '{"prompt":"test"}'`

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to the MCP server.

## License

Copyright (C) 2024 Sarthak Doshi  
SPDX-License-Identifier: AGPL-3.0-only
