from flask import Flask, request, redirect, render_template, session
import psycopg2
import string
import random
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static")
app.secret_key = "supersecretkey"

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
# GENERATE CODE
# ---------------------------
def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

# ---------------------------
# REGISTER
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))

        conn = get_conn()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
        except:
            return "❌ User already exists"

        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ---------------------------
# LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id, password FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user"] = username
            session["user_id"] = user[0]
            return redirect("/")

        return "❌ Invalid credentials"

    return render_template("login.html")

# ---------------------------
# LOGOUT
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

# ---------------------------
# SHORTEN
# ---------------------------
@app.route("/shorten", methods=["POST"])
def shorten_url():
    if "user" not in session:
        return redirect("/login")

    original_url = request.form.get("url")

    conn = get_conn()
    cur = conn.cursor()

    while True:
        code = generate_code()
        cur.execute("SELECT * FROM urls WHERE short_code=%s", (code,))
        if not cur.fetchone():
            break

    cur.execute(
        "INSERT INTO urls (short_code, original_url, user_id) VALUES (%s, %s, %s)",
        (code, original_url, session["user_id"])
    )

    conn.commit()
    cur.close()
    conn.close()

    short_url = request.host_url + code

    return render_template("index.html", short_url=short_url)

# ---------------------------
# REDIRECT
# ---------------------------
@app.route("/<code>")
def redirect_url(code):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT original_url FROM urls WHERE short_code=%s", (code,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        return redirect(result[0])

    return "❌ Invalid URL", 404

# ---------------------------
# SHOW USER URLS
# ---------------------------
@app.route("/all")
def show_all():
    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT short_code, original_url FROM urls WHERE user_id=%s",
        (session["user_id"],)
    )
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("all.html", data=data)

# ---------------------------
# DELETE
# ---------------------------
@app.route("/delete/<code>")
def delete_url(code):
    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM urls WHERE short_code=%s AND user_id=%s",
        (code, session["user_id"])
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/all")

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)