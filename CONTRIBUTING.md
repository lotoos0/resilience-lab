# Contributing to Resilience Lab

Thank you for your interest in contributing to Resilience Lab! This document provides guidelines and instructions for contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [How to Contribute](#-how-to-contribute)
- [Reporting Issues](#-reporting-issues)
- [Creating Pull Requests](#-creating-pull-requests)
- [Coding Standards](#-coding-standards)
- [Commit Message Format](#-commit-message-format)
- [Branching Workflow](#-branching-workflow)
- [Development Setup](#-development-setup)
- [Testing Requirements](#-testing-requirements)
- [Milestone Overview](#-milestone-overview)
- [Release Flow](#-release-flow)

---

## 📜 Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

---

## 🤝 How to Contribute

There are many ways to contribute to Resilience Lab:

1. **Report bugs** - Found an issue? Let us know!
2. **Suggest features** - Have ideas for improvements? We'd love to hear them!
3. **Write code** - Fix bugs or implement new features
4. **Improve documentation** - Help make our docs better
5. **Write tests** - Increase test coverage
6. **Review pull requests** - Help review code from other contributors

---

## 🐛 Reporting Issues

### Before Creating an Issue

1. **Search existing issues** - Check if the issue already exists
2. **Check documentation** - Review `docs/` directory for solutions
3. **Test with latest version** - Ensure you're running the latest code

### Creating a Bug Report

When creating a bug report, include:

**Title Format**: `[BUG] Short description`

**Issue Template**:

```markdown
## Bug Description
Clear and concise description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04, macOS 13, Windows 11]
- Docker version: [e.g., 24.0.5]
- Python version: [e.g., 3.11.5]
- Branch: [e.g., develop, main]

## Logs
```
Paste relevant logs here
```

## Additional Context
Any other relevant information
```

### Feature Requests

**Title Format**: `[FEATURE] Short description`

**Include**:
- Problem statement - What problem does this solve?
- Proposed solution - How should it work?
- Alternatives considered - Other approaches you've thought about
- Related milestone - Which milestone (M0-M4) does this fit?

---

## 🔀 Creating Pull Requests

### Before Creating a PR

1. **Create an issue first** (for significant changes)
2. **Fork and clone** the repository
3. **Create a feature branch** from `develop`
4. **Follow coding standards** (see below)
5. **Write tests** for new functionality
6. **Run tests locally** - Ensure all tests pass
7. **Run linting** - Code must pass `make lint`
8. **Update documentation** - If applicable

### PR Workflow

1. **Create feature branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**:
   ```bash
   # Edit code...
   make test-unit      # Fast feedback
   make lint           # Check code quality
   ```

3. **Commit changes** (follow commit format below):
   ```bash
   git add .
   git commit -m "[DAY##] feat: your feature description"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**:
   - Target branch: `develop`
   - Fill out PR template
   - Link related issues

### PR Title Format

```
[DAY##] type: short description
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `test` - Adding or updating tests
- `refactor` - Code refactoring
- `ci` - CI/CD changes
- `chore` - Maintenance tasks

**Examples**:
- `[DAY03] feat: add payment validation endpoint`
- `[DAY05] fix: correct healthcheck timeout`
- `[DAY07] docs: update deployment guide`

### PR Description Template

```markdown
## Description
Brief description of changes

## Related Issue
Fixes #123
Related to #456

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass (`make test-unit`)
- [ ] Integration tests pass (`make test-integration`)
- [ ] Linting passes (`make lint`)
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing

## Screenshots (if applicable)
Add screenshots for UI changes
```

### PR Review Process

1. **Automated checks** - CI must pass (lint, test, build)
2. **Code review** - At least one approval (for collaborative projects)
3. **Self-merge allowed** if:
   - CI is ✅ green
   - Code is tested locally
   - Documentation updated when relevant
   - No breaking changes

---

## 📝 Coding Standards

### Python Style Guide

Follow **PEP 8** enforced by `ruff`:

**Good Examples**:

```python
from typing import Dict, Any
from pydantic import BaseModel, Field

def process_payment(amount: float, currency: str) -> Dict[str, Any]:
    """Process a payment transaction.

    Args:
        amount: Payment amount (must be > 0)
        currency: ISO 4217 currency code

    Returns:
        Payment confirmation dict

    Raises:
        ValueError: If amount is not positive
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")

    return {
        "payment_id": generate_id(),
        "amount": amount,
        "currency": currency,
        "status": "completed"
    }
```

**Bad Examples**:

```python
# ❌ No type hints
def process_payment(amt, curr):
    pass

# ❌ Poor naming
def pp(a, c):
    pass

# ❌ No docstring
def process_payment(amount: float, currency: str):
    pass
```

### Type Hints

**Always use type hints**:

```python
from typing import List, Dict, Optional, Any

# Good ✅
def get_payments(
    tenant_id: str,
    limit: int = 10,
    offset: int = 0
) -> List[Dict[str, Any]]:
    pass

# Bad ❌
def get_payments(tenant_id, limit=10, offset=0):
    pass
```

### Pydantic Models

Use Pydantic for request/response validation:

```python
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount must be > 0")
    currency: str = Field(pattern="^[A-Z]{3}$", description="ISO 4217 code")
    tenant_id: str = "default"

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 100.0,
                "currency": "USD"
            }
        }
```

### Error Handling

```python
from fastapi import HTTPException, status

# Good ✅
async def get_payment(payment_id: str):
    payment = await repository.get(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found"
        )
    return payment

# Bad ❌
async def get_payment(payment_id: str):
    return repository.get(payment_id)  # No error handling
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use structured logging
logger.info(
    "Payment processed",
    extra={
        "payment_id": payment_id,
        "amount": amount,
        "currency": currency
    }
)

# Never log sensitive data ❌
logger.info(f"Credit card: {card_number}")  # ❌ NEVER
```

### Docstrings

Use **Google style** docstrings:

```python
def calculate_total(items: List[Item]) -> Decimal:
    """Calculate total price for items.

    Args:
        items: List of items to calculate

    Returns:
        Total price as Decimal

    Raises:
        ValueError: If items list is empty

    Example:
        >>> items = [Item(price=10), Item(price=20)]
        >>> calculate_total(items)
        Decimal('30.00')
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    return sum(item.price for item in items)
```

### Code Quality Checks

Before committing, run:

```bash
# Linting
make lint

# Auto-fix issues
ruff check --fix services/

# Unit tests
make test-unit

# All tests (requires services running)
make dev
make test
```

---

## 💬 Commit Message Format

### Standard Format

```
[DAY##] type: short description

Optional longer description explaining the change in more detail.

Fixes #123
Related to #456
```

### Components

1. **[DAY##]** - Day number in project timeline
   - Required for all commits
   - Tracks progress across milestones
   - Example: `[DAY01]`, `[DAY15]`

2. **type** - Type of change:
   - `feat` - New feature
   - `fix` - Bug fix
   - `docs` - Documentation only
   - `test` - Adding/updating tests
   - `refactor` - Code refactoring
   - `ci` - CI/CD changes
   - `chore` - Maintenance tasks
   - `perf` - Performance improvements
   - `style` - Code style changes (formatting)

3. **description** - Short summary (50 chars or less)
   - Use imperative mood: "add" not "added"
   - Don't capitalize first letter (lowercase)
   - No period at the end

### Examples

**Good commits**:

```bash
[DAY01] feat: add payment processing endpoint
[DAY02] fix: correct validation error in payment request
[DAY03] docs: update deployment guide with K8s instructions
[DAY05] test: add integration tests for payment flow
[DAY07] ci: add caching to GitHub Actions workflow
[DAY10] refactor: extract payment validation to separate module
```

**Bad commits**:

```bash
# ❌ Missing [DAY##]
feat: add payment endpoint

# ❌ No type
[DAY01] Add payment endpoint

# ❌ Too vague
[DAY01] fix: fix bug

# ❌ Past tense
[DAY01] feat: added payment endpoint

# ❌ Capitalized
[DAY01] feat: Add payment endpoint

# ❌ Period at end
[DAY01] feat: add payment endpoint.
```

### Multi-line Commit Messages

For complex changes, use detailed body:

```bash
git commit -m "[DAY05] feat: add circuit breaker pattern

Implement circuit breaker for external payment gateway calls.
Uses half-open state for recovery testing.
Configurable thresholds via environment variables.

Fixes #123
Related to #456"
```

---

## 🧭 Branching Workflow

This project follows a **light GitFlow model**:

### Branch Types

- `main` → Stable, production-ready releases only (tagged)
- `develop` → Active development branch (daily work and integration)
- `feature/<name>` → New functionality or task for current milestone
- `fix/<name>` → Bug fixes
- `test/<name>` → Experimental changes or testing
- `docs/<name>` → Documentation improvements
- `release/<version>` → Final polish and testing before release
- `hotfix/<name>` → Quick fix for urgent production issues

### Branch Naming

**Format**: `type/short-description`

**Examples**:
```
feature/helm-charts
feature/payment-validation
fix/healthcheck-timeout
test/ci-pipeline
docs/deployment-guide
release/v0.1.0
hotfix/missing-envoy-config
```

### Workflow

```
main (production)
  └── develop (integration)
       ├── feature/payment-validation
       ├── feature/helm-charts
       ├── fix/healthcheck-bug
       └── docs/api-guide
```

---

## 💻 Development Setup

### Prerequisites

- Docker 24+
- Docker Compose v2+
- Python 3.11+
- Make

### Setup Steps

1. **Fork and clone**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/resilience-lab.git
   cd resilience-lab
   ```

2. **Install dependencies**:
   ```bash
   make install
   ```

3. **Start services**:
   ```bash
   make dev
   ```

4. **Verify setup**:
   ```bash
   make ps
   make test
   ```

For detailed setup instructions, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## 🧪 Testing Requirements

### Test Coverage

- **Minimum**: 80% code coverage
- **Target**: 90% code coverage
- **Critical paths**: 100% coverage

### Writing Tests

**Unit Tests** (no external dependencies):

```python
# tests/test_payments.py
def test_payment_validation():
    """Test payment amount validation."""
    with pytest.raises(ValueError):
        PaymentRequest(amount=-50, currency="USD")
```

**Integration Tests** (require running services):

```python
# tests/test_integration.py
import pytest

pytestmark = pytest.mark.integration

def test_payment_flow():
    """Test complete payment processing flow."""
    response = requests.post(
        "http://localhost:8001/process",
        json={"amount": 100, "currency": "USD"}
    )
    assert response.status_code == 201
```

### Running Tests

```bash
# All tests (requires services)
make dev
make test

# Unit tests only (fast)
make test-unit

# Integration tests only
make dev
make test-integration

# With coverage
pytest --cov=services --cov-report=html
```

### CI Requirements

All PRs must pass:

1. **Lint** - `make lint` (ruff)
2. **Unit tests** - `make test-unit`
3. **Integration tests** - `make test-integration`
4. **Build** - Docker images build successfully

---

## 🧩 Milestone Overview

| Milestone | Focus                      | Dates    | Goal                                                |
| --------- | -------------------------- | -------- | --------------------------------------------------- |
| **M0**    | Bootstrap                  | 28–31.10 | Repo init, API + Payments + Compose                 |
| **M1**    | Core + CI/CD               | 17–25.11 | Helm deploy, atomic CI/CD, security baseline        |
| **M2**    | Networking & Health        | 26–30.11 | Traefik, Envoy, HPA, PDB, NetPol                    |
| **M3**    | Resilience + Observability | 01–15.12 | Rate-limit, bulkhead, Prometheus, Grafana, Loki     |
| **M4**    | Security + Chaos + Release | 16–31.12 | Backup/restore, chaos tests, polish, release v0.1.0 |

Each milestone has a Definition of Done (DoD) tracked through `[DAY##]` commits and GitHub issues.

See [README.md](README.md#-roadmap) for detailed roadmap.

---

## 🚀 Release Flow

1. **Create release branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v0.1.0
   ```

2. **Finalize release**:
   - Update version numbers
   - Update CHANGELOG.md
   - Update documentation
   - Final testing

3. **Merge to main**:
   ```bash
   git checkout main
   git merge --no-ff release/v0.1.0
   ```

4. **Tag release**:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin main --tags
   ```

5. **Merge back to develop**:
   ```bash
   git checkout develop
   git merge --no-ff main
   git push origin develop
   ```

---

## 📚 Additional Resources

- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Development Guide**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **API Documentation**: http://localhost:8001/docs (when running)

---

## 🧠 Questions or Help

- **Check documentation** - See `docs/` directory
- **Search issues** - [GitHub Issues](https://github.com/lotoos0/resilience-lab/issues)
- **Start discussion** - [GitHub Discussions](https://github.com/lotoos0/resilience-lab/discussions)
- **Email** - andii4444@gmail.com

---

**Thank you for contributing to Resilience Lab!** 🚀
