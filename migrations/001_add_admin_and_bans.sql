-- Migration: Add admin role and user banning functionality
-- Date: 2025-01-10
-- Description: Adds is_admin and is_banned fields to users table, creates audit_logs table

-- Add admin and ban fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_by INTEGER REFERENCES users(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason TEXT;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS ix_users_is_admin ON users(is_admin);
CREATE INDEX IF NOT EXISTS ix_users_is_banned ON users(is_banned);

-- Create audit logs table for tracking admin actions
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Add indexes for audit logs
CREATE INDEX IF NOT EXISTS ix_audit_logs_admin_id ON audit_logs(admin_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_target ON audit_logs(target_type, target_id);

-- Note: To create the first admin user, run:
-- UPDATE users SET is_admin = TRUE WHERE username = 'Veridian';
