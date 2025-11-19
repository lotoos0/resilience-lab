# 💻 Development Guide

**Resilience Lab - Developer Documentation**

*Last updated: November 18, 2025*

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guide](#testing-guide)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

Before you start development, ensure you have:

```bash
# Required
docker --version        # Docker 24+
docker compose version  # v2+
python --version        # Python 3.11+
make --version          # GNU Make

# Recommended
git --version          # Git 2.40+
```

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lotoos0/resilience-lab.git
   cd resilience-lab
   ```

2. **Install development dependencies**:
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

---

## Development Environment

### Option 1: Virtual Environment (Recommended)

**Setup**:
```bash
# Create and activate venv
make install
source venv/bin/activate

# Start services
make dev
```

**Benefits**:
- Fast local testing
- IDE integration
- Quick feedback loop

**Limitations**:
- Requires local Python 3.11+
- Some deps need system libraries (PostgreSQL)

### Option 2: Docker-Only Development

**Setup**:
```bash
# No local Python needed
make dev
make test-docker
```

**Benefits**:
- No local Python dependencies
- Environment parity
- Works everywhere

**Limitations**:
- Slower test execution
- No IDE integration

### Recommended Tools

#### Code Editor
- **VS Code** (recommended)
  - Extensions: Python, Docker, YAML
  - Settings: `.vscode/settings.json` (create if needed)

#### Database Tools
- **pgAdmin** or **DBeaver** for PostgreSQL
- **Redis Insight** for Redis

#### API Testing
- **HTTPie** or **Postman**
- Built-in: FastAPI `/docs` (Swagger UI)

---

## Development Workflow

### Daily Workflow

```bash
# 1. Start your day
git pull origin develop
make dev

# 2. Create feature branch
git checkout -b feature/your-feature

# 3. Development cycle
# Edit code...
make test-unit      # Fast feedback
make lint           # Check code quality

# 4. Full test before commit
make test           # All tests
make lint           # Final check

# 5. Commit and push
git add .
git commit -m "[DAYxx] feat: your feature"
git push origin feature/your-feature
```

### Branch Strategy

```
main (production)
  └── develop (integration)
       ├── feature/feature-name
       ├── fix/bug-name
       └── test/experiment-name
```

**Branch Naming**:
- Features: `feature/short-description`
- Fixes: `fix/bug-description`
- Tests: `test/experiment-name`
- Docs: `docs/what-changed`

---

## Coding Standards

### Python Style

Follow **PEP 8** enforced by `ruff`:

```python
# Good
def process_payment(amount: float, currency: str) -> dict:
    """Process a payment transaction.

    Args:
        amount: Payment amount (must be > 0)
        currency: ISO 4217 currency code

    Returns:
        Payment confirmation dict
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    # ...
```

```python
# Bad
def ProcessPayment(amt, curr):
    if amt<=0: raise ValueError("bad amount")
    # ...
```

### Type Hints

**Always use type hints**:

```python
# Good ✅
from typing import Dict, List, Optional

def get_payments(
    tenant_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    pass

# Bad ❌
def get_payments(tenant_id, limit=10):
    pass
```

### Pydantic Models

Use Pydantic for data validation:

```python
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount must be > 0")
    currency: str = Field(pattern="^[A-Z]{3}$")
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
    pass
```

---

## Testing Guide

### Test Structure

```
tests/
├── test_sanity.py          # Basic sanity checks
├── test_integration.py     # Integration tests (@pytest.mark.integration)
└── test_payments.py        # Unit tests (future)
```

### Writing Unit Tests

```python
# tests/test_payments.py
import pytest
from services.payments.main import PaymentProcessRequest

def test_payment_request_validation():
    """Test payment request validation."""
    # Valid request
    req = PaymentProcessRequest(amount=100, currency="USD")
    assert req.amount == 100

    # Invalid amount
    with pytest.raises(ValueError):
        PaymentProcessRequest(amount=-50, currency="USD")
```

### Writing Integration Tests

```python
# tests/test_integration.py
import pytest
import requests

pytestmark = pytest.mark.integration

def test_payment_flow():
    """Test complete payment flow."""
    # Create payment
    response = requests.post(
        "http://localhost:8001/process",
        json={"amount": 100, "currency": "USD"}
    )
    assert response.status_code == 201
    payment_id = response.json()["payment_id"]

    # Retrieve payment
    response = requests.get(f"http://localhost:8001/payments/{payment_id}")
    assert response.status_code == 200
```

### Test Commands

```bash
# Run all tests
make test

# Run only unit tests (fast)
make test-unit

# Run only integration tests (requires services)
make dev
make test-integration

# Run with coverage
pytest --cov=services --cov-report=html

# Run specific test
pytest tests/test_sanity.py::test_sanity -v
```

### Test Coverage Goals

- **Minimum**: 80% code coverage
- **Target**: 90% code coverage
- **Critical paths**: 100% coverage

---

## Debugging

### Local Debugging

#### FastAPI Debug Mode

Add to service `main.py`:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True,  # Auto-reload on code changes
        log_level="debug"
    )
```

#### VS Code Debugger

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Payments Service",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/services/payments/main.py",
            "console": "integratedTerminal",
            "env": {
                "DATABASE_URL": "postgresql://resilience:resilience@localhost:5432/resilience_db",
                "REDIS_URL": "redis://localhost:6379"
            }
        }
    ]
}
```

### Container Debugging

```bash
# View logs
make logs-payments
make logs-api

# Follow logs in real-time
docker compose logs -f payments

# Execute commands in container
docker compose exec payments bash

# Check environment variables
docker compose exec payments env

# Test connectivity
docker compose exec payments curl http://localhost:8001/healthz
```

### Database Debugging

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U resilience -d resilience_db

# Run queries
# \dt - list tables
# \d payments - describe table
# SELECT * FROM payments;

# Connect to Redis
docker compose exec redis redis-cli

# Redis commands
# KEYS *
# GET key
# FLUSHALL
```

---

## Common Tasks

### Adding a New Endpoint

1. **Define Pydantic models**:
   ```python
   class PaymentStatusRequest(BaseModel):
       payment_id: str
   ```

2. **Add endpoint**:
   ```python
   @app.get("/payments/{payment_id}/status")
   async def get_payment_status(payment_id: str):
       # Implementation
       pass
   ```

3. **Add tests**:
   ```python
   def test_payment_status():
       # Test implementation
       pass
   ```

4. **Update docs** (automatic via FastAPI)

### Adding a New Service

1. Create service directory:
   ```bash
   mkdir -p services/new-service
   ```

2. Add files:
   ```
   services/new-service/
   ├── Dockerfile
   ├── main.py
   └── __init__.py
   ```

3. Add to `docker-compose.yml`

4. Add to CI/CD pipeline

5. Add tests

6. Update README

### Database Migration (Future - M1)

```bash
# Create migration
alembic revision --autogenerate -m "Add payments table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Docker Issues

```bash
# Clean everything
make clean

# Rebuild from scratch
make build
make dev

# Remove all Docker data (CAUTION)
docker system prune -a --volumes
```

### Tests Failing

```bash
# Ensure services are running
make ps

# Check service health
curl http://localhost:8000/healthz
curl http://localhost:8001/healthz

# Check logs for errors
make logs

# Reset and restart
make down
make clean
make dev
```

### Import Errors

```bash
# Reinstall dependencies
make clean-venv
make install

# Or install specific package
pip install package-name
```

---

## Best Practices

### Code Organization

```python
# services/payments/
# main.py - FastAPI app and routes
# models.py - Pydantic models
# repository.py - Data access
# business.py - Business logic
# config.py - Configuration
```

### Configuration Management

```python
# Use environment variables
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://resilience:resilience@localhost:5432/resilience_db"
)
```

### Async Best Practices

```python
# Use async for I/O operations
async def get_payment(payment_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/payments/{payment_id}")
        return response.json()
```

### Security

```python
# Never log sensitive data
logger.info(f"Processing payment for user {user_id}")  # OK
logger.info(f"Credit card: {card_number}")  # ❌ NEVER

# Validate all inputs
# Use Pydantic models
# Sanitize user input
```

---

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Search [GitHub Issues](https://github.com/lotoos0/resilience-lab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lotoos0/resilience-lab/discussions)
- **API Docs**: http://localhost:8001/docs (when running)

---

## Next Steps

After mastering development:

1. Read [ARCHITECTURE.md](./ARCHITECTURE.md)
2. Read [DEPLOYMENT.md](./DEPLOYMENT.md)
3. Contribute! See [CONTRIBUTING.md](../CONTRIBUTING.md)
