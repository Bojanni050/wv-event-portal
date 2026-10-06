# Auth Testing Playbook (White Vision)

Credentials: see /app/memory/test_credentials.md

1. MongoDB: `mongosh test_database --eval 'db.users.find({}, {email:1, role:1, password_hash:1})'` — hashes start with `$2b$`; unique index on users.email.
2. API:
```
curl -c cookies.txt -X POST $API/api/auth/login -H "Content-Type: application/json" -d '{"email":"bojan.vanderheide@gmail.com","password":"WhiteVision!2026"}'
curl -b cookies.txt $API/api/auth/me
```
Login returns user object and sets access_token + refresh_token cookies. 5 failed attempts per ip+email → 429 for 15 min.
No public registration: accounts are created by admin via POST /api/customers or /api/djs (with optional password).
