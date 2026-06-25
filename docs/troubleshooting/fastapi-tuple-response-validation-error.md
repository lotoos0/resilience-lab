# FastAPI tuple response causes HTTP 500

**Discovered:** 2026-06-06
**Service:** Payments
**Fixed in:** `fix(payments): raise HTTPException on missing payment instead of returning tuple`

---

## What happened

`GET /payments/{id}` returned HTTP 500 instead of HTTP 404 when the payment
ID didn't exist. The kind of bug that sits quietly in production until
someone notices the error rate — no alert, no obvious cause, just a generic
500 that tells the caller nothing.

## Symptoms

- Test failed with `fastapi.exceptions.ResponseValidationError`.
- The endpoint was returning a tuple:

```python
return {"error": "payment not found"}, 404
```

- Clients received HTTP 500 with no useful error message.
- Bug was silent — no test covered the negative path, so it went undetected
  until I added one.

## Why it happened

FastAPI is not Flask. `return body, status_code` is a Flask pattern — in
FastAPI, the returned tuple `(dict, int)` is treated as the response body
itself, not as body + status code.

Since the endpoint declared `Dict[str, Any]` as return type, FastAPI's
response validation choked on the tuple and the request blew up as HTTP 500.
In newer FastAPI versions the `ResponseValidationError` is raised explicitly;
in older versions or a live server the client just gets a 500 with no hint
of the real cause.

## Fix

One line — swap the tuple return for `HTTPException`:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="payment not found")
```

The endpoint now does what it should have done from the start:

```
GET /payments/{id} → HTTP 404
{"detail": "payment not found"}
```

## How I found it

Added a unit test for the negative path (`GET /payments/nonexistent-id`).
`TestClient` raised `ResponseValidationError` immediately, making the bug
impossible to miss. Without the test, this would have kept returning 500 in
production indefinitely.

## Prevention

- FastAPI is not Flask — `return body, status_code` does not work. Use
  `HTTPException` for all error responses, `JSONResponse` only when you need
  full control over headers or body.
- Always test negative paths. The happy path passing is not proof the error
  path works — they're separate code branches.
