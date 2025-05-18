from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import re
from datetime import datetime
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    # Example connection
    conn = psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
    return "PostgreSQL connection successful!"

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        port=os.environ['POSTGRES_PORT'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )


def validate_task_data(data):
    if not re.match(r'^[\w\s\-()]{3,100}$', data.get('name', '')):
        return {"error": "Invalid task name (3-100 alphanumeric characters)"}, 400
    if data.get('priority') not in ['Low', 'Medium', 'High']:
        return {"error": "Invalid priority value"}, 400
    if 'deadline' in data and data['deadline']:
        try:
            deadline_dt = datetime.strptime(data['deadline'], '%Y-%m-%d')
            if deadline_dt < datetime.now():
                return {"error": "Deadline cannot be in the past"}, 400
        except ValueError:
            return {"error": "Invalid deadline format. Use YYYY-MM-DD."}, 400
    return None

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, progress, assigned_to, deadline, priority FROM tasks ORDER BY id")
        tasks = cursor.fetchall()
        for task in tasks:
            if task['deadline']:
                task['deadline'] = task['deadline'].strftime('%Y-%m-%d')
        cursor.close()
        conn.close()
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    validation = validate_task_data(data)
    if validation: return validation

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks (name, progress, assigned_to, deadline, priority)
            VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (data['name'], data.get('progress', 0), data['assigned_to'],
             data['deadline'] if data.get('deadline') else None,
             data['priority'])
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Task added successfully", "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    if 'progress' in data and not (0 <= data['progress'] <= 100):
        return jsonify({"error": "Progress must be between 0-100"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET progress = %s WHERE id = %s", 
                      (data['progress'], task_id))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
