from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_NAME = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            branch_name TEXT,
            expiry_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/check_license', methods=['POST'])
def check_license():
    data = request.json
    client_id = data.get('client_id')
    branch_name = data.get('branch_name', 'الإخوة ماركت')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM clients WHERE client_id = ?", (client_id,))
    row = cursor.fetchone()

    now = datetime.now()

    if not row:
        # تسجيل العميل لأول مرة لتجربة 10 دقائق مثلاً أو شهر
        default_expiry = now + timedelta(days=30)
        cursor.execute("INSERT INTO clients VALUES (?, ?, ?)", (client_id, branch_name, default_expiry.isoformat()))
        conn.commit()
        expiry_date = default_expiry
    else:
        expiry_date = datetime.fromisoformat(row[0])

    conn.close()

    time_left = expiry_date - now
    is_active = time_left.total_seconds() > 0

    return jsonify({
        "status": "active" if is_active else "expired",
        "seconds_left": int(time_left.total_seconds()),
        "expiry_date": expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/renew', methods=['POST'])
def renew():
    data = request.json
    client_id = data.get('client_id')
    unit = data.get('unit')  # minutes, hours, days, weeks, months
    amount = int(data.get('amount', 1))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM clients WHERE client_id = ?", (client_id,))
    row = cursor.fetchone()

    now = datetime.now()
    current_expiry = datetime.fromisoformat(row[0]) if row and datetime.fromisoformat(row[0]) > now else now

    if unit == 'دقيقة':
        new_expiry = current_expiry + timedelta(minutes=amount)
    elif unit == 'ساعة':
        new_expiry = current_expiry + timedelta(hours=amount)
    elif unit == 'يوم':
        new_expiry = current_expiry + timedelta(days=amount)
    elif unit == 'أسبوع':
        new_expiry = current_expiry + timedelta(weeks=amount)
    elif unit == 'شهر':
        new_expiry = current_expiry + timedelta(days=amount * 30)

    cursor.execute("UPDATE clients SET expiry_date = ? WHERE client_id = ?", (new_expiry.isoformat(), client_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "new_expiry": new_expiry.strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/branches', methods=['GET'])
def get_branches():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT client_id, branch_name, expiry_date FROM clients")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    result = []
    for row in rows:
        exp = datetime.fromisoformat(row[2])
        diff = exp - now
        result.append({
            "client_id": row[0],
            "branch_name": row[1],
            "days_left": max(0, diff.days),
            "is_active": diff.total_seconds() > 0
        })

    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5000)