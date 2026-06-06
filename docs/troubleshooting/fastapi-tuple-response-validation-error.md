# Troubleshooting: FastAPI tuple response causes HTTP 500

**Discovered:** 2026-06-06
**Service:** Payments
**Fixed in:** `fix(payments): raise HTTPException on missing payment instead of returning tuple`

## Problem

`GET /payments/{id}` returned HTTP 500 instead of HTTP 404 when the payment ID did not exist.

## Symptoms

- Test failed with `fastapi.exceptions.ResponseValidationError`.
- The endpoint returned a tuple:

```python
return {"error": "payment not found"}, 404
```

- Users received HTTP 500 with no useful error message.
- Bug was silent — no test covered the negative path, so it went undetected.

## Root Cause

FastAPI does not support Flask-style tuple responses to set the HTTP status code.

The returned tuple `(dict, int)` was treated as the response body. Because the endpoint declared `Dict[str, Any]` as return type, FastAPI response validation failed on the tuple and the request resulted in HTTP 500.

In newer versions of FastAPI the `ResponseValidationError` is raised explicitly. In older versions or when running as a live server, the client simply received HTTP 500 with no indication of the real cause.

## Fix

Use `HTTPException` for error responses:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="payment not found")
```

The endpoint now returns:

```
GET /payments/{id} -> HTTP 404
{
  "detail": "payment not found"
}
```

## How It Was Found

A unit test was added for the negative path (`GET /payments/nonexistent-id`). The `TestClient` raised `ResponseValidationError` directly, making the bug visible in CI.

Without the test, the bug would have remained hidden — HTTP 500 in production, no alert, no obvious cause.

## Prevention

- Never use Flask-style tuple returns in FastAPI — `return body, status_code` does not work.
- Use `HTTPException` for all error responses.
- Use `JSONResponse` only when you need full control over headers/body.
- Always add tests for negative/error paths, not only the happy path.
