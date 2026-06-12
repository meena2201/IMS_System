from tkinter import ttk, messagebox
import cv2
import numpy as np
import face_recognition
import sqlite3
import tkinter as tk
from PIL import Image, ImageTk ,ImageFont, ImageDraw
import qrcode  
import math
from datetime import datetime,time
import sys
import hashlib
import os
import time
os.environ["QT_QPA_PLATFORM"] = "xcb"

# Camera device index: 0 = built-in, 1+ = external/USB cameras
CAMERA_DEVICE_INDEX = 1

def text_to_speech(text):
    os.system(f'pico2wave -w output.wav "{text}" && aplay output.wav')

# --- Database Setup ---
DB_FILE = "DB_FILE"  # Replace with your desired database file path
try:
    # Connect to SQLite database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create required tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        face_encoding BLOB NOT NULL,
        type TEXT DEFAULT 'User'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        check_out_time TEXT NOT NULL,
        check_in_time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL
    )
    """)

    # Create the formatted_items view
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS formatted_items AS 
    SELECT 'slof_' || id AS product_id, product_name
    FROM items;
    """)

    # Create logusers table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logusers (
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)

    # Function to hash passwords before storing them
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    # Insert default admin user if not exists
    cursor.execute("""
    INSERT OR IGNORE INTO logusers (username, password)
    VALUES ('admin', ?)
    """, (hash_password('admin'),))

    # Commit changes to the database
    conn.commit()

except:
    False

finally:
    # Close the database connection
    if conn:
        conn.close()

def on_focus_in(entry):
    """Clear the placeholder text when the entry box gets focus."""
    if entry.get() == entry.placeholder:
        entry.delete(0, tk.END)
        entry.config(fg='black')  # Set text color to black when user starts typing

def on_focus_out(entry):
    """Restore the placeholder text when the entry box loses focus."""
    if entry.get() == "":
        entry.insert(0, entry.placeholder)
        entry.config(fg='gray')  # Set text color to gray for placeholder text
def placeholder(entry):
    entry.bind("<FocusIn>", lambda event: on_focus_in(entry))
    entry.bind("<FocusOut>", lambda event: on_focus_out(entry))

# --- Function to search products based on the user's input ---
def search_product(entry_search, tree):
    search_term = entry_search.get().strip()  # Get and strip the search term

    try:
        # Execute the search query
        cursor.execute(""" 
            SELECT product_id, product_name, check_out_time, check_in_time, user_id, user_name 
            FROM product_history 
            WHERE product_id LIKE ? OR product_name LIKE ? OR user_id LIKE ? OR user_name LIKE ?
        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))

        items = cursor.fetchall()

        # Update the Treeview with fetched items
        update_treeview(tree, items)

    finally:
        # Clear the entry field after searching
        entry_search.delete(0, tk.END)

# --- Helper function to update the Treeview ---
def update_treeview(tree, items):
    # Clear previous items in the Treeview
    for item in tree.get_children():
        tree.delete(item)

    # Insert fetched items into the Treeview
    for item in items:
        tree.insert("", "end", values=item)

# --- Function to show all items for the admin ---
def show_items_admin(tree):
    try:
        cursor.execute(""" 
            SELECT product_id, product_name, check_out_time, check_in_time, user_id, user_name 
            FROM product_history 
            ORDER BY check_out_time DESC
        """)
        items = cursor.fetchall()

        # Update the Treeview with fetched items
        update_treeview(tree, items)

    except:
        False

def execute_query(query, params=(), fetch=False):
    """Execute database queries with optional fetch."""
    conn = sqlite3.connect('DB_FILE')  # Replace 'DB_FILE' with your database path
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result


def fetch_user_data():
    """Fetch all user data from the database."""
    return execute_query("SELECT user_id, user_name, type FROM users", fetch=True)


def update_user_type(user_id, new_type):
    """Update user type in the database."""
    execute_query("UPDATE users SET type = ? WHERE user_id = ?", (new_type, user_id))


def remove_user(user_id):
    """Remove a user from the database."""
    execute_query("DELETE FROM users WHERE user_id = ?", (user_id,))

def setp_tab2(parent_window):
    # Page Title: Centered User Management label
    title_label = tk.Label(parent_window, text="User Management", font=("Arial", 15, "bold"))
    title_label.pack(pady=20)

    # Add User Section - Center the entry box and button
    add_user_frame = tk.Frame(parent_window, padx=10, pady=10)
    add_user_frame.pack(expand=True)  # Ensure the frame expands to fill available space

    # Label, Entry, and Button centered within the add_user_frame
    tk.Label(add_user_frame, text="Enter the Name:").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    
    # Fixed width for the entry box
    name_entry = tk.Entry(add_user_frame, width=30)
    name_entry.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    name_entry.placeholder = "Enter your Name"
    # Binding the Enter key to trigger the add_user button
    name_entry.bind("<Return>", lambda event: add_user())
    placeholder(name_entry)



    # Load Haar Cascade for face and eye detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    # def add_user():
    #     user_name = name_entry.get().strip()
    #     if not user_name:
    #         message_label.config(text="Please enter the Name", fg="red")
    #         return

    #     cap = cv2.VideoCapture(0)

    #     try:
    #         while True:
    #             ret, frame = cap.read()
    #             if not ret:
    #                 message_label.config(text="Error: Failed to capture frame.", fg="red")
    #                 break

    #             # Convert frame to grayscale for Haar Cascade
    #             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #             # Detect faces in the frame
    #             faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    #             for (x, y, w, h) in faces:
    #                 # Draw rectangle around the face
    #                 cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    #                 # Focus on the face region for eye detection
    #                 face_region = gray[y:y + h, x:x + w]
    #                 eyes = eye_cascade.detectMultiScale(face_region)

    #                 # Only proceed if eyes are detected in the face region
    #                 if len(eyes) > 0:
    #                     cv2.putText(frame, "", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    #                     # Show the frame to the user
    #                     cv2.imshow("Add User - Press 'Space' to confirm", frame)

    #             # Check for 'q' key press (exit the loop if 'q' is pressed)
    #             key = cv2.waitKey(1) & 0xFF
    #             if key == ord('q'):
    #                 message_label.config(text="Face capture canceled by user.", fg="red")
    #                 break
    #             elif key == ord(' '):  # Spacebar key to confirm
    #                 # Capture and process face encoding
    #                 for (x, y, w, h) in faces:
    #                     face_image = frame[y:y + h, x:x + w]
    #                     rgb_face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
    #                     encodings = face_recognition.face_encodings(rgb_face_image)

    #                     if encodings:  # Ensure at least one encoding is found
    #                         face_encoding = encodings[0]

    #                         known_encodings = load_known_encodings()
    #                         user_id, existing_user_name = find_matching_face(known_encodings, face_encoding)
    #                         if user_id:
    #                             message_label.config(text=f"User already exists: ID={user_id}, Name={existing_user_name}", fg="red")
    #                             return

    #                         # Save encoding to database
    #                         execute_query("INSERT INTO users (user_name, face_encoding) VALUES (?, ?)",
    #                                     (user_name, face_encoding.tobytes()))
    #                         message_label.config(text=f"User '{user_name}' added successfully!", fg="green")
    #                         refresh_user_list()
    #                         return
    #     finally:
    #         cap.release()
    #         cv2.destroyAllWindows()

    def add_user():
            user_name = name_entry.get().strip()
            if not user_name:
                messagebox.showwarning("Missing Name", "Please enter the Name.")
                return
                
            try:
                conn_check = sqlite3.connect(DB_FILE)
                cursor_check = conn_check.cursor()
                cursor_check.execute("SELECT user_id FROM users WHERE LOWER(user_name) = LOWER(?)", (user_name,))
                if cursor_check.fetchone():
                    messagebox.showwarning("Duplicate Name", "This username already exists. Please add an initial or last name.")
                    conn_check.close()
                    return
                conn_check.close()
            except Exception:
                pass

            cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
            start_time = time.time()
            face_detected = False

            try:
                while True:
                    # Check for timeout (30 seconds)
                    if time.time() - start_time > 30:
                        message_label.config(text="No face detected . Operation cancelled.", fg="red")
                        break

                    ret, frame = cap.read()
                    if not ret:
                        message_label.config(text="Error: Failed to capture frame.", fg="red")
                        break

                    frame = cv2.flip(frame, 1)  # Un-mirror the camera frame (horizontal flip)

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
                            #if encodings:
                                #face_encoding = encodings[0]
                                #known_encodings = load_known_encodings()
                                #user_id, existing_user_name = find_matching_face(known_encodings, face_encoding)
                                #if user_id:
                                    #message_label.config(text=f"User already exists: ID={user_id}, Name={existing_user_name}", fg="red")
                                    #return
                                #execute_query("INSERT INTO users (user_name, face_encoding) VALUES (?, ?)",
                                            #(user_name, face_encoding.tobytes()))
                                #message_label.config(text=f"User '{user_name}' added successfully!", fg="green")
                                #refresh_user_list()
                                #return
                            
                            if encodings:
                                face_encoding = encodings[0]
                                known_encodings = load_known_encodings()
                                # Only check for duplicates if there are known encodings
                                if known_encodings:
                                    user_id, existing_user_name = find_matching_face(known_encodings, face_encoding)
                                    if user_id:
                                        message_label.config(text=f"User already exists: ID={user_id}, Name={existing_user_name}", fg="red")
                                        return
                                execute_query("INSERT INTO users (user_name, face_encoding) VALUES (?, ?)",
                                              (user_name, face_encoding.tobytes()))
                                message_label.config(text=f"User '{user_name}' added successfully!", fg="green")
                                refresh_user_list()
                                return
            finally:
                cap.release()
                cv2.destroyAllWindows()


    # Fixed size for the "Add User" button
    add_user_button = tk.Button(add_user_frame, text="Add User", command=add_user, width=20)
    add_user_button.grid(row=2, column=0, columnspan=2, pady=10, padx=5, sticky="nsew")

    # User List Section
    user_list_frame = tk.Frame(parent_window, padx=10, pady=10)
    user_list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    tk.Label(user_list_frame, text="User List", font=("Arial", 14, "bold")).pack(anchor="w", pady=10)

    # Create the message label
    message_label = tk.Label(user_list_frame, text="", font=("Arial", 12), fg="red")
    message_label.pack(anchor='center')

    tree_frame = tk.Frame(user_list_frame)
    tree_frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(tree_frame, columns=("User ID", "User Name", "Type"), show="headings", height=15)
    tree.pack(fill="both", expand=True, side=tk.LEFT)

    for col, width in zip(["User ID", "User Name", "Type"], [100, 200, 100]):
        tree.heading(col, text=col, anchor=tk.CENTER)
        tree.column(col, anchor=tk.CENTER, width=width)

    # Add scrollbar to the right side of the Treeview
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill="y")

    # Buttons for User List (Fixed at the bottom of the Treeview)
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

    # Adding event binding for row selection
    tree.bind("<<TreeviewSelect>>", on_row_select)

    def show_level_options():
        # Fetch the current user level
        current_level = execute_query("SELECT type FROM users WHERE user_id = ?", (selected_user_id,), fetch=True)
        if current_level:
            current_level = current_level[0][0]

            # Toggle the level between Admin and User
            new_level = "Admin" if current_level == "User" else "User"
            update_user_type(selected_user_id, new_level)

            # Refresh the user list and show a success message
            refresh_user_list()
            message_label.config(text=f"User level changed to {new_level} successfully!", fg="green")

    def remove_selected_user():
        """Remove the selected user."""
        if selected_user_id and messagebox.askyesno("Confirm", "Are you sure you want to remove this user?"):
            remove_user(selected_user_id)
            refresh_user_list()
            message_label.config(text="User removed successfully!", fg="red")


    # Buttons for User List (Fixed at the bottom of the Treeview)
    change_button = tk.Button(buttons_frame, text="Change Level", state=tk.DISABLED, command=show_level_options, width=12)
    remove_button = tk.Button(buttons_frame, text="Remove User", state=tk.DISABLED, command=remove_selected_user, width=12)

    # Arrange buttons horizontally below the message label
    change_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    remove_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    # Adjust column weights to ensure buttons and message label are dynamically centered
    buttons_frame.grid_columnconfigure(0, weight=1)
    buttons_frame.grid_columnconfigure(1, weight=1)

    def refresh_user_list():
        """Refresh the user list in the Treeview."""
        for row in tree.get_children():
            tree.delete(row)
        for user in fetch_user_data():
            tree.insert("", tk.END, values=user)

    # Initial load of user data
    refresh_user_list()

def setup_tab3(tab3):
    def add_item():
        product_name = entry_pm.get()
        if product_name:
            cursor.execute("INSERT INTO items (product_name) VALUES (?)", (product_name,))
            conn.commit()
            entry_pm.delete(0, tk.END)
            show_items_pm()
            status_label.config(text="Product added successfully!", fg="green")
        else:
            status_label.config(text="Please enter a product name.", fg="red")

    def show_items_pm(search_term=None):
        for row in tree_pm.get_children():
            tree_pm.delete(row)
        if search_term and search_term.strip():
            # Allow search by product_id or product_name
            cursor.execute(
                "SELECT 'slof_' || id AS product_id, product_name FROM items WHERE product_name LIKE ? OR ('slof_' || id) LIKE ?",
                (f"%{search_term.strip()}%", f"%{search_term.strip()}%")
            )
        else:
            cursor.execute("SELECT 'slof_' || id AS product_id, product_name FROM items")
        items = cursor.fetchall()
        for item in items:
            tree_pm.insert("", tk.END, values=item)
        # --- Entry box logic based on modify_button state ---
        if modify_button['state'] == tk.NORMAL:
            selected_item = tree_pm.selection()
            if selected_item:
                product_name = tree_pm.item(selected_item)['values'][1]
                entry_pm.delete(0, tk.END)
                entry_pm.insert(0, product_name)
            else:
                entry_pm.delete(0, tk.END)
        else:
            entry_pm.delete(0, tk.END)

    def modify_item():
        selected_item = tree_pm.selection()
        if selected_item:
            item_id = tree_pm.item(selected_item)['values'][0].replace('slof_', '')
            new_product_name = entry_pm.get()
            if new_product_name:
                cursor.execute("UPDATE items SET product_name = ? WHERE id = ?", (new_product_name, item_id))
                conn.commit()
                show_items_pm()
                entry_pm.delete(0, tk.END)
                status_label.config(text="Product modified successfully!", fg="green")
            else:
                status_label.config(text="Please enter a new product name.", fg="red")
        else:
            status_label.config(text="Please select an item to modify.", fg="red")

    def generate_qr():
        selected_item = tree_pm.selection()
        if selected_item:
            product_id = tree_pm.item(selected_item)['values'][0]

            if product_id.startswith('slof_'):
                item_id = product_id.replace('slof_', '')

                cursor.execute("SELECT id FROM items WHERE id = ?", (item_id,))
                fetched_id = cursor.fetchone()

                if fetched_id:
                    selected_size_mm = size_combobox.get()
                    if selected_size_mm == "Select Size":
                        status_label.config(text="Please select a QR size.", fg="red")
                    else:
                        try:
                            size_mm = int(selected_size_mm)
                            box_size_px = math.ceil(size_mm / 0.264583)
                            box_size = max(1, box_size_px // 21)

                            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=box_size,
                                border=2
                            )
                            qr.add_data(product_id)
                            qr.make(fit=True)

                            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

                            # --- Add text under QR code ---
                            font_size = 14
                            try:
                                font = ImageFont.truetype("calibri.ttf", font_size)
                            except:
                                font = ImageFont.load_default()

                            draw_dummy = ImageDraw.Draw(qr_img)
                            text_bbox = draw_dummy.textbbox((0, 0), product_id, font=font)
                            text_width = text_bbox[2] - text_bbox[0]
                            text_height = text_bbox[3] - text_bbox[1]

                            img_width, img_height = qr_img.size
                            new_height = img_height + text_height + 2

                            new_img = Image.new("RGB", (img_width, new_height), "white")
                            new_img.paste(qr_img, (0, 0))

                            draw = ImageDraw.Draw(new_img)
                            text_position = ((img_width - text_width) // 2, img_height)
                            draw.text(text_position, product_id, font=font, fill="black")

                            save_directory = "QR_codes"
                            if not os.path.exists(save_directory):
                                os.makedirs(save_directory)

                            img_path = os.path.join(save_directory, f"{product_id}.png")
                            new_img.save(img_path)
                            new_img.show()

                            status_label.config(text=f"QR Code with text saved to '{img_path}'!", fg="green")
                        except Exception as e:
                            status_label.config(text=f"Error generating QR Code: {e}", fg="red")
                else:
                    status_label.config(text="Invalid item selected.", fg="red")
            else:
                status_label.config(text="Please select a valid product (with 'slof_' prefix).", fg="red")
        else:
            status_label.config(text="Please select an item to generate QR Code.", fg="red")

    def on_item_select(event):
        selected_item = tree_pm.selection()
        if selected_item:
            modify_button.config(state=tk.NORMAL)
            # Set the entry box to the current product name
            product_name = tree_pm.item(selected_item)['values'][1]
            entry_pm.delete(0, tk.END)
            entry_pm.insert(0, product_name)
        else:
            modify_button.config(state=tk.DISABLED)
            entry_pm.delete(0, tk.END)

    # Layout for Tab 3
    frame = tk.Frame(tab3)
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    title_label = tk.Label(frame, text="Product Manager", font=("Arial", 18, "bold"))
    title_label.pack(pady=10)

    entry_pm = tk.Entry(frame, width=30)
    entry_pm.pack(pady=10)

    # --- Search/Refresh Section (fixed to right top) ---
    search_frame = tk.Frame(frame)
    search_frame.place(relx=1.0, rely=0.0, anchor="ne")  # Fixed to top-right

    search_entry = tk.Entry(search_frame, width=25)
    search_entry.pack(side="left", padx=5)

    def search_items():
        search_term = search_entry.get()
        show_items_pm(search_term)

    def refresh_items():
        search_entry.delete(0, tk.END)
        show_items_pm()

    search_button = tk.Button(search_frame, text="Search", command=search_items)
    search_button.pack(side="left", padx=5)

    refresh_button = tk.Button(search_frame, text="Refresh", command=refresh_items)
    refresh_button.pack(side="left", padx=5)

    search_entry.bind("<Return>", lambda event: search_items())

    button_frame = tk.Frame(frame)
    button_frame.pack(pady=10)

    add_button = tk.Button(button_frame, text="Add Product", command=add_item)
    add_button.pack(side="left", padx=5)

    modify_button = tk.Button(button_frame, text="Modify Name", state=tk.DISABLED, command=modify_item)
    modify_button.pack(side="left", padx=5)

    tree_frame = tk.Frame(frame)
    tree_frame.pack(fill="both", expand=True)

    columns = ("Product ID", "Product Name")
    tree_pm = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree_pm.heading("Product ID", text="Product ID")
    tree_pm.heading("Product Name", text="Product Name")

    tree_pm.column("Product ID", width=130, anchor="center")
    tree_pm.column("Product Name", width=250, anchor="center")

    # Add scrollbar to Treeview
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_pm.yview)
    tree_pm.configure(yscrollcommand=scrollbar.set)

    tree_pm.pack(fill="both", expand=True, side="left", padx=(0, 5))
    scrollbar.pack(side="right", fill="y")

    bottom_frame = tk.Frame(frame)
    bottom_frame.pack(side="bottom", pady=10)

    size_combobox = ttk.Combobox(bottom_frame, values=["Select Size", "20", "25", "30"], state="readonly", width=10)
    size_combobox.set("Select Size")
    size_combobox.pack(side="left", padx=10)

    qr_button = tk.Button(bottom_frame, text="Generate QR Code", width=20, command=generate_qr)
    qr_button.pack(side="left", padx=20)

    status_label = tk.Label(frame, text="", fg="red")
    status_label.pack(pady=10)

    show_items_pm()
    entry_pm.bind("<Return>", lambda event: modify_item() if modify_button['state'] == tk.NORMAL else add_item())
    tree_pm.bind('<<TreeviewSelect>>', on_item_select)

    # --- EXCLUSIVE FOCUS HANDLING & ESCAPE KEY ---

    def clear_entry_focus(event=None):
        entry_pm.delete(0, tk.END)
        entry_pm.selection_clear()
        frame.focus_set()
        status_label.config(text="")

    def clear_search_focus(event=None):
        search_entry.delete(0, tk.END)
        frame.focus_set()
        show_items_pm()
        status_label.config(text="")

    def handle_esc(event):
        # If entry_pm or search_entry has focus, clear and remove focus
        if entry_pm == frame.focus_get():
            clear_entry_focus()
        elif search_entry == frame.focus_get():
            clear_search_focus()
        else:
            # If not in entry, just clear status and refresh
            status_label.config(text="")
            show_items_pm()

    # Bind ESC key to clear entry/search and remove focus
    frame.bind_all("<Escape>", handle_esc)

    # Clicking outside entry/search removes focus and refreshes
    def on_click(event):
        widget = event.widget
        if widget not in (entry_pm, search_entry, add_button, modify_button, search_button, refresh_button, qr_button, size_combobox):
            entry_pm.selection_clear()
            search_entry.selection_clear()
            frame.focus_set()
            status_label.config(text="")
            show_items_pm()

    frame.bind("<Button-1>", on_click)
    tree_pm.bind("<Button-1>", on_click)
    tab3.bind("<Button-1>", on_click)
  

def open_admin_window():
    admin_window = tk.Toplevel(window)
    admin_window.title("Administrator")
    admin_window.transient(window)
    admin_window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")

    # Dictionary to store images to prevent garbage collection
    image_references = {}

    # Create a notebook (tabs container)
    notebook = ttk.Notebook(admin_window)
    notebook.pack(expand=True, fill='both')

    # Tab 1: History
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="History")

    # Title label at the center
    title_label = tk.Label(tab1, text="HISTORY", font=("Arial", 15, "bold"))
    title_label.place(relx=0.5, rely=0.02, anchor="center")

    # Search frame (slightly moved left)
    search_frame = tk.Frame(tab1)
    search_frame.place(relx=0.95, rely=0.02, anchor="ne")  # Adjusted relx from 1.0 to 0.95

    # Create and layout widgets in the search frame
    entry_search = tk.Entry(search_frame, width=20)
    entry_search.grid(row=0, column=0, padx=5, pady=5)
    entry_search.placeholder = "Search"
    entry_search.bind("<Return>", lambda event: search_product(entry_search, tree))
    placeholder(entry_search)

    # Load images and create buttons
    refresh_image = Image.open(resource_path("icons/reload.ico")).resize((15, 15))
    search_image = Image.open(resource_path("icons/search_icon.ico")).resize((15, 15))

    refresh_icon = ImageTk.PhotoImage(refresh_image)
    search_icon = ImageTk.PhotoImage(search_image)

    image_references["refresh_icon"] = refresh_icon
    image_references["search_icon"] = search_icon

    search_button = tk.Button(search_frame, image=search_icon, command=lambda: search_product(entry_search, tree))
    search_button.grid(row=0, column=2, padx=5, pady=5)

    refresh_history_button = tk.Button(search_frame, image=refresh_icon, command=lambda: show_items_admin(tree))
    refresh_history_button.grid(row=0, column=3, padx=5, pady=5)

    admin_window.bind("<F5>", lambda event: show_items_admin(tree))

    # Tree view frame (below the search frame)
    tree_frame = tk.Frame(tab1)
    tree_frame.place(relx=0.5, rely=0.1, anchor="n", relwidth=1.0, relheight=0.85)

    columns = ("Product ID", "Product Name", "Check Out Time", "Check In Time", "User ID", "User Name")
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings')

    column_widths = [80, 150, 120, 120, 80, 150]
    for col, width in zip(columns, column_widths):
        tree.heading(col, text=col)
        tree.column(col, anchor=tk.CENTER, width=width)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Prevent garbage collection by attaching the dictionary to the window
    admin_window.image_references = image_references

    def on_tab_selected(event):
        selected_tab = event.widget.select()
        tab_index = notebook.index(selected_tab)

        if tab_index == 0:  # Only call for tab1
            show_items_admin(tree)

    notebook.bind("<<NotebookTabChanged>>", on_tab_selected)

    # Tab 2: User Management
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="User Management")
    setp_tab2(tab2)  # Ensure this function is defined

    # Tab 3: Product Manager
    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Product Manager")
    setup_tab3(tab3)  # Ensure this function is defined

    admin_window.mainloop()

# Ensure the database connection remains open
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()


# --- Open Login Page ---
def open_login_page():
    login_page = tk.Toplevel(window)
    login_page.title("Login")
    login_page.geometry("300x200")
    login_page.resizable(False, False)  # Disable resizing

    tk.Label(login_page, text="User name:").pack(pady=5)
    username_entry = tk.Entry(login_page)
    username_entry.pack(pady=5)

    tk.Label(login_page, text="Password:").pack(pady=5)
    password_entry = tk.Entry(login_page, show="*")
    password_entry.pack(pady=5)

    tk.Button(login_page, text="Login", command=lambda: verify_login(username_entry, password_entry, login_page)).pack(pady=10)
    login_page.bind("<Return>", lambda event: verify_login(username_entry, password_entry, login_page))

    login_page.grab_set()  # Ensures no interaction with the main window until login page is closed
    window.wait_window(login_page)

# --- Verify Login ---
def verify_login(username_entry, password_entry, login_page):
    username = username_entry.get().strip()
    password = password_entry.get()

    if not username or not password:
        messagebox.showerror("Login Failed", "Please enter both username and password")
        return

    # Hash the entered password
    hashed_password = hash_password(password)

    try:
        # Connect to the database
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Retrieve the stored hashed password for the entered username
            cursor.execute("SELECT password FROM logusers WHERE username = ?", (username,))
            result = cursor.fetchone()

        # Check if the username exists and the hashed password matches
        if result and result[0] == hashed_password:
            login_page.destroy()  # Close the login window
            open_admin_window()  # Open the admin window (define this function as per your application)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    except:
        False
                            
def zoom_in_on_qr_code(frame, points, zoom_factor=1.5):
    """
    Zoom into the region containing the QR code if it's smaller than a threshold.
    Args:
        frame (numpy array): The current video frame.
        points (numpy array): Coordinates of the detected QR code.
        zoom_factor (float): Factor by which to zoom into the QR code.
    Returns:
        numpy array: The processed frame (zoomed or original).
    """
    x_min = int(min(points[:, 0]))
    y_min = int(min(points[:, 1]))
    x_max = int(max(points[:, 0]))
    y_max = int(max(points[:, 1]))

    # Dimensions of the detected QR code
    qr_width = x_max - x_min
    qr_height = y_max - y_min

    # Threshold for zooming based on QR code size
    min_qr_size = 100  # Adjust this as needed based on your requirements

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

    return frame  # If the QR code is not too small, return the original frame

# def scan_qr_code():
#     """
#     Scans for a QR code using the webcam, zooming in if the QR code is too small.
#     """
#     cap = cv2.VideoCapture(0)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             text="Failed to capture frame"
#             text_to_speech(text)
#             break

#         detector = cv2.QRCodeDetector()
#         data, points, _ = detector.detectAndDecode(frame)

#         if points is not None:
#             points = points[0]
#             cv2.polylines(frame, [points.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)

#             # Apply zoom if QR code dimensions are below threshold
#             frame = zoom_in_on_qr_code(frame, points)

#             if data:
#                 cv2.putText(frame, data, (int(points[0][0]), int(points[0][1] - 10)),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
#                 product_id = data

#                 cap.release()
#                 cv2.destroyAllWindows()
#                 return product_id

#         cv2.imshow("QR Code Scanner", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             cap.release()
#             cv2.destroyAllWindows()
#             return None

def scan_qr_code():
    """
    Scans for a QR code using the webcam, zooming in if the QR code is too small.
    - Timeout is 30 seconds.
    - The camera frame is mirrored (horizontal flip) for user-friendly preview.
    """
    import time
    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    max_duration = 30  # seconds (fixed to 30 seconds)
    start_time = time.time()

    while True:
        # Check if maximum time exceeded
        if time.time() - start_time > max_duration:
            text = "QR scan timed out ."
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


# Function to get the correct path in both environments
def resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and PyInstaller. """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Load All Encodings into Memory
def load_known_encodings():
    try:
        rows = execute_query(
            """
            SELECT u.user_id, u.user_name, f.face_encoding
            FROM users u
            JOIN face_encodings f ON u.user_id = f.user_id
            UNION ALL
            SELECT user_id, user_name, face_encoding
            FROM users
            WHERE face_encoding IS NOT NULL
            """,
            fetch=True,
        )
    except sqlite3.OperationalError:
        rows = execute_query("SELECT user_id, user_name, face_encoding FROM users", fetch=True)
    return [(row[0], row[1], np.frombuffer(row[2], dtype=np.float64)) for row in rows]

def find_matching_face(known_encodings, test_encoding, tolerance=0.35):
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
   
# # Recognize User
# def recognize_user():
#     known_encodings = load_known_encodings()
#     cap = cv2.VideoCapture(0)

#     frame_skip = 3
#     frame_counter = 0

#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 messagebox.WARNING("Error: Camera not found.")
#                 break

#             frame_counter += 1
#             if frame_counter % frame_skip != 0:  # Skip frames
#                 continue

#             rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             face_locations = face_recognition.face_locations(rgb_frame)
#             face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

#             for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
#                 user_id, user_name = find_matching_face(known_encodings, face_encoding)
#                 if user_id:
#                     return user_id, user_name
#                 elif user_id is None:
#                     cap.release()
#                     cv2.destroyAllWindows()
#                     return 0,None
                
                
#             cv2.imshow("Recognize User - Press 'q' to quit", frame)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
                    
#     finally:
#         cap.release()
#         cv2.destroyAllWindows()
#     return None, None

# Recognize User
def recognize_user():
    known_encodings = load_known_encodings()
    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)

    frame_skip = 3
    frame_counter = 0
    timeout = 30  # seconds
    start_time = time.time()

    try:
        while True:
            # Timeout check
            if time.time() - start_time > timeout:
                # messagebox.showwarning("Timeout", "Face recognition timed out .")
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


# Function to show today's items in the Treeview
def show_items():
    global tree, scrollbar
    
    # Get today's date in the format YYYY-MM-DD
    today_date = datetime.today().strftime('%Y-%m-%d')
    
    try:
        conn = sqlite3.connect("DB_FILE")
        cursor = conn.cursor()

        # SQL query to filter data by today's date
        query = """
        SELECT product_id, product_name, user_id, user_name, check_out_time, check_in_time
        FROM product_history
        WHERE DATE(check_out_time) = ?
        ORDER BY check_out_time DESC
        """
        
        cursor.execute(query, (today_date,))
        items = cursor.fetchall()

        # Clear existing items in the Treeview
        tree.delete(*tree.get_children())

        # Insert rows into TreeView
        for row in items:
            tag = 'checked_in' if row[5] else 'checked_out'
            tree.insert("", "end", values=row, tags=(tag,))

    except:
        False
    finally:
        if conn:
            conn.close()

# Check product function to handle QR scanning and product check-in/check-out
def check_product():
    product_id = scan_qr_code()
    
    if product_id is None:
        # text = "Cancelled by user"
        # text_to_speech(text)
        return
    else:
        product_id = product_id.strip()  # Strip the product_id only if it is not None
        
        try:
            with sqlite3.connect('DB_FILE') as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT product_id, product_name FROM formatted_items WHERE product_id = ?", (product_id,))
                result = cursor.fetchone()

                if result:
                    product_name = result[1]
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    cursor.execute("SELECT * FROM product_history WHERE product_id = ? AND check_in_time IS NULL", (product_id,))
                    checked_out_record = cursor.fetchone()

                    if checked_out_record:
                        check_out_time = checked_out_record[5]
                        user_id = checked_out_record[3]
                        user_name = checked_out_record[4]

                        cursor.execute("""UPDATE product_history 
                                        SET check_in_time = ? 
                                        WHERE product_id = ? AND check_in_time IS NULL""",
                                    (current_time, product_id))
                        conn.commit()

                        # Update TreeView: remove the previous "checked out" entry and insert the "checked in" entry
                        tree.delete(*tree.get_children())  # Clear existing rows
                        show_items()  # Refresh TreeView by calling show_items

                        text = f"Checked in successfully: {product_id}"
                        text_to_speech(text)

                    else:
                        user_id, user_name = recognize_user()

                        if user_id == 0:
                            text = "Unknown user, please contact the administrator."
                            text_to_speech(text)
                            return
                        elif user_id is None:
                            text = "operation cancelled ."
                            text_to_speech(text)
                            return
                        else:
                            cursor.execute("""INSERT INTO product_history (product_id, product_name, user_id, user_name, check_out_time, check_in_time)
                                        VALUES (?, ?, ?, ?, ?, NULL)""", (product_id, product_name, user_id, user_name, current_time))
                            conn.commit()

                            # Update TreeView after check-out by calling show_items
                            tree.delete(*tree.get_children())  # Clear existing rows
                            show_items()  # Refresh TreeView

                            text = f"Checked out successfully: {product_id}"
                            text_to_speech(text)

                else:
                    text = "Invalid QR code"
                    text_to_speech(text)

        except sqlite3.Error as e:
            text = f"Database error: {e},contact the administrator"
            text_to_speech(text)

# Bind keys for scrolling
def on_treeview_key(event):
    if event.keysym == 'Up':
        tree.yview_scroll(-1, 'units')
    elif event.keysym == 'Down':
        tree.yview_scroll(1, 'units')

# Setting up the GUI
window = tk.Tk()
window.title("Check_out / check_in")
window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")

# Button to check product
button = tk.Button(window, text="Check Product", command=check_product)
button.pack(pady=10)

# Label for "Recent History"
history_label = tk.Label(window, text="Recent History", font=("Arial", 15,"bold"))
history_label.pack(pady=10)

# # Define the columns for the Treeview (no #0 column here)
tree = ttk.Treeview(window, columns=("product_id", "product_name", "user_id", "user_name", "check_out_time", "check_in_time"))

# # Remove the default column #0 by setting it to be hidden
tree["show"] = "headings"  # This removes the #0 column (index column)

# Set the headings for each column in the correct order
tree.heading("product_id", text="Product ID")
tree.column("product_id", anchor='center', width=120)  # Left-align product_id

tree.heading("product_name", text="Product Name")
tree.column("product_name", anchor='center', width=200)

tree.heading("user_id", text="User ID")
tree.column("user_id", anchor='center', width=100)

tree.heading("user_name", text="User Name")
tree.column("user_name", anchor='center', width=150)

tree.heading("check_out_time", text="Check Out Time")
tree.column("check_out_time", anchor='center', width=215)

tree.heading("check_in_time", text="Check In Time")
tree.column("check_in_time", anchor='center', width=215)

# Configure row colors based on status
tree.tag_configure('checked_out', background='lightblue')
tree.tag_configure('checked_in', background='lightgreen')

# Add Scrollbar for Treeview
scrollbar = ttk.Scrollbar(window, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side="right", fill="y")

# Add Treeview to the window and make it fill the space
tree.pack(padx=10, pady=10, fill="both", expand=True)

# Load and resize the admin icon image
admin_image = Image.open(resource_path("icons/admin_icon.ico"))
admin_image = admin_image.resize((50, 50))  # Resize the image for the button
admin_icon = ImageTk.PhotoImage(admin_image)

# Create the Admin button with the user icon and position it next to the help button
admin_button = tk.Button(window, image=admin_icon, command=lambda: open_login_page())
admin_button.place(x=35, y=5)  # Position next to the help button

# Key bindings for functions

window.bind("<space>", lambda event: check_product())
tree.bind("<Up>", on_treeview_key)
tree.bind("<Down>", on_treeview_key)
window.bind("<F2>", lambda event: open_login_page())

show_items()

# Start the main loop
window.mainloop()
