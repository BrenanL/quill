"""Threading utilities for Quill."""

import queue
import threading
from typing import Any, Optional


class RingBuffer:
    """Thread-safe ring buffer for audio chunks."""

    def __init__(self, maxsize: int = 50):
        """
        Initialize ring buffer.

        Args:
            maxsize: Maximum number of items in buffer
        """
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """
        Put item in buffer.

        Args:
            item: Item to add
            block: Block if buffer is full
            timeout: Timeout in seconds

        Raises:
            queue.Full: If buffer is full and block=False
        """
        self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get item from buffer.

        Args:
            block: Block if buffer is empty
            timeout: Timeout in seconds

        Returns:
            Item from buffer

        Raises:
            queue.Empty: If buffer is empty and block=False
        """
        return self._queue.get(block=block, timeout=timeout)

    def get_all(self) -> list:
        """
        Get all items from buffer (non-blocking).

        Returns:
            List of all items in buffer
        """
        items = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def clear(self) -> None:
        """Clear all items from buffer."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

    def qsize(self) -> int:
        """Get approximate size of buffer."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if buffer is empty."""
        return self._queue.empty()

    def full(self) -> bool:
        """Check if buffer is full."""
        return self._queue.full()
