from flask import Flask, render_template_string, request, redirect, send_file
from werkzeug.utils import secure_filename
import os
import sqlite3
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
DB_FILE = "group.db"

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    assigned_to TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS completion (
                    task_id INTEGER,
                    username TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    filename TEXT
                )''')
    conn.commit()
    conn.close()
init_db()

# --- HTML Template ---
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bảng Chia Việc Nhóm - Dashboard</title>
<style>
body { font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background:#f4f7f8; color:#333; padding:20px;}
h1{text-align:center;margin-bottom:20px;color:#2c3e50;}
h2{color:#34495e;margin-top:30px;margin-bottom:15px;}
table{width:100%;border-collapse:collapse;margin-bottom:20px;box-shadow:0 4px 10px rgba(0,0,0,0.1);background:#fff;border-radius:8px;overflow:hidden;}
th,td{padding:12px 15px;text-align:center;}
th{background-color:#3498db;color:white;font-weight:600;text-transform:uppercase;font-size:14px;}
tr{transition:all 0.2s ease-in-out;}
tr:hover{background-color:#f1f9ff;transform:scale(1.01);}
.completed td{background-color:#dff0d8;color:#155724;font-weight:bold;}
button{padding:6px 12px;border-radius:6px;border:none;cursor:pointer;transition:0.2s;font-weight:bold;}
button.tick{background-color:#2ecc71;color:#fff;}
button.tick:hover{background-color:#27ae60;}
button.delete{background-color:#e74c3c;color:#fff;}
button.delete:hover{background-color:#c0392b;}
form.inline{display:inline-block;margin:0;}
input[type=text]{padding:6px 10px;border-radius:6px;border:1px solid #ccc;margin-right:5px;}
.upload-section{background:#fff;padding:15px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-bottom:20px;}
ul.files{list-style:none;padding-left:0;}
ul.files li{padding:6px 0;border-bottom:1px solid #eee;}
ul.files li a{color:#2980b9;text-decoration:none;}
ul.files li a:hover{text-decoration:underline;}
.export-buttons button{margin-right:10px;}
</style>
</head>
<body>
<h1>Bảng Chia Việc Nhóm - Dashboard</h1>

<h2>Thêm công việc mới</h2>
<form method="POST" class="inline">
  <input type="text" name="task_name" placeholder="Tên công việc" required>
  <input type="text" name="assigned_to" placeholder="Tên các thành viên (ngăn cách ;)" required>
  <button type="submit" name="action" value="add_task">Thêm</button>
</form>

<table>
<tr>
<th>STT</th>
<th>Công việc</th>
<th>Người thực hiện</th>
<th>Hoàn thành</th>
<th>Tick</th>
<th>Xóa</th>
</tr>
{% for task in tasks %}
<tr class="{{ 'completed' if task.completed_count>0 else '' }}">
<td>{{ loop.index }}</td>
<td style="text-align:left;">{{ task.task_name }}</td>
<td style="text-align:left;">{{ task.assigned_to }}</td>
<td>{{ task.completed_count }}/{{ task.total_assigned }}</td>
<td>
<form method="POST" class="inline">
  <input type="hidden" name="task_id" value="{{ task.id }}">
  <input type="hidden" name="username" value="{{ current_user }}">
  <button type="submit" class="tick" name="action" value="toggle_complete">
    {% if current_user in task.completed_users %}Bỏ tick{% else %}Tick{% endif %}
  </button>
</form>
</td>
<td>
<form method="POST" class="inline">
  <input type="hidden" name="task_id" value="{{ task.id }}">
  <button type="submit" class="delete" name="action" value="delete_task">Xóa</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<div class="upload-section">
<h2>Upload file</h2>
<form method="POST" enctype="multipart/form-data" class="inline">
  <input type="text" name="username" placeholder="Tên bạn" required>
  <input type="file" name="file">
  <button type="submit" name="action" value="upload">Upload</button>
</form>

<h3>Files đã nộp</h3>
<ul class="files">
{% for file in files %}
<li>
  {{ file.username }}: <a href="/uploads/{{ file.filename }}" target="_blank">{{ file.filename }}</a>
  <form method="POST" class="inline">
    <input type="hidden" name="file_id" value="{{ file.id }}">
    <button type="submit" name="action" value="delete_file" class="delete">Xóa</button>
  </form>
</li>
{% endfor %}
</ul>
</div>

<h2>Export</h2>
<div class="export-buttons">
<form method="GET" action="/export" class="inline">
  <button type="submit" name="type" value="excel">Xuất Excel</button>
  <button type="submit" name="type" value="word">Xuất Word</button>
</form>
</div>

</body>
</html>
"""

# --- Helper ---
def get_tasks():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, task_name, assigned_to FROM tasks")
    rows = c.fetchall()
    tasks_list = []
    for r in rows:
        task_id, task_name, assigned_to_str = r
        assigned_list = [x.strip() for x in assigned_to_str.split(';') if x.strip()]
        total = len(assigned_list)
        c.execute("SELECT username FROM completion WHERE task_id=?", (task_id,))
        completed_users = [u[0] for u in c.fetchall()]
        tasks_list.append(type('Task', (), {
            'id': task_id,
            'task_name': task_name,
            'assigned_to': assigned_to_str,
            'total_assigned': total,
            'completed_count': len(completed_users),
            'completed_users': completed_users
        })())
    conn.close()
    return tasks_list

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    current_user = request.args.get('user', 'Anonymous')
    if request.method == 'POST':
        action = request.form.get('action')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if action == 'add_task':
            c.execute("INSERT INTO tasks(task_name, assigned_to) VALUES (?, ?)",
                      (request.form['task_name'], request.form['assigned_to']))
            conn.commit()
        elif action == 'delete_task':
            task_id = request.form['task_id']
            c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            c.execute("DELETE FROM completion WHERE task_id=?", (task_id,))
            conn.commit()
        elif action == 'toggle_complete':
            task_id = request.form['task_id']
            username = request.form['username']
            c.execute("SELECT * FROM completion WHERE task_id=? AND username=?", (task_id, username))
            if c.fetchone():
                c.execute("DELETE FROM completion WHERE task_id=? AND username=?", (task_id, username))
            else:
                c.execute("INSERT INTO completion(task_id, username) VALUES (?, ?)", (task_id, username))
            conn.commit()
        elif action == 'upload':
            username = request.form['username']
            file = request.files['file']
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                c.execute("INSERT INTO uploads(username, filename) VALUES (?, ?)", (username, filename))
                conn.commit()
        elif action == 'delete_file':
            file_id = request.form['file_id']
            c.execute("SELECT filename FROM uploads WHERE id=?", (file_id,))
            f = c.fetchone()
            if f:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f[0])
                if os.path.exists(filepath):
                    os.remove(filepath)
                c.execute("DELETE FROM uploads WHERE id=?", (file_id,))
                conn.commit()
        conn.close()
        return redirect(f"/?user={current_user}")

    tasks = get_tasks()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, filename FROM uploads")
    files = [type('File', (), {'id': fid, 'username': u, 'filename': f})() for fid, u, f in c.fetchall()]
    conn.close()
    return render_template_string(HTML, tasks=tasks, files=files, current_user=current_user)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/export')
def export():
    export_type = request.args.get('type', 'excel')
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT t.id, t.task_name, t.assigned_to,
        (SELECT COUNT(*) FROM completion c WHERE c.task_id=t.id) as completed_count
        FROM tasks t
    """, conn)
    conn.close()
    if export_type == 'excel':
        df.to_excel("tasks.xlsx", index=False)
        return send_file("tasks.xlsx", as_attachment=True)
    else:
        html = '<html><head><meta charset="utf-8"><style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #000;padding:8px;text-align:center;}th{background:#3498db;color:#fff;}</style></head><body>'
        html += '<h2>Bảng Chia Việc Nhóm</h2><table><tr><th>STT</th><th>Công việc</th><th>Người thực hiện</th><th>Hoàn thành</th></tr>'
        for idx, row in df.iterrows():
            total = len([x.strip() for x in row['assigned_to'].split(';') if x.strip()])
            html += f'<tr><td>{idx+1}</td><td>{row["task_name"]}</td><td>{row["assigned_to"]}</td><td>{row["completed_count"]}/{total}</td></tr>'
        html += '</table></body></html>'
        path = "tasks.doc"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        return send_file(path, as_attachment=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

