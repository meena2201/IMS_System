# Modular Project Structure

This project has been refactored into a clean modular architecture. Each module handles a specific responsibility.

## Module Overview

### 1. **main.py** - Main Application Entry Point
The main application file that sets up the GUI and controls the workflow.
- Sets up the main window with:
  - Check Product button
  - Recent History treeview
  - Admin login button
- Initializes the database
- Binds keyboard shortcuts (spacebar for check product, F2 for admin login)
- **Run this file to start the application**: `python main.py`

### 2. **database_utils.py** - Database Operations
Utility functions for interacting with the SQLite database.
- `execute_query()` - Execute SQL queries with optional fetch results
- `fetch_user_data()` - Get all users from database
- `update_user_type()` - Update user admin level
- `remove_user()` - Delete a user
- `hash_password()` - Hash passwords using SHA256

### 3. **database_init.py** - Database Initialization
Handles database schema setup and initialization.
- `initialize_database()` - Creates all required tables and views:
  - users (face recognition data)
  - product_history (check-in/check-out records)
  - items (product inventory)
  - logusers (admin credentials)

### 4. **ui_utils.py** - UI Utilities
Common UI utility functions.
- `on_focus_in()` - Clear placeholder text on input focus
- `on_focus_out()` - Restore placeholder text on focus out
- `setup_placeholder()` - Setup placeholder functionality
- `resource_path()` - Get correct path for resources (PyInstaller compatible)

### 5. **text_utils.py** - Text-to-Speech
Audio feedback system.
- `text_to_speech()` - Convert text to speech using pico2wave

### 6. **qr_utils.py** - QR Code Utilities
QR code scanning functionality.
- `scan_qr_code()` - Scan QR code from webcam (30-second timeout)
- `zoom_in_on_qr_code()` - Zoom into small QR codes for better detection

### 7. **face_recognition_utils.py** - Face Recognition
Face detection and matching utilities.
- `load_known_encodings()` - Load all user face encodings from database
- `find_matching_face()` - Match test encoding against known users
- `recognize_user()` - Recognize user from webcam (30-second timeout)

### 8. **product_management.py** - Product Management
Core product check-in/check-out logic.
- `check_product()` - Main workflow: scan QR → recognize user → check-in/out
- `show_items()` - Display today's product history
- `show_items_admin()` - Display all product history
- `search_product()` - Search product history
- `update_treeview()` - Update treeview with items

### 9. **login.py** - Authentication
Login and authentication system.
- `open_login_page()` - Show login modal
- `verify_login()` - Verify credentials against database

### 10. **admin_window.py** - Admin Interface
Main admin window with tabbed interface.
- `open_admin_window()` - Creates admin window with 3 tabs:
  - History (view all product history)
  - User Management (add/remove/promote users)
  - Product Manager (add/modify products, generate QR codes)

### 11. **user_management_ui.py** - User Management Tab
UI and logic for user management.
- `setup_tab2()` - Create user management tab with:
  - Add user (face capture)
  - User list
  - Change user level (Admin/User)
  - Remove user
- `load_known_encodings()` - Helper to load face encodings

### 12. **product_manager_ui.py** - Product Manager Tab
UI and logic for product management.
- `setup_tab3()` - Create product manager tab with:
  - Add product
  - Search products
  - Modify product names
  - Generate QR codes with text

## Project Dependencies

```bash
pip install opencv-python face-recognition numpy pillow qrcode[pil] tkinter sqlite3
```

## How to Run

1. Make sure all modules are in the same directory
2. Run the main file:
   ```bash
   python main.py
   ```

## Default Credentials

- Username: `admin`
- Password: `admin`

## File Structure

```
inventory_management_stemland/
├── main.py                    # Main entry point
├── database_utils.py          # Database operations
├── database_init.py           # Database initialization
├── ui_utils.py                # UI utilities
├── text_utils.py              # Text-to-speech
├── qr_utils.py                # QR code scanning
├── face_recognition_utils.py  # Face recognition
├── product_management.py      # Product check-in/out logic
├── login.py                   # Login system
├── admin_window.py            # Admin window controller
├── user_management_ui.py      # User management UI
├── product_manager_ui.py      # Product manager UI
├── DB_FILE                    # SQLite database
├── icons/
│   ├── admin_icon.ico
│   ├── reload.ico
│   └── search_icon.ico
└── README.md                  # This file
```

## Features

- **QR Code Scanning**: Scan product QR codes to check items in/out
- **Face Recognition**: Automatic user identification
- **User Management**: Admin can add/remove users and change permission levels
- **Product Inventory**: Manage products and generate QR codes
- **History Tracking**: Track all check-in/check-out records
- **Search**: Search through product history
- **Audio Feedback**: Text-to-speech notifications

## Benefits of Modular Architecture

1. **Maintainability**: Each module has a single responsibility
2. **Reusability**: Modules can be used in other projects
3. **Testability**: Easier to unit test individual modules
4. **Scalability**: Easy to add new features without modifying core code
5. **Readability**: Cleaner, more organized codebase
