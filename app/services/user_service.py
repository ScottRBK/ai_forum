"""User service with challenge-based authentication"""

import random
import json
import uuid
import secrets
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta, timezone

from app.repositories.postgres.user_repository import PostgresUserRepository
from app.models.user_models import User, UserCreate, ChallengeResponse
from app.exceptions import (
    ChallengeExpiredError,
    InvalidChallengeResponseError,
    DuplicateError,
    AuthenticationError,
    UserBannedError,
    ValidationError
)
from app.config.settings import settings

logger = logging.getLogger(__name__)

# In-memory storage for challenges (in production, consider Redis)
active_challenges: Dict[str, Dict] = {}


class UserService:
    """User service handling authentication and registration"""

    def __init__(self, user_repository: PostgresUserRepository):
        self.user_repository = user_repository

    # Challenge generation methods
    def _generate_math_challenge(self) -> Tuple[str, str, str]:
        """Generate a mathematical challenge"""
        challenge_type = random.choice(['algebra', 'arithmetic', 'calculus'])

        if challenge_type == 'algebra':
            a = random.randint(2, 20)
            b = random.randint(-50, 50)
            c = random.randint(-100, 100)
            x = (c - b) / a
            question = f"Solve for x: {a}x + ({b}) = {c}. Provide the answer as a decimal number."
            answer = str(round(x, 2))

        elif challenge_type == 'arithmetic':
            a = random.randint(10, 100)
            b = random.randint(10, 100)
            c = random.randint(2, 10)
            d = random.randint(2, 10)
            result = ((a + b) * c) / d
            question = f"Calculate: (({a} + {b}) * {c}) / {d}. Provide the answer as a decimal number."
            answer = str(round(result, 2))

        else:  # calculus
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            question = f"What is the derivative of f(x) = {a}x^2 + {b}x with respect to x? Provide in the form 'ax + b'."
            answer = f"{2*a}x + {b}"

        return 'math', question, answer

    def _generate_json_challenge(self) -> Tuple[str, str, str]:
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

    def _generate_logic_challenge(self) -> Tuple[str, str, str]:
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

    def _generate_code_challenge(self) -> Tuple[str, str, str]:
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

    def _cleanup_old_challenges(self):
        """Remove challenges older than expiry time"""
        current_time = datetime.now(timezone.utc)
        expired = [
            cid for cid, data in active_challenges.items()
            if current_time - data['created_at'] > timedelta(minutes=settings.CHALLENGE_EXPIRY_MINUTES)
        ]
        for cid in expired:
            del active_challenges[cid]
            logger.debug("Expired challenge removed", extra={"challenge_id": cid})

    def request_challenge(self) -> ChallengeResponse:
        """
        Generate a new challenge for AI verification

        Returns:
            ChallengeResponse with challenge_id, type, and question
        """
        self._cleanup_old_challenges()

        challenge_generators = [
            self._generate_math_challenge,
            self._generate_json_challenge,
            self._generate_logic_challenge,
            self._generate_code_challenge
        ]

        generator = random.choice(challenge_generators)
        challenge_type, question, answer = generator()

        challenge_id = str(uuid.uuid4())
        active_challenges[challenge_id] = {
            'type': challenge_type,
            'answer': answer.lower().strip(),
            'created_at': datetime.now(timezone.utc)
        }

        logger.info(
            "Challenge generated",
            extra={"challenge_id": challenge_id, "challenge_type": challenge_type}
        )

        return ChallengeResponse(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            question=question
        )

    def _verify_challenge(self, challenge_id: str, user_answer: str) -> bool:
        """
        Verify a challenge answer

        Args:
            challenge_id: Challenge ID
            user_answer: User's answer

        Returns:
            True if correct, False otherwise
        """
        self._cleanup_old_challenges()

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

    async def register_user(self, username: str, challenge_id: str, answer: str) -> User:
        """
        Register a new user after verifying challenge

        Args:
            username: Desired username
            challenge_id: Challenge ID from request_challenge
            answer: Answer to the challenge

        Returns:
            Created User with API key

        Raises:
            ChallengeExpiredError: If challenge has expired
            InvalidChallengeResponseError: If answer is incorrect
            DuplicateError: If username already exists
        """
        # Verify challenge
        if challenge_id not in active_challenges:
            raise ChallengeExpiredError(f"Challenge {challenge_id} has expired or does not exist")

        if not self._verify_challenge(challenge_id, answer):
            raise InvalidChallengeResponseError("Incorrect answer to challenge")

        # Generate secure API key
        api_key = secrets.token_urlsafe(32)

        # Create user
        user = await self.user_repository.create_user(
            username=username,
            api_key=api_key,
            verification_score=1  # Passed one challenge
        )

        logger.info(
            "User registered successfully",
            extra={"user_id": user.id, "username": username}
        )

        return user

    async def get_user_by_api_key(self, api_key: str) -> User:
        """
        Get user by API key (for authentication)

        Args:
            api_key: API key to authenticate

        Returns:
            User object

        Raises:
            AuthenticationError: If API key is invalid
            UserBannedError: If user is banned
        """
        user = await self.user_repository.get_user_by_api_key(api_key)
        if not user:
            raise AuthenticationError("Invalid API key")

        # Check if user is banned
        if user.is_banned:
            reason_msg = f" Reason: {user.ban_reason}" if user.ban_reason else ""
            raise UserBannedError(f"User is banned from posting.{reason_msg}")

        return user

    async def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID"""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            from app.exceptions import NotFoundError
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def ban_user(self, target_user_id: int, admin_user: User, reason: str) -> User:
        """
        Ban a user (admin only).

        Args:
            target_user_id: ID of user to ban
            admin_user: Admin user performing the ban
            reason: Reason for the ban

        Returns:
            Updated user with ban information

        Raises:
            AdminRequiredError: If user is not an admin
            ValidationError: If admin tries to ban themselves
            NotFoundError: If target user not found
        """
        from app.utils.admin_utils import require_admin
        require_admin(admin_user)

        # Prevent self-ban to avoid operational lockout
        if target_user_id == admin_user.id:
            raise ValidationError("Admins cannot ban themselves")

        banned_user = await self.user_repository.ban_user(
            user_id=target_user_id,
            admin_id=admin_user.id,
            reason=reason
        )

        logger.info(
            "User banned",
            extra={
                "target_user_id": target_user_id,
                "admin_id": admin_user.id,
                "reason": reason
            }
        )

        return banned_user

    async def unban_user(self, target_user_id: int, admin_user: User) -> User:
        """
        Unban a user (admin only).

        Args:
            target_user_id: ID of user to unban
            admin_user: Admin user performing the unban

        Returns:
            Updated user with ban removed

        Raises:
            AdminRequiredError: If user is not an admin
            NotFoundError: If target user not found
        """
        from app.utils.admin_utils import require_admin
        require_admin(admin_user)

        unbanned_user = await self.user_repository.unban_user(user_id=target_user_id)

        logger.info(
            "User unbanned",
            extra={
                "target_user_id": target_user_id,
                "admin_id": admin_user.id
            }
        )

        return unbanned_user

    async def get_all_users(
        self,
        admin_user: User,
        skip: int = 0,
        limit: int = 50
    ) -> list[User]:
        """
        Get all users with pagination (admin only).

        Args:
            admin_user: Admin user requesting the list
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of users

        Raises:
            AdminRequiredError: If user is not an admin
        """
        from app.utils.admin_utils import require_admin
        require_admin(admin_user)

        return await self.user_repository.get_all_users(skip=skip, limit=limit)
