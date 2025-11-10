"""
End-to-end tests for REST API vote endpoints

Requires:
- PostgreSQL running in Docker
- MCP server running: python main.py

Tests the complete stack: HTTP → REST API → Service → Repository → PostgreSQL
"""
import pytest
import httpx
import time
from .challenge_solver import solve_challenge


async def get_api_key(client):
    """Helper to get an API key for authenticated requests"""
    # Get challenge
    challenge_resp = await client.get("/api/auth/challenge")
    challenge = challenge_resp.json()

    # Solve and register
    answer = solve_challenge(challenge["question"], challenge["challenge_type"])
    register_resp = await client.post("/api/auth/register", json={
        "username": f"test_vote_user_{int(time.time()*1000)}",
        "challenge_id": challenge["challenge_id"],
        "answer": answer
    })
    return register_resp.json()["api_key"]


async def create_test_post(client, api_key):
    """Helper to create a test post"""
    categories = (await client.get("/api/categories")).json()
    category_id = categories[0]["id"]

    create_resp = await client.post(
        "/api/posts",
        json={
            "title": f"Test Post {int(time.time()*1000)}",
            "content": "Test content",
            "category_id": category_id
        },
        headers={"X-API-Key": api_key}
    )
    return create_resp.json()["id"]


async def create_test_reply(client, api_key, post_id):
    """Helper to create a test reply"""
    create_resp = await client.post(
        f"/api/posts/{post_id}/replies",
        json={"content": "Test reply"},
        headers={"X-API-Key": api_key}
    )
    return create_resp.json()["id"]


@pytest.mark.asyncio
async def test_vote_on_post_upvote_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/vote with upvote"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Upvote the post
        response = await client.post(
            f"/api/posts/{post_id}/vote",
            json={"vote_type": 1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_vote_on_post_downvote_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/vote with downvote"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Downvote the post
        response = await client.post(
            f"/api/posts/{post_id}/vote",
            json={"vote_type": -1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_vote_on_post_invalid_vote_type_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/vote with invalid vote type"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Try to vote with invalid vote type
        response = await client.post(
            f"/api/posts/{post_id}/vote",
            json={"vote_type": 0},  # Invalid - must be 1 or -1
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 400
        assert "Vote type must be" in response.json()["detail"]


@pytest.mark.asyncio
async def test_vote_on_post_without_auth_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/vote fails without authentication"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Try to vote without API key
        response = await client.post(
            f"/api/posts/{post_id}/vote",
            json={"vote_type": 1}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_vote_on_nonexistent_post_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/vote with nonexistent post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get an API key
        api_key = await get_api_key(client)

        # Try to vote on nonexistent post
        response = await client.post(
            "/api/posts/999999/vote",
            json={"vote_type": 1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_vote_on_reply_upvote_api_e2e(api_base_url):
    """Test POST /api/replies/{reply_id}/vote with upvote"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post and reply
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)
        reply_id = await create_test_reply(client, api_key, post_id)

        # Upvote the reply
        response = await client.post(
            f"/api/replies/{reply_id}/vote",
            json={"vote_type": 1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_vote_on_reply_downvote_api_e2e(api_base_url):
    """Test POST /api/replies/{reply_id}/vote with downvote"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post and reply
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)
        reply_id = await create_test_reply(client, api_key, post_id)

        # Downvote the reply
        response = await client.post(
            f"/api/replies/{reply_id}/vote",
            json={"vote_type": -1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_vote_on_reply_without_auth_api_e2e(api_base_url):
    """Test POST /api/replies/{reply_id}/vote fails without authentication"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post and reply
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)
        reply_id = await create_test_reply(client, api_key, post_id)

        # Try to vote without API key
        response = await client.post(
            f"/api/replies/{reply_id}/vote",
            json={"vote_type": 1}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_vote_on_nonexistent_reply_api_e2e(api_base_url):
    """Test POST /api/replies/{reply_id}/vote with nonexistent reply"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get an API key
        api_key = await get_api_key(client)

        # Try to vote on nonexistent reply
        response = await client.post(
            "/api/replies/999999/vote",
            json={"vote_type": 1},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 404
