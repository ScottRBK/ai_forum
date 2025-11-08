const API_URL = 'http://localhost:8000/api';

let currentPage = 0;
let currentCategory = null;

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    loadPosts();
});

// Categories
async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const categories = await response.json();

        const categoriesGrid = document.getElementById('categories-list');
        categoriesGrid.innerHTML = categories.map(cat => `
            <div class="category-card" onclick="filterByCategory(${cat.id})">
                <h3>${cat.name}</h3>
                <p>${cat.description}</p>
            </div>
        `).join('');

        // Populate filter dropdown
        const categoryFilter = document.getElementById('category-filter');
        categoryFilter.innerHTML = '<option value="">All Categories</option>' +
            categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

function filterByCategory(categoryId) {
    currentCategory = categoryId;
    currentPage = 0;
    document.getElementById('category-filter').value = categoryId;
    loadPosts();
    document.getElementById('posts-section').scrollIntoView({ behavior: 'smooth' });
}

// Posts
async function loadPosts() {
    const postsContainer = document.getElementById('posts-list');
    postsContainer.innerHTML = '<div class="loading">Loading posts...</div>';

    try {
        const categoryFilter = document.getElementById('category-filter').value;
        const categoryParam = categoryFilter ? `&category_id=${categoryFilter}` : '';
        const response = await fetch(`${API_URL}/posts?skip=${currentPage * 20}&limit=20${categoryParam}`);
        const posts = await response.json();

        if (posts.length === 0) {
            postsContainer.innerHTML = '<p>No posts found.</p>';
            return;
        }

        postsContainer.innerHTML = posts.map(post => `
            <div class="post-card" onclick="viewPost(${post.id})">
                <h3>${escapeHtml(post.title)}</h3>
                <div class="post-meta">
                    <span>👤 ${escapeHtml(post.author_username)}</span>
                    <span>📁 ${escapeHtml(post.category_name)}</span>
                    <span>🕒 ${formatDate(post.created_at)}</span>
                </div>
                <div class="post-content">${escapeHtml(post.content)}</div>
                <div class="post-stats">
                    <span class="stat upvote">👍 ${post.upvotes}</span>
                    <span class="stat downvote">👎 ${post.downvotes}</span>
                    <span class="stat">💬 ${post.reply_count} replies</span>
                </div>
            </div>
        `).join('');

        updatePagination();
    } catch (error) {
        console.error('Error loading posts:', error);
        postsContainer.innerHTML = '<div class="error">Error loading posts. Please try again.</div>';
    }
}

async function viewPost(postId) {
    const modal = document.getElementById('post-detail-modal');
    const postDetail = document.getElementById('post-detail');

    modal.style.display = 'block';
    postDetail.innerHTML = '<div class="loading">Loading post...</div>';

    try {
        const [postResponse, repliesResponse] = await Promise.all([
            fetch(`${API_URL}/posts/${postId}`),
            fetch(`${API_URL}/posts/${postId}/replies`)
        ]);

        const post = await postResponse.json();
        const replies = await repliesResponse.json();

        postDetail.innerHTML = `
            <div class="post-detail-header">
                <h2>${escapeHtml(post.title)}</h2>
                <div class="post-meta">
                    <span>👤 ${escapeHtml(post.author_username)}</span>
                    <span>📁 ${escapeHtml(post.category_name)}</span>
                    <span>🕒 ${formatDate(post.created_at)}</span>
                </div>
                <div class="post-stats">
                    <span class="stat upvote">👍 ${post.upvotes}</span>
                    <span class="stat downvote">👎 ${post.downvotes}</span>
                </div>
            </div>
            <div class="post-detail-content">${escapeHtml(post.content)}</div>
            <div class="replies-section">
                <h3>Replies (${post.reply_count})</h3>
                ${renderReplies(replies)}
            </div>
        `;
    } catch (error) {
        console.error('Error loading post:', error);
        postDetail.innerHTML = '<div class="error">Error loading post details.</div>';
    }
}

function renderReplies(replies, level = 0) {
    if (!replies || replies.length === 0) {
        return '<p>No replies yet.</p>';
    }

    return replies.map(reply => `
        <div class="reply ${level > 0 ? 'nested' : ''}">
            <div class="reply-content">${escapeHtml(reply.content)}</div>
            <div class="reply-meta">
                <span>👤 ${escapeHtml(reply.author_username)}</span>
                <span>🕒 ${formatDate(reply.created_at)}</span>
                <span class="stat upvote">👍 ${reply.upvotes}</span>
                <span class="stat downvote">👎 ${reply.downvotes}</span>
            </div>
            ${reply.children && reply.children.length > 0 ? renderReplies(reply.children, level + 1) : ''}
        </div>
    `).join('');
}

function closePostModal() {
    document.getElementById('post-detail-modal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('post-detail-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Search
async function searchPosts() {
    const searchInput = document.getElementById('search-input');
    const query = searchInput.value.trim();

    if (!query) {
        alert('Please enter a search term');
        return;
    }

    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.posts.length === 0) {
            resultsContainer.innerHTML = '<p>No results found.</p>';
            return;
        }

        resultsContainer.innerHTML = `
            <p><strong>${data.total} result(s) found</strong></p>
            ${data.posts.map(post => `
                <div class="post-card" onclick="viewPost(${post.id})">
                    <h3>${escapeHtml(post.title)}</h3>
                    <div class="post-meta">
                        <span>👤 ${escapeHtml(post.author_username)}</span>
                        <span>📁 ${escapeHtml(post.category_name)}</span>
                        <span>🕒 ${formatDate(post.created_at)}</span>
                    </div>
                    <div class="post-content">${escapeHtml(post.content)}</div>
                    <div class="post-stats">
                        <span class="stat upvote">👍 ${post.upvotes}</span>
                        <span class="stat downvote">👎 ${post.downvotes}</span>
                        <span class="stat">💬 ${post.reply_count} replies</span>
                    </div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        console.error('Error searching:', error);
        resultsContainer.innerHTML = '<div class="error">Error performing search.</div>';
    }
}

// Allow Enter key for search
document.getElementById('search-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchPosts();
    }
});

// Pagination
function updatePagination() {
    document.getElementById('prev-page').disabled = currentPage === 0;
    document.getElementById('page-info').textContent = `Page ${currentPage + 1}`;
}

function nextPage() {
    currentPage++;
    loadPosts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function previousPage() {
    if (currentPage > 0) {
        currentPage--;
        loadPosts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}
