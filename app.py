from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, hashlib, json, os
from datetime import datetime, date
from functools import wraps

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "pharmaverify.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "replace-this-demo-secret")

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def audit(event, payload):
    with connect() as c:
        last = c.execute("SELECT block_hash FROM audit_chain ORDER BY id DESC LIMIT 1").fetchone()
        prev = last["block_hash"] if last else "GENESIS"
        ts = datetime.now().isoformat(timespec="seconds")
        p = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(f"{prev}|{event}|{p}|{ts}".encode()).hexdigest()
        c.execute("INSERT INTO audit_chain(event_type,payload,previous_hash,block_hash,created_at) VALUES(?,?,?,?,?)",
                  (event, p, prev, h, ts))

def chain_ok():
    with connect() as c:
        rows = c.execute("SELECT * FROM audit_chain ORDER BY id").fetchall()
    prev = "GENESIS"
    for r in rows:
        expected = hashlib.sha256(f"{prev}|{r['event_type']}|{r['payload']}|{r['created_at']}".encode()).hexdigest()
        if r["previous_hash"] != prev or r["block_hash"] != expected:
            return False
        prev = r["block_hash"]
    return True

def status(exp):
    try:
        d = date.fromisoformat(exp)
        if d < date.today(): return "Expired"
        if (d - date.today()).days <= 90: return "Expiring Soon"
        return "Valid"
    except ValueError:
        return "Unknown"

def medicine_info(name):
    """Educational descriptions for demo UI; not individualized medical advice."""
    key = (name or "").lower()
    info = {
      "paracetamol": {"description": "Commonly used to relieve pain and reduce fever.", "warning": "Follow the package or clinician instructions. Avoid taking multiple products containing paracetamol; overdose can seriously harm the liver."},
      "cetirizine": {"description": "An antihistamine commonly used for allergy symptoms such as sneezing, runny nose, and itching.", "warning": "May cause drowsiness. Check the label and ask a pharmacist/clinician if you have health conditions or take other medicines."},
      "vitamin c": {"description": "A vitamin supplement used to help meet vitamin C needs.", "warning": "Use only as directed on the label. Supplements are not a substitute for a balanced diet or professional advice."},
      "ors": {"description": "Oral rehydration salts are mixed with the exact amount of clean water stated on the sachet to help replace fluids and salts.", "warning": "Do not guess the water amount or add extra sugar/salt. Seek urgent care for severe dehydration, confusion, or inability to drink."},
      "antacid": {"description": "Antacids are used for short-term relief of heartburn or indigestion, depending on the ingredients.", "warning": "Ingredients differ. Follow the label and ask a pharmacist if symptoms persist or if you have kidney disease or take other medicines."},
      "cough syrup": {"description": "Cough syrups have different ingredients and may be intended for different types of cough.", "warning": "Check the active ingredients and age restrictions. Do not use an unknown syrup or combine products without pharmacist advice."},
      "ibuprofen": {"description": "An anti-inflammatory medicine used for certain pain and inflammation conditions.", "warning": "May not be suitable with stomach ulcers, kidney disease, some asthma, pregnancy, or certain medicines. Ask a pharmacist/clinician and follow the exact label."},
      "amoxicillin": {"description": "A prescription antibiotic used for certain bacterial infections.", "warning": "Use only when prescribed by a qualified clinician. Do not self-start or share antibiotics; tell the clinician about penicillin allergy."},
      "calcium": {"description": "A calcium and vitamin D supplement used when intake or levels need support.", "warning": "Follow the label or professional advice; ask a clinician first if you have kidney problems or take other medicines."},
      "pantoprazole": {"description": "A medicine that reduces stomach acid for certain conditions.", "warning": "Use as directed by a clinician or the product label; persistent symptoms need medical assessment."}
    }
    for k, v in info.items():
        if k in key: return v
    return {"description": "No verified description is available in this demo database.", "warning": "Do not identify or take medicine based only on appearance. Confirm the exact name and active ingredients with the package and a pharmacist."}

app.jinja_env.globals["medicine_info"] = medicine_info

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("username"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access only.", "warning")
            return redirect(url_for("customer_home"))
        return fn(*a, **kw)
    return wrapper

def customer_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("username"):
            flash("Please log in or create a customer account.", "warning")
            return redirect(url_for("customer_login"))
        if session.get("role") != "customer":
            return redirect(url_for("dashboard"))
        return fn(*a, **kw)
    return wrapper

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS medicines(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, manufacturer TEXT NOT NULL,
            batch_no TEXT UNIQUE NOT NULL, mfg_date TEXT NOT NULL, expiry_date TEXT NOT NULL,
            description TEXT, created_at TEXT NOT NULL, record_hash TEXT NOT NULL, barcode TEXT, price TEXT, composition TEXT)""")
        cols = [row["name"] for row in c.execute("PRAGMA table_info(medicines)").fetchall()]
        if "barcode" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN barcode TEXT")
        if "price" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN price TEXT")
        if "composition" not in cols:
            c.execute("ALTER TABLE medicines ADD COLUMN composition TEXT")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_chain(
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, payload TEXT,
            previous_hash TEXT, block_hash TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT)""")
        if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
            c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                      ("admin", hashlib.sha256(b"admin123").hexdigest(), "admin"))
        if c.execute("SELECT COUNT(*) n FROM medicines").fetchone()["n"] == 0:
            # All six records below are fictional examples, not genuine commercial batches.
            demo = [
              ("Paracetamol 500 mg","Demo Pharma Ltd.","DEMO-PARA-001","2025-01-10","2027-01-09","Fictional demo record."),
              ("Cetirizine 10 mg","Sample Healthcare","DEMO-CET-002","2025-06-01","2027-05-31","Fictional demo record."),
              ("Vitamin C 500 mg","Demo Wellness Labs","DEMO-VITC-003","2025-02-15","2026-12-15","Fictional demo record."),
              ("ORS Sachet","Sample Life Sciences","DEMO-ORS-004","2024-01-01","2026-08-31","Fictional record to show expired status."),
              ("Antacid Tablets","Demo Pharma Ltd.","DEMO-ANTI-005","2026-01-01","2026-11-20","Fictional record to show expiring-soon status."),
              ("Cough Syrup","Sample Healthcare","DEMO-COUGH-006","2025-04-01","2027-03-31","Fictional demo record.")
            ]
            for name, maker, batch, mfg, exp, desc in demo:
                ts = datetime.now().isoformat(timespec="seconds")
                payload = dict(name=name, manufacturer=maker, batch_no=batch, mfg_date=mfg, expiry_date=exp, description=desc)
                c.execute("""INSERT INTO medicines(name,manufacturer,batch_no,mfg_date,expiry_date,description,created_at,record_hash)
                    VALUES(?,?,?,?,?,?,?,?)""", (name,maker,batch,mfg,exp,desc,ts,digest(payload)))
    # Add 100+ clearly fictional records for college demonstration. Prices and batches are sample data.
    demo_catalog = [
      ("Paracetamol 500 mg", "Paracetamol IP 500 mg", "Fever and mild-to-moderate pain relief; use only as directed on the package/clinician instructions.", "₹32.50 / 10 tablets"),
      ("Cetirizine 10 mg", "Cetirizine hydrochloride 10 mg", "Allergy symptoms such as sneezing, runny nose and itching; may cause drowsiness.", "₹24.00 / 10 tablets"),
      ("Vitamin C 500 mg", "Ascorbic acid 500 mg", "Vitamin C supplement when needed; follow the product label.", "₹45.00 / 10 tablets"),
      ("ORS Sachet", "Oral rehydration salts; formula varies by product", "Helps replace fluids and salts lost through diarrhoea/vomiting. Mix with exactly the water amount on the sachet.", "₹20.00 / sachet"),
      ("Antacid Tablets", "Ingredients vary by brand", "Short-term heartburn/indigestion relief for some formulations; check the exact ingredients.", "₹35.00 / 10 tablets"),
      ("Cough Syrup", "Ingredients and strength vary by product", "Cough products differ; check the exact active ingredients and age instructions.", "₹85.00 / 100 ml"),
      ("Ibuprofen 200 mg", "Ibuprofen 200 mg", "Pain/inflammation relief for some people; not suitable for everyone. Ask a pharmacist/clinician first.", "₹38.00 / 10 tablets"),
      ("Amoxicillin 500 mg", "Amoxicillin 500 mg", "Prescription antibiotic for certain bacterial infections only; use only when prescribed and complete directions given.", "₹72.00 / 10 capsules"),
      ("Calcium + Vitamin D3", "Calcium and vitamin D3; strengths vary", "Supplement used to support calcium/vitamin D intake when indicated; follow the label/professional advice.", "₹110.00 / 10 tablets"),
      ("Pantoprazole 40 mg", "Pantoprazole 40 mg", "Reduces stomach acid for specific conditions when prescribed/advised; follow the clinician's instructions.", "₹68.00 / 10 tablets"),
    ]
    with connect() as c:
        existing = c.execute("SELECT COUNT(*) n FROM medicines WHERE batch_no LIKE 'DEMO-EXTRA-%'").fetchone()["n"]
        if existing < 100:
            # Ensure this is idempotent if the app is restarted.
            for i in range(1, 101):
                name, composition, desc, price = demo_catalog[(i-1) % len(demo_catalog)]
                batch = f"DEMO-EXTRA-{i:03d}"
                if c.execute("SELECT 1 FROM medicines WHERE batch_no=?", (batch,)).fetchone():
                    continue
                maker = ["Demo Pharma Ltd.", "Sample Healthcare Pvt. Ltd.", "Academic Demo Labs"][i % 3]
                mfg_year = 2025
                mfg_date = date(mfg_year, (i % 12)+1, min((i*3)%27+1, 28)).isoformat()
                expiry_year = 2027 if i % 4 else 2026
                expiry_date = date(expiry_year, (i % 12)+1, min((i*5)%27+1, 28)).isoformat()
                ts = datetime.now().isoformat(timespec="seconds")
                payload = dict(name=name, manufacturer=maker, batch_no=batch, mfg_date=mfg_date, expiry_date=expiry_date,
                               description=desc, price=price, composition=composition, demo_record=True)
                rh = digest(payload)
                c.execute("""INSERT INTO medicines(name,manufacturer,batch_no,mfg_date,expiry_date,description,created_at,record_hash,barcode,price,composition)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                          (name, maker, batch, mfg_date, expiry_date, desc, ts, rh, f"DEMO-BARCODE-{i:03d}", price, composition))

    # Add educational fields to the original six demo records as well.
    initial_fields = {
      "DEMO-PARA-001": ("₹32.50 / 10 tablets", "Paracetamol IP 500 mg"),
      "DEMO-CET-002": ("₹24.00 / 10 tablets", "Cetirizine hydrochloride 10 mg"),
      "DEMO-VITC-003": ("₹45.00 / 10 tablets", "Ascorbic acid 500 mg"),
      "DEMO-ORS-004": ("₹20.00 / sachet", "Oral rehydration salts; formula varies by product"),
      "DEMO-ANTI-005": ("₹35.00 / 10 tablets", "Ingredients vary by brand"),
      "DEMO-COUGH-006": ("₹85.00 / 100 ml", "Ingredients and strength vary by product")
    }
    with connect() as c:
        for batch, (price, composition) in initial_fields.items():
            c.execute("UPDATE medicines SET price=COALESCE(price,?), composition=COALESCE(composition,?) WHERE batch_no=?", (price, composition, batch))

    # Seed records into audit chain on first start, if no events exist.
    with connect() as c:
        has_events = c.execute("SELECT COUNT(*) n FROM audit_chain").fetchone()["n"]
        records = c.execute("SELECT batch_no,record_hash FROM medicines ORDER BY id").fetchall()
    if not has_events:
        for r in records:
            audit("DEMO_MEDICINE_REGISTERED", {"batch_no":r["batch_no"],"record_hash":r["record_hash"]})
    with connect() as c:
        already = c.execute("SELECT 1 FROM audit_chain WHERE event_type='DEMO_EXTRA_RECORDS_SEEDED' LIMIT 1").fetchone()
        extra_count = c.execute("SELECT COUNT(*) n FROM medicines WHERE batch_no LIKE 'DEMO-EXTRA-%'").fetchone()["n"]
    if extra_count and not already:
        audit("DEMO_EXTRA_RECORDS_SEEDED", {"count": extra_count, "note": "Fictional academic demo records"})

@app.route("/")
def index():
    if session.get("role") == "customer":
        return redirect(url_for("customer_home"))
    if session.get("role") != "admin":
        return redirect(url_for("customer_login"))
    q = request.args.get("q","").strip()
    with connect() as c:
        if q:
            rows = c.execute("SELECT * FROM medicines WHERE name LIKE ? OR manufacturer LIKE ? OR batch_no LIKE ? ORDER BY id DESC",
                             (f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
        else:
            rows = c.execute("SELECT * FROM medicines ORDER BY id DESC").fetchall()
        total = c.execute("SELECT COUNT(*) n FROM medicines").fetchone()["n"]
    items = [dict(r, status=status(r["expiry_date"])) for r in rows]
    return render_template("index.html", medicines=items, total=total, query=q)

@app.route("/verify", methods=["GET","POST"])
def verify():
    if not session.get("username"):
        return redirect(url_for("customer_login"))
    result = None
    state = None
    if request.method == "POST":
        batch = request.form.get("batch_no","").strip()
        with connect() as c:
            row = c.execute("SELECT * FROM medicines WHERE batch_no=?", (batch,)).fetchone()
        if row:
            result = dict(row)
            state = status(row["expiry_date"])
            audit("BATCH_VERIFIED", {"batch_no":batch,"status":state})
        else:
            state = "Not Found"
            audit("BATCH_NOT_FOUND", {"batch_no":batch})
    return render_template("verify.html", medicine=result, state=state)

@app.route("/barcode-lookup", methods=["GET","POST"])
def barcode_lookup():
    if not session.get("username"):
        return redirect(url_for("customer_login"))
    medicine = None
    state = None
    scanned = ""
    if request.method == "POST":
        scanned = request.form.get("barcode", "").strip()
        with connect() as c:
            row = c.execute("SELECT * FROM medicines WHERE barcode=? OR batch_no=?", (scanned, scanned)).fetchone()
        if row:
            medicine = dict(row)
            state = status(row["expiry_date"])
            audit("BARCODE_LOOKUP", {"code": scanned, "status": state})
        else:
            state = "Not Found"
            audit("BARCODE_LOOKUP_NOT_FOUND", {"code": scanned})
    return render_template("barcode_lookup.html", medicine=medicine, state=state, scanned=scanned)

@app.route("/api/demo-medicine/<batch_no>")
def demo_medicine_details(batch_no):
    # Photo OCR is available to signed-in customers as well as admins.
    # Keep the endpoint private to authenticated project users.
    if not session.get("username") or session.get("role") not in ("admin", "customer"):
        return {"error": "Please log in to view medicine details."}, 401
    with connect() as c:
        row = c.execute("SELECT * FROM medicines WHERE batch_no=?", (batch_no,)).fetchone()
    if not row:
        return {"found": False}, 404
    item = dict(row)
    info = medicine_info(item.get("name", ""))
    item.update({"status": status(item["expiry_date"]), "uses": info["description"], "when_used": info["description"], "safety": info["warning"], "demo_only": True})
    return item

@app.route("/admin/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        pw = hashlib.sha256(request.form.get("password","").encode()).hexdigest()
        with connect() as c:
            user = c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username,pw)).fetchone()
        if user:
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard" if user["role"] == "admin" else "customer_home"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/customer/register", methods=["GET", "POST"])
def customer_register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3 or len(password) < 6:
            flash("Username must be 3+ characters and password at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            try:
                with connect() as c:
                    c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                              (username, hashlib.sha256(password.encode()).hexdigest(), "customer"))
                audit("CUSTOMER_REGISTERED", {"username": username})
                flash("Customer account created. Please log in.", "success")
                return redirect(url_for("customer_login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "danger")
    return render_template("customer_register.html")

@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        pw = hashlib.sha256(request.form.get("password", "").encode()).hexdigest()
        with connect() as c:
            user = c.execute("SELECT * FROM users WHERE username=? AND password_hash=? AND role='customer'", (username, pw)).fetchone()
        if user:
            session.clear()
            session["username"] = user["username"]
            session["role"] = "customer"
            flash("Welcome! You are signed in as a customer.", "success")
            return redirect(url_for("customer_home"))
        flash("Invalid customer username or password.", "danger")
    return render_template("customer_login.html")

@app.route("/customer")
@customer_required
def customer_home():
    return render_template("customer_home.html")

@app.route("/customer/logout")
def customer_logout():
    session.clear()
    return redirect(url_for("customer_login"))

@app.route("/admin")
@login_required
def dashboard():
    with connect() as c:
        rows = c.execute("SELECT * FROM medicines ORDER BY id DESC").fetchall()
        blocks = c.execute("SELECT * FROM audit_chain ORDER BY id DESC LIMIT 8").fetchall()
    return render_template("dashboard.html", medicines=[dict(r,status=status(r["expiry_date"])) for r in rows],
                           blocks=blocks, integrity=chain_ok())

@app.route("/admin/add", methods=["GET","POST"])
@login_required
def add():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        maker = request.form.get("manufacturer","").strip()
        batch = request.form.get("batch_no","").strip()
        mfg = request.form.get("mfg_date","")
        exp = request.form.get("expiry_date","")
        desc = request.form.get("description","").strip()
        barcode = request.form.get("barcode","").strip()
        if not all([name,maker,batch,mfg,exp]):
            flash("Fill all required fields.", "danger")
        else:
            try:
                if date.fromisoformat(exp) < date.fromisoformat(mfg):
                    flash("Expiry date cannot be earlier than manufacturing date.", "danger")
                    return render_template("add.html")
                ts = datetime.now().isoformat(timespec="seconds")
                payload = dict(name=name,manufacturer=maker,batch_no=batch,mfg_date=mfg,expiry_date=exp,description=desc,barcode=barcode)
                rh = digest(payload)
                with connect() as c:
                    c.execute("""INSERT INTO medicines(name,manufacturer,batch_no,mfg_date,expiry_date,description,created_at,record_hash,barcode)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (name,maker,batch,mfg,exp,desc,ts,rh,barcode or None))
                audit("MEDICINE_REGISTERED", {"batch_no":batch,"barcode":barcode,"record_hash":rh})
                flash("Medicine record added.", "success")
                return redirect(url_for("dashboard"))
            except ValueError:
                flash("Enter valid dates.", "danger")
            except sqlite3.IntegrityError:
                flash("Batch number already exists. Use a unique number.", "danger")
    return render_template("add.html")

@app.route("/admin/chain")
@login_required
def chain():
    with connect() as c:
        blocks = c.execute("SELECT * FROM audit_chain ORDER BY id DESC").fetchall()
    return render_template("chain.html", blocks=blocks, integrity=chain_ok())

@app.route("/health")
def health():
    return {"status":"ok","audit_chain_integrity":chain_ok()}

init_db()
if __name__ == "__main__":
    app.run(debug=True)
