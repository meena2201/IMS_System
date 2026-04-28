"""
Login and authentication module.
"""
import sqlite3
import tkinter as tk
from tkinter import messagebox
from db import hash_password


def open_login_page(window, open_admin_window_callback):
    """
    Open the login page as a modal dialog.
    
    Args:
        window (tk.Tk): The parent window.
        open_admin_window_callback (callable): Callback function to open admin window after login.
    """
    login_page = tk.Toplevel(window)
    login_page.title("Login")
    login_page.geometry("300x200")
    login_page.resizable(False, False)

    tk.Label(login_page, text="User name:").pack(pady=5)
    username_entry = tk.Entry(login_page)
    username_entry.pack(pady=5)

    tk.Label(login_page, text="Password:").pack(pady=5)
    password_entry = tk.Entry(login_page, show="*")
    password_entry.pack(pady=5)

    tk.Button(login_page, text="Login", 
              command=lambda: verify_login(username_entry, password_entry, login_page, open_admin_window_callback)).pack(pady=10)
    
    login_page.bind("<Return>", lambda event: verify_login(username_entry, password_entry, login_page, open_admin_window_callback))

    login_page.grab_set()
    window.wait_window(login_page)


def verify_login(username_entry, password_entry, login_page, open_admin_window_callback, db_file='DB_FILE'):
    """
    Verify login credentials against the database.
    
    Args:
        username_entry (tk.Entry): The username entry widget.
        password_entry (tk.Entry): The password entry widget.
        login_page (tk.Toplevel): The login window.
        open_admin_window_callback (callable): Callback to open admin window.
        db_file (str): The database file path.
    """
    username = username_entry.get().strip()
    password = password_entry.get()

    if not username or not password:
        messagebox.showerror("Login Failed", "Please enter both username and password")
        return

    # Hash the entered password
    hashed_password = hash_password(password)

    try:
        # Connect to the database
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            # Retrieve the stored hashed password for the entered username
            cursor.execute("SELECT password FROM logusers WHERE username = ?", (username,))
            result = cursor.fetchone()

        # Check if the username exists and the hashed password matches
        if result and result[0] == hashed_password:
            login_page.destroy()
            open_admin_window_callback()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    except Exception as e:
        messagebox.showerror("Error", f"Database error: {e}")
