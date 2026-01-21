-- Table: users
CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    persona TEXT,
                    background_labels JSON,
                    creation_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    follower_count INTEGER DEFAULT 0,
                    total_likes_received INTEGER DEFAULT 0,
                    total_shares_received INTEGER DEFAULT 0,
                    total_comments_received INTEGER DEFAULT 0,
                    influence_score FLOAT DEFAULT 0.0,
                    is_influencer BOOLEAN DEFAULT FALSE,
                    last_influence_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

-- Table: posts
CREATE TABLE posts (
                    post_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    summary TEXT,
                    author_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    num_likes INTEGER DEFAULT 0,
                    num_shares INTEGER DEFAULT 0,
                    num_flags INTEGER DEFAULT 0,
                    num_comments INTEGER DEFAULT 0,
                    original_post_id TEXT,
                    is_news BOOLEAN DEFAULT FALSE,
                    news_type TEXT,
                    FOREIGN KEY (author_id) REFERENCES users(user_id),
                    FOREIGN KEY (original_post_id) REFERENCES posts(post_id)
                );

-- Table: user_actions
CREATE TABLE user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_id TEXT,
                    content TEXT,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

-- Table: follows
CREATE TABLE follows (
                    follower_id TEXT NOT NULL,
                    followed_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (follower_id, followed_id),
                    FOREIGN KEY (follower_id) REFERENCES users(user_id),
                    FOREIGN KEY (followed_id) REFERENCES users(user_id)
                );

-- Table: comments
CREATE TABLE comments (
                    comment_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    num_likes INTEGER DEFAULT 0,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id),
                    FOREIGN KEY (author_id) REFERENCES users(user_id)
                );

-- Table: agent_memories
CREATE TABLE agent_memories (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decay_factor FLOAT DEFAULT 1.0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

