"""
User management UI module for managing users in the admin panel.
"""
import os
import sys
import warnings

# Suppress warnings and OpenCV output
warnings.filterwarnings("ignore")
os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'

import cv2
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import face_recognition
from PIL import Image, ImageTk
from db import execute_query, fetch_user_data, update_user_type, remove_user
from utils import setup_placeholder, text_to_speech
from utils import load_known_encodings as get_known_encodings
from utils import find_matching_face

# Camera device index: 0 = built-in, 1+ = external/USB cameras
CAMERA_DEVICE_INDEX = 1

def _cv2_has_gui():
    try:
        cv2.namedWindow("__test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__test__")
        return True
    except cv2.error:
        return False

_CV2_GUI = _cv2_has_gui()


def setup_tab2(parent_window, db_file='DB_FILE'):
    """
    Setup the User Management tab in the admin window.
    
    Args:
        parent_window (tk.Frame): The parent frame for the tab.
        db_file (str): The database file path.
    """
    # Page Title
    title_label = tk.Label(parent_window, text="User Management", font=("Arial", 15, "bold"))
    title_label.pack(pady=20)

    # Add User Section
    add_user_frame = tk.Frame(parent_window, padx=10, pady=10)
    add_user_frame.pack(expand=True)

    tk.Label(add_user_frame, text="Enter the Name:").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

    name_entry = tk.Entry(add_user_frame, width=30)
    name_entry.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    name_entry.placeholder = "Enter your Name"
    name_entry.bind("<Return>", lambda event: add_user())
    setup_placeholder(name_entry)

    # Camera preview label inside the panel
    camera_label = tk.Label(add_user_frame, bg="black", width=40, height=15)
    camera_label.grid(row=2, column=0, columnspan=2, pady=8)

    btn_frame = tk.Frame(add_user_frame)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=4)

    add_user_button = tk.Button(btn_frame, text="Start Camera / Add User", width=25)
    add_user_button.pack(side=tk.LEFT, padx=4)
    capture_button = tk.Button(btn_frame, text="Capture Sample (Space)", width=22, state=tk.DISABLED)
    capture_button.pack(side=tk.LEFT, padx=4)
    cancel_button = tk.Button(btn_frame, text="Cancel", width=10, state=tk.DISABLED)
    cancel_button.pack(side=tk.LEFT, padx=4)

    # Shared state between camera thread and Tkinter callbacks
    _state = {
        "cap": None,
        "running": False,
        "captured_encodings": [],
        "face_detected": False,
        "current_rgb": None,
        "current_locations": [],
        "start_time": 0,
    }
    SAMPLE_TARGET = 4

    def _largest_face_location(locations):
        if not locations:
            return None
        return max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))

    def _update_frame():
        """Poll camera in Tkinter event loop and update the preview label."""
        if not _state["running"]:
            return
        cap = _state["cap"]
        ret, frame = cap.read()
        if not ret:
            _stop_camera()
            message_label.config(text="Camera read error.", fg="red")
            return

        import time
        if time.time() - _state["start_time"] > 60:
            _stop_camera()
            message_label.config(text="Timed out. Please try again.", fg="red")
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_frame, model="hog")
        _state["face_detected"] = len(locations) > 0
        _state["current_rgb"] = rgb_frame
        _state["current_locations"] = locations

        display = frame.copy()
        for (top, right, bottom, left) in locations:
            cv2.rectangle(display, (left, top), (right, bottom), (0, 255, 0), 2)
        n = len(_state["captured_encodings"])
        cv2.putText(display, f"Samples: {n}/{SAMPLE_TARGET}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        img = Image.fromarray(cv2.cvtColor(display, cv2.COLOR_BGR2RGB))
        img.thumbnail((320, 240))
        photo = ImageTk.PhotoImage(img)
        camera_label.config(image=photo)
        camera_label.image = photo  # prevent GC

        add_user_frame.after(30, _update_frame)

    def _stop_camera():
        _state["running"] = False
        if _state["cap"]:
            _state["cap"].release()
            _state["cap"] = None
        camera_label.config(image="", bg="black")
        camera_label.image = None
        add_user_button.config(text="Start Camera / Add User", state=tk.NORMAL)
        capture_button.config(state=tk.DISABLED)
        cancel_button.config(state=tk.DISABLED)

    def _start_capture():
        user_name = name_entry.get().strip()
        if not user_name or user_name == getattr(name_entry, 'placeholder', ''):
            message_label.config(text="Please enter a name first.", fg="red")
            return
        import time
        cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            message_label.config(text="Could not open camera.", fg="red")
            return
        _state["cap"] = cap
        _state["running"] = True
        _state["captured_encodings"] = []
        _state["start_time"] = time.time()
        message_label.config(text="Camera started. Click 'Capture Sample' for each sample.", fg="blue")
        add_user_button.config(state=tk.DISABLED)
        capture_button.config(state=tk.NORMAL)
        cancel_button.config(state=tk.NORMAL)
        _update_frame()

    def _do_capture():
        if not _state["running"]:
            return
        if not _state["face_detected"]:
            message_label.config(text="No face detected. Adjust position and try again.", fg="red")
            return
        rgb_frame = _state["current_rgb"]
        locations = _state["current_locations"]
        largest = _largest_face_location(locations)
        encodings = face_recognition.face_encodings(rgb_frame, [largest], num_jitters=2)
        if not encodings:
            message_label.config(text="Could not read face clearly. Improve lighting.", fg="red")
            return
        _state["captured_encodings"].append(encodings[0])
        n = len(_state["captured_encodings"])
        message_label.config(text=f"Captured sample {n}/{SAMPLE_TARGET}", fg="green")
        if n < SAMPLE_TARGET:
            return
        # All samples collected — save user
        _stop_camera()
        user_name = name_entry.get().strip()
        known_encodings = get_known_encodings(db_file=db_file)
        if known_encodings:
            for enc in _state["captured_encodings"]:
                uid, existing_name = find_matching_face(known_encodings, enc)
                if uid:
                    message_label.config(
                        text=f"User already exists: ID={uid}, Name={existing_name}", fg="red")
                    return
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_name) VALUES (?)", (user_name,))
        user_id = cursor.lastrowid
        for enc in _state["captured_encodings"]:
            cursor.execute(
                "INSERT INTO face_encodings (user_id, face_encoding) VALUES (?, ?)",
                (user_id, enc.tobytes()))
        conn.commit()
        conn.close()
        message_label.config(text=f"User '{user_name}' added successfully!", fg="green")
        name_entry.delete(0, tk.END)
        refresh_user_list()

    def _do_cancel():
        _stop_camera()
        message_label.config(text="Capture cancelled.", fg="gray")

    add_user_button.config(command=_start_capture)
    capture_button.config(command=_do_capture)
    cancel_button.config(command=_do_cancel)

    # Allow Space key shortcut when camera is running
    add_user_frame.winfo_toplevel().bind("<space>", lambda e: _do_capture() if _state["running"] else None)

    # User List Section
    user_list_frame = tk.Frame(parent_window, padx=10, pady=10)
    user_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    tk.Label(user_list_frame, text="User List", font=("Arial", 14, "bold")).pack(anchor="w", pady=10)

    message_label = tk.Label(user_list_frame, text="", font=("Arial", 12), fg="red")
    message_label.pack(anchor='center')

    tree_frame = tk.Frame(user_list_frame)
    tree_frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(tree_frame, columns=("User ID", "User Name", "Type"), show="headings", height=15)
    tree.pack(fill="both", expand=True, side=tk.LEFT)

    for col, width in zip(["User ID", "User Name", "Type"], [100, 200, 100]):
        tree.heading(col, text=col, anchor=tk.CENTER)
        tree.column(col, anchor=tk.CENTER, width=width)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill="y")

    buttons_frame = tk.Frame(user_list_frame)
    buttons_frame.pack(fill="x", pady=10, side=tk.BOTTOM)

    selected_user_id = None

    def on_row_select(event):
        """Handle row selection in the user list."""
        nonlocal selected_user_id
        selected_item = tree.focus()
        if selected_item:
            values = tree.item(selected_item, "values")
            selected_user_id = values[0]
            change_button.config(state=tk.NORMAL)
            remove_button.config(state=tk.NORMAL)

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def show_level_options():
        """Change the user level between Admin and User."""
        current_level = execute_query("SELECT type FROM users WHERE user_id = ?", (selected_user_id,), fetch=True, db_file=db_file)
        if current_level:
            current_level = current_level[0][0]
            new_level = "Admin" if current_level == "User" else "User"
            update_user_type(selected_user_id, new_level, db_file=db_file)
            refresh_user_list()
            message_label.config(text=f"User level changed to {new_level} successfully!", fg="green")

    def remove_selected_user():
        """Remove the selected user."""
        if selected_user_id and messagebox.askyesno("Confirm", "Are you sure you want to remove this user?"):
            remove_user(selected_user_id, db_file=db_file)
            refresh_user_list()
            message_label.config(text="User removed successfully!", fg="red")

    change_button = tk.Button(buttons_frame, text="Change Level", state=tk.DISABLED, command=show_level_options, width=12)
    remove_button = tk.Button(buttons_frame, text="Remove User", state=tk.DISABLED, command=remove_selected_user, width=12)

    change_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    remove_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    buttons_frame.grid_columnconfigure(0, weight=1)
    buttons_frame.grid_columnconfigure(1, weight=1)

    def refresh_user_list():
        """Refresh the user list in the Treeview."""
        for row in tree.get_children():
            tree.delete(row)
        for user in fetch_user_data(db_file=db_file):
            tree.insert("", tk.END, values=user)

    # Initial load of user data
    refresh_user_list()
