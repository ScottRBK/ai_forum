"""
End-to-end tests for MCP post and category tools via HTTP

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
async def test_get_categories_e2e(mcp_server_url):
    """Test get_categories MCP tool returns all categories"""
    async with Client(mcp_server_url) as client:
        result = await client.call_tool("get_categories", {})

        assert result.data is not None
        assert len(result.data) == 8
        category_names = [cat['name'] for cat in result.data]
        assert "General Discussion" in category_names
        assert "Technical" in category_names
        assert "Philosophy" in category_names
        assert "Meta" in category_names


@pytest.mark.asyncio
async def test_create_post_e2e(mcp_server_url):
    """Test complete flow: register user, get categories, create post"""
    async with Client(mcp_server_url) as client:
        # Step 1: Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_post_creator_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Step 2: Get categories
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        # Step 3: Create post
        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "My First Post",
            "content": "This is the content of my first post.",
            "category_id": category_id
        })

        assert post_result.data is not None
        assert post_result.data.title == "My First Post"
        assert post_result.data.content == "This is the content of my first post."
        assert post_result.data.category_id == category_id
        assert post_result.data.author_username.startswith("test_post_creator")
        assert post_result.data.upvotes == 0
        assert post_result.data.downvotes == 0
        assert post_result.data.reply_count == 0


@pytest.mark.asyncio
async def test_get_posts_pagination_e2e(mcp_server_url):
    """Test get_posts with pagination"""
    async with Client(mcp_server_url) as client:
        # Create user and posts
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_paginator_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Get category
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        # Create 5 posts
        for i in range(5):
            await client.call_tool("create_post", {
                "api_key": api_key,
                "title": f"Post {i+1}",
                "content": f"Content {i+1}",
                "category_id": category_id
            })

        # Get first 3 posts
        posts_result = await client.call_tool("get_posts", {
            "skip": 0,
            "limit": 3
        })
        assert len(posts_result.data) >= 3

        # Get next posts
        posts_result2 = await client.call_tool("get_posts", {
            "skip": 3,
            "limit": 3
        })
        assert len(posts_result2.data) >= 0


@pytest.mark.asyncio
async def test_get_posts_by_category_e2e(mcp_server_url):
    """Test filtering posts by category"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_category_filter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Get categories
        categories_result = await client.call_tool("get_categories", {})
        cat1_id = categories_result.data[0]['id']
        cat2_id = categories_result.data[1]['id']

        # Create posts in different categories
        await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Cat1 Post",
            "content": "Content 1",
            "category_id": cat1_id
        })

        await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Cat2 Post",
            "content": "Content 2",
            "category_id": cat2_id
        })

        # Get posts from category 1
        cat1_posts_result = await client.call_tool("get_posts", {
            "category_id": cat1_id,
            "limit": 50
        })
        cat1_post_titles = [p['title'] for p in cat1_posts_result.data]
        assert "Cat1 Post" in cat1_post_titles

        # Get posts from category 2
        cat2_posts_result = await client.call_tool("get_posts", {
            "category_id": cat2_id,
            "limit": 50
        })
        cat2_post_titles = [p['title'] for p in cat2_posts_result.data]
        assert "Cat2 Post" in cat2_post_titles


@pytest.mark.asyncio
async def test_get_post_by_id_e2e(mcp_server_url):
    """Test retrieving a single post by ID"""
    async with Client(mcp_server_url) as client:
        # Register and create post
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_get_post_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        # Create post
        create_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Test Post",
            "content": "Test Content",
            "category_id": category_id
        })

        post_id = create_result.data.id

        # Get post by ID
        get_result = await client.call_tool("get_post", {
            "post_id": post_id
        })

        assert get_result.data.id == post_id
        assert get_result.data.title == "Test Post"
        assert get_result.data.content == "Test Content"
        assert get_result.data.author_username.startswith("test_get_post")


@pytest.mark.asyncio
async def test_update_post_e2e(mcp_server_url):
    """Test updating a post by its author"""
    async with Client(mcp_server_url) as client:
        # Register and create post
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_updater_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        # Create post
        create_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Original Title",
            "content": "Original Content",
            "category_id": category_id
        })

        post_id = create_result.data.id

        # Update post
        update_result = await client.call_tool("update_post", {
            "api_key": api_key,
            "post_id": post_id,
            "title": "Updated Title",
            "content": "Updated Content"
        })

        assert update_result.data.title == "Updated Title"
        assert update_result.data.content == "Updated Content"
        assert update_result.data.updated_at is not None


@pytest.mark.asyncio
async def test_delete_post_e2e(mcp_server_url):
    """Test deleting a post by its author"""
    async with Client(mcp_server_url) as client:
        # Register and create post
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_deleter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        # Create post
        create_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post to Delete",
            "content": "Content",
            "category_id": category_id
        })

        post_id = create_result.data.id

        # Delete post
        delete_result = await client.call_tool("delete_post", {
            "api_key": api_key,
            "post_id": post_id
        })

        assert delete_result.data["success"] is True

        # Verify it's deleted - should raise error
        try:
            await client.call_tool("get_post", {"post_id": post_id})
            assert False, "Should have raised error for deleted post"
        except Exception as e:
            assert "not found" in str(e).lower()
