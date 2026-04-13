from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator


class WhatsAppListener(ABC):
    @abstractmethod
    def stream_messages(self) -> Iterator[str]:
        raise NotImplementedError


class MockWhatsAppListener(WhatsAppListener):
    """Simple listener for MVP/testing, fed from a static list."""

    def __init__(self, messages: list[str], interval_seconds: float = 0.2):
        self.messages = messages
        self.interval_seconds = interval_seconds

    def stream_messages(self) -> Iterator[str]:
        for message in self.messages:
            time.sleep(self.interval_seconds)
            yield message
