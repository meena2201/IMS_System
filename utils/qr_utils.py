"""
QR code utilities module for QR code scanning and processing.
"""
import cv2
import time
from .text_utils import text_to_speech


def zoom_in_on_qr_code(frame, points, zoom_factor=1.5):
    """
    Zoom into the region containing the QR code if it's smaller than a threshold.
    
    Args:
        frame (numpy.ndarray): The current video frame.
        points (numpy.ndarray): Coordinates of the detected QR code.
        zoom_factor (float): Factor by which to zoom into the QR code.
        
    Returns:
        numpy.ndarray: The processed frame (zoomed or original).
    """
    x_min = int(min(points[:, 0]))
    y_min = int(min(points[:, 1]))
    x_max = int(max(points[:, 0]))
    y_max = int(max(points[:, 1]))

    # Dimensions of the detected QR code
    qr_width = x_max - x_min
    qr_height = y_max - y_min

    # Threshold for zooming based on QR code size
    min_qr_size = 100

    # If the QR code is too small, zoom into the region
    if qr_width < min_qr_size or qr_height < min_qr_size:
        center_x = x_min + qr_width // 2
        center_y = y_min + qr_height // 2

        new_w = int(qr_width * zoom_factor)
        new_h = int(qr_height * zoom_factor)

        x_start = max(0, center_x - new_w // 2)
        y_start = max(0, center_y - new_h // 2)
        x_end = min(frame.shape[1], center_x + new_w // 2)
        y_end = min(frame.shape[0], center_y + new_h // 2)

        cropped_frame = frame[y_start:y_end, x_start:x_end]
        zoomed_frame = cv2.resize(cropped_frame, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
        return zoomed_frame

    return frame


def scan_qr_code():
    """
    Scans for a QR code using the webcam, zooming in if the QR code is too small.
    
    Features:
        - Timeout is 30 seconds.
        - The camera frame is mirrored (horizontal flip) for user-friendly preview.
        
    Returns:
        str or None: The decoded QR code data, or None if not found/cancelled.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    max_duration = 30  # seconds
    start_time = time.time()

    while True:
        # Check if maximum time exceeded
        if time.time() - start_time > max_duration:
            text = "QR scan timed out."
            text_to_speech(text)
            break

        ret, frame = cap.read()
        if not ret:
            text = "Failed to capture frame"
            text_to_speech(text)
            break

        frame = cv2.flip(frame, 1)  # Mirror the camera frame (horizontal flip)

        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(frame)

        if points is not None:
            points = points[0]
            cv2.polylines(frame, [points.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)

            # Apply zoom if QR code dimensions are below threshold
            frame = zoom_in_on_qr_code(frame, points)

            if data:
                cv2.putText(frame, data, (int(points[0][0]), int(points[0][1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                product_id = data

                cap.release()
                cv2.destroyAllWindows()
                return product_id

        cv2.imshow("QR Code Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return None

    cap.release()
    cv2.destroyAllWindows()
    return None
