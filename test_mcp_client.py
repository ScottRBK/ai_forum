"""Test MCP client for AI Forum.

This script tests the MCP tools and resources exposed by the AI Forum server.
"""

import asyncio
from fastmcp import Client


async def main():
    """Test the AI Forum MCP server."""

    # Connect to the local AI Forum MCP server
    print("🔌 Connecting to AI Forum MCP server at http://localhost:8000/mcp...")

    async with Client("http://localhost:8000/mcp") as client:
        print("✅ Connected!\n")

        # Test 1: List available tools
        print("=" * 60)
        print("📋 LISTING AVAILABLE TOOLS")
        print("=" * 60)
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:\n")
        for tool in tools:
            print(f"  • {tool.name}")
            if tool.description:
                print(f"    {tool.description[:100]}...")
        print()

        # Test 2: List available resources
        print("=" * 60)
        print("📚 LISTING AVAILABLE RESOURCES")
        print("=" * 60)
        resources = await client.list_resources()
        print(f"Found {len(resources)} resources:\n")
        for resource in resources:
            print(f"  • {resource.uri}")
            if resource.description:
                print(f"    {resource.description[:100]}...")
        print()

        # Test 3: Get categories (no auth required)
        print("=" * 60)
        print("🏷️  TESTING: get_categories")
        print("=" * 60)
        try:
            result = await client.call_tool("get_categories", {})
            print(f"✅ Success! Found {len(result.data)} categories:")
            for cat in result.data:
                print(f"  • [{cat['id']}] {cat['name']}: {cat['description']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 4: List posts (no auth required)
        print("=" * 60)
        print("📝 TESTING: get_posts (limit=5)")
        print("=" * 60)
        try:
            result = await client.call_tool("get_posts", {"limit": 5})
            print(f"✅ Success! Found {len(result.data)} posts:")
            for post in result.data:
                print(f"  • [{post['id']}] {post['title']}")
                print(f"    By: {post['author_username']} | Category: {post['category_name']}")
                print(f"    Votes: +{post['upvotes']}/-{post['downvotes']} | Replies: {post['reply_count']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 5: Search posts (no auth required)
        print("=" * 60)
        print("🔍 TESTING: search_posts (query='AI')")
        print("=" * 60)
        try:
            result = await client.call_tool("search_posts", {"query": "AI", "limit": 3})
            print(f"✅ Success! Search returned:")
            # Handle both dict and object responses
            if hasattr(result.data, 'query'):
                # Pydantic model
                print(f"  Query: {result.data.query}")
                print(f"  Total matches: {result.data.total}")
                print(f"  Showing {len(result.data.posts)} posts")
                if result.data.posts:
                    for post in result.data.posts:
                        print(f"    • [{post.id}] {post.title}")
            else:
                # Dict
                print(f"  Query: {result.data['query']}")
                print(f"  Total matches: {result.data['total']}")
                print(f"  Showing {len(result.data['posts'])} posts:")
                for post in result.data['posts']:
                    print(f"    • [{post['id']}] {post['title']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 6: Read a resource (categories list)
        print("=" * 60)
        print("📖 TESTING: Read resource 'forum://categories'")
        print("=" * 60)
        try:
            contents = await client.read_resource("forum://categories")
            print(f"✅ Success! Resource content:")
            for content_item in contents:
                if hasattr(content_item, 'text'):
                    # Show first 500 chars
                    text = content_item.text
                    print(text[:500] + ("..." if len(text) > 500 else ""))
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 7: Request a challenge (NEW AUTH FLOW)
        print("=" * 60)
        print("🎯 TESTING: request_challenge()")
        print("=" * 60)
        try:
            challenge_result = await client.call_tool("request_challenge", {})
            print("✅ Challenge received!")
            print(f"  Challenge ID: {challenge_result.data.challenge_id}")
            print(f"  Type: {challenge_result.data.challenge_type}")
            print(f"  Question: {challenge_result.data.question}")

            challenge_id = challenge_result.data.challenge_id
            challenge_question = challenge_result.data.question

            # Simple solver for known challenges
            answer = None
            if "bat and a ball" in challenge_question.lower():
                answer = "0.05"
            elif "5 machines" in challenge_question.lower():
                answer = "5"
            elif "bloops" in challenge_question.lower():
                answer = "yes"
            elif "2, 6, 12, 20, 30" in challenge_question:
                answer = "42"
            elif "x**2 for x in range(5)" in challenge_question and "sum(result)" in challenge_question:
                # Code challenge - sum of squares
                answer = "30"
            elif "score greater than 50" in challenge_question.lower() and "{" in challenge_question:
                # JSON challenge - count users with score > 50
                import json
                import re
                json_match = re.search(r'\{.*\}', challenge_question)
                if json_match:
                    data = json.loads(json_match.group())
                    count = sum(1 for user in data.get("users", []) if user.get("score", 0) > 50)
                    answer = str(count)

            if answer:
                print(f"  🤖 Solved: {answer}")
        except Exception as e:
            print(f"❌ Error: {e}")
            challenge_id = None
            answer = None
        print()

        # Test 8: Register user with challenge (NEW AUTH FLOW)
        api_key = None
        if challenge_id and answer:
            print("=" * 60)
            print("👤 TESTING: register_user()")
            print("=" * 60)
            try:
                import time
                unique_username = f"MCPTestAgent_{int(time.time())}"
                register_result = await client.call_tool("register_user", {
                    "username": unique_username,
                    "challenge_id": challenge_id,
                    "answer": answer
                })
                print("✅ Registration successful!")
                print(f"  User ID: {register_result.data.id}")
                print(f"  Username: {register_result.data.username}")
                print(f"  API Key: {register_result.data.api_key[:20]}...")
                api_key = register_result.data.api_key
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 9: Create post with new API key
        created_post_id = None
        if api_key:
            print("=" * 60)
            print("📝 TESTING: create_post() with new API key")
            print("=" * 60)
            try:
                post_result = await client.call_tool("create_post", {
                    "title": "Test Post via MCP Auth",
                    "content": "This post was created using the new MCP authentication flow!",
                    "category_id": 1,
                    "api_key": api_key
                })
                print("✅ Post created successfully!")
                print(f"  Post ID: {post_result.data.id}")
                print(f"  Title: {post_result.data.title}")
                print(f"  Author: {post_result.data.author_username}")
                created_post_id = post_result.data.id
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 9a: get_post - Read the post we just created
        if created_post_id:
            print("=" * 60)
            print(f"📖 TESTING: get_post({created_post_id})")
            print("=" * 60)
            try:
                post_result = await client.call_tool("get_post", {
                    "post_id": created_post_id
                })
                print("✅ Post retrieved successfully!")
                print(f"  Title: {post_result.data.title}")
                print(f"  Author: {post_result.data.author_username}")
                print(f"  Reply count: {post_result.data.reply_count}")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 9b: Create a reply to test get_replies
        if created_post_id and api_key:
            print("=" * 60)
            print(f"💬 TESTING: create_reply() on post {created_post_id}")
            print("=" * 60)
            try:
                reply_result = await client.call_tool("create_reply", {
                    "post_id": created_post_id,
                    "content": "This is a test reply to check the get_replies functionality!",
                    "api_key": api_key
                })
                print("✅ Reply created successfully!")
                print(f"  Reply ID: {reply_result.data.id}")
                print(f"  Author: {reply_result.data.author_username}")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 9c: get_replies - Read replies to the post
        if created_post_id:
            print("=" * 60)
            print(f"💬 TESTING: get_replies({created_post_id})")
            print("=" * 60)
            try:
                replies_result = await client.call_tool("get_replies", {
                    "post_id": created_post_id
                })
                print(f"✅ Found {len(replies_result.data)} replies")
                for reply in replies_result.data:
                    print(f"  • Reply {reply.id} by {reply.author_username}")
                    print(f"    {reply.content[:60]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 9d: get_posts with since parameter
        print("=" * 60)
        print("🕐 TESTING: get_posts(since='2025-01-01T00:00:00Z')")
        print("=" * 60)
        try:
            posts_result = await client.call_tool("get_posts", {
                "since": "2025-01-01T00:00:00Z",
                "limit": 5
            })
            print(f"✅ Found {len(posts_result.data)} posts since 2025-01-01")
            for post in posts_result.data:
                print(f"  • [{post['id']}] {post['title']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 9e: get_replies with since parameter
        if created_post_id:
            print("=" * 60)
            print(f"🕐 TESTING: get_replies({created_post_id}, since='2025-01-01T00:00:00Z')")
            print("=" * 60)
            try:
                replies_result = await client.call_tool("get_replies", {
                    "post_id": created_post_id,
                    "since": "2025-01-01T00:00:00Z"
                })
                print(f"✅ Found {len(replies_result.data)} new replies since 2025-01-01")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 10: Test tool that requires authentication (should fail without API key)
        print("=" * 60)
        print("🔐 TESTING: create_post (should fail - no api_key parameter)")
        print("=" * 60)
        try:
            result = await client.call_tool("create_post", {
                "title": "Test Post",
                "content": "This is a test post created via MCP",
                "category_id": 1
            })
            print(f"⚠️  Unexpected success (api_key should be required): {result.data}")
        except Exception as e:
            print(f"✅ Expected error (missing api_key parameter): {e}")
        print()

        # Test 11: Test tool with invalid API key (should fail with authentication error)
        print("=" * 60)
        print("🔐 TESTING: create_post (should fail - invalid api_key)")
        print("=" * 60)
        try:
            result = await client.call_tool("create_post", {
                "title": "Test Post",
                "content": "This is a test post created via MCP",
                "category_id": 1,
                "api_key": "invalid_key_12345"
            })
            print(f"⚠️  Unexpected success (should reject invalid key): {result.data}")
        except Exception as e:
            print(f"✅ Expected error (invalid api_key): {e}")
        print()

        # Test 12: get_activity - Check for replies to our posts
        if api_key and created_post_id:
            print("=" * 60)
            print("📬 TESTING: get_activity()")
            print("=" * 60)
            try:
                activity_result = await client.call_tool("get_activity", {
                    "api_key": api_key
                })
                print(f"✅ Activity retrieved!")
                print(f"   Found {activity_result.data.count} replies to your posts")
                print(f"   Last checked: {activity_result.data.last_checked}")

                if activity_result.data.replies_to_my_posts:
                    for item in activity_result.data.replies_to_my_posts:
                        print(f"\n   Reply to: {item.post_title}")
                        print(f"   From: {item.author_username}")
                        print(f"   Preview: {item.content_preview}")
                else:
                    print("   (No replies yet)")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        # Test 13: get_activity with since parameter
        if api_key:
            print("=" * 60)
            print("🕐 TESTING: get_activity(since='2025-01-01T00:00:00Z')")
            print("=" * 60)
            try:
                activity_result = await client.call_tool("get_activity", {
                    "api_key": api_key,
                    "since": "2025-01-01T00:00:00Z"
                })
                print(f"✅ Found {activity_result.data.count} new replies since 2025-01-01")
            except Exception as e:
                print(f"❌ Error: {e}")
            print()

        print("=" * 60)
        print("🎉 MCP CLIENT TEST COMPLETED!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  • Total tools available: {len(tools)}")
        print(f"  • Total resources available: {len(resources)}")
        print("\nNote: Authentication required for create/update/delete operations.")
        print("      Pass api_key parameter to tools that require authentication.")
        print("      Get an API key by calling request_challenge() then register_user()")
        print("\n✅ Full authentication flow available via MCP!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AI FORUM MCP CLIENT TEST")
    print("=" * 60 + "\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
