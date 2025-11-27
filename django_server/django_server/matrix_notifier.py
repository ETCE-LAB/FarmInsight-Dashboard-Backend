import logging
import asyncio
import threading
from collections import deque
from django.conf import settings
from nio import AsyncClient, RoomSendError, LoginError
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class MatrixClient:
    def __init__(self):
        self.client = None
        self.loop = None
        self.is_running = False
        self._thread = None
        self._ready_event = threading.Event()
        self._message_queue = deque()

    def start_in_thread(self):
        """Starts the Matrix client in a separate thread with its own event loop."""
        if self._thread and self._thread.is_alive():
            logger.warning("Matrix client thread is already running.")
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

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

            try:
                # This function will run in a separate thread,
                # so it's safe to run synchronous DB code.
                def get_room_ids_sync():
                    # Import here to avoid circular dependencies on startup
                    from farminsight_dashboard_backend.models import Notification

                    # Your exact query
                    room_ids = list(Notification.objects.values_list('room_id', flat=True))
                    return room_ids

                # Run the synchronous function in an async-safe way
                room_ids = await sync_to_async(get_room_ids_sync, thread_sensitive=True)()

                if not room_ids:
                    logger.warning("No Matrix rooms found in the database. No rooms will be joined.")
                else:
                    for room_id in room_ids:
                        if room_id:
                            join_response = await self.client.join(room_id)
                            if isinstance(join_response, RoomSendError):
                                logger.error(f"Failed to join Matrix room {room_id}: {join_response.message}")
                            else:
                                logger.info(f"Joined Matrix room: {room_id}")

            except Exception as e:
                logger.error(f"Failed to query or join Matrix rooms from database: {e}")

            self.is_running = True
            self._ready_event.set()  # Signal that the client is ready
            # Process any messages that were queued before the client was ready
            asyncio.run_coroutine_threadsafe(self._process_message_queue(), self.loop)

        except Exception as e:
            logger.error(f"Matrix client startup error: {e}")
            if self.client:
                await self.client.close()
            self.client = None
            self._ready_event.set()  # Unblock waiters even on failure

    async def stop(self):
        if self.client:
            await self.client.close()
            self.is_running = False
            logger.info("Matrix client stopped.")
        if self.loop:
            self.loop.stop()

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        """Blocks until the client is ready or the timeout is reached."""
        logger.info("Waiting for Matrix client to be ready...")
        return self._ready_event.wait(timeout)

    async def _process_message_queue(self):
        logger.info(f"Processing {len(self._message_queue)} queued Matrix messages.")
        while self._message_queue:
            room_id, plain_text, html_body = self._message_queue.popleft()
            await self.send_message(room_id, plain_text, html_body)


    async def send_message(self, room_id: str, plain_text: str, html_body: str | None = None):
        if not self.is_running:
            logger.warning("Matrix client is not running. Skipping notification.")
            return
        if not room_id:
            logger.warning("No room_id provided. Skipping notification.")
            return

        try:
            if room_id not in self.client.rooms:
                logger.info(f"Not a member of room {room_id}, joining now.")
                join_response = await self.client.join(room_id)
                if isinstance(join_response, RoomSendError):
                    logger.error(f"Failed to join Matrix room {room_id}: {join_response.message}")
                    return
                logger.info(f"Successfully joined room {room_id}")

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
                logger.error(f"Failed to send Matrix notification: {response.message}")
        except Exception as e:
            logger.error(f"Error sending Matrix notification: {e}")

    def send_message_sync(self, room_id: str, plain_text: str, html_body: str | None = None):
        """
        Schedules sending a message from a synchronous context.
        This is thread-safe.
        """
        if not self.is_running:
            # If the client isn't ready, queue the message instead of blocking.
            logger.debug("Matrix client not ready, queueing message.")
            self._message_queue.append((room_id, plain_text, html_body))
            return

        if not self.loop:
            logger.error("Matrix client event loop is not available. Cannot send message.")

        # Schedule the async send_message coroutine to run on the client's event loop
        asyncio.run_coroutine_threadsafe(
            self.send_message(room_id, plain_text, html_body), self.loop
        )


matrix_client = MatrixClient()


async def send_matrix_notification(room_id: str, plain_text: str, html_body: str | None = None):
    await matrix_client.send_message(room_id, plain_text, html_body)


def send_matrix_notification_sync(room_id: str, plain_text: str, html_body: str | None = None):
    """Synchronous wrapper to send a Matrix notification."""
    matrix_client.send_message_sync(room_id, plain_text, html_body)
