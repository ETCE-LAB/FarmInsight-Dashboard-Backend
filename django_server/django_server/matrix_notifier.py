import logging
import asyncio
import threading
from django.conf import settings
from nio import AsyncClient, RoomSendError, LoginError
import time

logger = logging.getLogger(__name__)


class MatrixClient:
    def __init__(self):
        self.client = None
        self.loop = None
        self.is_running = False
        self._thread = None
        self._ready_event = threading.Event()

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
            await self.client.login(settings.MATRIX_PASSWORD)
            logger.info("Matrix client logged in successfully.")

            for room_id in settings.MATRIX_ROOM_IDS.values():
                if room_id:
                    await self.client.join(room_id)
                    logger.info(f"Joined Matrix room: {room_id}")

            self.is_running = True
            self._ready_event.set()  # Signal that the client is ready
        except LoginError as e:
            logger.error(f"Matrix login failed: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Matrix client startup error: {e}")
            self.client = None

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


    async def send_message(self, room_id: str, plain_text: str, html_body: str | None = None):
        if not self.is_running:
            logger.warning("Matrix client is not running. Skipping notification.")
            return
        if not room_id:
            logger.warning("No room_id provided. Skipping notification.")
            return

        try:
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


matrix_client = MatrixClient()


async def send_matrix_notification(room_id: str, plain_text: str, html_body: str | None = None):
    await matrix_client.send_message(room_id, plain_text, html_body)
