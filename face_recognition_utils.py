"""
Face recognition utilities module for face detection and matching.
"""
import cv2
import numpy as np
import face_recognition
import sqlite3
import tkinter.messagebox as messagebox
import time


def load_known_encodings(db_file='DB_FILE'):
    """
    Load all face encodings from the database into memory.
    
    Args:
        db_file (str): The database file path.
        
    Returns:
        list: List of tuples (user_id, user_name, face_encoding).
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, user_name, face_encoding FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    return [(row[0], row[1], np.frombuffer(row[2], dtype=np.float64)) for row in rows]


def find_matching_face(known_encodings, test_encoding, tolerance=0.35):
    """
    Find a matching face from known encodings.
    
    Args:
        known_encodings (list): List of known face encodings (user_id, user_name, encoding).
        test_encoding (numpy.ndarray): The test face encoding to match.
        tolerance (float): The maximum distance for a match.
        
    Returns:
        tuple: (user_id, user_name) if match found, otherwise (None, None).
    """
    # Ensure the encoding is valid
    if test_encoding is None or len(test_encoding) == 0:
        return None, None

    # Calculate the distances between the test encoding and known encodings
    distances = face_recognition.face_distance([enc[2] for enc in known_encodings], test_encoding)

    # Check if distances list is not empty
    if len(distances) == 0:
        return None, None

    # Find the index of the minimum distance
    min_index = np.argmin(distances)

    if distances[min_index] <= tolerance:
        return known_encodings[min_index][:2]  # Return user_id and user_name
    
    return None, None


def recognize_user(timeout=30, db_file='DB_FILE'):
    """
    Recognize a user from the webcam using face recognition.
    
    Args:
        timeout (int): Maximum time in seconds to wait for face recognition.
        db_file (str): The database file path.
        
    Returns:
        tuple: (user_id, user_name) if recognized, (0, None) if unknown, (None, None) if cancelled.
    """
    known_encodings = load_known_encodings(db_file=db_file)
    cap = cv2.VideoCapture(0)

    frame_skip = 3
    frame_counter = 0
    start_time = time.time()

    try:
        while True:
            # Timeout check
            if time.time() - start_time > timeout:
                break

            ret, frame = cap.read()
            if not ret:
                messagebox.showwarning("Error", "Failed to capture frame.")
                break

            frame = cv2.flip(frame, 1)  # Mirror the camera frame (horizontal flip)

            frame_counter += 1
            if frame_counter % frame_skip != 0:  # Skip frames
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                user_id, user_name = find_matching_face(known_encodings, face_encoding)
                if user_id:
                    cap.release()
                    cv2.destroyAllWindows()
                    return user_id, user_name
                elif user_id is None:
                    cap.release()
                    cv2.destroyAllWindows()
                    return 0, None

            cv2.imshow("Recognize User - Press 'q' to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return None, None
