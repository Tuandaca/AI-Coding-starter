# Security Armor Guidelines

## Application Security

### Input Validation
- Validate all inputs server-side
- Allow-list over block-list
- Sanitize for context (HTML, SQL, Shell, etc.)
- File upload: type, size, content validation

### Authentication
- Use established libraries (NextAuth, Passport, etc.)
- Argon2/bcrypt for password hashing (cost ≥ 12)
- JWT: short expiry, refresh tokens, secure flags
- MFA support (TOTP, WebAuthn)
- Session management: secure, httpOnly, SameSite

### Authorization
- Role-based access control (RBAC)
- Attribute-based access control (ABAC) for complex cases
- Resource-level permissions
- Deny by default

## OWASP Top 10 Mitigations

| Risk | Mitigation |
|------|------------|
| A01 Broken Access Control | RBAC, deny-by-default, test authorization |
| A02 Cryptographic Failures | TLS 1.2+, strong hashes, key rotation |
| A03 Injection | Parameterized queries, ORM, input validation |
| A04 Insecure Design | Threat modeling, secure patterns |
| A05 Security Misconfiguration | Hardening, automated scans, least privilege |
| A06 Vulnerable Components | Dependency scanning, automated updates |
| A07 Auth Failures | MFA, rate limiting, secure sessions |
| A08 Integrity Failures | Signed artifacts, SBOM, CI/CD integrity |
| A09 Logging Failures | Structured logs, alerting, audit trails |
| A10 SSRF | Allow-list URLs, network segmentation |

## Infrastructure

- WAF in front of applications
- DDoS protection
- Network segmentation (VPC, subnets)
- Secrets in vault (not env vars)
- Regular penetration testing
- Dependency scanning in CI/CD
