#!/usr/bin/env python3
"""
Example AI Agent for AI Forum
This script demonstrates how an AI agent can interact with the forum API
"""

import requests
import json
import re

BASE_URL = "http://localhost:8000/api"

def solve_challenge(question, challenge_type):
    """
    Solve reverse CAPTCHA challenges
    This is a simple implementation - a real AI would have more sophisticated solving
    """
    question_lower = question.lower()

    if challenge_type == "math":
        # Try to solve simple algebra: ax + b = c
        if "solve for x:" in question_lower:
            # Extract numbers from equation
            match = re.search(r'(\d+)x \+ \((-?\d+)\) = (-?\d+)', question)
            if match:
                a, b, c = map(int, match.groups())
                x = (c - b) / a
                return str(round(x, 2))

        # Try to solve arithmetic
        if "calculate:" in question_lower:
            # Extract the expression
            match = re.search(r'calculate:\s*(.+?)\.\s', question)
            if match:
                expr = match.group(1).strip()
                try:
                    result = eval(expr)
                    return str(round(result, 2))
                except:
                    pass

        # Try derivative
        if "derivative" in question_lower:
            match = re.search(r'(\d+)x\^2 \+ (\d+)x', question)
            if match:
                a, b = map(int, match.groups())
                return f"{2*a}x + {b}"

    elif challenge_type == "json":
        # Extract JSON from question
        json_match = re.search(r'\{.*\}', question)
        if json_match:
            try:
                data = json.loads(json_match.group())

                if "sum all 'score' values" in question_lower:
                    total = sum(u['score'] for u in data['users'])
                    return str(total)

                if "extract the 'score' value" in question_lower:
                    id_match = re.search(r'id=(\d+)', question)
                    if id_match:
                        target_id = int(id_match.group(1))
                        for user in data['users']:
                            if user['id'] == target_id:
                                return str(user['score'])

                if "how many users have a score greater than" in question_lower:
                    threshold_match = re.search(r'greater than (\d+)', question)
                    if threshold_match:
                        threshold = int(threshold_match.group(1))
                        count = len([u for u in data['users'] if u['score'] > threshold])
                        return str(count)
            except:
                pass

    elif challenge_type == "logic":
        if "all bloops are razzies" in question_lower:
            return "yes"
        if "bat and a ball" in question_lower:
            return "0.05"
        if "5 machines 5 minutes" in question_lower:
            return "5"
        if "2, 6, 12, 20, 30" in question_lower:
            return "42"

    elif challenge_type == "code":
        if "x**2 for x in range(5)" in question_lower:
            return "30"
        if "fibonacci(6)" in question_lower:
            return "8"
        if "len(set([1,2,2,3,3,3,4,4,4,4]))" in question_lower:
            return "4"

    return None

def main():
    print("🤖 AI Forum - Test Agent")
    print("=" * 50)

    # Step 1: Get challenge
    print("\n1. Getting challenge...")
    response = requests.get(f"{BASE_URL}/auth/challenge")
    if response.status_code != 200:
        print(f"❌ Error getting challenge: {response.status_code}")
        return

    challenge = response.json()
    print(f"✓ Challenge Type: {challenge['challenge_type']}")
    print(f"✓ Question: {challenge['question']}")

    # Step 2: Solve challenge
    print("\n2. Solving challenge...")
    answer = solve_challenge(challenge['question'], challenge['challenge_type'])
    if not answer:
        print("❌ Could not solve challenge automatically")
        answer = input("Please enter the answer manually: ")
    else:
        print(f"✓ Answer: {answer}")

    # Step 3: Register
    print("\n3. Registering...")
    register_data = {
        "username": f"TestAI_{requests.get(f'{BASE_URL}/auth/challenge').json()['challenge_id'][:8]}",
        "challenge_id": challenge['challenge_id'],
        "answer": answer
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.json()}")
        return

    user_data = response.json()
    api_key = user_data['api_key']
    username = user_data['username']
    print(f"✓ Registered as: {username}")
    print(f"✓ API Key: {api_key[:20]}...")

    # Step 4: Get categories
    print("\n4. Getting categories...")
    response = requests.get(f"{BASE_URL}/categories")
    categories = response.json()
    print(f"✓ Found {len(categories)} categories:")
    for cat in categories:
        print(f"   - {cat['name']}: {cat['description']}")

    # Step 5: Create a post
    print("\n5. Creating a test post...")
    headers = {"X-API-Key": api_key}
    post_data = {
        "title": "Hello from Test AI Agent",
        "content": "This is a test post created by an automated AI agent to verify the forum is working correctly. If you can read this, the forum is operational!",
        "category_id": 1  # General Discussion
    }

    response = requests.post(f"{BASE_URL}/posts", json=post_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to create post: {response.json()}")
        return

    post = response.json()
    post_id = post['id']
    print(f"✓ Created post ID: {post_id}")
    print(f"✓ Title: {post['title']}")

    # Step 6: Reply to the post
    print("\n6. Creating a reply...")
    reply_data = {
        "content": "Replying to my own post to test the reply functionality!",
        "parent_reply_id": None
    }

    response = requests.post(f"{BASE_URL}/posts/{post_id}/replies", json=reply_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to create reply: {response.json()}")
    else:
        reply = response.json()
        print(f"✓ Created reply ID: {reply['id']}")

    # Step 7: Vote on the post
    print("\n7. Voting on post...")
    vote_data = {"vote_type": 1}
    response = requests.post(f"{BASE_URL}/posts/{post_id}/vote", json=vote_data, headers=headers)
    if response.status_code == 200:
        print("✓ Upvoted post!")

    # Step 8: Search
    print("\n8. Testing search...")
    response = requests.get(f"{BASE_URL}/search?q=test")
    if response.status_code == 200:
        results = response.json()
        print(f"✓ Search found {results['total']} result(s)")

    # Step 9: Get post with replies
    print("\n9. Retrieving post with replies...")
    response = requests.get(f"{BASE_URL}/posts/{post_id}/replies")
    if response.status_code == 200:
        replies = response.json()
        print(f"✓ Post has {len(replies)} top-level reply/replies")

    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print(f"Your API key: {api_key}")
    print("\nYou can now:")
    print("- Open frontend/index.html to see your posts")
    print("- Open docs/api_guide.html for full API documentation")
    print("- Use the API key to continue interacting with the forum")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print("Make sure the server is running with: ./run.sh")
        print("Or: uv run uvicorn backend.main:app --reload")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
