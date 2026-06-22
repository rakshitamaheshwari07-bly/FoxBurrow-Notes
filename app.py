from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet

key = b'S4Ige8CDGzANHBfSe_BAtZmwS22dl6aiFhw1UmCjCIo='
cipher = Fernet(key)


app = Flask(__name__)
app.secret_key = "mysecretkey"

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            """,
            (username, )
        )

        user = cursor.fetchone()
        
        print("USER =", user)
        print("PASSWORD ENTERED =", password)
        conn.close()

        if user and check_password_hash(user[3], password):
            
            print("LOGIN SUCCESS")
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/notes")

        else:
            print("LOGIN FAILED")
            return "Invalid Username or Password ❌"
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
            """,
            (username, email, hashed_password)
        )

        conn.commit()
        conn.close()
     
        print("User Saved Successfully!")
        return redirect("/login")
    return render_template("register.html")

@app.route("/create-note", methods=["GET", "POST"])
def create_note():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        content = request.form["content"]
        encrypted_content = cipher.encrypt(
    content.encode()
).decode()

        print("========== DEBUG ==========")
        print(content)
        print("===========================")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        created_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        cursor.execute(
            """
            INSERT INTO notes
            (title, content, user_id, created_at, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                encrypted_content,
                session["user_id"],
                created_at,
                category
            )
        )

        conn.commit()
        conn.close()

        return redirect("/notes")

    return render_template("create_note.html")

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM users
        WHERE id=?
        """,
        (session["user_id"],)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM notes
        WHERE user_id=?
        """,
        (session["user_id"],)
    )

    note_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        note_count=note_count
    )
    
    
@app.route("/notes")
def view_notes():

    
    if "user_id" not in session:
        return redirect("/login")

    search = request.args.get("search")
    category = request.args.get("category")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if category:

        cursor.execute(
            """
            SELECT * FROM notes
            WHERE user_id=? AND category=?
            """,
            (session["user_id"], category)
        )

    elif search:

        cursor.execute(
            """
            SELECT * FROM notes
            WHERE user_id=? AND title LIKE ?
            """,
            (session["user_id"], f"%{search}%")
        )

    else:

        cursor.execute(
            """
            SELECT * FROM notes
            WHERE user_id=?
            """,
            (session["user_id"],)
        )

    notes = cursor.fetchall()

    decrypted_notes = []

    for note in notes:

        try:
            decrypted_content = cipher.decrypt(
                note[2].encode()
            ).decode()

            note = list(note)
            note[2] = decrypted_content

        except:
            pass

        decrypted_notes.append(note)

    notes = decrypted_notes

    note_count = len(notes)

    conn.close()

    return render_template(
        "notes.html",
        notes=notes,
        note_count=note_count
    )

@app.route("/edit-note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]

        encrypted_content = cipher.encrypt(
            content.encode()
        ).decode()

        cursor.execute(
            """
            UPDATE notes
            SET title=?, content=?
            WHERE id=?
            """,
            (
                title,
                encrypted_content,
                note_id
            )
        )

        conn.commit()
        conn.close()

        return redirect("/notes")

    cursor.execute(
        """
        SELECT * FROM notes
        WHERE id=? AND user_id=?
        """,
        (note_id, session["user_id"])
    )

    note = cursor.fetchone()

    if not note:
        conn.close()
        return "Access Denied ❌"

    try:
        decrypted_content = cipher.decrypt(
            note[2].encode()
        ).decode()

        note = list(note)
        note[2] = decrypted_content

    except:
        pass

    conn.close()

    return render_template(
        "edit_note.html",
        note=note
    )
@app.route("/delete-note/<int:note_id>")
def delete_note(note_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM notes
        WHERE id=? AND user_id=?
        """,
        (note_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/notes")    

@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE id=?
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        if not check_password_hash(user[3], current_password):
            conn.close()
            return "Current Password is Incorrect ❌"

        if new_password != confirm_password:
            conn.close()
            return "Passwords Do Not Match ❌"

        hashed_password = generate_password_hash(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password=?
            WHERE id=?
            """,
            (hashed_password, session["user_id"])
        )

        conn.commit()
        conn.close()

        return "Password Changed Successfully! ✅"

    return render_template("change_password.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=False)
    