# Contributing to Smart Transportation System

## Development Setup

1. **Clone and setup**:
   ```bash
   git clone <repo-url>
   cd smart-transport
   make install
   ```

2. **Start services**:
   ```bash
   make docker-up
   ```

3. **Run tests**:
   ```bash
   make test
   ```

## Code Standards

- **Python**: Follow PEP 8, use Black formatter
- **JavaScript**: Use ESLint with Airbnb config
- **Commits**: Use conventional commits format
- **Tests**: Maintain >80% coverage

## Pull Request Process

1. Create feature branch from `develop`
2. Make changes with tests
3. Run `make lint` and `make test`
4. Submit PR to `develop` branch
5. Ensure CI passes and get review approval

## Security

- Never commit secrets or credentials
- Run security scans: `./tools/security/scan_deps.sh`
- Report vulnerabilities to security@company.com

## Architecture Decisions

Document significant changes in `/docs/adr/` using ADR format.