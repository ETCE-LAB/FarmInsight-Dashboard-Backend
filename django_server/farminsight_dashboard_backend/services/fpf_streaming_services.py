import cv2
import asyncio
import base64
from typing import Optional
import cv2
from channels.layers import get_channel_layer
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()

async def websocket_stream(livestream_url: str,
                           groupname: str,
                           max_fps: int = 30,
                           stop_event: Optional[asyncio.Event] = None) -> None:
    """
    Read frames from livestream_url in a thread pool, encode them as JPEG + base64
    and send them to the given channels group_name via channel_layer.group_send.
    """
    loop = asyncio.get_event_loop()
    channel_layer = get_channel_layer()
    frame_interval = 1.0 / 2

    # open VideoCapture in the Executor
    cap = await loop.run_in_executor(None, cv2.VideoCapture, livestream_url)
    opened = await loop.run_in_executor(None, cap.isOpened)
    if not opened:
        if channel_layer is not None:
            await channel_layer.group_send(
                groupname,
                {"type": "camera_frame", "frame_data": "ERROR: Unable to open stream"}
            )
        await loop.run_in_executor(None, cap.release)
        return

    try:

        last_time = loop.time()
        while True:
            # optional: check stop_event
            if stop_event and stop_event.is_set():
                break

            # read frame (blocking call) im Executor
            result = await loop.run_in_executor(None, cap.read)
            if not result:
                break
            ret, frame = result
            if not ret or frame is None:
                break

            now = loop.time()
            elapsed = now - last_time
            if elapsed < frame_interval:
                # Sleep minimal, damit andere Tasks laufen können
                await asyncio.sleep(frame_interval - elapsed)
                now = loop.time()
                elapsed = now - last_time

            # JPEG encode in the Executor
            encode_result = await loop.run_in_executor(None, cv2.imencode, '.jpg', frame)
            if not encode_result or not encode_result[0]:
                last_time = now
                continue
            jpeg = encode_result[1]

            # Bytes -> base64
            b64 = base64.b64encode(jpeg.tobytes()).decode('ascii')

            # Send to channel layer
            if channel_layer is not None:
                #logger.info(f'Sending frame to group {groupname}')
                await channel_layer.group_send(
                    groupname,
                    {"type": "camera_frame", "frame_data": b64}
                )
                logger.info("Livestream frame sent")
            last_time = now

    finally:
        await loop.run_in_executor(None, cap.release)




