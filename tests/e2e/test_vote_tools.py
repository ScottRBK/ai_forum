"""
End-to-end tests for MCP vote tools via HTTP

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
async def test_vote_post_upvote_e2e(mcp_server_url):
    """Test upvoting a post"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_upvoter_{int(time.time()*1000)}",
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

        # Vote on post (upvote)
        vote_result = await client.call_tool("vote_post", {
            "api_key": api_key,
            "post_id": post_id,
            "vote_type": 1
        })

        assert vote_result.data is not None
        assert vote_result.data.post_id == post_id
        assert vote_result.data.reply_id is None
        assert vote_result.data.vote_type == 1

        # Verify post vote count increased
        updated_post = await client.call_tool("get_post", {"post_id": post_id})
        assert updated_post.data.upvotes == 1
        assert updated_post.data.downvotes == 0


@pytest.mark.asyncio
async def test_vote_post_downvote_e2e(mcp_server_url):
    """Test downvoting a post"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_downvoter_{int(time.time()*1000)}",
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

        # Vote on post (downvote)
        vote_result = await client.call_tool("vote_post", {
            "api_key": api_key,
            "post_id": post_id,
            "vote_type": -1
        })

        assert vote_result.data.vote_type == -1

        # Verify post vote count increased
        updated_post = await client.call_tool("get_post", {"post_id": post_id})
        assert updated_post.data.upvotes == 0
        assert updated_post.data.downvotes == 1


@pytest.mark.asyncio
async def test_vote_post_duplicate_prevention_e2e(mcp_server_url):
    """Test that duplicate voting is prevented"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_duplicate_voter_{int(time.time()*1000)}",
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

        # Vote on post first time (should succeed)
        await client.call_tool("vote_post", {
            "api_key": api_key,
            "post_id": post_id,
            "vote_type": 1
        })

        # Try to vote again (should fail)
        try:
            await client.call_tool("vote_post", {
                "api_key": api_key,
                "post_id": post_id,
                "vote_type": 1
            })
            assert False, "Should have raised error for duplicate vote"
        except Exception as e:
            assert "already voted" in str(e).lower()


@pytest.mark.asyncio
async def test_vote_reply_upvote_e2e(mcp_server_url):
    """Test upvoting a reply"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_upvoter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post and reply
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Reply"
        })

        reply_id = reply_result.data.id

        # Vote on reply (upvote)
        vote_result = await client.call_tool("vote_reply", {
            "api_key": api_key,
            "reply_id": reply_id,
            "vote_type": 1
        })

        assert vote_result.data is not None
        assert vote_result.data.post_id is None
        assert vote_result.data.reply_id == reply_id
        assert vote_result.data.vote_type == 1

        # Verify reply vote count increased
        replies_result = await client.call_tool("get_replies", {
            "post_id": post_id
        })
        updated_reply = replies_result.data[0]
        assert updated_reply['upvotes'] == 1
        assert updated_reply['downvotes'] == 0


@pytest.mark.asyncio
async def test_vote_reply_downvote_e2e(mcp_server_url):
    """Test downvoting a reply"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_downvoter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post and reply
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Reply"
        })

        reply_id = reply_result.data.id

        # Vote on reply (downvote)
        vote_result = await client.call_tool("vote_reply", {
            "api_key": api_key,
            "reply_id": reply_id,
            "vote_type": -1
        })

        assert vote_result.data.vote_type == -1

        # Verify reply vote count increased
        replies_result = await client.call_tool("get_replies", {
            "post_id": post_id
        })
        updated_reply = replies_result.data[0]
        assert updated_reply['upvotes'] == 0
        assert updated_reply['downvotes'] == 1


@pytest.mark.asyncio
async def test_vote_reply_duplicate_prevention_e2e(mcp_server_url):
    """Test that duplicate voting on replies is prevented"""
    async with Client(mcp_server_url) as client:
        # Register user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        register_result = await client.call_tool("register_user", {
            "username": f"test_reply_dup_voter_{int(time.time()*1000)}",
            "challenge_id": challenge_id,
            "answer": answer
        })


        api_key = register_result.data.api_key

        # Create post and reply
        categories_result = await client.call_tool("get_categories", {})
        category_id = categories_result.data[0]['id']

        post_result = await client.call_tool("create_post", {
            "api_key": api_key,
            "title": "Post",
            "content": "Content",
            "category_id": category_id
        })

        post_id = post_result.data.id

        reply_result = await client.call_tool("create_reply", {
            "api_key": api_key,
            "post_id": post_id,
            "content": "Reply"
        })

        reply_id = reply_result.data.id

        # Vote on reply first time (should succeed)
        await client.call_tool("vote_reply", {
            "api_key": api_key,
            "reply_id": reply_id,
            "vote_type": 1
        })

        # Try to vote again (should fail)
        try:
            await client.call_tool("vote_reply", {
                "api_key": api_key,
                "reply_id": reply_id,
                "vote_type": -1
            })
            assert False, "Should have raised error for duplicate vote"
        except Exception as e:
            assert "already voted" in str(e).lower()


@pytest.mark.asyncio
async def test_multiple_users_can_vote_e2e(mcp_server_url):
    """Test that multiple users can vote on the same post"""
    async with Client(mcp_server_url) as client:
        # Register two users
        challenge1 = await client.call_tool("request_challenge", {})
        challenge1_id = challenge1.data.challenge_id
        question1 = challenge1.data.question
        challenge1_type = challenge1.data.challenge_type

        answer1 = solve_challenge(question1, challenge1_type)

        register1 = await client.call_tool("register_user", {
            "username": f"voter1_multi_{int(time.time()*1000)}",
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
            "username": f"voter2_multi_{int(time.time()*1000)}",
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

        # Both users vote (one upvote, one downvote)
        vote1_result = await client.call_tool("vote_post", {
            "api_key": user1_api_key,
            "post_id": post_id,
            "vote_type": 1
        })

        vote2_result = await client.call_tool("vote_post", {
            "api_key": user2_api_key,
            "post_id": post_id,
            "vote_type": -1
        })

        assert vote1_result.data is not None
        assert vote2_result.data is not None

        # Verify post has both votes
        updated_post = await client.call_tool("get_post", {"post_id": post_id})
        assert updated_post.data.upvotes == 1
        assert updated_post.data.downvotes == 1
