"""
End-to-end tests for REST API post endpoints

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
        "username": f"test_post_user_{int(time.time()*1000)}",
        "challenge_id": challenge["challenge_id"],
        "answer": answer
    })
    return register_resp.json()["api_key"]


@pytest.mark.asyncio
async def test_list_posts_api_e2e(api_base_url):
    """Test GET /api/posts returns list of posts"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/posts")

        assert response.status_code == 200
        data = response.json()

        # Should be a list
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_post_api_e2e(api_base_url):
    """Test POST /api/posts creates a new post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get API key
        api_key = await get_api_key(client)

        # Get categories to use a valid category_id
        categories_resp = await client.get("/api/categories")
        categories = categories_resp.json()
        assert len(categories) > 0
        category_id = categories[0]["id"]

        # Create post
        post_data = {
            "title": f"Test Post {int(time.time()*1000)}",
            "content": "This is a test post content",
            "category_id": category_id
        }
        response = await client.post(
            "/api/posts",
            json=post_data,
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["title"] == post_data["title"]
        assert data["content"] == post_data["content"]
        assert data["category_id"] == category_id
        assert "author_id" in data
        assert "created_at" in data


@pytest.mark.asyncio
async def test_create_post_without_auth_api_e2e(api_base_url):
    """Test POST /api/posts fails without authentication"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get a valid category
        categories_resp = await client.get("/api/categories")
        categories = categories_resp.json()
        category_id = categories[0]["id"]

        # Try to create without API key
        response = await client.post("/api/posts", json={
            "title": "Unauthorized Post",
            "content": "Should fail",
            "category_id": category_id
        })

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_post_api_e2e(api_base_url):
    """Test GET /api/posts/{post_id} returns single post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post first
        api_key = await get_api_key(client)
        categories = (await client.get("/api/categories")).json()
        category_id = categories[0]["id"]

        create_resp = await client.post(
            "/api/posts",
            json={
                "title": "Post to Retrieve",
                "content": "Content here",
                "category_id": category_id
            },
            headers={"X-API-Key": api_key}
        )
        post_id = create_resp.json()["id"]

        # Get the post
        response = await client.get(f"/api/posts/{post_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == post_id
        assert data["title"] == "Post to Retrieve"
        assert data["content"] == "Content here"


@pytest.mark.asyncio
async def test_update_post_api_e2e(api_base_url):
    """Test PUT /api/posts/{post_id} updates a post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        categories = (await client.get("/api/categories")).json()
        category_id = categories[0]["id"]

        create_resp = await client.post(
            "/api/posts",
            json={
                "title": "Original Title",
                "content": "Original Content",
                "category_id": category_id
            },
            headers={"X-API-Key": api_key}
        )
        post_id = create_resp.json()["id"]

        # Update the post
        response = await client.put(
            f"/api/posts/{post_id}",
            json={
                "title": "Updated Title",
                "content": "Updated Content"
            },
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == post_id
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated Content"


@pytest.mark.asyncio
async def test_update_other_user_post_api_e2e(api_base_url):
    """Test PUT /api/posts/{post_id} fails for other user's post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # User 1 creates a post
        api_key_1 = await get_api_key(client)
        categories = (await client.get("/api/categories")).json()
        category_id = categories[0]["id"]

        create_resp = await client.post(
            "/api/posts",
            json={
                "title": "User 1 Post",
                "content": "Content",
                "category_id": category_id
            },
            headers={"X-API-Key": api_key_1}
        )
        post_id = create_resp.json()["id"]

        # User 2 tries to update
        api_key_2 = await get_api_key(client)
        response = await client.put(
            f"/api/posts/{post_id}",
            json={"title": "Hacked", "content": "Hacked"},
            headers={"X-API-Key": api_key_2}
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_post_api_e2e(api_base_url):
    """Test DELETE /api/posts/{post_id} deletes a post"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a post
        api_key = await get_api_key(client)
        categories = (await client.get("/api/categories")).json()
        category_id = categories[0]["id"]

        create_resp = await client.post(
            "/api/posts",
            json={
                "title": "Post to Delete",
                "content": "Will be deleted",
                "category_id": category_id
            },
            headers={"X-API-Key": api_key}
        )
        post_id = create_resp.json()["id"]

        # Delete the post
        response = await client.delete(
            f"/api/posts/{post_id}",
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's deleted
        get_resp = await client.get(f"/api/posts/{post_id}")
        assert get_resp.status_code == 404
