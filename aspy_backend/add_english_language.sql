-- SQL Query to add English language to the database
-- This assumes you're using SQLite (as seen in dev.db) or PostgreSQL

-- For SQLite or PostgreSQL:
INSERT INTO languages (name, slug) 
VALUES ('English', 'english')
ON CONFLICT (slug) DO NOTHING;

-- Alternative for MySQL (if you're using MySQL):
-- INSERT IGNORE INTO languages (name, slug) VALUES ('English', 'english');

-- To verify the insertion:
-- SELECT * FROM languages WHERE slug = 'english';

-- To view all languages:
-- SELECT * FROM languages ORDER BY id;
