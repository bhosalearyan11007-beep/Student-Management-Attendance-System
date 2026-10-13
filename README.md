# Student Management & Attendance System

College mini-project built with Python Flask, SQLite, HTML and CSS.

## Features
- Add, view, search, edit and delete students
- Mark attendance by subject and date
- Fixed subjects: Ethical Hacking, STQA, Numerical Methods, IKS, AI, Cyber Security
- Attendance history with date and subject filters
- Student-wise attendance report
- Subject-wise attendance summary
- Attendance percentage calculation

## Run the project
```bash
python -m venv venv
venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000` in a browser.

## Important
The new attendance database uses `student + subject + date` as the unique attendance combination. If you already have an older `students.db` from the previous version, back it up before running the upgraded version. Old attendance records from the previous subject-less version are not assigned to a subject automatically.
