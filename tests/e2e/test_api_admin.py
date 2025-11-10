"""
End-to-end tests for REST API admin endpoints

Requires:
- PostgreSQL running in Docker with test_admin user created
- MCP server running: python main.py
- Admin user in database:
  INSERT INTO users (username, api_key, verification_score, is_admin, is_banned, created_at)
  VALUES ('test_admin', 'test_admin_key_12345', 1, TRUE, FALSE, NOW())

Tests the complete stack: HTTP → REST API → Service → Repository → PostgreSQL
"""
import pytest
import httpx
import time
from .challenge_solver import solve_challenge


# Test admin API key (must match the DB)
TEST_ADMIN_API_KEY = "test_admin_key_12345"


@pytest.mark.asyncio
async def test_ban_user_api_e2e(api_base_url):
    """Test POST /api/admin/ban-user - admin bans a regular user"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Create a regular user to ban
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_ban_user_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        assert register_response.status_code == 200
        user_data = register_response.json()
        user_id = user_data["id"]

        # Step 2: Admin bans the user
        ban_response = await client.post("/api/admin/ban-user", json={
            "target_user_id": user_id,
            "reason": "Test ban via REST API"
        }, headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })

        assert ban_response.status_code == 200
        ban_data = ban_response.json()
        assert ban_data["success"] is True
        assert "banned" in ban_data["message"].lower()
        assert ban_data["banned_user"]["id"] == user_id
        assert ban_data["banned_user"]["username"] == username
        assert ban_data["banned_user"]["ban_reason"] == "Test ban via REST API"


@pytest.mark.asyncio
async def test_unban_user_api_e2e(api_base_url):
    """Test POST /api/admin/unban-user - admin unbans a banned user"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Create and ban a user
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_unban_user_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        user_data = register_response.json()
        user_id = user_data["id"]

        # Ban the user
        await client.post("/api/admin/ban-user", json={
            "target_user_id": user_id,
            "reason": "Temporary test ban"
        }, headers={"X-API-Key": TEST_ADMIN_API_KEY})

        # Step 2: Admin unbans the user
        unban_response = await client.post("/api/admin/unban-user", json={
            "target_user_id": user_id
        }, headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })

        assert unban_response.status_code == 200
        unban_data = unban_response.json()
        assert unban_data["success"] is True
        assert "unbanned" in unban_data["message"].lower()
        assert unban_data["user"]["id"] == user_id
        assert unban_data["user"]["is_banned"] is False


@pytest.mark.asyncio
async def test_get_all_users_api_e2e(api_base_url):
    """Test GET /api/admin/users - admin lists all users"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/admin/users?skip=0&limit=50", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })

        assert response.status_code == 200
        data = response.json()

        assert "users" in data
        assert isinstance(data["users"], list)
        assert data["count"] > 0  # Should have at least the admin user

        # Check user structure
        if len(data["users"]) > 0:
            user = data["users"][0]
            assert "id" in user
            assert "username" in user
            assert "is_admin" in user
            assert "is_banned" in user
            assert "created_at" in user


@pytest.mark.asyncio
async def test_get_all_users_pagination_api_e2e(api_base_url):
    """Test GET /api/admin/users with pagination"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get first page
        response1 = await client.get("/api/admin/users?skip=0&limit=2", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })
        data1 = response1.json()

        # Get second page
        response2 = await client.get("/api/admin/users?skip=2&limit=2", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })
        data2 = response2.json()

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert data1["skip"] == 0
        assert data1["limit"] == 2
        assert data2["skip"] == 2
        assert data2["limit"] == 2


@pytest.mark.asyncio
async def test_get_audit_logs_api_e2e(api_base_url):
    """Test GET /api/admin/audit-logs - admin views audit trail"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create and ban a user to generate audit logs
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_audit_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        user_data = register_response.json()
        user_id = user_data["id"]

        # Ban user (creates audit log)
        await client.post("/api/admin/ban-user", json={
            "target_user_id": user_id,
            "reason": "Test ban for REST audit log"
        }, headers={"X-API-Key": TEST_ADMIN_API_KEY})

        # Get audit logs
        response = await client.get("/api/admin/audit-logs?skip=0&limit=50", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })

        assert response.status_code == 200
        data = response.json()

        assert "audit_logs" in data
        assert isinstance(data["audit_logs"], list)
        assert data["count"] > 0

        # Find the ban_user action we just created
        ban_logs = [
            log for log in data["audit_logs"]
            if log["action"] == "ban_user" and log["target_id"] == user_id
        ]
        assert len(ban_logs) > 0

        log = ban_logs[0]
        assert log["target_type"] == "user"
        assert log["target_id"] == user_id
        assert "Test ban for REST audit log" in log["details"]


@pytest.mark.asyncio
async def test_get_audit_logs_filter_by_admin_api_e2e(api_base_url):
    """Test GET /api/admin/audit-logs with admin_id filter"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Get audit logs without filter
        response_all = await client.get("/api/admin/audit-logs?skip=0&limit=50", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })
        data_all = response_all.json()

        # Get audit logs filtered by admin (assuming admin_id=1)
        response_filtered = await client.get("/api/admin/audit-logs?skip=0&limit=50&admin_id=1", headers={
            "X-API-Key": TEST_ADMIN_API_KEY
        })
        data_filtered = response_filtered.json()

        assert response_all.status_code == 200
        assert response_filtered.status_code == 200
        assert data_all["filtered_by_admin"] is None
        assert data_filtered["filtered_by_admin"] == 1


@pytest.mark.asyncio
async def test_non_admin_cannot_use_admin_endpoints_api_e2e(api_base_url):
    """Test that regular users get 403 Forbidden on admin endpoints"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Create a regular user
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_regular_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        user_data = register_response.json()
        regular_api_key = user_data["api_key"]

        # Try to ban a user as non-admin (should get 403)
        ban_response = await client.post("/api/admin/ban-user", json={
            "target_user_id": 999,
            "reason": "Should fail"
        }, headers={"X-API-Key": regular_api_key})

        assert ban_response.status_code == 403
        data = ban_response.json()
        assert "detail" in data
        assert "admin" in data["detail"].lower() or "forbidden" in data["detail"].lower()


@pytest.mark.asyncio
async def test_missing_authorization_header_api_e2e(api_base_url):
    """Test that admin endpoints return 401 without Authorization header"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Try to ban a user without auth header
        ban_response = await client.post("/api/admin/ban-user", json={
            "target_user_id": 999,
            "reason": "Should fail"
        })

        assert ban_response.status_code == 401
        data = ban_response.json()
        assert "detail" in data
        assert ("authorization" in data["detail"].lower() or "x-api-key" in data["detail"].lower())


@pytest.mark.asyncio
async def test_invalid_api_key_api_e2e(api_base_url):
    """Test that admin endpoints return 401 with invalid API key"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Try to ban a user with invalid API key
        ban_response = await client.post("/api/admin/ban-user", json={
            "target_user_id": 999,
            "reason": "Should fail"
        }, headers={"Authorization": "invalid_api_key_12345"})

        assert ban_response.status_code == 401
        data = ban_response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_admin_can_delete_any_post_api_e2e(api_base_url):
    """Test that admin can delete posts created by other users"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Create a regular user and their post
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_post_owner_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        user_data = register_response.json()
        user_api_key = user_data["api_key"]

        # Create a post
        post_response = await client.post("/api/posts", json={
            "title": "Test post to be deleted by admin",
            "content": "This post will be deleted by admin",
            "category_id": 1
        }, headers={"X-API-Key": user_api_key})
        assert post_response.status_code == 200
        post_data = post_response.json()
        post_id = post_data["id"]

        # Step 2: Admin deletes the post
        delete_response = await client.delete(
            f"/api/posts/{post_id}",
            headers={"X-API-Key": TEST_ADMIN_API_KEY}
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert "deleted successfully" in delete_data["message"].lower()

        # Step 3: Verify post is gone
        get_response = await client.get(f"/api/posts/{post_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_update_any_post_api_e2e(api_base_url):
    """Test that admin can update posts created by other users"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        # Step 1: Create a regular user and their post
        challenge_response = await client.get("/api/auth/challenge")
        challenge_data = challenge_response.json()
        answer = solve_challenge(challenge_data["question"], challenge_data["challenge_type"])

        username = f"test_api_post_updater_{int(time.time()*1000)}"
        register_response = await client.post("/api/auth/register", json={
            "username": username,
            "challenge_id": challenge_data["challenge_id"],
            "answer": answer
        })
        user_data = register_response.json()
        user_api_key = user_data["api_key"]

        # Create a post
        post_response = await client.post("/api/posts", json={
            "title": "Original title",
            "content": "Original content",
            "category_id": 1
        }, headers={"X-API-Key": user_api_key})
        assert post_response.status_code == 200
        post_data = post_response.json()
        post_id = post_data["id"]

        # Step 2: Admin updates the post
        update_response = await client.put(
            f"/api/posts/{post_id}",
            json={
                "title": "Updated by admin",
                "content": "Content updated by admin"
            },
            headers={"X-API-Key": TEST_ADMIN_API_KEY}
        )

        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["title"] == "Updated by admin"
        assert updated_data["content"] == "Content updated by admin"
