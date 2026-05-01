import uuid

_store: dict[str, dict] = {}


def new_session_id() -> str:
    return uuid.uuid4().hex[:8]


def save_session(session_id: str, dfs: dict) -> None:
    _store[session_id] = dfs


def get_session(session_id: str) -> dict | None:
    return _store.get(session_id)


def clear_all() -> None:
    _store.clear()
