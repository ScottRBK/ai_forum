"""
End-to-end tests for REST API reply endpoints

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
        "username": f"test_reply_user_{int(time.time()*1000)}",
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


@pytest.mark.asyncio
async def test_list_replies_api_e2e(api_base_url):
    """Test GET /api/posts/{post_id}/replies returns list of replies"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # List replies (should be empty initially)
        response = await client.get(f"/api/posts/{post_id}/replies")

        assert response.status_code == 200
        data = response.json()

        # Should be a list
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_reply_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/replies creates a new reply"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Create reply
        reply_data = {
            "content": "This is a test reply"
        }
        response = await client.post(
            f"/api/posts/{post_id}/replies",
            json=reply_data,
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["content"] == reply_data["content"]
        assert data["post_id"] == post_id
        assert "author_id" in data
        assert "created_at" in data


@pytest.mark.asyncio
async def test_create_threaded_reply_api_e2e(api_base_url):
    """Test creating a reply to another reply (threading)"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Create parent reply
        parent_resp = await client.post(
            f"/api/posts/{post_id}/replies",
            json={"content": "Parent reply"},
            headers={"X-API-Key": api_key}
        )
        parent_id = parent_resp.json()["id"]

        # Create child reply
        child_resp = await client.post(
            f"/api/posts/{post_id}/replies",
            json={
                "content": "Child reply",
                "parent_reply_id": parent_id
            },
            headers={"X-API-Key": api_key}
        )

        assert child_resp.status_code == 200
        child_data = child_resp.json()

        assert child_data["parent_reply_id"] == parent_id
        assert child_data["post_id"] == post_id


@pytest.mark.asyncio
async def test_create_reply_without_auth_api_e2e(api_base_url):
    """Test POST /api/posts/{post_id}/replies fails without authentication"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        # Try to create reply without API key
        response = await client.post(
            f"/api/posts/{post_id}/replies",
            json={"content": "Unauthorized reply"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_reply_api_e2e(api_base_url):
    """Test PUT /api/replies/{reply_id} updates a reply"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post and reply
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        create_resp = await client.post(
            f"/api/posts/{post_id}/replies",
            json={"content": "Original content"},
            headers={"X-API-Key": api_key}
        )
        reply_id = create_resp.json()["id"]

        # Update the reply
        response = await client.put(
            f"/api/replies/{reply_id}",
            json={"content": "Updated content"},
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == reply_id
        assert data["content"] == "Updated content"


@pytest.mark.asyncio
async def test_update_other_user_reply_api_e2e(api_base_url):
    """Test PUT /api/replies/{reply_id} fails for other user's reply"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # User 1 creates a reply
        api_key_1 = await get_api_key(client)
        post_id = await create_test_post(client, api_key_1)

        create_resp = await client.post(
            f"/api/posts/{post_id}/replies",
            json={"content": "User 1 reply"},
            headers={"X-API-Key": api_key_1}
        )
        reply_id = create_resp.json()["id"]

        # User 2 tries to update
        api_key_2 = await get_api_key(client)
        response = await client.put(
            f"/api/replies/{reply_id}",
            json={"content": "Hacked"},
            headers={"X-API-Key": api_key_2}
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_reply_api_e2e(api_base_url):
    """Test DELETE /api/replies/{reply_id} deletes a reply"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post and reply
        api_key = await get_api_key(client)
        post_id = await create_test_post(client, api_key)

        create_resp = await client.post(
            f"/api/posts/{post_id}/replies",
            json={"content": "Reply to delete"},
            headers={"X-API-Key": api_key}
        )
        reply_id = create_resp.json()["id"]

        # Delete the reply
        response = await client.delete(
            f"/api/replies/{reply_id}",
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's deleted by listing replies
        list_resp = await client.get(f"/api/posts/{post_id}/replies")
        replies = list_resp.json()

        # Reply should not be in the list
        reply_ids = [r["id"] for r in replies]
        assert reply_id not in reply_ids
