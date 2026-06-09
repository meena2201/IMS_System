"""
FAISS-based Face Recognition Module
Fast and scalable face matching using FAISS
"""
import os
import sys
import warnings

# Suppress warnings and OpenCV output
warnings.filterwarnings("ignore")
os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'

import cv2
import numpy as np
import face_recognition
import sqlite3
import time
import pickle
from collections import Counter
import faiss

# Camera device index: 0 = built-in, 1+ = external/USB cameras
CAMERA_DEVICE_INDEX = 1


# -------------------------------
# 🔹 Load Encodings from Database
# -------------------------------
def _load_known_encodings_faiss(db_file='DB_FILE'):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT u.user_id, u.user_name, f.face_encoding
            FROM users u
            JOIN face_encodings f ON u.user_id = f.user_id
            UNION ALL
            SELECT user_id, user_name, face_encoding
            FROM users
            WHERE face_encoding IS NOT NULL
            """
        )
    except sqlite3.OperationalError:
        cursor.execute("SELECT user_id, user_name, face_encoding FROM users")

    rows = cursor.fetchall()
    conn.close()

    encodings = []
    labels = []

    for row in rows:
        try:
            # Unpickle the encoding data from database
            encoding = pickle.loads(row[2])
            
            # Convert to numpy array if needed
            if not isinstance(encoding, np.ndarray):
                encoding = np.array(encoding)
            
            # Ensure it's float32 for FAISS
            encoding = encoding.astype(np.float32)

            # Safety check - face_recognition encodings are 128-dimensional
            if encoding.shape[0] != 128:
                continue

            encodings.append(encoding)
            labels.append((row[0], row[1]))
        except (pickle.UnpicklingError, ValueError, TypeError):
            # Skip corrupted entries
            continue

    if len(encodings) == 0:
        return np.array([]), []

    return np.array(encodings).astype('float32'), labels


# -------------------------------
# 🔹 Build FAISS Index
# -------------------------------
def build_faiss_index(embeddings):
    dimension = embeddings.shape[1]  # should be 128

    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index


# -------------------------------
# 🔹 Match Face using FAISS
# -------------------------------
def find_matching_face_faiss(index, labels, test_encoding, threshold=0.5):
    if test_encoding is None or len(test_encoding) == 0:
        return None, None

    test_encoding = np.array([test_encoding]).astype('float32')

    distances, indices = index.search(test_encoding, k=1)

    distance = distances[0][0]
    idx = indices[0][0]

    print("FAISS Distance:", distance)

    if distance <= threshold:
        return labels[idx]

    return None, None


# -------------------------------
# 🔹 Optional: Preprocessing
# -------------------------------
def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return cv2.cvtColor(equalized, cv2.COLOR_GRAY2RGB)


# -------------------------------
# 🔹 Recognize User (Main Function)
# -------------------------------
def _recognize_user_faiss(timeout=30, db_file='face_db.sqlite', threshold=0.5, votes_needed=3, frame_skip=2, show_preview=False):
    """FAISS recognition with simple voting across frames.

    Args:
        timeout (int): seconds to wait
        db_file (str): database path
        threshold (float): distance threshold for FAISS match
        votes_needed (int): number of matching frames required to accept a user
        frame_skip (int): process every Nth frame to reduce CPU
    """
    embeddings, labels = _load_known_encodings_faiss(db_file)

    if len(embeddings) == 0:
        print("No face data found in database.")
        return None, None

    index = build_faiss_index(embeddings)

    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)

    # Improve camera quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    results = []
    start_time = time.time()
    frame_counter = 0

    try:
        while True:
            if time.time() - start_time > timeout:
                print("Timeout reached.")
                break

            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame.")
                break

            frame = cv2.flip(frame, 1)

            frame_counter += 1
            if frame_counter % frame_skip != 0:
                # Skip heavy processing on some frames. Only show preview when
                # explicitly requested (and when running in main thread).
                if show_preview:
                    cv2.imshow("FAISS Face Recognition - Press 'q' to quit", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        return 'CANCELLED', None
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=2)

            for face_encoding in face_encodings:
                user_id, user_name = find_matching_face_faiss(index, labels, face_encoding, threshold=threshold)
                if user_id:
                    results.append((user_id, user_name))

            # Voting system (reduce false positives)
            if len(results) >= votes_needed:
                most_common = Counter(results).most_common(1)[0][0]
                print(f"Recognized: {most_common}")
                return most_common

            # Draw bounding boxes
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Show preview only when requested. Avoid calling OpenCV GUI
            # functions from background threads.
            if show_preview:
                cv2.imshow("FAISS Face Recognition - Press 'q' to quit", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    # Explicit cancel by user
                    return 'CANCELLED', None

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return None, None


# -------------------------------
# 🔹 Backwards-compatible wrapper API
# -------------------------------
def load_known_encodings(db_file='DB_FILE'):
    """Return list of tuples (user_id, user_name, encoding) for legacy callers."""
    embeddings, labels = _load_known_encodings_faiss(db_file)
    if embeddings.size == 0:
        return []

    results = []
    for i, (uid, uname) in enumerate(labels):
        enc = embeddings[i].astype(np.float64)
        results.append((uid, uname, enc))
    return results


def find_matching_face(known_encodings, test_encoding, tolerance=0.55):
    """Legacy matching function: uses FAISS when available, falls back to face_distance."""
    if test_encoding is None or len(test_encoding) == 0:
        return None, None

    if len(known_encodings) == 0:
        return None, None

    try:
        embeddings = np.array([enc[2] for enc in known_encodings]).astype('float32')
        labels = [(enc[0], enc[1]) for enc in known_encodings]
        index = build_faiss_index(embeddings)
        uid_name = find_matching_face_faiss(
            index,
            labels,
            test_encoding.astype('float32'),
            threshold=tolerance,
        )
        if uid_name is not None:
            return uid_name
    except Exception:
        distances = face_recognition.face_distance([enc[2] for enc in known_encodings], test_encoding)
        if len(distances) == 0:
            return None, None
        min_index = np.argmin(distances)
        if distances[min_index] <= tolerance:
            return known_encodings[min_index][:2]

    return None, None


def recognize_user(timeout=30, db_file='DB_FILE'):
    """Legacy recognize_user wrapper that maps FAISS behavior to previous return codes.

    Returns (user_id, user_name) if recognized, (0, None) if unknown, (None, None) if cancelled.
    """
    result = _recognize_user_faiss(timeout=timeout, db_file=db_file, threshold=0.55)
    if isinstance(result, tuple):
        if result[0] == 'CANCELLED':
            return None, None
        if result[0] is None:
            return 0, None
        # result is (user_id, user_name)
        return result

    return None, None


# -------------------------------
# 🔹 Run Directly
# -------------------------------
if __name__ == "__main__":
    user_id, user_name = recognize_user_faiss(timeout=30)

    if user_id:
        print(f"✅ User Recognized: {user_name} (ID: {user_id})")
    else:
        print("❌ No user recognized")