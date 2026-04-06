from flask import Flask, request, redirect, render_template, session
import psycopg2
import string, random, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 🔥 VERY IMPORTANT FOR RENDER (HTTPS)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = "None"

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---------------------------
# INIT DB
# ---------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id SERIAL PRIMARY KEY,
        short_code TEXT UNIQUE,
        original_url TEXT,
        user_id INTEGER REFERENCES users(id)
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------------------------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ---------------------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_conn()
        cur = conn.cursor()

        try:
            cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)", (username,password))
            conn.commit()
        except:
            return "User exists"

        cur.close()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# ---------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id,password FROM users WHERE username=%s",(username,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session.clear()
            session["user_id"] = user[0]
            return redirect("/")

        return "Invalid login"

    return render_template("login.html")

# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

# ---------------------------
@app.route("/shorten", methods=["POST"])
def shorten():
    if "user_id" not in session:
        return redirect("/login")

    url = request.form["url"]

    conn = get_conn()
    cur = conn.cursor()

    while True:
        code = generate_code()
        cur.execute("SELECT 1 FROM urls WHERE short_code=%s",(code,))
        if not cur.fetchone():
            break

    cur.execute(
        "INSERT INTO urls (short_code, original_url, user_id) VALUES (%s,%s,%s)",
        (code, url, session["user_id"])
    )

    conn.commit()
    cur.close()
    conn.close()

    return render_template("index.html", short_url=request.host_url + code)

# ---------------------------
@app.route("/<code>")
def redirect_url(code):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT original_url FROM urls WHERE short_code=%s",(code,))
    data = cur.fetchone()

    cur.close()
    conn.close()

    if data:
        return redirect(data[0])
    return "Not found"

# ---------------------------
@app.route("/all")
def all_urls():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT short_code, original_url FROM urls WHERE user_id=%s",(session["user_id"],))
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("all.html", data=data)

# ---------------------------
@app.route("/delete/<code>")
def delete(code):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM urls WHERE short_code=%s AND user_id=%s",(code,session["user_id"]))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/all")

# ---------------------------
app.config['SESSION_COOKIE_SECURE'] = True

# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)