# Security: Authentication and Authorization

- **Authentication** answers "who are you?". Users log in with email and password and receive a token.
- **Authorization** answers "what may you do?". Each user has a role (`CUSTOMER` or `ADMIN`), and write endpoints require `ADMIN`.

## Login flow

```text
1. POST /auth/register  {email, password}       -> 201 user (always CUSTOMER)
2. POST /auth/login     form: username, password -> 200 {access_token, token_type: "bearer"}
3. Any protected call   Authorization: Bearer <access_token>
       get_current_user: verify signature + expiry -> load user from DB -> 401 if anything fails
       require_admin:    user.role == ADMIN?        -> 403 if not
```

The code is spread over four files:
- `app/core/security.py`: hashing and tokens. Pure functions with no HTTP code.
- `app/core/dependencies.py`: the `get_current_user` and `require_admin` FastAPI dependencies.
- `app/routers/auth.py`: the register and login endpoints.
- `app/routers/users.py`: `GET /users/me`.

## Passwords
- **Hashed with Argon2id** (`argon2-cffi`), the winner of the Password Hashing Competition and the current OWASP recommendation.
  - It is deliberately slow and memory-hungry, so guessing passwords from a stolen hash is expensive.
- **Salted automatically.** Every hash includes a random salt, so two users with the same password get different hashes, and precomputed "rainbow tables" are useless.
- **Never stored, logged or returned in plain text.**
  - Only `hashed_password` is saved.
  - `UserResponse` has no password field.
  - The manual check in Week 4 confirmed that no password or token appears in the server log.
- **Length rules: 8 to 128 characters.** The maximum stops someone sending huge inputs to the slow hasher, which would be a cheap denial of service.

## Tokens (JWT)
- **Format.** A JWT is `header.payload.signature`. Anyone can *read* the payload, which is only base64-encoded, but nobody can *change* it without the secret key, because the signature would no longer match.
- **Contents.** The payload holds only `sub` (user ID), `iat` (issued at) and `exp` (expiry). There is no role and no personal data.
- **Signing.** Tokens are signed with **HS256** using `SECRET_KEY`. Decoding accepts *only* HS256, which blocks forged tokens that claim `"alg": "none"` (unsigned).
- **`SECRET_KEY` must be at least 32 characters**, or the app refuses to start. With a short key, an attacker could brute-force it offline from one captured token and then forge admin tokens. `.env.example` deliberately contains a placeholder that is too short, so it cannot be used by accident.
- **Expiry is 30 minutes by default** (`ACCESS_TOKEN_EXPIRE_MINUTES`). An expired token gets 401 `"Token has expired"`.
- **The user is loaded from the database on every request.** If an account is deleted or its role changes, that takes effect immediately rather than when the token expires.

## Roles
| Action | Anonymous | CUSTOMER | ADMIN |
| --- | --- | --- | --- |
| Read products, categories, stock | ✅ | ✅ | ✅ |
| `GET /users/me` | 401 | ✅ | ✅ |
| Create/update/delete products, create categories, set stock | 401 | 403 | ✅ |

- **Registration always creates a CUSTOMER.** `UserCreate` has no `role` field, and a `role` sent in the request is ignored, so nobody can register as an admin.
- **Admins are created on the command line:** `python -m app.scripts.create_admin <email>`. The password is typed at a hidden prompt. If the user already exists, they are promoted.
- **401 vs 403.**
  - 401 means "we don't know who you are", and comes with a `WWW-Authenticate: Bearer` header.
  - 403 means "we know who you are, and you may not do this".

## Defences against common attacks
| Attack | Defence |
| --- | --- |
| Stolen database | Only Argon2 hashes are stored |
| Guessing which emails are registered | Login returns the same message for an unknown email and a wrong password. An unknown email still runs one Argon2 check, so response times look the same. |
| Editing a token, e.g. changing `sub` | The signature check fails, so 401 |
| Unsigned `alg: none` token | Only HS256 is accepted |
| Self-promotion to admin | No `role` field at registration |
| Duplicate accounts by changing letter case | Emails are stored in lowercase, and the unique index returns 409 |

## Known limitations (out of scope for this project)
- **No logout or token revocation.** A stolen token works until it expires. The short 30-minute lifetime limits the damage. A production system would add refresh tokens and a revocation list.
- **No rate limiting on login.** Password guessing is slowed only by Argon2. In production, add rate limiting at the API gateway or App Service level, or account lockout.
- **No email verification or password reset.**
- **Tokens are only as safe as the connection.** They must travel over HTTPS. Azure App Service provides HTTPS from Week 8.

## Tests
| File | What it covers |
| --- | --- |
| `tests/test_security.py` | Hashing, salts, and token round-trip. Rejection of expired, wrong-key, edited-payload, `alg: none`, missing-expiry and garbage tokens. |
| `tests/test_auth.py` | Register, duplicate email, invalid input, login, and `/users/me` with missing, invalid and expired tokens and a token for a deleted user |
| `tests/test_permissions.py` | Every write endpoint returns 401 to anonymous users and 403 to customers. Reads are public. |
| `tests/test_create_admin.py` | The admin bootstrap command |
