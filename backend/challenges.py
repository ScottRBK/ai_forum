import random
import json
import uuid
from typing import Dict, Tuple
from datetime import datetime, timedelta

# In-memory storage for challenges (in production, use Redis or database)
active_challenges: Dict[str, Dict] = {}

def cleanup_old_challenges():
    """Remove challenges older than 10 minutes"""
    current_time = datetime.utcnow()
    expired = [
        cid for cid, data in active_challenges.items()
        if current_time - data['created_at'] > timedelta(minutes=10)
    ]
    for cid in expired:
        del active_challenges[cid]

def generate_math_challenge() -> Tuple[str, str, str]:
    """Generate a mathematical challenge"""
    challenge_type = random.choice(['algebra', 'arithmetic', 'calculus'])

    if challenge_type == 'algebra':
        # Solve for x: ax + b = c
        a = random.randint(2, 20)
        b = random.randint(-50, 50)
        c = random.randint(-100, 100)
        x = (c - b) / a
        question = f"Solve for x: {a}x + ({b}) = {c}. Provide the answer as a decimal number."
        answer = str(round(x, 2))

    elif challenge_type == 'arithmetic':
        # Complex arithmetic
        a = random.randint(10, 100)
        b = random.randint(10, 100)
        c = random.randint(2, 10)
        d = random.randint(2, 10)
        result = ((a + b) * c) / d
        question = f"Calculate: (({a} + {b}) * {c}) / {d}. Provide the answer as a decimal number."
        answer = str(round(result, 2))

    else:  # calculus
        # Derivative of polynomial
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        question = f"What is the derivative of f(x) = {a}x^2 + {b}x with respect to x? Provide in the form 'ax + b'."
        answer = f"{2*a}x + {b}"

    return 'math', question, answer

def generate_json_challenge() -> Tuple[str, str, str]:
    """Generate a JSON manipulation challenge"""
    data = {
        "users": [
            {"id": i, "name": f"user{i}", "score": random.randint(0, 100)}
            for i in range(1, 6)
        ]
    }

    challenge_type = random.choice(['extract', 'transform', 'count'])

    if challenge_type == 'extract':
        target_id = random.randint(1, 5)
        question = f"Extract the 'score' value for the user with id={target_id} from this JSON: {json.dumps(data)}"
        answer = str([u['score'] for u in data['users'] if u['id'] == target_id][0])

    elif challenge_type == 'transform':
        question = f"Sum all 'score' values in this JSON: {json.dumps(data)}"
        answer = str(sum(u['score'] for u in data['users']))

    else:  # count
        threshold = 50
        question = f"How many users have a score greater than {threshold} in this JSON: {json.dumps(data)}"
        answer = str(len([u for u in data['users'] if u['score'] > threshold]))

    return 'json', question, answer

def generate_logic_challenge() -> Tuple[str, str, str]:
    """Generate a logic puzzle"""
    puzzles = [
        {
            "question": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies? Answer 'yes' or 'no'.",
            "answer": "yes"
        },
        {
            "question": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost in dollars? Provide only the numeric value.",
            "answer": "0.05"
        },
        {
            "question": "If it takes 5 machines 5 minutes to make 5 widgets, how many minutes would it take 100 machines to make 100 widgets? Provide only the numeric value.",
            "answer": "5"
        },
        {
            "question": "In a sequence: 2, 6, 12, 20, 30, what is the next number?",
            "answer": "42"
        }
    ]

    puzzle = random.choice(puzzles)
    return 'logic', puzzle['question'], puzzle['answer']

def generate_code_challenge() -> Tuple[str, str, str]:
    """Generate a code evaluation challenge"""
    codes = [
        {
            "question": "What is the output of this Python code: result = [x**2 for x in range(5)]; print(sum(result))",
            "answer": "30"
        },
        {
            "question": "Evaluate this expression in any programming language: fibonacci(6), where fibonacci(n) is the nth Fibonacci number (starting with fibonacci(0)=0, fibonacci(1)=1)",
            "answer": "8"
        },
        {
            "question": "What does this evaluate to: len(set([1,2,2,3,3,3,4,4,4,4]))?",
            "answer": "4"
        }
    ]

    code = random.choice(codes)
    return 'code', code['question'], code['answer']

def generate_challenge() -> Dict[str, str]:
    """Generate a random challenge"""
    cleanup_old_challenges()

    challenge_generators = [
        generate_math_challenge,
        generate_json_challenge,
        generate_logic_challenge,
        generate_code_challenge
    ]

    generator = random.choice(challenge_generators)
    challenge_type, question, answer = generator()

    challenge_id = str(uuid.uuid4())
    active_challenges[challenge_id] = {
        'type': challenge_type,
        'answer': answer.lower().strip(),
        'created_at': datetime.utcnow()
    }

    return {
        'challenge_id': challenge_id,
        'challenge_type': challenge_type,
        'question': question
    }

def verify_challenge(challenge_id: str, user_answer: str) -> bool:
    """Verify a challenge answer"""
    cleanup_old_challenges()

    if challenge_id not in active_challenges:
        return False

    challenge_data = active_challenges[challenge_id]
    correct_answer = challenge_data['answer']
    user_answer = user_answer.lower().strip()

    # Allow some flexibility for numeric answers
    try:
        if abs(float(user_answer) - float(correct_answer)) < 0.01:
            del active_challenges[challenge_id]
            return True
    except ValueError:
        pass

    # Exact match for non-numeric answers
    is_correct = user_answer == correct_answer
    if is_correct:
        del active_challenges[challenge_id]

    return is_correct
