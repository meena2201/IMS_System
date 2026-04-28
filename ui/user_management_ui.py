"""
User management UI module for managing users in the admin panel.
"""
import cv2
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import face_recognition
from db import execute_query, fetch_user_data, update_user_type, remove_user
from utils import setup_placeholder, text_to_speech
from utils import load_known_encodings as get_known_encodings
from utils import find_matching_face


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

    # Load Haar Cascade for face and eye detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    def add_user():
        """Add a new user with face recognition."""
        import time
        user_name = name_entry.get().strip()
        if not user_name:
            message_label.config(text="Please enter the Name", fg="red")
            return

        cap = cv2.VideoCapture(0)
        start_time = time.time()
        face_detected = False

        try:
            while True:
                # Check for timeout (30 seconds)
                if time.time() - start_time > 30:
                    message_label.config(text="No face detected. Operation cancelled.", fg="red")
                    break

                ret, frame = cap.read()
                if not ret:
                    message_label.config(text="Error: Failed to capture frame.", fg="red")
                    break

                frame = cv2.flip(frame, 1)

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)

                if len(faces) > 0:
                    face_detected = True
                else:
                    face_detected = False

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    face_region = gray[y:y + h, x:x + w]
                    eyes = eye_cascade.detectMultiScale(face_region)
                    if len(eyes) > 0:
                        cv2.putText(frame, "", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                        cv2.imshow("Add User - Press 'Space' to confirm", frame)
                    else:
                        cv2.imshow("Add User - Press 'Space' to confirm", frame)
                
                if len(faces) == 0:
                    cv2.imshow("Add User - Press 'Space' to confirm", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    message_label.config(text="Face capture canceled by user.", fg="red")
                    break
                elif key == ord(' '):
                    if not face_detected:
                        message_label.config(text="No face detected. Please try again.", fg="red")
                        continue
                    
                    for (x, y, w, h) in faces:
                        face_image = frame[y:y + h, x:x + w]
                        rgb_face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                        encodings = face_recognition.face_encodings(rgb_face_image)

                        if encodings:
                            face_encoding = encodings[0]
                            known_encodings = get_known_encodings(db_file=db_file)
                            
                            if known_encodings:
                                user_id, existing_user_name = find_matching_face(known_encodings, face_encoding)
                                if user_id:
                                    message_label.config(text=f"User already exists: ID={user_id}, Name={existing_user_name}", fg="red")
                                    return
                            
                            execute_query("INSERT INTO users (user_name, face_encoding) VALUES (?, ?)",
                                        (user_name, face_encoding.tobytes()), db_file=db_file)
                            message_label.config(text=f"User '{user_name}' added successfully!", fg="green")
                            refresh_user_list()
                            return
        finally:
            cap.release()
            cv2.destroyAllWindows()

    add_user_button = tk.Button(add_user_frame, text="Add User", command=add_user, width=20)
    add_user_button.grid(row=2, column=0, columnspan=2, pady=10, padx=5, sticky="nsew")

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
