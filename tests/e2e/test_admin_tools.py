"""
End-to-end tests for MCP admin tools via HTTP

Requires:
- PostgreSQL running in Docker with test_admin user created
- MCP server running: python main.py
- Admin user in database:
  INSERT INTO users (username, api_key, verification_score, is_admin, is_banned, created_at)
  VALUES ('test_admin', 'test_admin_key_12345', 1, TRUE, FALSE, NOW())

Tests the complete stack: HTTP → FastMCP Client → MCP Protocol → Service → Repository → PostgreSQL
"""
import pytest
from fastmcp import Client
from .challenge_solver import solve_challenge
import time


# Test admin API key (must match the DB)
TEST_ADMIN_API_KEY = "test_admin_key_12345"


@pytest.mark.asyncio
async def test_ban_user_e2e(mcp_server_url):
    """Test ban_user MCP tool - admin bans a regular user"""
    async with Client(mcp_server_url) as client:
        # Step 1: Create a regular user to ban
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        username = f"test_user_to_ban_{int(time.time()*1000)}"
        register_result = await client.call_tool("register_user", {
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })
        user_id = register_result.data.id

        # Step 2: Admin bans the user
        ban_result = await client.call_tool("ban_user", {
            "api_key": TEST_ADMIN_API_KEY,
            "target_user_id": user_id,
            "reason": "Test ban for e2e testing"
        })

        assert ban_result.data is not None
        assert ban_result.data["success"] is True
        assert ban_result.data["message"] is not None
        assert "banned" in ban_result.data["message"].lower()
        assert ban_result.data["banned_user"] is not None
        assert ban_result.data["banned_user"]["id"] == user_id
        assert ban_result.data["banned_user"]["username"] == username
        assert ban_result.data["banned_user"]["ban_reason"] == "Test ban for e2e testing"


@pytest.mark.asyncio
async def test_unban_user_e2e(mcp_server_url):
    """Test unban_user MCP tool - admin unbans a banned user"""
    async with Client(mcp_server_url) as client:
        # Step 1: Create and ban a user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        username = f"test_user_to_unban_{int(time.time()*1000)}"
        register_result = await client.call_tool("register_user", {
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })
        user_id = register_result.data.id

        # Ban the user
        await client.call_tool("ban_user", {
            "api_key": TEST_ADMIN_API_KEY,
            "target_user_id": user_id,
            "reason": "Temporary test ban"
        })

        # Step 2: Admin unbans the user
        unban_result = await client.call_tool("unban_user", {
            "api_key": TEST_ADMIN_API_KEY,
            "target_user_id": user_id
        })

        assert unban_result.data is not None
        assert unban_result.data["success"] is True
        assert "unbanned" in unban_result.data["message"].lower()
        assert unban_result.data["user"] is not None
        assert unban_result.data["user"]["id"] == user_id
        assert unban_result.data["user"]["is_banned"] is False


@pytest.mark.asyncio
async def test_get_all_users_e2e(mcp_server_url):
    """Test get_all_users MCP tool - admin lists all users"""
    async with Client(mcp_server_url) as client:
        # Get all users as admin
        result = await client.call_tool("get_all_users", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 0,
            "limit": 50
        })

        assert result.data is not None
        assert result.data["users"] is not None
        assert isinstance(result.data["users"], list)
        assert result.data["count"] > 0  # Should have at least the admin user

        # Check that users have required fields
        if len(result.data["users"]) > 0:
            user = result.data["users"][0]
            assert "id" in user
            assert "username" in user
            assert "is_admin" in user
            assert "is_banned" in user
            assert "created_at" in user


@pytest.mark.asyncio
async def test_get_all_users_pagination_e2e(mcp_server_url):
    """Test get_all_users pagination parameters"""
    async with Client(mcp_server_url) as client:
        # Get first page
        result1 = await client.call_tool("get_all_users", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 0,
            "limit": 2
        })

        # Get second page
        result2 = await client.call_tool("get_all_users", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 2,
            "limit": 2
        })

        assert result1.data["skip"] == 0
        assert result1.data["limit"] == 2
        assert result2.data["skip"] == 2
        assert result2.data["limit"] == 2


@pytest.mark.asyncio
async def test_get_audit_logs_e2e(mcp_server_url):
    """Test get_audit_logs MCP tool - admin views audit trail"""
    async with Client(mcp_server_url) as client:
        # Create and ban a user to generate audit logs
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        username = f"test_user_audit_{int(time.time()*1000)}"
        register_result = await client.call_tool("register_user", {
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })
        user_id = register_result.data.id

        # Ban user (creates audit log)
        await client.call_tool("ban_user", {
            "api_key": TEST_ADMIN_API_KEY,
            "target_user_id": user_id,
            "reason": "Test ban for audit log"
        })

        # Get audit logs
        result = await client.call_tool("get_audit_logs", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 0,
            "limit": 50
        })

        assert result.data is not None
        assert result.data["audit_logs"] is not None
        assert isinstance(result.data["audit_logs"], list)
        assert result.data["count"] > 0  # Should have at least one log

        # Find the ban_user action we just created
        ban_logs = [
            log for log in result.data["audit_logs"]
            if log["action"] == "ban_user" and log["target_id"] == user_id
        ]
        assert len(ban_logs) > 0

        log = ban_logs[0]
        assert log["target_type"] == "user"
        assert log["target_id"] == user_id
        assert "Test ban for audit log" in log["details"]


@pytest.mark.asyncio
async def test_get_audit_logs_filter_by_admin_e2e(mcp_server_url):
    """Test get_audit_logs with admin_id filter"""
    async with Client(mcp_server_url) as client:
        # Get audit logs without filter
        result_all = await client.call_tool("get_audit_logs", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 0,
            "limit": 50
        })

        # Get audit logs filtered by admin (assuming admin_id=1)
        result_filtered = await client.call_tool("get_audit_logs", {
            "api_key": TEST_ADMIN_API_KEY,
            "skip": 0,
            "limit": 50,
            "admin_id": 1  # Assuming test_admin has id=1
        })

        assert result_all.data["filtered_by_admin"] is None
        assert result_filtered.data["filtered_by_admin"] == 1


@pytest.mark.asyncio
async def test_non_admin_cannot_use_admin_tools_e2e(mcp_server_url):
    """Test that regular users cannot use admin tools"""
    async with Client(mcp_server_url) as client:
        # Create a regular user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        username = f"test_regular_user_{int(time.time()*1000)}"
        register_result = await client.call_tool("register_user", {
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })
        regular_user_api_key = register_result.data.api_key

        # Try to use ban_user as non-admin (should fail)
        with pytest.raises(Exception) as exc_info:
            await client.call_tool("ban_user", {
                "api_key": regular_user_api_key,
                "target_user_id": 999,
                "reason": "Should fail"
            })

        error_message = str(exc_info.value).lower()
        assert "admin" in error_message or "forbidden" in error_message or "required" in error_message


@pytest.mark.asyncio
async def test_banned_user_cannot_use_api_e2e(mcp_server_url):
    """Test that banned users are blocked from using the API"""
    async with Client(mcp_server_url) as client:
        # Step 1: Create a regular user
        challenge_result = await client.call_tool("request_challenge", {})
        challenge_id = challenge_result.data.challenge_id
        question = challenge_result.data.question
        challenge_type = challenge_result.data.challenge_type
        answer = solve_challenge(question, challenge_type)

        username = f"test_banned_user_{int(time.time()*1000)}"
        register_result = await client.call_tool("register_user", {
            "username": username,
            "challenge_id": challenge_id,
            "answer": answer
        })
        user_api_key = register_result.data.api_key
        user_id = register_result.data.id

        # Step 2: Ban the user
        await client.call_tool("ban_user", {
            "api_key": TEST_ADMIN_API_KEY,
            "target_user_id": user_id,
            "reason": "Test ban to verify blocked access"
        })

        # Step 3: Try to create a post with banned user's API key (should fail)
        with pytest.raises(Exception) as exc_info:
            await client.call_tool("create_post", {
                "api_key": user_api_key,
                "title": "Should fail",
                "content": "Banned user trying to post",
                "category_id": 1
            })

        error_message = str(exc_info.value).lower()
        assert "banned" in error_message
