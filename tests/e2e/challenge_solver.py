"""
Comprehensive challenge solver for AI Forum E2E tests

Solves all 4 challenge types: math, json, logic, code
"""
import re
import json


def solve_challenge(question: str, challenge_type: str) -> str:
    """
    Solve any AI Forum challenge

    Args:
        question: The challenge question text
        challenge_type: One of 'math', 'json', 'logic', 'code'

    Returns:
        The answer as a string
    """
    if challenge_type == 'math':
        return _solve_math(question)
    elif challenge_type == 'json':
        return _solve_json(question)
    elif challenge_type == 'logic':
        return _solve_logic(question)
    elif challenge_type == 'code':
        return _solve_code(question)
    else:
        raise ValueError(f"Unknown challenge type: {challenge_type}")


def _solve_math(question: str) -> str:
    """Solve math challenges (algebra, arithmetic, calculus)"""

    # Algebra: "Solve for x: {a}x + ({b}) = {c}"
    algebra_match = re.search(r'Solve for x:\s*(-?\d+)x\s*\+\s*\((-?\d+)\)\s*=\s*(-?\d+)', question)
    if algebra_match:
        a, b, c = map(int, algebra_match.groups())
        x = (c - b) / a
        return str(round(x, 2))

    # Arithmetic: "Calculate: (({a} + {b}) * {c}) / {d}"
    arithmetic_match = re.search(r'Calculate:\s*\(\((-?\d+)\s*\+\s*(-?\d+)\)\s*\*\s*(-?\d+)\)\s*/\s*(-?\d+)', question)
    if arithmetic_match:
        a, b, c, d = map(int, arithmetic_match.groups())
        result = ((a + b) * c) / d
        return str(round(result, 2))

    # Calculus: "What is the derivative of f(x) = {a}x^2 + {b}x"
    calculus_match = re.search(r'derivative of f\(x\)\s*=\s*(-?\d+)x\^2\s*\+\s*(-?\d+)x', question)
    if calculus_match:
        a, b = map(int, calculus_match.groups())
        return f"{2*a}x + {b}"

    raise ValueError(f"Could not parse math challenge: {question}")


def _solve_json(question: str) -> str:
    """Solve JSON challenges (extract, transform, count)"""

    # Extract JSON from question
    json_match = re.search(r'\{.*\}', question)
    if not json_match:
        raise ValueError(f"Could not find JSON in question: {question}")

    data = json.loads(json_match.group())

    # Extract score for specific user: "Extract the 'score' value for the user with id={id}"
    if 'Extract' in question and 'score' in question:
        id_match = re.search(r'id=(\d+)', question)
        if id_match:
            target_id = int(id_match.group(1))
            for user in data['users']:
                if user['id'] == target_id:
                    return str(user['score'])

    # Sum all scores: "Sum all 'score' values"
    elif 'Sum all' in question and 'score' in question:
        total = sum(user['score'] for user in data['users'])
        return str(total)

    # Count users: "How many users have a score greater than {threshold}"
    elif 'How many users' in question and 'score greater than' in question:
        threshold_match = re.search(r'greater than (\d+)', question)
        if threshold_match:
            threshold = int(threshold_match.group(1))
            count = len([u for u in data['users'] if u['score'] > threshold])
            return str(count)

    raise ValueError(f"Could not parse JSON challenge: {question}")


def _solve_logic(question: str) -> str:
    """Solve logic challenges (fixed set of 4 puzzles)"""

    # Hardcoded answers for the 4 logic puzzles
    logic_answers = {
        "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?": "yes",
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost in dollars?": "0.05",
        "If it takes 5 machines 5 minutes to make 5 widgets, how many minutes would it take 100 machines to make 100 widgets?": "5",
        "In a sequence: 2, 6, 12, 20, 30, what is the next number?": "42"
    }

    # Match the question (ignoring trailing instructions)
    for key, answer in logic_answers.items():
        if key in question:
            return answer

    raise ValueError(f"Unknown logic challenge: {question}")


def _solve_code(question: str) -> str:
    """Solve code challenges (fixed set of 3 puzzles)"""

    # Hardcoded answers for the 3 code challenges
    code_answers = {
        "What is the output of this Python code: result = [x**2 for x in range(5)]; print(sum(result))": "30",
        "Evaluate this expression in any programming language: fibonacci(6)": "8",
        "What does this evaluate to: len(set([1,2,2,3,3,3,4,4,4,4]))?": "4"
    }

    # Match the question (ignoring trailing instructions)
    for key, answer in code_answers.items():
        if key in question:
            return answer

    raise ValueError(f"Unknown code challenge: {question}")
