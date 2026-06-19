## Telegram Auth Error Normalization

### Goal

Normalize backend auth failures in two layers:

- `client.py` owns transport and HTTP normalization
- `auth/service.py` owns auth-flow semantics

### Client Contract

- `ClientError` and `asyncio.TimeoutError` map to `BackendUnavailableError`
- backend `5xx` maps to `BackendUnavailableError`
- `POST /telegram/login` may raise `BackendUserNotFoundError` on `404`
- other `4xx` responses map to `BackendUnexpectedResponseError`
- `POST /telegram/users` must never surface `BackendUserNotFoundError`

### Auth Service Contract

- first login may legitimately return `BackendUserNotFoundError`
- provisioning means `create user` and retry `login`
- if retry login still returns `BackendUserNotFoundError`, convert it to `AuthenticationFlowError`
- transport and backend-shape errors propagate as normalized backend errors

### Handler Contract

- handlers only react to final normalized categories:
  - `BackendNotConfiguredError`
  - `BackendUnavailableError`
  - `BackendUnexpectedResponseError`
  - `AuthenticationFlowError`

### Verification

- unit-test timeout normalization
- unit-test `404` on login vs `404` on create
- unit-test retry-login `404` after provisioning
