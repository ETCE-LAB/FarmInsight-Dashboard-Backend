import logging
import asyncio
import threading
import time
from asyncio import Queue
from dataclasses import dataclass, field
from typing import Optional
from django.conf import settings
from nio import AsyncClient, RoomSendError, LoginError

# Use a SEPARATE logger that won't trigger the MatrixLogHandler
# This logger name is explicitly ignored in custom_logger.py
logger = logging.getLogger('matrix_notifier_internal')


@dataclass
class RateLimiter:
    """Token bucket rate limiter for Matrix API calls."""
    max_tokens: int = 2  # Maximum burst size
    refill_rate: float = 1.0  # Tokens per second
    tokens: float = field(default=2.0, init=False)
    last_refill: float = field(default_factory=time.time, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def acquire(self, timeout: float = 0) -> bool:
        """Try to acquire a token. Returns True if successful."""
        with self._lock:
            now = time.time()
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    def tokens_available(self) -> int:
        """Returns the number of tokens currently available."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            return int(min(self.max_tokens, self.tokens + elapsed * self.refill_rate))


@dataclass
class QueuedMessage:
    """Represents a message queued for sending."""
    room_id: str
    plain_text: str
    html_body: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0


class MatrixClient:
    # Configuration constants
    MAX_QUEUE_SIZE = 100  # Maximum messages in queue before dropping
    MAX_RETRIES = 2  # Maximum retry attempts for failed messages
    RETRY_DELAY = 5.0  # Seconds between retries

    def __init__(self):
        self.client = None
        self.loop = None
        self.is_running = False
        self._thread = None
        self._ready_event = threading.Event()
        self._message_queue: Optional[Queue] = None
        self._lock = threading.Lock()  # Lock für is_running und andere shared state
        self._rate_limiter = RateLimiter(max_tokens=5, refill_rate=1.0)  # 5 msgs/s burst, 1/s sustained
        self._processor_task = None
        self._dropped_count = 0  # Track dropped messages for monitoring
        self._send_failure_count = 0  # Track send failures

    def start_in_thread(self):
        """Starts the Matrix client in a separate thread with its own event loop."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.warning("Matrix client thread is already running.")
                return

            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="MatrixClientThread")
            self._thread.start()

        logger.info("Matrix client thread started.")

    def _run_loop(self):
        """Creates and runs the event loop in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start())
        self.loop.run_forever()

    async def start(self):
        if not all([settings.MATRIX_HOMESERVER, settings.MATRIX_USER, settings.MATRIX_PASSWORD]):
            logger.warning("Matrix notification settings are not configured.")
            return

        self._message_queue = Queue(maxsize=self.MAX_QUEUE_SIZE)
        self.client = AsyncClient(settings.MATRIX_HOMESERVER, settings.MATRIX_USER)
        try:
            login_response = await self.client.login(settings.MATRIX_PASSWORD)
            if isinstance(login_response, LoginError):
                logger.error(f"Matrix login failed: {login_response.message}")
                await self.client.close()
                self.client = None
                self._ready_event.set()  # Unblock waiters even on failure
                return

            logger.info("Matrix client logged in successfully.")

            # NOTE: We don't pre-join rooms at startup to avoid DB access in the event loop thread.
            # Rooms will be joined on-demand when sending the first message to them.
            # This prevents DB locking issues especially with SQLite in production.


            with self._lock:
                self.is_running = True
            self._ready_event.set()  # Signal that the client is ready
            # Start the message processing task
            if self._processor_task is None or self._processor_task.done():
                self._processor_task = asyncio.create_task(self._message_processor_loop())

        except Exception as e:
            logger.error(f"Matrix client startup error: {e}")
            if self.client:
                await self.client.close()
            self.client = None
            self._ready_event.set()  # Unblock waiters even on failure

    async def stop(self):
        if self.client:
            await self.client.close()
            with self._lock:
                self.is_running = False
            logger.info("Matrix client stopped.")
        if self.loop:
            self.loop.stop()

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        """Blocks until the client is ready or the timeout is reached."""
        logger.info("Waiting for Matrix client to be ready...")
        return self._ready_event.wait(timeout)

    async def _message_processor_loop(self):
        """Background task that processes messages from the queue one by one."""
        while True:
            # Thread-safe check for is_running
            with self._lock:
                running = self.is_running

            if not running:
                break

            try:
                # Wait for a message from the queue with timeout to allow checking is_running
                try:
                    room_id, plain_text, html_body = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue  # Check is_running again

                # Wait for the rate limiter to allow sending
                while not self._rate_limiter.acquire():
                    await asyncio.sleep(0.1)

                # Send the message
                await self._send_message_internal(room_id, plain_text, html_body)

                # Mark the task as done
                self._message_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                # Don't log here to avoid recursion, but sleep to prevent a tight loop on error
                await asyncio.sleep(1.0)

    async def _send_message_internal(self, room_id: str, plain_text: str, html_body: str | None = None, retry_count: int = 0):
        """Internal method to send a message with retry logic."""
        # Thread-safe check
        with self._lock:
            running = self.is_running

        if not running or not self.client:
            return
        if not room_id:
            return

        try:
            if room_id not in self.client.rooms:
                join_response = await self.client.join(room_id)
                if isinstance(join_response, RoomSendError):
                    with self._lock:
                        self._send_failure_count += 1
                    # Log this specific error as it indicates a configuration issue
                    logger.debug(f"Failed to join room {room_id}: {join_response.message}")
                    return

            content = {
                "msgtype": "m.notice",
                "body": plain_text,
            }
            if html_body:
                content["format"] = "org.matrix.custom.html"
                content["formatted_body"] = html_body

            response = await self.client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content=content
            )
            if isinstance(response, RoomSendError):
                # Check if rate limited (M_LIMIT_EXCEEDED)
                if retry_count < self.MAX_RETRIES and "limit" in str(response.message).lower():
                    await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                    await self._send_message_internal(room_id, plain_text, html_body, retry_count + 1)
                else:
                    with self._lock:
                        self._send_failure_count += 1
                    logger.debug(f"Failed to send message to room {room_id}: {response.message}")
        except Exception as e:
            # Silently fail to avoid recursion, but count the failure
            with self._lock:
                self._send_failure_count += 1
            # Use debug level to avoid spam, but still log for debugging
            logger.debug(f"Exception sending message to room {room_id}: {type(e).__name__}")

    def send_message_sync(self, room_id: str, plain_text: str, html_body: str | None = None):
        """
        Schedules sending a message from a synchronous context.
        This is thread-safe. Messages are queued and processed with rate limiting.
        """
        # Thread-safe checks
        with self._lock:
            running = self.is_running

        if not self.loop or not running or not self._message_queue:
            return

        try:
            # Use call_soon_threadsafe to safely put items in the asyncio Queue from another thread
            self.loop.call_soon_threadsafe(self._message_queue.put_nowait, (room_id, plain_text, html_body))
        except asyncio.QueueFull:
            with self._lock:
                self._dropped_count += 1
            logger.debug(f"Matrix message queue full. Dropping message for room {room_id}.")
        except RuntimeError as e:
            # Event loop might be closed
            logger.debug(f"Event loop error when queueing message: {type(e).__name__}")
        except Exception as e:
            # Log unexpected errors at debug level
            logger.debug(f"Unexpected error queueing message: {type(e).__name__}")


matrix_client = MatrixClient()


async def send_matrix_notification(room_id: str, plain_text: str, html_body: str | None = None):
    # This function is now deprecated in favor of the sync version with the queue
    # but we keep it for compatibility. It bypasses the queue.
    with matrix_client._lock:
        running = matrix_client.is_running

    if not running:
        return
    while not matrix_client._rate_limiter.acquire():
        await asyncio.sleep(0.1)
    await matrix_client._send_message_internal(room_id, plain_text, html_body)


def send_matrix_notification_sync(room_id: str, plain_text: str, html_body: str | None = None):
    """Synchronous wrapper to send a Matrix notification."""
    matrix_client.send_message_sync(room_id, plain_text, html_body)
