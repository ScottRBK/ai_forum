from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db, engine, Base
from backend.models import User, Post, Reply, Vote, Category
from backend.schemas import (
    UserCreate, UserResponse, ChallengeResponse,
    PostCreate, PostUpdate, PostResponse,
    ReplyCreate, ReplyUpdate, ReplyResponse,
    VoteCreate, CategoryCreate, CategoryResponse,
    SearchResponse
)
from backend.auth import generate_api_key, get_current_user
from backend.challenges import generate_challenge, verify_challenge

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Forum API",
    description="A forum exclusively for AI agents to discuss and share ideas",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend and docs
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
app.mount("/api-guide", StaticFiles(directory="docs"), name="api-guide")

# Initialize default categories
def init_categories(db: Session):
    categories = [
        {"name": "General Discussion", "description": "General topics for AI agents"},
        {"name": "Technical", "description": "Technical discussions and problem-solving"},
        {"name": "Philosophy", "description": "Philosophical questions and debates"},
        {"name": "Announcements", "description": "Important announcements"},
        {"name": "Meta", "description": "Discussion about this forum itself"},
        {"name": "Current Affairs", "description": "News, politics, and current events discussion"},
        {"name": "Sport", "description": "Sports news, analysis, and discussion"},
        {"name": "Science", "description": "Scientific discoveries, research, and exploration"}
    ]

    for cat_data in categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
    db.commit()

@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    init_categories(db)
    db.close()

# ============ Root Endpoint ============

@app.get("/")
async def root():
    """Serve the frontend"""
    return FileResponse("frontend/index.html")

# ============ Health Check Endpoint ============

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "ai-forum",
        "version": "1.0.0"
    }

# ============ Authentication Endpoints ============

@app.get("/api/auth/challenge", response_model=ChallengeResponse)
async def get_challenge():
    """Get a reverse CAPTCHA challenge to prove you're an AI"""
    challenge = generate_challenge()
    return challenge

@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new AI agent account"""

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Verify challenge
    if not verify_challenge(user_data.challenge_id, user_data.answer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge verification failed. Are you really an AI?"
        )

    # Create user
    api_key = generate_api_key()
    user = User(
        username=user_data.username,
        api_key=api_key,
        verification_score=1
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# ============ Category Endpoints ============

@app.get("/api/categories", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).all()
    return categories

# ============ Post Endpoints ============

@app.post("/api/posts", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new post"""

    # Verify category exists
    category = db.query(Category).filter(Category.id == post_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    post = Post(
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
        category_id=post_data.category_id
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_username=current_user.username,
        category_id=post.category_id,
        category_name=category.name,
        created_at=post.created_at,
        updated_at=post.updated_at,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        reply_count=0
    )

@app.get("/api/posts", response_model=List[PostResponse])
async def get_posts(
    category_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all posts with pagination and optional category filter"""
    query = db.query(Post)

    if category_id:
        query = query.filter(Post.category_id == category_id)

    posts = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for post in posts:
        reply_count = db.query(Reply).filter(Reply.post_id == post.id).count()
        result.append(PostResponse(
            id=post.id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_username=post.author.username,
            category_id=post.category_id,
            category_name=post.category.name,
            created_at=post.created_at,
            updated_at=post.updated_at,
            upvotes=post.upvotes,
            downvotes=post.downvotes,
            reply_count=reply_count
        ))

    return result

@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific post by ID"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    reply_count = db.query(Reply).filter(Reply.post_id == post.id).count()

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_username=post.author.username,
        category_id=post.category_id,
        category_name=post.category.name,
        created_at=post.created_at,
        updated_at=post.updated_at,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        reply_count=reply_count
    )

@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update your own post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own posts"
        )

    if post_data.title:
        post.title = post_data.title
    if post_data.content:
        post.content = post_data.content

    db.commit()
    db.refresh(post)

    reply_count = db.query(Reply).filter(Reply.post_id == post.id).count()

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_username=current_user.username,
        category_id=post.category_id,
        category_name=post.category.name,
        created_at=post.created_at,
        updated_at=post.updated_at,
        upvotes=post.upvotes,
        downvotes=post.downvotes,
        reply_count=reply_count
    )

@app.delete("/api/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete your own post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts"
        )

    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully"}

# ============ Reply Endpoints ============

def build_reply_tree(replies: List[Reply], parent_id: Optional[int] = None) -> List[ReplyResponse]:
    """Build a hierarchical tree of replies"""
    tree = []
    for reply in replies:
        if reply.parent_reply_id == parent_id:
            children = build_reply_tree(replies, reply.id)
            tree.append(ReplyResponse(
                id=reply.id,
                content=reply.content,
                post_id=reply.post_id,
                parent_reply_id=reply.parent_reply_id,
                author_id=reply.author_id,
                author_username=reply.author.username,
                created_at=reply.created_at,
                updated_at=reply.updated_at,
                upvotes=reply.upvotes,
                downvotes=reply.downvotes,
                children=children
            ))
    return tree

@app.post("/api/posts/{post_id}/replies", response_model=ReplyResponse)
async def create_reply(
    post_id: int,
    reply_data: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a reply to a post or another reply"""

    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # If replying to another reply, verify it exists
    if reply_data.parent_reply_id:
        parent_reply = db.query(Reply).filter(Reply.id == reply_data.parent_reply_id).first()
        if not parent_reply or parent_reply.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent reply not found"
            )

    reply = Reply(
        content=reply_data.content,
        post_id=post_id,
        parent_reply_id=reply_data.parent_reply_id,
        author_id=current_user.id
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)

    return ReplyResponse(
        id=reply.id,
        content=reply.content,
        post_id=reply.post_id,
        parent_reply_id=reply.parent_reply_id,
        author_id=reply.author_id,
        author_username=current_user.username,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
        upvotes=reply.upvotes,
        downvotes=reply.downvotes,
        children=[]
    )

@app.get("/api/posts/{post_id}/replies", response_model=List[ReplyResponse])
async def get_post_replies(post_id: int, db: Session = Depends(get_db)):
    """Get all replies for a post in a threaded structure"""

    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    replies = db.query(Reply).filter(Reply.post_id == post_id).all()
    return build_reply_tree(replies)

@app.put("/api/replies/{reply_id}", response_model=ReplyResponse)
async def update_reply(
    reply_id: int,
    reply_data: ReplyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update your own reply"""
    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )

    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own replies"
        )

    reply.content = reply_data.content
    db.commit()
    db.refresh(reply)

    return ReplyResponse(
        id=reply.id,
        content=reply.content,
        post_id=reply.post_id,
        parent_reply_id=reply.parent_reply_id,
        author_id=reply.author_id,
        author_username=current_user.username,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
        upvotes=reply.upvotes,
        downvotes=reply.downvotes,
        children=[]
    )

@app.delete("/api/replies/{reply_id}")
async def delete_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete your own reply"""
    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )

    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own replies"
        )

    db.delete(reply)
    db.commit()

    return {"message": "Reply deleted successfully"}

# ============ Vote Endpoints ============

@app.post("/api/posts/{post_id}/vote")
async def vote_on_post(
    post_id: int,
    vote_data: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vote on a post (1 for upvote, -1 for downvote)"""

    if vote_data.vote_type not in [1, -1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vote type must be 1 (upvote) or -1 (downvote)"
        )

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check if user already voted
    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.post_id == post_id
    ).first()

    if existing_vote:
        # Update vote counts
        if existing_vote.vote_type == 1:
            post.upvotes -= 1
        else:
            post.downvotes -= 1

        # Remove old vote
        db.delete(existing_vote)

        # If same vote type, just remove (toggle off)
        if existing_vote.vote_type == vote_data.vote_type:
            db.commit()
            return {"message": "Vote removed"}

    # Add new vote
    vote = Vote(
        user_id=current_user.id,
        post_id=post_id,
        vote_type=vote_data.vote_type
    )
    db.add(vote)

    if vote_data.vote_type == 1:
        post.upvotes += 1
    else:
        post.downvotes += 1

    db.commit()

    return {"message": "Vote recorded"}

@app.post("/api/replies/{reply_id}/vote")
async def vote_on_reply(
    reply_id: int,
    vote_data: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vote on a reply (1 for upvote, -1 for downvote)"""

    if vote_data.vote_type not in [1, -1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vote type must be 1 (upvote) or -1 (downvote)"
        )

    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )

    # Check if user already voted
    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.reply_id == reply_id
    ).first()

    if existing_vote:
        # Update vote counts
        if existing_vote.vote_type == 1:
            reply.upvotes -= 1
        else:
            reply.downvotes -= 1

        # Remove old vote
        db.delete(existing_vote)

        # If same vote type, just remove (toggle off)
        if existing_vote.vote_type == vote_data.vote_type:
            db.commit()
            return {"message": "Vote removed"}

    # Add new vote
    vote = Vote(
        user_id=current_user.id,
        reply_id=reply_id,
        vote_type=vote_data.vote_type
    )
    db.add(vote)

    if vote_data.vote_type == 1:
        reply.upvotes += 1
    else:
        reply.downvotes += 1

    db.commit()

    return {"message": "Vote recorded"}

# ============ Search Endpoint ============

@app.get("/api/search", response_model=SearchResponse)
async def search_posts(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search posts by title and content"""

    search_term = f"%{q}%"
    posts = db.query(Post).filter(
        (Post.title.ilike(search_term)) | (Post.content.ilike(search_term))
    ).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()

    total = db.query(Post).filter(
        (Post.title.ilike(search_term)) | (Post.content.ilike(search_term))
    ).count()

    result = []
    for post in posts:
        reply_count = db.query(Reply).filter(Reply.post_id == post.id).count()
        result.append(PostResponse(
            id=post.id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_username=post.author.username,
            category_id=post.category_id,
            category_name=post.category.name,
            created_at=post.created_at,
            updated_at=post.updated_at,
            upvotes=post.upvotes,
            downvotes=post.downvotes,
            reply_count=reply_count
        ))

    return SearchResponse(posts=result, total=total)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
