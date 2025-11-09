"""
End-to-end tests for MCP reply tools via HTTP

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
async def test_create_reply_e2e(mcp_server_url):
    """Test creating a reply to a post"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_replier_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Test Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # Create reply
        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "This is my reply"
        })

        assert reply_result.data is not None
        assert reply_result.data.content == "This is my reply"
        assert reply_result.data.post_id == post_id
        assert reply_result.data.author_username.startswith("test_replier")
        assert reply_result.data.parent_reply_id is None
        assert reply_result.data.upvotes == 0
        assert reply_result.data.downvotes == 0


@pytest.mark.asyncio
async def test_create_threaded_reply_e2e(mcp_server_url):
    """Test creating a threaded reply (reply to a reply)"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_threader_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # Create parent reply
        parent_reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Parent reply"
        })

        parent_reply_id = parent_reply_result.data.id

        # Create child reply
        child_reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Child reply",
            "parent_reply_id": parent_reply_id
        })

        assert child_reply_result.data.parent_reply_id == parent_reply_id


@pytest.mark.asyncio
async def test_get_replies_no_exclusion_e2e(mcp_server_url):
    """Test getting all replies without authentication (no exclusion)"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_getter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # Create multiple replies
        for i in range(3):
            await client.call_tool("create_reply", {
                "api_key": api_key,
                "post_id": post_id,
                "content": f"Reply {i+1}"
            })

        # Get all replies without authentication (no exclusion)
        replies_result = await client.call_tool("get_replies", {
            "post_id": post_id
        })

        assert len(replies_result.data) == 3
        reply_contents = [r['content'] for r in replies_result.data]
        assert "Reply 1" in reply_contents
        assert "Reply 2" in reply_contents
        assert "Reply 3" in reply_contents


@pytest.mark.asyncio
async def test_get_replies_with_exclusion_e2e(mcp_server_url):
    """Test the key feature: excluding author's own replies when authenticated"""
    async with Client(mcp_server_url) as client:
        # Register two users
        challenge1 = await client.call_tool("request_challenge", {})
        challenge1_id = challenge1.data.challenge_id
        question1 = challenge1.data.question
        challenge1_type = challenge1.data.challenge_type

        answer1 = solve_challenge(question1, challenge1_type)

        register1 = await client.call_tool("register_user", {
            "username": f"user1_reply_exclude_{int(time.time()*1000)}",
            "challenge_id": challenge1_id,
            "answer": answer1
        })

        if not register1.data:
            pytest.skip("Challenge answer incorrect - skipping test")

        user1_api_key = register1.data.api_key

        # Register second user
        challenge2 = await client.call_tool("request_challenge", {})
        challenge2_id = challenge2.data.challenge_id
        question2 = challenge2.data.question
        challenge2_type = challenge2.data.challenge_type

        answer2 = solve_challenge(question2, challenge2_type)

        register2 = await client.call_tool("register_user", {
            "username": f"user2_reply_exclude_{int(time.time()*1000)}",
            "challenge_id": challenge2_id,
            "answer": answer2
        })

        if not register2.data:
            pytest.skip("Challenge answer incorrect - skipping test")

        user2_api_key = register2.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": user1_api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # User1 creates 2 replies
        await client.call_tool("create_reply", {
            "api_key": user1_api_key,
            "post_id": post_id,
            "content": "User1 reply 1"
        })

        await client.call_tool("create_reply", {
            "api_key": user1_api_key,
            "post_id": post_id,
            "content": "User1 reply 2"
        })

        # User2 creates 1 reply
        await client.call_tool("create_reply", {
            "api_key": user2_api_key,
            "post_id": post_id,
            "content": "User2 reply"
        })

        # Get all replies (no authentication - should see all 3)
        all_replies_result = await client.call_tool("get_replies", {
            "post_id": post_id
        })
        assert len(all_replies_result.data) == 3

        # Get replies with user1's api_key (should exclude user1's replies)
        user1_view_result = await client.call_tool("get_replies", {
            "post_id": post_id,
            "api_key": user1_api_key
        })
        assert len(user1_view_result.data) == 1
        assert user1_view_result.data[0]['content'] == "User2 reply"
        assert user1_view_result.data[0]['author_username'].startswith("user2_reply_exclude")

        # Get replies with user2's api_key (should exclude user2's replies)
        user2_view_result = await client.call_tool("get_replies", {
            "post_id": post_id,
            "api_key": user2_api_key
        })
        assert len(user2_view_result.data) == 2
        reply_contents = [r['content'] for r in user2_view_result.data]
        assert "User1 reply 1" in reply_contents
        assert "User1 reply 2" in reply_contents


@pytest.mark.asyncio
async def test_update_reply_e2e(mcp_server_url):
    """Test updating a reply by its author"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_editor_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # Create reply
        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Original content"
        })

        reply_id = reply_result.data.id

        # Update reply
        update_result = await client.call_tool("update_reply", {
            "api_key": api_key,
            "reply_id": reply_id,
            "content": "Updated content"
        })

        assert update_result.data.content == "Updated content"
        assert update_result.data.updated_at is not None


@pytest.mark.asyncio
async def test_delete_reply_e2e(mcp_server_url):
    """Test deleting a reply by its author"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_deleter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        # Create reply
        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "To be deleted"
        })

        reply_id = reply_result.data.id

        # Delete reply
        delete_result = await client.call_tool("delete_reply", {
            "api_key": api_key,
            "reply_id": reply_id
        })

        assert delete_result.data["success"] is True

        # Verify reply was deleted - getting replies should show 0
        replies_result = await client.call_tool("get_replies", {
            "post_id": post_id
        })
        assert len(replies_result.data) == 0
