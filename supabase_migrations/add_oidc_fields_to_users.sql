-- Add OIDC fields to existing users table
-- This migration adds columns needed for Google OIDC authentication via Streamlit

-- Add OIDC-specific columns if they don't exist
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS sub TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS name TEXT,
ADD COLUMN IF NOT EXISTS given_name TEXT,
ADD COLUMN IF NOT EXISTS family_name TEXT,
ADD COLUMN IF NOT EXISTS picture TEXT,
ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user',
ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'google',
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Create index on sub for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_sub ON users(sub);

-- Create index on email for faster lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create index on role for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Add helpful comments
COMMENT ON COLUMN users.sub IS 'OIDC sub claim - unique identifier from identity provider (Google)';
COMMENT ON COLUMN users.role IS 'User role: user, admin, moderator, etc.';
COMMENT ON COLUMN users.provider IS 'OAuth provider: google, microsoft, etc.';
COMMENT ON COLUMN users.full_name IS 'Deprecated: Use name instead. Kept for backward compatibility';
COMMENT ON COLUMN users.preferences IS 'JSON field for user preferences (e.g. favorite sports)';

