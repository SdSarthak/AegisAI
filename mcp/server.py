"""
AegisAI MCP Server — wraps key AegisAI endpoints as Model Context Protocol tools.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

What is MCP?
  Model Context Protocol (MCP) lets AI assistants (editors, coding tools) call
  external services as structured tools. See https://modelcontextprotocol.io.

Features:
  - scan_prompt: Scan prompts for injection risks using AegisAI Guard
  - classify_ai_system: Classify AI systems by EU AI Act risk levels
  - query_regulations: Query regulatory knowledge base for compliance info

Configuration:
  Set environment variables:
    AEGISAI_BASE_URL (default: http://localhost:8000)
    AEGISAI_API_TOKEN (required)

Run:
  python mcp/server.py
"""

import os
import sys
import json
import httpx
from typing import Optional, Any
from pydantic import BaseModel, Field

# Configuration from environment
AEGISAI_BASE_URL = os.getenv("AEGISAI_BASE_URL", "http://localhost:8000").rstrip("/")
AEGISAI_API_TOKEN = os.getenv("AEGISAI_API_TOKEN", "")

# Verify API token is set
if not AEGISAI_API_TOKEN:
    print("ERROR: AEGISAI_API_TOKEN environment variable is not set.", file=sys.stderr)
    print("Please set AEGISAI_API_TOKEN before running the MCP server.", file=sys.stderr)
    sys.exit(1)

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent, CallToolResult
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Initialize MCP server
server = Server("aegisai")

# HTTP client for calling AegisAI backend
http_client = httpx.AsyncClient(
    base_url=AEGISAI_BASE_URL,
    headers={
        "Authorization": f"Bearer {AEGISAI_API_TOKEN}",
        "Content-Type": "application/json",
    },
    timeout=30.0,
)


# ============================================================================
# Tool 1: scan_prompt
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="scan_prompt",
            description="Scan a prompt for injection risks using AegisAI Guard. Returns a decision (allow/sanitize/block) with confidence score and matched patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt text to scan for injection risks"
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="classify_ai_system",
            description="Classify an AI system's risk level according to EU AI Act criteria. Provides risk classification, compliance requirements, and next steps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_case_category": {
                        "type": "string",
                        "description": "Category of AI system (e.g., 'hr_recruitment', 'credit_scoring', 'healthcare', 'general')"
                    },
                    "is_safety_component": {
                        "type": "boolean",
                        "description": "Whether this AI is part of a safety component of a product"
                    },
                    "affects_fundamental_rights": {
                        "type": "boolean",
                        "description": "Whether this AI affects fundamental rights (employment, education, essential services)"
                    },
                    "uses_biometric_data": {
                        "type": "boolean",
                        "description": "Whether this system uses biometric data"
                    },
                    "makes_automated_decisions": {
                        "type": "boolean",
                        "description": "Whether this system makes automated decisions without human review"
                    },
                    "hr_recruitment_screening": {
                        "type": "boolean",
                        "description": "Whether this is for CV filtering or candidate ranking"
                    },
                    "hr_promotion_termination": {
                        "type": "boolean",
                        "description": "Whether this is for promotion or termination decisions"
                    },
                    "credit_worthiness": {
                        "type": "boolean",
                        "description": "Whether this assesses creditworthiness"
                    },
                    "insurance_risk_assessment": {
                        "type": "boolean",
                        "description": "Whether this assesses insurance risk"
                    },
                    "law_enforcement": {
                        "type": "boolean",
                        "description": "Whether this is used in law enforcement"
                    },
                    "border_control": {
                        "type": "boolean",
                        "description": "Whether this is used for border control"
                    },
                    "justice_system": {
                        "type": "boolean",
                        "description": "Whether this is used in the justice system"
                    },
                    "interacts_with_humans": {
                        "type": "boolean",
                        "description": "Whether this system directly interacts with humans (e.g., chatbots)"
                    },
                    "generates_synthetic_content": {
                        "type": "boolean",
                        "description": "Whether this system generates synthetic or manipulated content"
                    },
                    "emotion_recognition": {
                        "type": "boolean",
                        "description": "Whether this system performs emotion recognition"
                    },
                    "biometric_categorization": {
                        "type": "boolean",
                        "description": "Whether this system uses biometric categorization"
                    }
                },
                "required": ["use_case_category"]
            }
        ),
        Tool(
            name="query_regulations",
            description="Query the AegisAI regulatory knowledge base to get answers about compliance, regulatory requirements, and AI governance. Grounded in regulatory documents like EU AI Act, GDPR, and ISO standards.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your compliance or regulatory question"
                    }
                },
                "required": ["question"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP client."""
    
    if name == "scan_prompt":
        return await handle_scan_prompt(arguments)
    elif name == "classify_ai_system":
        return await handle_classify_ai_system(arguments)
    elif name == "query_regulations":
        return await handle_query_regulations(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_scan_prompt(arguments: dict) -> list[TextContent]:
    """Handle scan_prompt tool call."""
    try:
        prompt = arguments.get("prompt", "")
        if not prompt:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "prompt parameter is required"})
            )]
        
        response = await http_client.post(
            "/api/v1/guard/scan",
            json={"prompt": prompt}
        )
        response.raise_for_status()
        result = response.json()
        
        # Format response for MCP client
        output = {
            "decision": result.get("decision"),
            "confidence": result.get("confidence"),
            "reasoning": result.get("reasoning"),
            "matched_patterns": result.get("matched_patterns", []),
        }
        if result.get("sanitized_prompt"):
            output["sanitized_prompt"] = result["sanitized_prompt"]
        
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    
    except httpx.HTTPStatusError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json().get("detail", error_detail)
        except:
            pass
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"API error ({e.response.status_code}): {error_detail}"})
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to call scan_prompt: {str(e)}"})
        )]


async def handle_classify_ai_system(arguments: dict) -> list[TextContent]:
    """Handle classify_ai_system tool call."""
    try:
        # Prepare request with defaults for boolean fields
        request_data = {
            "use_case_category": arguments.get("use_case_category", "general"),
            "is_safety_component": arguments.get("is_safety_component", False),
            "affects_fundamental_rights": arguments.get("affects_fundamental_rights", False),
            "uses_biometric_data": arguments.get("uses_biometric_data", False),
            "makes_automated_decisions": arguments.get("makes_automated_decisions", True),
            "hr_recruitment_screening": arguments.get("hr_recruitment_screening", False),
            "hr_promotion_termination": arguments.get("hr_promotion_termination", False),
            "credit_worthiness": arguments.get("credit_worthiness", False),
            "insurance_risk_assessment": arguments.get("insurance_risk_assessment", False),
            "law_enforcement": arguments.get("law_enforcement", False),
            "border_control": arguments.get("border_control", False),
            "justice_system": arguments.get("justice_system", False),
            "interacts_with_humans": arguments.get("interacts_with_humans", True),
            "generates_synthetic_content": arguments.get("generates_synthetic_content", False),
            "emotion_recognition": arguments.get("emotion_recognition", False),
            "biometric_categorization": arguments.get("biometric_categorization", False),
        }
        
        response = await http_client.post(
            "/api/v1/classification/classify",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        
        # Format response for MCP client
        output = {
            "risk_level": result.get("risk_level"),
            "confidence": result.get("confidence"),
            "reasons": result.get("reasons", []),
            "requirements": result.get("requirements", []),
            "next_steps": result.get("next_steps", []),
        }
        
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    
    except httpx.HTTPStatusError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json().get("detail", error_detail)
        except:
            pass
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"API error ({e.response.status_code}): {error_detail}"})
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to call classify_ai_system: {str(e)}"})
        )]


async def handle_query_regulations(arguments: dict) -> list[TextContent]:
    """Handle query_regulations tool call."""
    try:
        question = arguments.get("question", "")
        if not question:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "question parameter is required"})
            )]
        
        response = await http_client.post(
            "/api/v1/rag/query",
            json={"question": question}
        )
        response.raise_for_status()
        result = response.json()
        
        # Format response for MCP client
        output = {
            "answer": result.get("answer"),
            "sources": result.get("sources", []),
        }
        if result.get("answer_id"):
            output["answer_id"] = result["answer_id"]
        
        return [TextContent(type="text", text=json.dumps(output, indent=2))]
    
    except httpx.HTTPStatusError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json().get("detail", error_detail)
        except:
            pass
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"API error ({e.response.status_code}): {error_detail}"})
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to call query_regulations: {str(e)}"})
        )]


def main():
    """Run the MCP server with stdio transport."""
    from mcp.server.stdio import stdio_server
    
    # Run server with stdio
    stdio_server(server)


if __name__ == "__main__":
    main()
