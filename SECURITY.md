# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, email security@company.com with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

## Security Measures

- All API endpoints require authentication
- Input validation on all user data
- Encrypted communication (TLS 1.3)
- Regular dependency scanning
- Container security scanning
- Secrets management via environment variables

## Responsible Disclosure

We follow a 90-day disclosure timeline:
1. Report received and acknowledged (24h)
2. Initial assessment (7 days)
3. Fix development and testing (30-60 days)
4. Coordinated disclosure (90 days max)