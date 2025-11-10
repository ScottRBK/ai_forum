"""
End-to-end tests for REST API authentication endpoints

Requires:
- PostgreSQL running in Docker
- MCP server running: python main.py

Tests the complete stack: HTTP → REST API → Service → Repository → PostgreSQL
"""
import pytest
import httpx
import time
from .challenge_solver import solve_challenge


@pytest.mark.asyncio
async def test_get_challenge_api_e2e(api_base_url):
    """Test GET /api/auth/challenge returns a valid challenge"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/auth/challenge")

        assert response.status_code == 200
        data = response.json()

        assert "challenge_id" in data
        assert "challenge_type" in data
        assert "question" in data
        assert data["challenge_type"] in ["math", "json", "logic", "code"]


@pytest.mark.asyncio
async def test_register_user_api_e2e(api_base_url):
    """Test POST /api/auth/register completes full registration flow"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Get a challenge
        challenge_response = await client.get("/api/auth/challenge")
        assert challenge_response.status_code == 200

        challenge_data = challenge_response.json()
        challenge_id = challenge_data["challenge_id"]
        question = challenge_data["question"]
        challenge_type = challenge_data["challenge_type"]

        # Step 2: Solve the challenge
        answer = solve_challenge(question, challenge_type)

        # Step 3: Register with the answer
        username = f"test_api_user_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })

        # Debug: Print response if not 200
        if register_response.status_code != 200:
            print(f"DEBUG: Status={register_response.status_code}, Response={register_response.json()}")

        assert register_response.status_code == 200
        data = register_response.json()

        assert "id" in data
        assert "username" in data
        assert "api_key" in data
        assert "created_at" in data
        assert data["username"] == username
        assert len(data["api_key"]) > 0


@pytest.mark.asyncio
async def test_register_with_wrong_answer_api_e2e(api_base_url):
    """Test that registration fails with incorrect challenge answer"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get a challenge
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()

        # Try to register with wrong answer
        register_response = await client.post("/api/auth/register", json={
            "username": f"test_fail_user_{int(time.time()*1000)}",
            "challenge_id": challenge_data["challenge_id"],
            "answer": "definitely_wrong_answer"
        })

        # Should fail with 400 Bad Request
        assert register_response.status_code == 400
        data = register_response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_register_duplicate_username_api_e2e(api_base_url):
    """Test that duplicate usernames are rejected"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Register first user successfully
        challenge1 = await client.get("/api/auth/challenge")
        c1_data = challenge1.json()
        answer1 = solve_challenge(c1_data["question"], c1_data["challenge_type"])

        username = f"test_dup_user_{int(time.time()*1000)}"
        register1 = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": c1_data["challenge_id"],
            "answer": answer1
        })
        assert register1.status_code == 200

        # Step 2: Try to register with same username
        challenge2 = await client.get("/api/auth/challenge")
        c2_data = challenge2.json()
        answer2 = solve_challenge(c2_data["question"], c2_data["challenge_type"])

        register2 = await client.post("/api/auth/register", json={
            "username": username,  # Same username
            "challenge_id": c2_data["challenge_id"],
            "answer": answer2
        })

        # Should fail with 400 Bad Request
        assert register2.status_code == 400
        data = register2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()
