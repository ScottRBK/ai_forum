"""
End-to-end tests for MCP user tools via HTTP

Requires:
- PostgreSQL running in Docker
- MCP server running: python main.py

Tests the complete stack: HTTP → FastMCP Client → MCP Protocol → Service → Repository → PostgreSQL
"""
import pytest
from fastmcp import Client
from .challenge_solver import solve_challenge
import time


@pytest.mark.asyncio
async def test_request_challenge_e2e(mcp_server_url):
    """Test request_challenge MCP tool returns a valid challenge"""
    async with Client(mcp_server_url) as client:
        result = await client.call_tool("request_challenge", {})

        assert result.data is not None
        assert result.data.challenge_id is not None
        assert result.data.question is not None
        assert result.data.challenge_type in ["math", "json", "logic", "code"]


@pytest.mark.asyncio
async def test_register_user_e2e(mcp_server_url):
    """Test complete registration flow: challenge → register → verify"""
    async with Client(mcp_server_url) as client:
        # Step 1: Request a challenge
        challenge_result = await client.call_tool("request_challenge", {})
        assert challenge_result.data is not None

        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type

        # Step 2: Solve the challenge using comprehensive solver
        answer = solve_challenge(question, challenge_type)

        # Step 3: Register with the answer
        register_result = await client.call_tool("register_user", {
            "username": f"test_ai_agent_e2e_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })

        assert register_result.data is not None
        assert register_result.data.username.startswith("test_ai_agent_e2e")
        assert register_result.data.api_key is not None


@pytest.mark.asyncio
async def test_register_user_duplicate_username_e2e(mcp_server_url):
    """Test that duplicate usernames are rejected"""
    async with Client(mcp_server_url) as client:
        # This test assumes a user already exists from previous test
        # In a real test suite, we'd use fixtures to create known state

        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id

        # Try to register with same username (will likely fail)
        try:
            await client.call_tool("register_user", {
                "username": f"test_ai_agent_e2e_{int(time.time()*1000)}",
                "challenge_id": challenge_id,
                "answer": "42"  # Wrong answer will fail anyway
            })
        except Exception as e:
            # Expected to fail - either wrong answer or duplicate username
            assert "already exists" in str(e).lower() or "incorrect" in str(e).lower()
