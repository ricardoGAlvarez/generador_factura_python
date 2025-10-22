import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Image as RLImage
from PIL import Image
from reportlab.lib.units import cm
import datetime
import os
import sys


# ================== BASE DE DATOS ==================
def init_db():
    conn = sqlite3.connect("facturas.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            dni TEXT,          -- 👈 NUEVO CAMPO
            fecha TEXT,
            total REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER,
            producto TEXT,
            precio REAL,
            FOREIGN KEY (factura_id) REFERENCES facturas (id)
        )
    """)
    conn.commit()
    conn.close()


def resource_path(relative_path):
    """Devuelve la ruta absoluta, compatible con PyInstaller"""
    try:
        # Cuando se ejecuta empaquetado con PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Cuando se ejecuta en modo desarrollo
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ================== PDF ==================
def crear_pdf(cliente, dni, items, total, factura_id):
    nombre_archivo = f"factura_{cliente.replace(' ', '_')}_{factura_id}.pdf"
    c = canvas.Canvas(nombre_archivo, pagesize=A4)
    width, height = A4

    # ------------------ CABECERA ------------------
    logo_path = resource_path("logo.png")
    if os.path.exists(logo_path):
        try:
            img = Image.open(logo_path)
            if img.mode in ("RGBA", "LA"):  # Tiene canal alfa (transparencia)
                fondo = Image.new("RGB", img.size, (255, 255, 255))  # fondo blanco
                fondo.paste(img, mask=img.split()[3])  # usa alfa como máscara
                logo_temp = resource_path("logo_temp.jpg")
                fondo.save(logo_temp, "JPEG")
                logo_final = logo_temp
            else:
                logo_final = logo_path

            c.drawImage(logo_final, 30, height - 80, width=5 * cm, height=2.5 * cm)
        except Exception as e:
            print(f"No se pudo cargar el logo: {e}")
            c.setFont("Helvetica-Bold", 18)
            c.drawString(30, height - 50, "NOMBRE DE TU EMPRESA")
    else:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(30, height - 50, "NOMBRE DE TU EMPRESA")

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 30, height - 50, "COMPROBANTE DE PAGO")

    c.setFont("Helvetica", 12)
    c.drawRightString(width - 30, height - 70, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}")
    c.drawRightString(width - 30, height - 85, f"N°: {factura_id}")
    c.line(30, height - 95, width - 30, height - 95)

    # ------------------ DATOS DEL CLIENTE ------------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, height - 120, "Datos del Cliente:")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 140, f"Nombre y Apellido: {cliente}")
    c.drawString(30, height - 160, f"DNI: {dni}")

    c.line(30, height - 180, width - 30, height - 180)

    # ------------------ DETALLES DE LOS PRODUCTOS ------------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, height - 200, "Producto")
    c.drawRightString(width - 30, height - 200, "Precio")

    y_position = height - 220
    c.setFont("Helvetica", 12)
    for producto, precio in items:
        c.drawString(30, y_position, f"{producto}")
        c.drawRightString(width - 30, y_position, f"${precio:.2f}")
        y_position -= 20

    # ------------------ TOTAL ------------------
    c.line(30, y_position - 10, width - 30, y_position - 10)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 30, y_position - 30, f"TOTAL: ${total:.2f}")

    c.save()
    return nombre_archivo

# ================== FUNCIONES ==================
def agregar_item():
    producto = entry_producto.get()
    try:
        precio = float(entry_precio.get())
    except ValueError:
        messagebox.showerror("Error", "El precio debe ser un número.")
        return

    if producto and precio >= 0:
        tree.insert("", "end", values=(producto, precio))
        entry_producto.delete(0, tk.END)
        entry_precio.delete(0, tk.END)
    else:
        messagebox.showwarning("Atención", "Ingrese un producto y precio válidos.")


def generar_factura():
    cliente = entry_cliente.get().strip()
    dni = entry_dni.get().strip()

    if not cliente or not dni:
        messagebox.showwarning("Atención", "Ingrese el nombre y DNI del cliente.")
        return

    items = []
    total = 0
    for child in tree.get_children():
        producto, precio_str = tree.item(child, "values")
        precio = float(precio_str)
        items.append((producto, precio))
        total += precio

    if not items:
        messagebox.showwarning("Atención", "Debe agregar al menos un producto.")
        return

    conn = sqlite3.connect("facturas.db")
    cursor = conn.cursor()

    fecha = datetime.date.today().isoformat()
    cursor.execute("INSERT INTO facturas (cliente, dni, fecha, total) VALUES (?, ?, ?, ?)", 
                   (cliente, dni, fecha, total))
    factura_id = cursor.lastrowid

    for producto, precio in items:
        cursor.execute("INSERT INTO items (factura_id, producto, precio) VALUES (?, ?, ?)", 
                       (factura_id, producto, precio))

    conn.commit()
    conn.close()

    nombre_archivo = crear_pdf(cliente, dni, items, total, factura_id)
    messagebox.showinfo("Éxito", f"Factura generada correctamente ({nombre_archivo})")

    tree.delete(*tree.get_children())
    entry_cliente.delete(0, tk.END)
    entry_dni.delete(0, tk.END)

# ================== INTERFAZ ==================
root = tk.Tk()
root.title("Gestor de Comprobantes de Pago PDF")
root.geometry("600x500")

frame_cliente = tk.Frame(root)
frame_cliente.pack(pady=10)

tk.Label(frame_cliente, text="Cliente:").grid(row=0, column=0, padx=5)
entry_cliente = tk.Entry(frame_cliente, width=30)
entry_cliente.grid(row=0, column=1)

tk.Label(frame_cliente, text="DNI:").grid(row=0, column=2, padx=5)
entry_dni = tk.Entry(frame_cliente, width=15)
entry_dni.grid(row=0, column=3)

frame_items = tk.Frame(root)
frame_items.pack(pady=10)

tk.Label(frame_items, text="Producto:").grid(row=0, column=0, padx=5)
entry_producto = tk.Entry(frame_items, width=25)
entry_producto.grid(row=0, column=1)

tk.Label(frame_items, text="Precio:").grid(row=0, column=2, padx=5)
entry_precio = tk.Entry(frame_items, width=10)
entry_precio.grid(row=0, column=3)

btn_agregar = tk.Button(frame_items, text="Agregar", command=agregar_item)
btn_agregar.grid(row=0, column=4, padx=10)

tree = ttk.Treeview(root, columns=("Producto", "Precio"), show="headings", height=10)
tree.heading("Producto", text="Producto")
tree.heading("Precio", text="Precio")
tree.pack(pady=10)

btn_generar = tk.Button(root, text="Generar Comprobante de Pago", command=generar_factura, bg="green", fg="white")
btn_generar.pack(pady=20)

init_db()
root.mainloop()
