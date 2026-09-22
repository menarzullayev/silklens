---
description: Inspect or read OTP codes from Redis for SilkLens email verification debugging
allowed-tools: Bash
argument-hint: "[email | list | clear]"
---

# /silklens-otp

OTP debugging shortcut. Three modes via `$ARGUMENTS`:

- **`<email>`** — read the OTP for that email + its TTL
- **`list`** — show all active `otp:email_verify:*` keys
- **`clear`** — delete all OTP keys (rarely needed; useful when testing expiry paths)

If no arg given, lists all active OTPs.

---

```bash
ARG="${1:-list}"

case "$ARG" in
  list|"")
    echo "🔑 Active OTP keys:"
    docker exec silklens-redis redis-cli KEYS 'otp:email_verify:*' | while read -r key; do
      [ -z "$key" ] && continue
      code=$(docker exec silklens-redis redis-cli GET "$key")
      ttl=$(docker exec silklens-redis redis-cli TTL "$key")
      email="${key#otp:email_verify:}"
      printf "  %-45s code=%s  TTL=%ds\n" "$email" "$code" "$ttl"
    done
    ;;
  clear)
    echo "🗑️  Clearing all OTP keys…"
    docker exec silklens-redis redis-cli --no-raw KEYS 'otp:email_verify:*' | \
      xargs -r -I {} docker exec silklens-redis redis-cli DEL {}
    echo "✓ Cleared"
    ;;
  *)
    EMAIL="$ARG"
    KEY="otp:email_verify:${EMAIL,,}"
    code=$(docker exec silklens-redis redis-cli GET "$KEY")
    ttl=$(docker exec silklens-redis redis-cli TTL "$KEY")
    if [ -z "$code" ]; then
      echo "❌ No OTP found for $EMAIL"
      echo "   (Either never generated, expired, or already consumed.)"
      exit 1
    fi
    echo "📧 OTP for $EMAIL"
    echo "   Code: $code"
    echo "   TTL:  ${ttl}s"
    echo ""
    echo "💡 To verify via the app: enter $code in the 6-box OTP screen"
    echo "💡 To verify via curl:"
    echo "   curl -X POST http://localhost:8000/v1/auth/verify-email \\"
    echo "     -H 'Authorization: Bearer <token>' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"email\":\"$EMAIL\",\"code\":\"$code\"}'"
    ;;
esac
```
