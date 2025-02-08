import cv2
import asyncio

async def http_stream(livestream_url: str):
    """
    Asynchronous generator for streaming frames from an HTTP endpoint.
    """
    camera = cv2.VideoCapture(livestream_url)
    if not camera.isOpened():
        print("Could not open the camera or stream.")
        yield b"Error: Could not open the camera or stream.\r\n"
        return

    try:
        frame_interval = 1 / 5  # 5 FPS = 1 frame every 0.2 seconds (200 ms)
        last_frame_time = 0  # Initial time to track when the last frame was sent

        while True:
            # Get the current time at the start of each loop iteration
            current_time = asyncio.get_event_loop().time()

            # Capture frame, even if we are skipping it (to keep the stream going)
            success, frame = camera.read()
            if not success:
                print("Failed to grab frame.")
                break

            # Skip this frame if not enough time has passed (less than 200ms since the last frame)
            if current_time - last_frame_time < frame_interval:
                await asyncio.sleep(0.05)
                continue  # Simply skip this frame and go to the next one

            # If enough time has passed, process and send this frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Failed to encode frame.")
                continue

            # Update the last frame time after successfully sending the frame
            last_frame_time = current_time

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    finally:
        camera.release()
        print("Camera released.")


async def rtsp_stream(livestream_url:str):
    """
     Asynchronous generator for streaming frames from rtsp endpoint.
     """
    cap = cv2.VideoCapture(livestream_url)
    if not cap.isOpened():
        yield b"Error: Unable to open RTSP stream."
        return
    try:
        frame_interval = 1 / 5  # 5 FPS = 1 frame every 0.2 seconds (200 ms)
        last_frame_time = 0  # Initial time to track when the last frame was sent
        while True:
            # Get the current time at the start of each loop iteration
            current_time = asyncio.get_event_loop().time()
            ret, frame = cap.read()
            if not ret:
                break

            # Skip this frame if not enough time has passed (less than 200ms since the last frame)
            if current_time - last_frame_time < frame_interval:
                await asyncio.sleep(0.05)
                continue  # Simply skip this frame and go to the next one

            _, jpeg = cv2.imencode('.jpg', frame)
            yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
            )

            # Update the last frame time after successfully sending the frame
            last_frame_time = current_time

    finally:
        cap.release()
        print("Camera released.")
