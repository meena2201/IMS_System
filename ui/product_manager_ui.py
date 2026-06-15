"""
Product manager UI module for managing products and generating QR codes.
"""
import cv2
import tkinter as tk
from tkinter import ttk, messagebox
import os
import math
import sqlite3
from PIL import Image, ImageTk, ImageFont, ImageDraw
import qrcode


def setup_tab3(tab3, db_file='DB_FILE'):
    """
    Setup the Product Manager tab in the admin window.
    
    Args:
        tab3 (tk.Frame): The product manager tab frame.
        db_file (str): The database file path.
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    def add_item():
        """Add a new product to the inventory."""
        product_name = entry_pm.get()
        if product_name:
            cursor.execute("INSERT INTO items (product_name) VALUES (?)", (product_name,))
            conn.commit()
            entry_pm.delete(0, tk.END)
            show_items_pm()
            status_label.config(text="Product added successfully!", fg="green")
            messagebox.showinfo("Success", f"Product '{product_name}' added successfully!")
        else:
            status_label.config(text="Please enter a product name.", fg="red")

    def show_items_pm(search_term=None):
        """Display products in the tree view."""
        for row in tree_pm.get_children():
            tree_pm.delete(row)
        if search_term and search_term.strip():
            cursor.execute(
                "SELECT 'slof_' || id AS product_id, product_name FROM items WHERE product_name LIKE ? OR ('slof_' || id) LIKE ?",
                (f"%{search_term.strip()}%", f"%{search_term.strip()}%")
            )
        else:
            cursor.execute("SELECT 'slof_' || id AS product_id, product_name FROM items")
        items = cursor.fetchall()
        for item in items:
            tree_pm.insert("", tk.END, values=item)
        
        selected_item = tree_pm.selection()
        if selected_item:
            product_name = tree_pm.item(selected_item)['values'][1]
            entry_pm.delete(0, tk.END)
            entry_pm.insert(0, product_name)
        else:
            entry_pm.delete(0, tk.END)

    def generate_qr():
        """Generate and save QR code for the selected product."""
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

                            # Add text under QR code
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
        """Handle item selection in the tree view."""
        selected_item = tree_pm.selection()
        if selected_item:
            product_name = tree_pm.item(selected_item)['values'][1]
            entry_pm.delete(0, tk.END)
            entry_pm.insert(0, product_name)
        else:
            entry_pm.delete(0, tk.END)

    def on_item_double_click(event):
        selected_item = tree_pm.selection()
        if not selected_item:
            return
            
        item_values = tree_pm.item(selected_item)['values']
        product_id = str(item_values[0])
        product_name = str(item_values[1])
        
        dlg = tk.Toplevel(tab3)
        dlg.title(product_id)
        dlg.grab_set()
        dlg.resizable(False, False)
        
        tk.Label(dlg, text="Product Details", font=("Arial", 14, "bold")).pack(pady=10)
        
        f = tk.Frame(dlg, padx=20, pady=10)
        f.pack(fill="both", expand=True)
        
        tk.Label(f, text="Product ID:", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="e", pady=5, padx=5)
        tk.Label(f, text=product_id, font=("Arial", 11)).grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        tk.Label(f, text="Product Name:", font=("Arial", 11, "bold")).grid(row=1, column=0, sticky="e", pady=5, padx=5)
        
        name_var = tk.StringVar(value=product_name)
        name_entry = tk.Entry(f, textvariable=name_var, font=("Arial", 11), state="disabled", width=25)
        name_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        
        btn_frame = tk.Frame(dlg, pady=10)
        btn_frame.pack()
        
        def _edit():
            name_entry.config(state="normal")
            name_entry.focus()
            edit_btn.config(text="Save Changes", command=_save, fg="green")
            
        def _save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Warning", "Product name cannot be empty.", parent=dlg)
                return
            item_id = product_id.replace("slof_", "")
            cursor.execute("UPDATE items SET product_name=? WHERE id=?", (new_name, item_id))
            conn.commit()
            show_items_pm()
            status_label.config(text="Product modified successfully!", fg="green")
            messagebox.showinfo("Success", "Product updated successfully.", parent=dlg)
            dlg.destroy()
            
        def _remove():
            if messagebox.askyesno("Confirm Remove", f"Are you sure you want to remove this product permanently?\n\nProduct: {product_name}", parent=dlg):
                item_id = product_id.replace("slof_", "")
                cursor.execute("DELETE FROM items WHERE id=?", (item_id,))
                conn.commit()
                show_items_pm()
                status_label.config(text="Product removed successfully!", fg="red")
                messagebox.showinfo("Removed", "The product was removed.", parent=dlg)
                dlg.destroy()

        edit_btn = tk.Button(btn_frame, text="Edit", command=_edit, width=12)
        edit_btn.grid(row=0, column=0, padx=10)
        
        remove_btn = tk.Button(btn_frame, text="Remove", command=_remove, width=12, fg="red")
        remove_btn.grid(row=0, column=1, padx=10)

        def _download_qr():
            import os, math, qrcode
            from PIL import Image, ImageFont, ImageDraw
            
            box_size = max(1, math.ceil(25 / 0.264583) // 21)
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=box_size, border=2)
            qr.add_data(product_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            
            try:
                font = ImageFont.truetype("calibri.ttf", 14)
            except Exception:
                font = ImageFont.load_default()
                
            d = ImageDraw.Draw(img)
            tb = d.textbbox((0, 0), product_id, font=font)
            tw, th = tb[2]-tb[0], tb[3]-tb[1]
            iw, ih = img.size
            new_img = Image.new("RGB", (iw, ih + th + 4), "white")
            new_img.paste(img, (0, 0))
            ImageDraw.Draw(new_img).text(((iw-tw)//2, ih), product_id, font=font, fill="black")
            
            new_img.show()
            
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            path = os.path.join(downloads_dir, f"{product_id}.png")
            new_img.save(path)
            messagebox.showinfo("Downloaded", f"QR Code saved to Downloads folder:\n{path}", parent=dlg)

        dl_btn = tk.Button(dlg, text="Download QR Code", command=_download_qr, width=20)
        dl_btn.pack(pady=(0, 10))

    # Layout for Tab 3
    frame = tk.Frame(tab3)
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    title_label = tk.Label(frame, text="Product Manager", font=("Arial", 18, "bold"))
    title_label.pack(pady=10)

    entry_pm = tk.Entry(frame, width=30)
    entry_pm.pack(pady=10)

    # Search/Refresh Section
    search_frame = tk.Frame(frame)
    search_frame.place(relx=1.0, rely=0.0, anchor="ne")

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

    tree_frame = tk.Frame(frame)
    tree_frame.pack(fill="both", expand=True)

    columns = ("Product ID", "Product Name")
    tree_pm = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree_pm.heading("Product ID", text="Product ID")
    tree_pm.heading("Product Name", text="Product Name")

    tree_pm.column("Product ID", width=130, anchor="center")
    tree_pm.column("Product Name", width=250, anchor="center")

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
    entry_pm.bind("<Return>", lambda event: add_item())
    tree_pm.bind('<<TreeviewSelect>>', on_item_select)
    tree_pm.bind('<Double-1>', on_item_double_click)

    # Escape key handling
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
        if entry_pm == frame.focus_get():
            clear_entry_focus()
        elif search_entry == frame.focus_get():
            clear_search_focus()
        else:
            status_label.config(text="")
            show_items_pm()

    frame.bind_all("<Escape>", handle_esc)

    def on_click(event):
        widget = event.widget
        if widget not in (entry_pm, search_entry, add_button, search_button, refresh_button, qr_button, size_combobox):
            entry_pm.selection_clear()
            search_entry.selection_clear()
            frame.focus_set()
            status_label.config(text="")
            show_items_pm()

    frame.bind("<Button-1>", on_click)
    tree_pm.bind("<Button-1>", on_click)
    tab3.bind("<Button-1>", on_click)
