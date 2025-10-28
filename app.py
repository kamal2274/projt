from flask import Flask, request, redirect, render_template, flash
import psycopg2, os, string, random, datetime

def get_db():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "shorty"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
        host=os.getenv("DB_HOST", "db"),
        port="5432"
    )
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS links (
        id SERIAL PRIMARY KEY,
        code VARCHAR(10) UNIQUE NOT NULL,
        target TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

def gen_code(length=6):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def make_unique_code():
    conn = get_db()
    cur = conn.cursor()
    while True:
        code = gen_code()
        cur.execute("SELECT 1 FROM links WHERE code=%s;", (code,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return code

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "devsecret")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        target = request.form.get("target").strip()
        custom = request.form.get("custom").strip() if request.form.get("custom") else None
        if not target:
            flash("Please enter a valid URL", "error")
            return render_template("index.html")
        conn = get_db()
        cur = conn.cursor()
        if custom:
            cur.execute("SELECT 1 FROM links WHERE code=%s;", (custom,))
            if cur.fetchone():
                flash("Custom code already in use", "error")
                conn.close()
                return render_template("index.html")
            code = custom
        else:
            code = make_unique_code()
        cur.execute("INSERT INTO links (code, target, created_at) VALUES (%s,%s,%s);",
                    (code, target, datetime.datetime.utcnow()))
        conn.commit()
        cur.close()
        conn.close()
        short_url = f"http://localhost:5000/{code}"
        return render_template("info.html", short=short_url, target=target)
    return render_template("index.html")

@app.route("/<code>")
def redirect_short(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT target FROM links WHERE code=%s;", (code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return ("Not Found", 404)
    return redirect(row[0])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
