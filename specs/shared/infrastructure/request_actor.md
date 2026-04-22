# `_shared/request_actor.py` — Design

> View-side helper for extracting the typed actor from an authenticated request. Introduced in initiative 004.

## Purpose

The `JwtAuthenticationMiddleware` attaches `request.user_dto: UserDTO` on every authenticated request, alongside the standard `request.user` (an ORM instance, possibly `AnonymousUser`). Views guarded by `LoginRequiredMixin` (or any subclass) need the typed DTO to pass into services without `# type: ignore` comments on `User | AnonymousUser` unions.

## Contract

```python
# _shared/request_actor.py
def actor_from_request(request: HttpRequest) -> UserDTO:
    """Return the typed actor for an authenticated request.

    Must only be called from views protected by ``LoginRequiredMixin``. If
    ``request.user_dto`` is missing — which means an anonymous request slipped
    past the login mixin — raise ``AuthenticationRequired`` so the global
    error handler issues the same redirect the mixin would.
    """
```

Returns `UserDTO`. Raises `_shared.exceptions.AuthenticationRequired` if the request is not authenticated. Never returns `None`.

## Why not `assert`?

Earlier drafts used `assert actor is not None`. `python -O` strips assertions, weakening the security-adjacent guard. Replacing with an explicit `raise AuthenticationRequired(...)` ensures the same redirect behavior whether or not the runtime is optimized.

## Call sites

Every authenticated view in 004 reads its actor through this helper:

- `intake/views/{catalog,create,mis_solicitudes,detail,cancel}.py`
- `revision/views/{queue,detail,take,finalize,cancel}.py`

Future views should follow the same pattern. Direct attribute access on `request.user` is acceptable for views that don't pass the actor downstream (e.g., `usuarios/views/me.py`), but the helper is preferred whenever a `UserDTO` is needed.

## Related

- [`audit.md`](./audit.md) — the other shared infra piece introduced in 004.
- `usuarios/middleware.py::JwtAuthenticationMiddleware` — sets `request.user_dto`.
- `_shared/exceptions.py::AuthenticationRequired` — exception this helper raises; the middleware error handler redirects to the login flow on this type.
