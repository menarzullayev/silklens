---
description: Wipe non-system users + flush Redis + clear app data to a clean slate for testing
allowed-tools: Bash
argument-hint: "[email pattern, default: all non-system users]"
---

# /silklens-reset-db

Resets the SilkLens local dev state for a clean test run:

1. Postgres: deletes all users except `system_actor` (sessions, identities, emails, profiles, login_attempts cascade)
2. Redis: `FLUSHDB`
3. Android app: `pm clear com.silklens.app`

**Optional arg** `$ARGUMENTS`: SQL `LIKE` pattern for `user_emails.email` (e.g. `%@silklens-test.com`). Default deletes all non-system users.

---

```bash
PATTERN="${1:-%}"
echo "🧹 Resetting SilkLens local state (email pattern: $PATTERN)"

docker exec silklens-postgres psql -U silklens silklens -c "
WITH targets AS (
  SELECT u.id FROM users u
  JOIN user_emails ue ON ue.user_id = u.id
  WHERE u.pub_id != 'system_actor' AND ue.email LIKE '$PATTERN'
)
DELETE FROM refresh_tokens    WHERE user_id IN (SELECT id FROM targets);
"

docker exec silklens-postgres psql -U silklens silklens -c "
WITH targets AS (
  SELECT u.id FROM users u
  JOIN user_emails ue ON ue.user_id = u.id
  WHERE u.pub_id != 'system_actor' AND ue.email LIKE '$PATTERN'
)
DELETE FROM sessions          WHERE user_id IN (SELECT id FROM targets);
"

docker exec silklens-postgres psql -U silklens silklens -c "
DELETE FROM login_attempts WHERE identifier LIKE '$PATTERN';
"

docker exec silklens-postgres psql -U silklens silklens -c "
WITH targets AS (
  SELECT u.id FROM users u
  JOIN user_emails ue ON ue.user_id = u.id
  WHERE u.pub_id != 'system_actor' AND ue.email LIKE '$PATTERN'
)
DELETE FROM user_identities   WHERE user_id IN (SELECT id FROM targets);
"

docker exec silklens-postgres psql -U silklens silklens -c "
DELETE FROM user_emails ue
USING users u
WHERE ue.user_id = u.id
  AND u.pub_id != 'system_actor'
  AND ue.email LIKE '$PATTERN';
"

docker exec silklens-postgres psql -U silklens silklens -c "
DELETE FROM user_profiles up
USING users u
WHERE up.user_id = u.id AND u.pub_id != 'system_actor'
  AND NOT EXISTS (SELECT 1 FROM user_emails ue WHERE ue.user_id = u.id);
"

docker exec silklens-postgres psql -U silklens silklens -c "
DELETE FROM users
WHERE pub_id != 'system_actor'
  AND NOT EXISTS (SELECT 1 FROM user_emails ue WHERE ue.user_id = users.id);
"

echo "  Redis FLUSHDB"
docker exec silklens-redis redis-cli FLUSHDB

echo "  Android app pm clear"
/home/nsn/Android/Sdk/platform-tools/adb shell pm clear com.silklens.app 2>/dev/null || echo "  (device not connected — skipping app clear)"

echo "✓ Reset complete"
docker exec silklens-postgres psql -U silklens silklens -c "
SELECT count(*) AS remaining_users FROM users WHERE pub_id != 'system_actor';
"
```
