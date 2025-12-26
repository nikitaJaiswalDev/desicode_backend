-- Fix user_type enum values in users table
-- This script updates lowercase enum values to uppercase to match the UserType enum

-- Step 1: Check current values in user_type column
SELECT id, email, user_type 
FROM users;

-- Step 2: Update lowercase 'user' to uppercase 'USER'
-- Note: This might fail if the enum constraint is already enforced
-- If it fails, you'll need to temporarily remove the constraint

-- For SQLite (if using dev.db):
-- SQLite doesn't enforce enums strictly, so direct update should work
UPDATE users 
SET user_type = 'USER' 
WHERE user_type = 'user';

UPDATE users 
SET user_type = 'ADMIN' 
WHERE user_type = 'admin';

-- Step 3: Verify the changes
SELECT id, email, user_type, is_superuser 
FROM users;

-- Step 4: If you want to set a specific user as admin
-- Replace 'your-email@example.com' with the actual email
UPDATE users 
SET user_type = 'ADMIN', is_superuser = 1 
WHERE email = 'your-email@example.com';

-- Step 5: Final verification
SELECT id, email, user_type, is_superuser 
FROM users 
ORDER BY user_type DESC;
