from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "student-attendance-demo-key"
DB = "students.db"

SUBJECTS = [
    (1, "Ethical Hacking"),
    (2, "STQA"),
    (3, "Numerical Methods"),
    (4, "IKS"),
    (5, "AI"),
    (6, "Cyber Security"),
]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL UNIQUE,
            course TEXT NOT NULL,
            email TEXT,
            phone TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY,
            subject_name TEXT NOT NULL UNIQUE
        )
    """)
    for subject_id, subject_name in SUBJECTS:
        conn.execute(
            "INSERT OR IGNORE INTO subjects (id, subject_name) VALUES (?, ?)",
            (subject_id, subject_name),
        )

    # Fresh subject-wise attendance schema. If an older database exists,
    # preserve its student data and recreate attendance without guessing
    # subjects for old records.
    attendance_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'"
    ).fetchone()
    if attendance_exists:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(attendance)").fetchall()]
        if "subject_id" not in columns:
            conn.execute("ALTER TABLE attendance RENAME TO attendance_old")
            conn.execute("""
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    attendance_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                    UNIQUE(student_id, subject_id, attendance_date)
                )
            """)
            conn.execute("DROP TABLE attendance_old")
    else:
        conn.execute("""
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE(student_id, subject_id, attendance_date)
            )
        """)
    conn.commit()
    conn.close()


def today_string():
    return date.today().isoformat()


@app.route("/")
def index():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_records = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    present_records = conn.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'").fetchone()[0]
    today = today_string()
    today_present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present'", (today,)
    ).fetchone()[0]
    conn.close()
    return render_template(
        "index.html", students=students, total_students=total_students,
        total_records=total_records, present_records=present_records,
        today_present=today_present, today=today,
    )


@app.route("/add", methods=["GET", "POST"])
def add_student():
    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        roll_no = request.form["roll_no"].strip()
        course = request.form["course"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        if not name or not roll_no or not course:
            error = "Name, Roll Number and Course are required."
        else:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO students (name, roll_no, course, email, phone) VALUES (?, ?, ?, ?, ?)",
                    (name, roll_no, course, email, phone),
                )
                conn.commit()
                conn.close()
                flash("Student added successfully.", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                error = "Roll Number already exists."
    return render_template("add_student.html", error=error)


@app.route("/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404

    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        roll_no = request.form["roll_no"].strip()
        course = request.form["course"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        if not name or not roll_no or not course:
            error = "Name, Roll Number and Course are required."
        else:
            try:
                conn.execute(
                    "UPDATE students SET name=?, roll_no=?, course=?, email=?, phone=? WHERE id=?",
                    (name, roll_no, course, email, phone, student_id),
                )
                conn.commit()
                conn.close()
                flash("Student updated successfully.", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                error = "Roll Number already exists."
    conn.close()
    return render_template("edit_student.html", student=student, error=error)


@app.route("/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully. Related attendance records were also removed.", "success")
    return redirect(url_for("index"))


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    conn = get_db()
    students = conn.execute("""
        SELECT * FROM students
        WHERE name LIKE ? OR roll_no LIKE ? OR course LIKE ? OR email LIKE ? OR phone LIKE ?
        ORDER BY id DESC
    """, tuple(f"%{q}%" for _ in range(5))).fetchall()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_records = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    present_records = conn.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'").fetchone()[0]
    today = today_string()
    today_present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present'", (today,)
    ).fetchone()[0]
    conn.close()
    return render_template(
        "index.html", students=students, q=q, total_students=total_students,
        total_records=total_records, present_records=present_records,
        today_present=today_present, today=today,
    )


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    selected_date = request.values.get("attendance_date", today_string())
    selected_subject_id = request.values.get("subject_id", "1")

    try:
        selected_subject_id = int(selected_subject_id)
    except ValueError:
        selected_subject_id = 1

    if request.method == "POST":
        try:
            datetime.strptime(selected_date, "%Y-%m-%d")
        except ValueError:
            conn.close()
            flash("Please select a valid date.", "error")
            return redirect(url_for("attendance"))

        subject = conn.execute("SELECT * FROM subjects WHERE id=?", (selected_subject_id,)).fetchone()
        if subject is None:
            conn.close()
            flash("Please select a valid subject.", "error")
            return redirect(url_for("attendance"))

        if not students:
            conn.close()
            flash("Add at least one student before marking attendance.", "error")
            return redirect(url_for("add_student"))

        try:
            for student in students:
                status = request.form.get(f"student_{student['id']}")
                if status not in ("Present", "Absent"):
                    continue
                conn.execute(
                    """
                    INSERT INTO attendance (student_id, subject_id, attendance_date, status)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(student_id, subject_id, attendance_date)
                    DO UPDATE SET status=excluded.status
                    """,
                    (student["id"], selected_subject_id, selected_date, status),
                )
            conn.commit()
            conn.close()
            flash(f"Attendance saved for {subject['subject_name']} on {selected_date}.", "success")
            return redirect(url_for("attendance", attendance_date=selected_date, subject_id=selected_subject_id))
        except sqlite3.Error as exc:
            conn.rollback()
            conn.close()
            flash(f"Could not save attendance: {exc}", "error")
            return redirect(url_for("attendance", attendance_date=selected_date, subject_id=selected_subject_id))

    existing = conn.execute(
        "SELECT student_id, status FROM attendance WHERE attendance_date=? AND subject_id=?",
        (selected_date, selected_subject_id),
    ).fetchall()
    existing_map = {row["student_id"]: row["status"] for row in existing}
    conn.close()
    return render_template(
        "attendance.html", students=students, subjects=subjects,
        selected_date=selected_date, selected_subject_id=selected_subject_id,
        existing_map=existing_map,
    )


@app.route("/attendance/history")
def attendance_history():
    selected_date = request.args.get("attendance_date", "").strip()
    selected_subject_id = request.args.get("subject_id", "").strip()
    conn = get_db()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    query = """
        SELECT a.attendance_date, a.status, s.name, s.roll_no, s.course,
               sub.subject_name
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        JOIN subjects sub ON sub.id = a.subject_id
    """
    conditions = []
    params = []
    if selected_date:
        conditions.append("a.attendance_date = ?")
        params.append(selected_date)
    if selected_subject_id:
        try:
            int(selected_subject_id)
            conditions.append("a.subject_id = ?")
            params.append(int(selected_subject_id))
        except ValueError:
            selected_subject_id = ""
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY a.attendance_date DESC, sub.id ASC, s.roll_no ASC"
    records = conn.execute(query, params).fetchall()
    conn.close()
    return render_template(
        "history.html", records=records, subjects=subjects,
        selected_date=selected_date, selected_subject_id=selected_subject_id,
    )


@app.route("/report")
def report():
    selected_subject_id = request.args.get("subject_id", "").strip()
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
    reports = []

    for student in students:
        query_total = "SELECT COUNT(*) FROM attendance WHERE student_id=?"
        query_present = "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'"
        params = [student["id"]]
        if selected_subject_id:
            try:
                sid = int(selected_subject_id)
                query_total += " AND subject_id=?"
                query_present += " AND subject_id=?"
                params.append(sid)
            except ValueError:
                selected_subject_id = ""
                params = [student["id"]]
        total = conn.execute(query_total, params).fetchone()[0]
        present = conn.execute(query_present, params).fetchone()[0]
        absent = total - present
        percentage = round((present / total) * 100, 2) if total else 0
        reports.append({
            "name": student["name"], "roll_no": student["roll_no"],
            "course": student["course"], "total": total, "present": present,
            "absent": absent, "percentage": percentage,
        })

    subject_reports = []
    for subject in subjects:
        total = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE subject_id=?", (subject["id"],)
        ).fetchone()[0]
        present = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE subject_id=? AND status='Present'", (subject["id"],)
        ).fetchone()[0]
        subject_reports.append({
            "name": subject["subject_name"], "total": total, "present": present,
            "absent": total - present,
            "percentage": round((present / total) * 100, 2) if total else 0,
        })

    conn.close()
    return render_template(
        "report.html", reports=reports, subjects=subjects,
        subject_reports=subject_reports, selected_subject_id=selected_subject_id,
    )


# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)

# Initialize database when the application starts
init_db()

if __name__ == "__main__":
    app.run(debug=True)
