from flask import Flask, request, redirect, render_template
import psycopg2, os, string, random
from werkzeug.security import generate_password_hash, check_password_hash

# 🔐 Flask Login
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---------------------------
# LOGIN MANAGER
# ---------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

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
        user_id INTEGER
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------------------------
def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

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
            return "User already exists"

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
            login_user(User(user[0]))   # 🔥 FIXED LOGIN
            return redirect("/")

        return "Invalid credentials"

    return render_template("login.html")

# ---------------------------
@app.route("/")
@login_required
def home():
    return render_template("index.html")

# ---------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ---------------------------
@app.route("/shorten", methods=["POST"])
@login_required
def shorten():
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
        (code, url, current_user.id)
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
    return "Invalid URL"

# ---------------------------
@app.route("/all")
@login_required
def all_urls():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT short_code, original_url FROM urls WHERE user_id=%s",(current_user.id,))
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("all.html", data=data)

# ---------------------------
@app.route("/delete/<code>")
@login_required
def delete(code):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM urls WHERE short_code=%s AND user_id=%s",(code,current_user.id))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/all")

# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)