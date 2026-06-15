"""
ServeQuick - Vehicle Service Management System
Python + MySQL + Tkinter | SRM Institute of Science and Technology
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re

# ─── Try importing mysql.connector ──────────────────────────────────────────
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# ════════════════════════════════════════════════════════════════════════════
#  THEME CONSTANTS
# ════════════════════════════════════════════════════════════════════════════
BG_DARK     = "#0f172a"   # main background
BG_SIDEBAR  = "#1e293b"   # sidebar
BG_CARD     = "#1e293b"   # card background
BG_PANEL    = "#0f172a"   # content panel
ACCENT      = "#3b82f6"   # blue accent
ACCENT_2    = "#10b981"   # green accent
ACCENT_3    = "#f59e0b"   # amber
ACCENT_4    = "#ef4444"   # red
TEXT_PRI    = "#f1f5f9"   # primary text
TEXT_SEC    = "#94a3b8"   # secondary text
TEXT_MUT    = "#475569"   # muted text
BORDER      = "#334155"   # border colour
ROW_ODD     = "#1e293b"
ROW_EVEN    = "#162032"
ROW_SEL     = "#1d4ed8"

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_HEAD   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 10)

# Card colour palette
CARD_COLORS = [ACCENT, ACCENT_2, ACCENT_3, "#8b5cf6", ACCENT_4]

# ════════════════════════════════════════════════════════════════════════════
#  DATABASE MANAGER
# ════════════════════════════════════════════════════════════════════════════
class DatabaseManager:
    def __init__(self):
        self.conn   = None
        self.cursor = None
        self.config = {
            "host":     "localhost",
            "user": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "database": "vehicles_service_db",
            "autocommit": False,
        }

    # ── Connection ──────────────────────────────────────────────────────────
    def connect(self, host="localhost", user="root", password="admin",
                database="vehicles_service_db"):
        if not MYSQL_AVAILABLE:
            raise RuntimeError("supp")
        self.config.update(host=host, user=user,
                           password=password, database=database)
        self.conn   = mysql.connector.connect(**self.config)
        self.cursor = self.conn.cursor(buffered=True)
        self._init_schema()

    def disconnect(self):
        try:
            if self.cursor: self.cursor.close()
            if self.conn:   self.conn.close()
        except Exception:
            pass
        self.conn = self.cursor = None

    def is_connected(self):
        return self.conn is not None and self.conn.is_connected()

    # ── Auto-reconnect execute ──────────────────────────────────────────────
    def execute(self, query, params=None, many=False):
        """Execute a query, auto-reconnecting on stale connections."""
        for attempt in range(2):
            try:
                if not self.is_connected():
                    self.conn   = mysql.connector.connect(**self.config)
                    self.cursor = self.conn.cursor(buffered=True)
                if many:
                    self.cursor.executemany(query, params or [])
                elif params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                return True
            except Error as e:
                if attempt == 0:
                    try:
                        self.conn   = mysql.connector.connect(**self.config)
                        self.cursor = self.conn.cursor(buffered=True)
                    except Exception:
                        pass
                else:
                    raise e
        return False

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def commit(self):
        if self.conn: self.conn.commit()

    def rollback(self):
        if self.conn: self.conn.rollback()

    def lastrowid(self):
        return self.cursor.lastrowid

    # ── Schema initialisation ───────────────────────────────────────────────
    def _init_schema(self):
        """Create all 8 tables if they do not exist yet."""
        stmts = [
            """CREATE TABLE IF NOT EXISTS Customer (
                customer_id  INT AUTO_INCREMENT PRIMARY KEY,
                name         VARCHAR(100) NOT NULL,
                phone        VARCHAR(15)  NOT NULL UNIQUE,
                email        VARCHAR(100),
                address      TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS Vehicle (
                vehicle_id           INT AUTO_INCREMENT PRIMARY KEY,
                customer_id          INT NOT NULL,
                registration_number  VARCHAR(20) NOT NULL UNIQUE,
                make                 VARCHAR(50) NOT NULL,
                model                VARCHAR(50) NOT NULL,
                year                 INT,
                color                VARCHAR(30),
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS Booking (
                booking_id    INT AUTO_INCREMENT PRIMARY KEY,
                customer_id   INT NOT NULL,
                vehicle_id    INT NOT NULL,
                booking_date  DATE NOT NULL,
                service_type  VARCHAR(100) NOT NULL,
                status        ENUM('Pending','In Progress','Completed','Cancelled')
                              DEFAULT 'Pending',
                notes         TEXT,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
                FOREIGN KEY (vehicle_id)  REFERENCES Vehicle(vehicle_id)
            )""",
            """CREATE TABLE IF NOT EXISTS Service (
                service_id    INT AUTO_INCREMENT PRIMARY KEY,
                booking_id    INT NOT NULL,
                service_name  VARCHAR(100) NOT NULL,
                description   TEXT,
                labour_cost   DECIMAL(10,2) DEFAULT 0.00,
                start_date    DATE,
                end_date      DATE,
                technician    VARCHAR(100),
                FOREIGN KEY (booking_id) REFERENCES Booking(booking_id)
                    ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS SparePart (
                part_id        INT AUTO_INCREMENT PRIMARY KEY,
                part_name      VARCHAR(100) NOT NULL,
                part_number    VARCHAR(50)  UNIQUE,
                unit_price     DECIMAL(10,2) NOT NULL,
                stock_quantity INT DEFAULT 0,
                supplier       VARCHAR(100)
            )""",
            """CREATE TABLE IF NOT EXISTS SparepartUsage (
                usage_id    INT AUTO_INCREMENT PRIMARY KEY,
                service_id  INT NOT NULL,
                part_id     INT NOT NULL,
                quantity    INT NOT NULL DEFAULT 1,
                total_cost  DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (service_id) REFERENCES Service(service_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (part_id)    REFERENCES SparePart(part_id)
            )""",
            """CREATE TABLE IF NOT EXISTS Bill (
                bill_id       INT AUTO_INCREMENT PRIMARY KEY,
                booking_id    INT NOT NULL UNIQUE,
                service_cost  DECIMAL(10,2) DEFAULT 0.00,
                parts_cost    DECIMAL(10,2) DEFAULT 0.00,
                tax_percent   DECIMAL(5,2)  DEFAULT 18.00,
                discount      DECIMAL(10,2) DEFAULT 0.00,
                total_amount  DECIMAL(10,2) NOT NULL,
                bill_date     DATE NOT NULL,
                status        ENUM('Unpaid','Paid','Partial') DEFAULT 'Unpaid',
                FOREIGN KEY (booking_id) REFERENCES Booking(booking_id)
            )""",
            """CREATE TABLE IF NOT EXISTS Payment (
                payment_id     INT AUTO_INCREMENT PRIMARY KEY,
                bill_id        INT NOT NULL,
                amount_paid    DECIMAL(10,2) NOT NULL,
                payment_date   DATE NOT NULL,
                payment_mode   ENUM('Cash','Card','UPI','Net Banking','Cheque')
                               DEFAULT 'Cash',
                reference_no   VARCHAR(50),
                FOREIGN KEY (bill_id) REFERENCES Bill(bill_id)
                    ON DELETE CASCADE
            )""",
        ]
        for s in stmts:
            self.cursor.execute(s)
        self.conn.commit()

# ════════════════════════════════════════════════════════════════════════════
#  REUSABLE UI WIDGETS
# ════════════════════════════════════════════════════════════════════════════
class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, color=ACCENT,
                 text_color=TEXT_PRI, width=12, **kwargs):
        super().__init__(
            parent, text=text, command=command,
            bg=color, fg=text_color,
            activebackground=color, activeforeground=TEXT_PRI,
            font=FONT_BODY, relief="flat", bd=0,
            padx=14, pady=7, cursor="hand2", width=width, **kwargs
        )
        self._color = color
        self.bind("<Enter>", lambda e: self.config(bg=self._darken(color)))
        self.bind("<Leave>", lambda e: self.config(bg=color))

    @staticmethod
    def _darken(hex_color):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        factor = 0.80
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def labeled_entry(parent, label, row, col=0, width=28, var=None, combo_values=None):
    """Create a label + entry/combobox pair in a grid."""
    tk.Label(parent, text=label, bg=BG_CARD, fg=TEXT_SEC,
             font=FONT_SMALL).grid(row=row, column=col*2,
                                   sticky="w", padx=(8,4), pady=4)
    if var is None:
        var = tk.StringVar()
    if combo_values is not None:
        w = ttk.Combobox(parent, textvariable=var, values=combo_values,
                         width=width, font=FONT_BODY, state="readonly")
    else:
        w = tk.Entry(parent, textvariable=var, width=width,
                     bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                     relief="flat", font=FONT_BODY,
                     highlightthickness=1,
                     highlightbackground=BORDER,
                     highlightcolor=ACCENT)
    w.grid(row=row, column=col*2+1, padx=(0,16), pady=4, sticky="w")
    return var, w


def build_tree(parent, columns, show_cols=None):
    """Build a styled ttk.Treeview with scrollbars."""
    frame = tk.Frame(parent, bg=BG_DARK)
    frame.pack(fill="both", expand=True, padx=10, pady=6)

    style = ttk.Style()
    style.configure("SQ.Treeview",
                    background=ROW_ODD, foreground=TEXT_PRI,
                    fieldbackground=ROW_ODD, rowheight=28,
                    font=FONT_BODY)
    style.configure("SQ.Treeview.Heading",
                    background=BG_SIDEBAR, foreground=ACCENT,
                    font=("Segoe UI", 10, "bold"), relief="flat")
    style.map("SQ.Treeview",
              background=[("selected", ROW_SEL)],
              foreground=[("selected", "#ffffff")])

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        style="SQ.Treeview")
    display = show_cols or columns
    for col in columns:
        tree.heading(col, text=col)
        w = max(80, len(col) * 11)
        tree.column(col, width=w, anchor="w")

    vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree.grid(row=0, column=0, sticky="nsew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    # Alternating row tags
    tree.tag_configure("odd",  background=ROW_ODD)
    tree.tag_configure("even", background=ROW_EVEN)
    return tree


def refresh_tags(tree):
    """Reapply alternating row tags after any update."""
    for i, item in enumerate(tree.get_children()):
        tree.item(item, tags=("even" if i % 2 else "odd",))


# ════════════════════════════════════════════════════════════════════════════
#  CONNECTION DIALOG
# ════════════════════════════════════════════════════════════════════════════
class ConnectionDialog(tk.Toplevel):
    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent)
        self.db     = db
        self.result = False
        self.title("Connect to MySQL")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)
        self.grab_set()

        tk.Label(self, text="🔌  Database Connection",
                 font=FONT_HEAD, bg=BG_DARK, fg=ACCENT).pack(pady=(20,10))

        form = tk.Frame(self, bg=BG_CARD, padx=20, pady=16)
        form.pack(padx=20, pady=8, fill="x")

        fields = [
            ("Host",     "localhost"),
            ("User",     "root"),
            ("Password", "admin"),
            ("Database", "vehicles_service_db"),
        ]
        self._vars = {}
        for i, (lbl, default) in enumerate(fields):
            tk.Label(form, text=lbl+":", bg=BG_CARD, fg=TEXT_SEC,
                     font=FONT_BODY, width=10, anchor="w").grid(
                row=i, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=default)
            show = "*" if lbl == "Password" else ""
            e = tk.Entry(form, textvariable=var, show=show,
                         bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                         relief="flat", font=FONT_BODY, width=28,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=ACCENT)
            e.grid(row=i, column=1, padx=8, pady=4)
            self._vars[lbl] = var

        btn_row = tk.Frame(self, bg=BG_DARK)
        btn_row.pack(pady=14)
        StyledButton(btn_row, "Connect", command=self._connect,
                     color=ACCENT_2).pack(side="left", padx=8)
        StyledButton(btn_row, "Cancel",  command=self.destroy,
                     color=ACCENT_4).pack(side="left", padx=8)

        self.status = tk.Label(self, text="", bg=BG_DARK,
                               fg=ACCENT_4, font=FONT_SMALL)
        self.status.pack(pady=(0,12))

    def _connect(self):
        try:
            self.db.connect(
                host     = self._vars["Host"].get(),
                user     = self._vars["User"].get(),
                password = self._vars["Password"].get(),
                database = self._vars["Database"].get(),
            )
            self.result = True
            self.destroy()
        except Exception as e:
            self.status.config(text=f"❌  {e}")


# ════════════════════════════════════════════════════════════════════════════
#  INDIVIDUAL TAB CLASSES
# ════════════════════════════════════════════════════════════════════════════

# ── Customer Tab ─────────────────────────────────────────────────────────────
class CustomerTab(tk.Frame):
    COLS = ("ID","Name","Phone","Email","Address","Joined")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="👥  Customers", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        # Form card
        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        self.vars = {}
        for i, (lbl, key) in enumerate([
            ("Full Name","name"), ("Phone","phone"),
            ("Email","email"),    ("Address","address"),
        ]):
            v, _ = labeled_entry(card, lbl, i//2, i%2)
            self.vars[key] = v

        # Buttons
        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=2, column=0, columnspan=4, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(
                side="left", padx=5)

        # Tree
        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT customer_id,name,phone,email,address,"
                "DATE_FORMAT(created_at,'%d-%b-%Y') FROM Customer ORDER BY customer_id")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        keys = ["name","phone","email","address"]
        for i, k in enumerate(keys):
            self.vars[k].set(vals[i+1] if i+1 < len(vals) else "")

    def _crud(self, action):
        v = self.vars
        try:
            if action == "INSERT":
                if not v["name"].get() or not v["phone"].get():
                    return messagebox.showwarning("Validation","Name & Phone required")
                self.db.execute(
                    "INSERT INTO Customer (name,phone,email,address) VALUES (%s,%s,%s,%s)",
                    (v["name"].get(), v["phone"].get(),
                     v["email"].get(), v["address"].get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                cid = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "UPDATE Customer SET name=%s,phone=%s,email=%s,address=%s "
                    "WHERE customer_id=%s",
                    (v["name"].get(), v["phone"].get(),
                     v["email"].get(), v["address"].get(), cid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                cid = self.tree.item(sel[0])["values"][0]
                if not messagebox.askyesno("Confirm","Delete this customer and all linked records?"):
                    return
                self.db.execute("DELETE FROM Customer WHERE customer_id=%s", (cid,))

            self.db.commit()
            self.refresh()
            for k in v: v[k].set("")
            messagebox.showinfo("✅ Success", f"Customer {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Vehicle Tab ───────────────────────────────────────────────────────────────
class VehicleTab(tk.Frame):
    COLS = ("VID","CID","Customer","Reg No","Make","Model","Year","Color")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="🚗  Vehicles", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # Customer combobox
        tk.Label(card, text="Customer:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.cust_var = tk.StringVar()
        self.cust_combo = ttk.Combobox(card, textvariable=self.cust_var,
                                        width=32, font=FONT_BODY, state="readonly")
        self.cust_combo.grid(row=0, column=1, padx=(0,8), pady=4, sticky="w")
        StyledButton(card, "↺", command=self._load_customers,
                     color=TEXT_MUT, width=3).grid(row=0, column=2)

        self.vars = {}
        for i, (lbl, key) in enumerate([
            ("Reg No","reg"), ("Make","make"),
            ("Model","model"), ("Year","year"), ("Color","color"),
        ]):
            r, c = (i//2)+1, i%2
            v, _ = labeled_entry(card, lbl, r, c)
            self.vars[key] = v

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, columnspan=4, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._load_customers()
        self.refresh()

    def _load_customers(self):
        try:
            self.db.execute("SELECT customer_id, name, phone FROM Customer ORDER BY name")
            rows = self.db.fetchall()
            self._cust_map = {f"{r[1]} ({r[2]})": r[0] for r in rows}
            self.cust_combo["values"] = list(self._cust_map.keys())
        except Exception:
            pass

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT v.vehicle_id, v.customer_id, c.name, "
                "v.registration_number, v.make, v.model, v.year, v.color "
                "FROM Vehicle v JOIN Customer c ON v.customer_id=c.customer_id "
                "ORDER BY v.vehicle_id")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        # vals: VID, CID, Customer, RegNo, Make, Model, Year, Color
        self.vars["reg"].set(vals[3])
        self.vars["make"].set(vals[4])
        self.vars["model"].set(vals[5])
        self.vars["year"].set(vals[6])
        self.vars["color"].set(vals[7] if len(vals) > 7 else "")

    def _crud(self, action):
        try:
            if action == "INSERT":
                cid = self._cust_map.get(self.cust_var.get())
                if not cid or not self.vars["reg"].get():
                    return messagebox.showwarning("Validation","Select customer & enter Reg No")
                self.db.execute(
                    "INSERT INTO Vehicle (customer_id,registration_number,make,model,year,color) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (cid, self.vars["reg"].get(), self.vars["make"].get(),
                     self.vars["model"].get(), self.vars["year"].get() or None,
                     self.vars["color"].get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                vid = self.tree.item(sel[0])["values"][0]
                cid = self._cust_map.get(self.cust_var.get())
                self.db.execute(
                    "UPDATE Vehicle SET customer_id=%s,registration_number=%s,"
                    "make=%s,model=%s,year=%s,color=%s WHERE vehicle_id=%s",
                    (cid or self.tree.item(sel[0])["values"][1],
                     self.vars["reg"].get(), self.vars["make"].get(),
                     self.vars["model"].get(), self.vars["year"].get() or None,
                     self.vars["color"].get(), vid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                vid = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM Vehicle WHERE vehicle_id=%s", (vid,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Vehicle {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Booking Tab ───────────────────────────────────────────────────────────────
class BookingTab(tk.Frame):
    COLS = ("BID","Customer","Reg No","Date","Service Type","Status")
    SERVICE_TYPES = ["Oil Change","Tyre Replacement","General Service",
                     "Engine Repair","AC Service","Body Work",
                     "Battery Replacement","Brake Service","Other"]
    STATUSES = ["Pending","In Progress","Completed","Cancelled"]

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="📅  Bookings", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # Row 0 – Customer + Vehicle dropdowns
        for col_i, (lbl, attr) in enumerate([("Customer:","_cust"),("Vehicle:","_veh")]):
            tk.Label(card, text=lbl, bg=BG_CARD, fg=TEXT_SEC,
                     font=FONT_SMALL).grid(row=0, column=col_i*3, sticky="w", padx=8)
            var = tk.StringVar()
            cb  = ttk.Combobox(card, textvariable=var, width=28,
                                font=FONT_BODY, state="readonly")
            cb.grid(row=0, column=col_i*3+1, padx=(0,8), pady=4)
            setattr(self, attr+"_var", var)
            setattr(self, attr+"_combo", cb)

        StyledButton(card, "↺", command=self._load_dropdowns,
                     color=TEXT_MUT, width=3).grid(row=0, column=6)

        # Cascade: selecting customer filters vehicles
        self._cust_combo.bind("<<ComboboxSelected>>", lambda _: self._filter_vehicles())

        # Row 1 – Date, ServiceType
        tk.Label(card, text="Date (YYYY-MM-DD):", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.date_var = tk.StringVar(value=str(date.today()))
        tk.Entry(card, textvariable=self.date_var, width=18,
                 bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                 relief="flat", font=FONT_BODY,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).grid(row=1, column=1, padx=(0,8), pady=4)

        tk.Label(card, text="Service Type:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=1, column=3, sticky="w", padx=8, pady=4)
        self.stype_var = tk.StringVar()
        ttk.Combobox(card, textvariable=self.stype_var, values=self.SERVICE_TYPES,
                     width=28, font=FONT_BODY).grid(row=1, column=4, padx=(0,8), pady=4)

        # Row 2 – Status + Notes
        tk.Label(card, text="Status:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.status_var = tk.StringVar(value="Pending")
        ttk.Combobox(card, textvariable=self.status_var, values=self.STATUSES,
                     width=18, state="readonly",
                     font=FONT_BODY).grid(row=2, column=1, padx=(0,8), pady=4)

        tk.Label(card, text="Notes:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=2, column=3, sticky="w", padx=8)
        self.notes_var = tk.StringVar()
        tk.Entry(card, textvariable=self.notes_var, width=36,
                 bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                 relief="flat", font=FONT_BODY,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).grid(row=2, column=4, padx=(0,8))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=3, column=0, columnspan=7, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._load_dropdowns()
        self.refresh()

    def _load_dropdowns(self):
        try:
            self.db.execute("SELECT customer_id, name, phone FROM Customer ORDER BY name")
            rows = self.db.fetchall()
            self._cust_map = {f"{r[1]} ({r[2]})": r[0] for r in rows}
            self._cust_combo["values"] = list(self._cust_map.keys())
            self._load_all_vehicles()
        except Exception:
            pass

    def _load_all_vehicles(self):
        try:
            self.db.execute(
                "SELECT vehicle_id, registration_number, customer_id FROM Vehicle")
            rows = self.db.fetchall()
            self._all_vehs = rows
            self._veh_map  = {r[1]: r[0] for r in rows}
            self._veh_combo["values"] = [r[1] for r in rows]
        except Exception:
            pass

    def _filter_vehicles(self):
        cid = self._cust_map.get(self._cust_var.get())
        if cid:
            filtered = [r[1] for r in self._all_vehs if r[2] == cid]
            self._veh_combo["values"] = filtered
            self._veh_var.set(filtered[0] if filtered else "")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT b.booking_id, c.name, v.registration_number, "
                "b.booking_date, b.service_type, b.status "
                "FROM Booking b "
                "JOIN Customer c ON b.customer_id=c.customer_id "
                "JOIN Vehicle  v ON b.vehicle_id =v.vehicle_id "
                "ORDER BY b.booking_id ASC")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        self.date_var.set(str(vals[3]))
        self.stype_var.set(vals[4])
        self.status_var.set(vals[5])

    def _crud(self, action):
        try:
            if action == "INSERT":
                cid = self._cust_map.get(self._cust_var.get())
                vid = self._veh_map.get(self._veh_var.get())
                if not cid or not vid:
                    return messagebox.showwarning("Validation","Select customer & vehicle")
                self.db.execute(
                    "INSERT INTO Booking (customer_id,vehicle_id,booking_date,"
                    "service_type,status,notes) VALUES (%s,%s,%s,%s,%s,%s)",
                    (cid, vid, self.date_var.get(), self.stype_var.get(),
                     self.status_var.get(), self.notes_var.get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                bid = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "UPDATE Booking SET booking_date=%s,service_type=%s,"
                    "status=%s,notes=%s WHERE booking_id=%s",
                    (self.date_var.get(), self.stype_var.get(),
                     self.status_var.get(), self.notes_var.get(), bid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                bid = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM Booking WHERE booking_id=%s", (bid,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Booking {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Service Tab ───────────────────────────────────────────────────────────────
class ServiceTab(tk.Frame):
    COLS = ("SID","Booking","Service","Technician","Labour (₹)","Start","End")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="🔧  Services", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # Booking dropdown
        tk.Label(card, text="Booking:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=8)
        self.book_var = tk.StringVar()
        self.book_combo = ttk.Combobox(card, textvariable=self.book_var,
                                        width=36, font=FONT_BODY, state="readonly")
        self.book_combo.grid(row=0, column=1, padx=(0,8), pady=4)
        StyledButton(card, "↺", command=self._load_bookings,
                     color=TEXT_MUT, width=3).grid(row=0, column=2)

        self.vars = {}
        fields = [
            ("Service Name","sname",0,0),("Technician","tech",0,1),
            ("Labour Cost (₹)","labour",1,0),("Description","desc",1,1),
            ("Start Date","start",2,0),("End Date","end",2,1),
        ]
        for lbl, key, r, c in fields:
            v, _ = labeled_entry(card, lbl, r+1, c)
            self.vars[key] = v

        # Default dates
        self.vars["start"].set(str(date.today()))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, columnspan=4, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._load_bookings()
        self.refresh()

    def _load_bookings(self):
        try:
            self.db.execute(
                "SELECT b.booking_id, c.name, v.registration_number, b.service_type "
                "FROM Booking b JOIN Customer c ON b.customer_id=c.customer_id "
                "JOIN Vehicle v ON b.vehicle_id=v.vehicle_id "
                "ORDER BY b.booking_id ASC")
            rows = self.db.fetchall()
            self._book_map = {
                f"#{r[0]} | {r[1]} | {r[2]} | {r[3]}": r[0]
                for r in rows
            }
            self.book_combo["values"] = list(self._book_map.keys())
        except Exception:
            pass

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT s.service_id, s.booking_id, s.service_name, "
                "s.technician, s.labour_cost, s.start_date, s.end_date "
                "FROM Service s ORDER BY s.service_id ASC")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        self.vars["sname"].set(vals[2])
        self.vars["tech"].set(vals[3] or "")
        self.vars["labour"].set(vals[4] or "")
        self.vars["start"].set(str(vals[5] or ""))
        self.vars["end"].set(str(vals[6] or ""))

    def _crud(self, action):
        try:
            if action == "INSERT":
                bid = self._book_map.get(self.book_var.get())
                if not bid or not self.vars["sname"].get():
                    return messagebox.showwarning("Validation","Select booking & enter service name")
                self.db.execute(
                    "INSERT INTO Service (booking_id,service_name,description,"
                    "labour_cost,start_date,end_date,technician) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (bid, self.vars["sname"].get(), self.vars["desc"].get(),
                     self.vars["labour"].get() or 0,
                     self.vars["start"].get() or None,
                     self.vars["end"].get() or None,
                     self.vars["tech"].get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                sid = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "UPDATE Service SET service_name=%s,description=%s,"
                    "labour_cost=%s,start_date=%s,end_date=%s,technician=%s "
                    "WHERE service_id=%s",
                    (self.vars["sname"].get(), self.vars["desc"].get(),
                     self.vars["labour"].get() or 0,
                     self.vars["start"].get() or None,
                     self.vars["end"].get() or None,
                     self.vars["tech"].get(), sid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                sid = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM Service WHERE service_id=%s", (sid,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Service {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── SparePart Tab ─────────────────────────────────────────────────────────────
class SparePartTab(tk.Frame):
    COLS = ("PID","Part Name","Part No","Unit Price (₹)","Stock","Supplier")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="🔩  Spare Parts", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        self.vars = {}
        fields = [
            ("Part Name","pname",0,0), ("Part Number","pno",0,1),
            ("Unit Price (₹)","price",1,0), ("Stock Qty","stock",1,1),
            ("Supplier","supplier",2,0),
        ]
        for lbl, key, r, c in fields:
            v, _ = labeled_entry(card, lbl, r, c)
            self.vars[key] = v

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=3, column=0, columnspan=4, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT part_id,part_name,part_number,unit_price,"
                "stock_quantity,supplier FROM SparePart ORDER BY part_id")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        keys = ["pname","pno","price","stock","supplier"]
        for i, k in enumerate(keys):
            self.vars[k].set(vals[i+1] if i+1 < len(vals) else "")

    def _crud(self, action):
        try:
            if action == "INSERT":
                if not self.vars["pname"].get():
                    return messagebox.showwarning("Validation","Part Name required")
                self.db.execute(
                    "INSERT INTO SparePart (part_name,part_number,unit_price,"
                    "stock_quantity,supplier) VALUES (%s,%s,%s,%s,%s)",
                    (self.vars["pname"].get(), self.vars["pno"].get() or None,
                     self.vars["price"].get() or 0,
                     self.vars["stock"].get() or 0,
                     self.vars["supplier"].get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                pid = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "UPDATE SparePart SET part_name=%s,part_number=%s,"
                    "unit_price=%s,stock_quantity=%s,supplier=%s "
                    "WHERE part_id=%s",
                    (self.vars["pname"].get(), self.vars["pno"].get() or None,
                     self.vars["price"].get() or 0,
                     self.vars["stock"].get() or 0,
                     self.vars["supplier"].get(), pid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                pid = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM SparePart WHERE part_id=%s",(pid,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Spare Part {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── SparepartUsage Tab ───────────────────────────────────────────────────────
class SparepartUsageTab(tk.Frame):
    COLS = ("Usage ID", "Service", "Part Name", "Qty", "Unit Price (₹)", "Total Cost (₹)")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._book_map  = {}
        self._part_map  = {}
        self._part_price = {}   # part label → unit price
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(hdr, text="🔩  Spare Part Usage", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # ── Row 0: Service dropdown ──────────────────────────────────────────
        tk.Label(card, text="Service:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.svc_var   = tk.StringVar()
        self.svc_combo = ttk.Combobox(card, textvariable=self.svc_var,
                                      width=38, font=FONT_BODY, state="readonly")
        self.svc_combo.grid(row=0, column=1, padx=(0, 8), pady=4, columnspan=3)
        StyledButton(card, "↺", command=self._load_dropdowns,
                     color=TEXT_MUT, width=3).grid(row=0, column=4)

        # ── Row 1: Spare-part dropdown ───────────────────────────────────────
        tk.Label(card, text="Spare Part:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.part_var   = tk.StringVar()
        self.part_combo = ttk.Combobox(card, textvariable=self.part_var,
                                       width=38, font=FONT_BODY, state="readonly")
        self.part_combo.grid(row=1, column=1, padx=(0, 8), pady=4, columnspan=3)
        # Auto-fill unit price when part changes
        self.part_combo.bind("<<ComboboxSelected>>", lambda _: self._on_part_select())

        # ── Row 2: Qty, Unit Price (read-only display), Total Cost ────────────
        tk.Label(card, text="Quantity:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.qty_var = tk.StringVar(value="1")
        qty_entry = tk.Entry(card, textvariable=self.qty_var, width=8,
                             bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                             relief="flat", font=FONT_BODY,
                             highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=ACCENT)
        qty_entry.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=4)
        self.qty_var.trace_add("write", lambda *_: self._calc_total())

        tk.Label(card, text="Unit Price (₹):", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=2, column=2, sticky="w", padx=8, pady=4)
        self.unit_var = tk.StringVar(value="0.00")
        tk.Entry(card, textvariable=self.unit_var, width=14,
                 bg=BG_DARK, fg=TEXT_SEC, state="readonly",
                 relief="flat", font=FONT_BODY,
                 readonlybackground=BG_DARK).grid(
            row=2, column=3, sticky="w", padx=(0, 16), pady=4)

        tk.Label(card, text="Total Cost (₹):", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.total_var = tk.StringVar(value="0.00")
        tk.Entry(card, textvariable=self.total_var, width=14,
                 bg=BG_DARK, fg=ACCENT_2, state="readonly",
                 relief="flat", font=("Segoe UI", 10, "bold"),
                 readonlybackground=BG_DARK).grid(
            row=3, column=1, sticky="w", padx=(0, 16), pady=4)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=4, column=0, columnspan=5, pady=(10, 0))
        for lbl, col, fn in [
            ("➕ Add",     ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update",  ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete",  ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh", TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._load_dropdowns()
        self.refresh()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _load_dropdowns(self):
        # Services
        try:
            self.db.execute(
                "SELECT s.service_id, s.service_name, b.booking_id "
                "FROM Service s JOIN Booking b ON s.booking_id=b.booking_id "
                "ORDER BY s.service_id DESC")
            rows = self.db.fetchall()
            self._svc_map = {
                f"#{r[0]} | Booking #{r[2]} | {r[1]}": r[0] for r in rows
            }
            self.svc_combo["values"] = list(self._svc_map.keys())
        except Exception:
            pass

        # Spare parts
        try:
            self.db.execute(
                "SELECT part_id, part_name, unit_price FROM SparePart ORDER BY part_name")
            rows = self.db.fetchall()
            self._part_map   = {f"{r[1]} (#{r[0]})": r[0] for r in rows}
            self._part_price = {f"{r[1]} (#{r[0]})": float(r[2]) for r in rows}
            self.part_combo["values"] = list(self._part_map.keys())
        except Exception:
            pass

    def _on_part_select(self):
        price = self._part_price.get(self.part_var.get(), 0.0)
        self.unit_var.set(f"{price:.2f}")
        self._calc_total()

    def _calc_total(self):
        try:
            qty   = int(self.qty_var.get() or 0)
            price = float(self.unit_var.get() or 0)
            self.total_var.set(f"{qty * price:.2f}")
        except Exception:
            pass

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT su.usage_id, "
                "CONCAT('#', su.service_id, ' | ', s.service_name), "
                "sp.part_name, su.quantity, sp.unit_price, su.total_cost "
                "FROM SparepartUsage su "
                "JOIN Service   s  ON su.service_id = s.service_id "
                "JOIN SparePart sp ON su.part_id    = sp.part_id "
                "ORDER BY su.usage_id ASC")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        # vals: UsageID, Service label, Part Name, Qty, UnitPrice, TotalCost
        self.qty_var.set(vals[3])
        self.unit_var.set(vals[4])
        self.total_var.set(vals[5])

    def _crud(self, action):
        try:
            if action == "INSERT":
                sid  = self._svc_map.get(self.svc_var.get())
                pid  = self._part_map.get(self.part_var.get())
                if not sid or not pid:
                    return messagebox.showwarning("Validation",
                                                  "Select a Service and a Spare Part")
                qty   = int(self.qty_var.get() or 1)
                total = float(self.total_var.get() or 0)
                self.db.execute(
                    "INSERT INTO SparepartUsage "
                    "(service_id, part_id, quantity, total_cost) "
                    "VALUES (%s, %s, %s, %s)",
                    (sid, pid, qty, total))
                # Deduct from stock
                self.db.execute(
                    "UPDATE SparePart "
                    "SET stock_quantity = stock_quantity - %s "
                    "WHERE part_id = %s",
                    (qty, pid))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel:
                    return messagebox.showwarning("Select", "Select a row first")
                uid   = self.tree.item(sel[0])["values"][0]
                qty   = int(self.qty_var.get() or 1)
                total = float(self.total_var.get() or 0)
                self.db.execute(
                    "UPDATE SparepartUsage "
                    "SET quantity=%s, total_cost=%s "
                    "WHERE usage_id=%s",
                    (qty, total, uid))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel:
                    return messagebox.showwarning("Select", "Select a row first")
                uid = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "DELETE FROM SparepartUsage WHERE usage_id=%s", (uid,))

            self.db.commit()
            self.refresh()
            self._load_dropdowns()          # refresh stock numbers in dropdown
            messagebox.showinfo("✅ Success", f"Spare Part Usage {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Bill Tab ──────────────────────────────────────────────────────────────────
class BillTab(tk.Frame):
    COLS = ("BillID","Booking","Service ₹","Parts ₹","Tax %","Discount ₹","Total ₹","Date","Status")

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="🧾  Bills", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # Booking dropdown
        tk.Label(card, text="Booking:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=8)
        self.book_var = tk.StringVar()
        self.book_combo = ttk.Combobox(card, textvariable=self.book_var,
                                        width=36, font=FONT_BODY, state="readonly")
        self.book_combo.grid(row=0, column=1, padx=(0,8), pady=4, columnspan=3)
        StyledButton(card, "↺", command=self._load_bookings,
                     color=TEXT_MUT, width=3).grid(row=0, column=4)
        StyledButton(card, "⚡ Auto-Fill", command=self._autofill,
                     color=ACCENT_3, width=12).grid(row=0, column=5, padx=6)

        self.vars = {}
        fields = [
            ("Service Cost (₹)","svc",1,0), ("Parts Cost (₹)","parts",1,1),
            ("Tax %","tax",2,0),             ("Discount (₹)","disc",2,1),
            ("Total Amount (₹)","total",3,0),("Bill Date","bdate",3,1),
        ]
        for lbl, key, r, c in fields:
            v, _ = labeled_entry(card, lbl, r, c)
            self.vars[key] = v
        self.vars["tax"].set("18.00")
        self.vars["bdate"].set(str(date.today()))

        tk.Label(card, text="Status:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=4, column=0, sticky="w", padx=8)
        self.status_var = tk.StringVar(value="Unpaid")
        ttk.Combobox(card, textvariable=self.status_var,
                     values=["Unpaid","Paid","Partial"],
                     width=18, state="readonly",
                     font=FONT_BODY).grid(row=4, column=1, padx=(0,8), pady=4)

        # Auto-calculate total on cost change
        for k in ["svc","parts","tax","disc"]:
            self.vars[k].trace_add("write", lambda *_: self._calc_total())

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=5, column=0, columnspan=6, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("✏️ Update", ACCENT,   lambda: self._crud("UPDATE")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._load_bookings()
        self.refresh()

    def _load_bookings(self):
        try:
            self.db.execute(
                "SELECT b.booking_id, c.name, v.registration_number "
                "FROM Booking b JOIN Customer c ON b.customer_id=c.customer_id "
                "JOIN Vehicle v ON b.vehicle_id=v.vehicle_id ORDER BY b.booking_id ASC")
            rows = self.db.fetchall()
            self._book_map = {f"#{r[0]} | {r[1]} | {r[2]}": r[0] for r in rows}
            self.book_combo["values"] = list(self._book_map.keys())
        except Exception:
            pass

    def _autofill(self):
        bid = self._book_map.get(self.book_var.get())
        if not bid:
            return messagebox.showwarning("Select","Select a booking first")
        try:
            # Labour cost
            self.db.execute(
                "SELECT COALESCE(SUM(labour_cost),0) FROM Service WHERE booking_id=%s",
                (bid,))
            labour = float(self.db.fetchone()[0])

            # Parts cost via SparepartUsage → Service
            self.db.execute(
                """SELECT COALESCE(SUM(su.total_cost),0)
                   FROM SparepartUsage su
                   JOIN Service s ON su.service_id=s.service_id
                   WHERE s.booking_id=%s""", (bid,))
            parts = float(self.db.fetchone()[0])

            self.vars["svc"].set(f"{labour:.2f}")
            self.vars["parts"].set(f"{parts:.2f}")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _calc_total(self):
        try:
            svc   = float(self.vars["svc"].get()   or 0)
            parts = float(self.vars["parts"].get() or 0)
            tax   = float(self.vars["tax"].get()   or 0)
            disc  = float(self.vars["disc"].get()  or 0)
            sub   = svc + parts
            total = sub + (sub * tax / 100) - disc
            self.vars["total"].set(f"{total:.2f}")
        except Exception:
            pass

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT bill_id,booking_id,service_cost,parts_cost,tax_percent,"
                "discount,total_amount,bill_date,status FROM Bill ORDER BY bill_id ASC")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        self.vars["svc"].set(vals[2])
        self.vars["parts"].set(vals[3])
        self.vars["tax"].set(vals[4])
        self.vars["disc"].set(vals[5])
        self.vars["total"].set(vals[6])
        self.vars["bdate"].set(str(vals[7]))
        self.status_var.set(vals[8])

    def _crud(self, action):
        try:
            if action == "INSERT":
                bid = self._book_map.get(self.book_var.get())
                if not bid or not self.vars["total"].get():
                    return messagebox.showwarning("Validation","Select booking & fill amounts")
                self.db.execute(
                    "INSERT INTO Bill (booking_id,service_cost,parts_cost,tax_percent,"
                    "discount,total_amount,bill_date,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (bid,
                     self.vars["svc"].get() or 0,
                     self.vars["parts"].get() or 0,
                     self.vars["tax"].get() or 18,
                     self.vars["disc"].get() or 0,
                     self.vars["total"].get(),
                     self.vars["bdate"].get(),
                     self.status_var.get()))

            elif action == "UPDATE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                bill_id = self.tree.item(sel[0])["values"][0]
                self.db.execute(
                    "UPDATE Bill SET service_cost=%s,parts_cost=%s,tax_percent=%s,"
                    "discount=%s,total_amount=%s,bill_date=%s,status=%s WHERE bill_id=%s",
                    (self.vars["svc"].get() or 0,
                     self.vars["parts"].get() or 0,
                     self.vars["tax"].get() or 18,
                     self.vars["disc"].get() or 0,
                     self.vars["total"].get(),
                     self.vars["bdate"].get(),
                     self.status_var.get(), bill_id))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                bill_id = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM Bill WHERE bill_id=%s", (bill_id,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Bill {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Payment Tab ───────────────────────────────────────────────────────────────
class PaymentTab(tk.Frame):
    COLS = ("PayID","Bill ID","Amount (₹)","Date","Mode","Reference")
    MODES = ["Cash","Card","UPI","Net Banking","Cheque"]

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill="x", padx=16, pady=(14,0))
        tk.Label(hdr, text="💳  Payments", font=FONT_HEAD,
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side="left")

        card = tk.Frame(self, bg=BG_CARD, padx=12, pady=12)
        card.pack(fill="x", padx=16, pady=10)

        # Bill dropdown
        tk.Label(card, text="Bill:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=8)
        self.bill_var = tk.StringVar()
        self.bill_combo = ttk.Combobox(card, textvariable=self.bill_var,
                                        width=36, font=FONT_BODY, state="readonly")
        self.bill_combo.grid(row=0, column=1, padx=(0,8), pady=4, columnspan=3)
        StyledButton(card, "↺", command=self._load_bills,
                     color=TEXT_MUT, width=3).grid(row=0, column=4)

        self.vars = {}
        v1, _ = labeled_entry(card, "Amount (₹)", 1, 0)
        self.vars["amount"] = v1

        tk.Label(card, text="Payment Date:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=1, column=2, sticky="w", padx=8)
        self.pdate_var = tk.StringVar(value=str(date.today()))
        tk.Entry(card, textvariable=self.pdate_var, width=18,
                 bg=BG_DARK, fg=TEXT_PRI, insertbackground=TEXT_PRI,
                 relief="flat", font=FONT_BODY,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).grid(row=1, column=3, padx=(0,8))

        tk.Label(card, text="Mode:", bg=BG_CARD, fg=TEXT_SEC,
                 font=FONT_SMALL).grid(row=2, column=0, sticky="w", padx=8)
        self.mode_var = tk.StringVar(value="Cash")
        ttk.Combobox(card, textvariable=self.mode_var, values=self.MODES,
                     width=18, state="readonly",
                     font=FONT_BODY).grid(row=2, column=1, padx=(0,8), pady=4)

        v2, _ = labeled_entry(card, "Reference No", 2, 1)
        self.vars["ref"] = v2

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.grid(row=3, column=0, columnspan=5, pady=(10,0))
        for lbl, col, fn in [
            ("➕ Add",    ACCENT_2, lambda: self._crud("INSERT")),
            ("🗑️ Delete", ACCENT_4, lambda: self._crud("DELETE")),
            ("🔄 Refresh",TEXT_MUT, self.refresh),
        ]:
            StyledButton(btn_row, lbl, command=fn, color=col).pack(side="left", padx=5)

        self.tree = build_tree(self, self.COLS)
        self._load_bills()
        self.refresh()

    def _load_bills(self):
        try:
            self.db.execute(
                "SELECT b.bill_id, b.total_amount, b.status, bk.booking_id "
                "FROM Bill b JOIN Booking bk ON b.booking_id=bk.booking_id "
                "ORDER BY b.bill_id ASC")
            rows = self.db.fetchall()
            self._bill_map = {
                f"Bill #{r[0]} | ₹{r[1]} | {r[2]}": r[0] for r in rows
            }
            self.bill_combo["values"] = list(self._bill_map.keys())
        except Exception:
            pass

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT payment_id,bill_id,amount_paid,payment_date,"
                "payment_mode,reference_no FROM Payment ORDER BY payment_id ASC")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception as e:
            messagebox.showerror("DB Error", str(e))

    def _crud(self, action):
        try:
            if action == "INSERT":
                bid = self._bill_map.get(self.bill_var.get())
                if not bid or not self.vars["amount"].get():
                    return messagebox.showwarning("Validation","Select bill & enter amount")
                self.db.execute(
                    "INSERT INTO Payment (bill_id,amount_paid,payment_date,"
                    "payment_mode,reference_no) VALUES (%s,%s,%s,%s,%s)",
                    (bid, self.vars["amount"].get(), self.pdate_var.get(),
                     self.mode_var.get(), self.vars["ref"].get() or None))
                # Mark bill as Paid
                self.db.execute(
                    "UPDATE Bill SET status='Paid' WHERE bill_id=%s", (bid,))

            elif action == "DELETE":
                sel = self.tree.selection()
                if not sel: return messagebox.showwarning("Select","Select a row first")
                pid = self.tree.item(sel[0])["values"][0]
                self.db.execute("DELETE FROM Payment WHERE payment_id=%s",(pid,))

            self.db.commit()
            self.refresh()
            messagebox.showinfo("✅ Success", f"Payment {action} successful!")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("DB Error", str(e))


# ── Dashboard Tab ─────────────────────────────────────────────────────────────
class DashboardTab(tk.Frame):
    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG_PANEL)
        self.db = db
        self._build()

    def _build(self):
        # Title
        tk.Label(self, text="📊  Dashboard Overview",
                 font=("Segoe UI", 16, "bold"),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(pady=(18,6))
        tk.Label(self, text="Live summary of your service center",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUT).pack()

        # Stat cards row
        cards_frame = tk.Frame(self, bg=BG_PANEL)
        cards_frame.pack(fill="x", padx=20, pady=14)
        self._cards_frame = cards_frame

        card_defs = [
            ("👥 Customers",   "customers", ACCENT),
            ("🚗 Vehicles",    "vehicles",  ACCENT_2),
            ("📅 Bookings",    "bookings",  ACCENT_3),
            ("⏳ Pending Bills","pending",  "#8b5cf6"),
            ("💰 Revenue (₹)", "revenue",   ACCENT_4),
        ]
        self._val_labels = {}
        for i, (label, key, color) in enumerate(card_defs):
            card = tk.Frame(cards_frame, bg=BG_CARD,
                            padx=16, pady=14, relief="flat")
            card.grid(row=0, column=i, padx=8, pady=6, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)

            # Coloured top border simulation via label
            accent_bar = tk.Frame(card, bg=color, height=4)
            accent_bar.pack(fill="x", pady=(0,8))

            tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                     bg=BG_CARD, fg=TEXT_SEC).pack()
            val_lbl = tk.Label(card, text="—", font=("Segoe UI", 22, "bold"),
                               fg=color, bg=BG_CARD)
            val_lbl.pack(pady=4)
            self._val_labels[key] = val_lbl

        # Refresh button
        StyledButton(self, "🔄 Refresh Dashboard",
                     command=self.refresh, color=ACCENT,
                     width=22).pack(pady=8)

        # Recent bookings table
        tk.Label(self, text="Recent Bookings",
                 font=FONT_HEAD, bg=BG_PANEL, fg=TEXT_PRI).pack(
            anchor="w", padx=20, pady=(10,0))
        self.tree = build_tree(
            self,
            ("Booking ID","Customer","Vehicle","Date","Service","Status"))

        self.refresh()

    def refresh(self):
        if not self.db.is_connected():
            return
        queries = {
            "customers": "SELECT COUNT(*) FROM Customer",
            "vehicles":  "SELECT COUNT(*) FROM Vehicle",
            "bookings":  "SELECT COUNT(*) FROM Booking",
            "pending":   "SELECT COUNT(*) FROM Bill WHERE status='Unpaid'",
            "revenue":   "SELECT COALESCE(SUM(amount_paid),0) FROM Payment",
        }
        for key, q in queries.items():
            try:
                self.db.execute(q)
                val = self.db.fetchone()[0]
                if key == "revenue":
                    val = f"₹{float(val):,.2f}"
                self._val_labels[key].config(text=str(val))
            except Exception:
                self._val_labels[key].config(text="err")

        # Recent bookings
        self.tree.delete(*self.tree.get_children())
        try:
            self.db.execute(
                "SELECT b.booking_id, c.name, v.registration_number, "
                "b.booking_date, b.service_type, b.status "
                "FROM Booking b "
                "JOIN Customer c ON b.customer_id=c.customer_id "
                "JOIN Vehicle  v ON b.vehicle_id =v.vehicle_id "
                "ORDER BY b.booking_id ASC LIMIT 15")
            for row in self.db.fetchall():
                self.tree.insert("", "end", values=row)
            refresh_tags(self.tree)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ════════════════════════════════════════════════════════════════════════════
class ServeQuickApp(tk.Tk):
    NAV_ITEMS = [
        ("📊 Dashboard",  "dashboard"),
        ("👥 Customers",  "customers"),
        ("🚗 Vehicles",   "vehicles"),
        ("📅 Bookings",   "bookings"),
        ("🔧 Services",   "services"),
        ("🔩 Spare Parts","spareparts"),
        ("📦 Part Usage", "partusage"),
        ("🧾 Bills",      "bills"),
        ("💳 Payments",   "payments"),
    ]

    def __init__(self):
        super().__init__()
        self.title("ServeQuick – Vehicle Service Management System")
        self.geometry("1280x780")
        self.minsize(960, 620)
        self.configure(bg=BG_DARK)
        self.db = DatabaseManager()
        self._active_nav = None
        self._tabs = {}

        self._apply_ttk_style()
        self._build_layout()
        self._prompt_connection()

    # ── TTK global styling ───────────────────────────────────────────────────
    def _apply_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".",
            background=BG_DARK, foreground=TEXT_PRI,
            fieldbackground=BG_DARK, font=FONT_BODY)
        style.configure("TCombobox",
            background=BG_DARK, foreground=TEXT_PRI,
            selectbackground=ACCENT, selectforeground="#fff",
            arrowcolor=ACCENT)
        style.map("TCombobox",
            fieldbackground=[("readonly", BG_DARK)],
            foreground=[("readonly", TEXT_PRI)])
        style.configure("TScrollbar",
            background=BG_SIDEBAR, troughcolor=BG_DARK,
            arrowcolor=TEXT_SEC)
        style.configure("TFrame", background=BG_DARK)

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_layout(self):
        # Top bar
        topbar = tk.Frame(self, bg=BG_SIDEBAR, height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="⚙️  ServeQuick",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_PRI).pack(side="left", padx=18, pady=12)

        self._conn_label = tk.Label(topbar, text="● Not Connected",
                                     font=FONT_SMALL, bg=BG_SIDEBAR, fg=ACCENT_4)
        self._conn_label.pack(side="right", padx=16)

        StyledButton(topbar, "Connect DB", command=self._prompt_connection,
                     color=ACCENT_2, width=12).pack(side="right", padx=8, pady=8)
        StyledButton(topbar, "Disconnect", command=self._disconnect,
                     color=ACCENT_4, width=12).pack(side="right", padx=4, pady=8)

        # Main body: sidebar + content
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=BG_SIDEBAR, width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="NAVIGATION",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUT).pack(anchor="w", padx=16, pady=(16,6))

        self._nav_btns = {}
        for label, key in self.NAV_ITEMS:
            btn = tk.Button(
                sidebar, text=label, anchor="w",
                bg=BG_SIDEBAR, fg=TEXT_SEC,
                activebackground=ACCENT, activeforeground=TEXT_PRI,
                font=FONT_BODY, relief="flat", bd=0,
                padx=16, pady=10, cursor="hand2",
                command=lambda k=key: self._switch_tab(k)
            )
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        # Footer in sidebar
        tk.Label(sidebar,
                 text="SRM Institute\nof Science & Technology",
                 font=("Segoe UI", 8), bg=BG_SIDEBAR, fg=TEXT_MUT,
                 justify="center").pack(side="bottom", pady=12)

        # Content area
        self._content = tk.Frame(body, bg=BG_PANEL)
        self._content.pack(side="left", fill="both", expand=True)

        # Placeholder before DB connection
        self._placeholder = tk.Frame(self._content, bg=BG_PANEL)
        self._placeholder.pack(fill="both", expand=True)
        tk.Label(self._placeholder,
                 text="🔌\n\nConnect to your MySQL database\nto get started",
                 font=("Segoe UI", 14), bg=BG_PANEL, fg=TEXT_MUT,
                 justify="center").pack(expand=True)

    # ── DB Connection flow ───────────────────────────────────────────────────
    def _prompt_connection(self):
        dlg = ConnectionDialog(self, self.db)
        self.wait_window(dlg)
        if dlg.result:
            self._on_connected()

    def _on_connected(self):
        self._conn_label.config(text="● Connected", fg=ACCENT_2)
        self._placeholder.destroy()
        self._build_tabs()
        self._switch_tab("dashboard")

    def _disconnect(self):
        self.db.disconnect()
        self._conn_label.config(text="● Not Connected", fg=ACCENT_4)
        for t in self._tabs.values():
            t.destroy()
        self._tabs = {}
        self._active_nav = None
        self._placeholder = tk.Frame(self._content, bg=BG_PANEL)
        self._placeholder.pack(fill="both", expand=True)
        tk.Label(self._placeholder,
                 text="🔌\n\nConnect to your MySQL database\nto get started",
                 font=("Segoe UI", 14), bg=BG_PANEL, fg=TEXT_MUT,
                 justify="center").pack(expand=True)

    # ── Build tab pages ──────────────────────────────────────────────────────
    def _build_tabs(self):
        self._tabs = {
            "dashboard":  DashboardTab(self._content, self.db),
            "customers":  CustomerTab(self._content,  self.db),
            "vehicles":   VehicleTab(self._content,   self.db),
            "bookings":   BookingTab(self._content,   self.db),
            "services":   ServiceTab(self._content,   self.db),
            "spareparts": SparePartTab(self._content,      self.db),
            "partusage":  SparepartUsageTab(self._content,  self.db),
            "bills":      BillTab(self._content,            self.db),
            "payments":   PaymentTab(self._content,   self.db),
        }

    # ── Navigation ───────────────────────────────────────────────────────────
    def _switch_tab(self, key):
        if not self._tabs:
            return
        # Hide all
        for t in self._tabs.values():
            t.pack_forget()
        # Show selected
        self._tabs[key].pack(fill="both", expand=True)

        # Refresh data on switch
        tab = self._tabs[key]
        if hasattr(tab, "refresh"):
            tab.refresh()

        # Update nav highlight
        if self._active_nav:
            self._nav_btns[self._active_nav].config(bg=BG_SIDEBAR, fg=TEXT_SEC)
        self._nav_btns[key].config(bg=ACCENT, fg=TEXT_PRI)
        self._active_nav = key

    def on_close(self):
        self.db.disconnect()
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ServeQuickApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
