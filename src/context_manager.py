from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


class DialogContext:
    """Хранит последние сообщения диалога для каждого chat_id."""

    def __init__(self, max_pairs: int = 8) -> None:
        self._max_messages = max_pairs * 2
        self._storage: dict[int, deque[ChatMessage]] = defaultdict(
            lambda: deque(maxlen=self._max_messages)
        )

    def add_user(self, chat_id: int, text: str) -> None:
        self._storage[chat_id].append(ChatMessage("user", text))

    def add_assistant(self, chat_id: int, text: str) -> None:
        self._storage[chat_id].append(ChatMessage("assistant", text))

    def get_messages(self, chat_id: int) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self._storage[chat_id]]

    def clear(self, chat_id: int) -> None:
        self._storage.pop(chat_id, None)
