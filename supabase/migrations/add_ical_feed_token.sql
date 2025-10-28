-- Migration: Add ical_feed_token to users table
-- This enables personalized iCal feed URLs for each user

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS ical_feed_token TEXT UNIQUE;

-- Add index for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_ical_feed_token ON users(ical_feed_token);

-- Comment
COMMENT ON COLUMN users.ical_feed_token IS 'Unique token for personal iCal feed URL. Generated automatically on first access to My Profile > Calendar tab.';
