"""
Main application module for inventory management check-in/check-out system.
"""
import os
import sys
import sqlite3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from database_init import initialize_database
from ui_utils import resource_path
from product_management import check_product, show_items
from login import open_login_page
from admin_window import open_admin_window
from text_utils import text_to_speech

# Set up environment
os.environ["QT_QPA_PLATFORM"] = "xcb"

# Database file
DB_FILE = "DB_FILE"

# Initialize database
initialize_database(DB_FILE)

# Connect to database for the main window
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Setting up the main GUI
window = tk.Tk()
window.title("Check_out / check_in")
window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}")

# Button to check product
button = tk.Button(window, text="Check Product", command=lambda: check_product(tree, db_file=DB_FILE))
button.pack(pady=10)

# Label for "Recent History"
history_label = tk.Label(window, text="Recent History", font=("Arial", 15, "bold"))
history_label.pack(pady=10)

# Define the columns for the Treeview
tree = ttk.Treeview(window, columns=("product_id", "product_name", "user_id", "user_name", "check_out_time", "check_in_time"))

# Remove the default column #0
tree["show"] = "headings"

# Set the headings for each column
tree.heading("product_id", text="Product ID")
tree.column("product_id", anchor='center', width=120)

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

# Add Treeview to the window
tree.pack(padx=10, pady=10, fill="both", expand=True)

# Load and resize the admin icon image
admin_image = Image.open(resource_path("icons/admin_icon.ico"))
admin_image = admin_image.resize((50, 50))
admin_icon = ImageTk.PhotoImage(admin_image)

# Create the Admin button
admin_button = tk.Button(window, image=admin_icon, command=lambda: open_login_page(window, lambda: open_admin_window(window, DB_FILE)))
admin_button.place(x=35, y=5)

# Key bindings for functions
def on_treeview_key(event):
    """Handle treeview key events for scrolling."""
    if event.keysym == 'Up':
        tree.yview_scroll(-1, 'units')
    elif event.keysym == 'Down':
        tree.yview_scroll(1, 'units')

window.bind("<space>", lambda event: check_product(tree, db_file=DB_FILE))
tree.bind("<Up>", on_treeview_key)
tree.bind("<Down>", on_treeview_key)
window.bind("<F2>", lambda event: open_login_page(window, lambda: open_admin_window(window, DB_FILE)))

# Initial load of today's items
show_items(tree, db_file=DB_FILE)

# Start the main loop
window.mainloop()
