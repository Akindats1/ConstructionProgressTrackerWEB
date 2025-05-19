from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import re
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Consider adding origin restrictions in production

# Database connection pooling
db_url = urlparse(os.environ['DATABASE_URL'])
pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    user=db_url.username,
    password=db_url.password,
    host=db_url.hostname,
    port=db_url.port,
    database=db_url.path[1:]
)

def get_db_connection():
    return pool.getconn()

def release_db_connection(conn):
    pool.putconn(conn)

# Validation functions
def validate_task_data(data):
    # Name validation
    if not re.match(r'^[\w\s\-()]{3,100}$', data.get('name', '')):
        return {"error": "Invalid task name (3-100 alphanumeric characters)"}, 400
    
    # Priority validation
    if data.get('priority') not in ['Low', 'Medium', 'High']:
        return {"error": "Invalid priority value"}, 400
    
    # Deadline validation with timezone awareness
    if 'deadline' in data and data['deadline']:
        try:
            deadline_dt = datetime.strptime(data['deadline'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if deadline_dt < datetime.now(timezone.utc):
                return {"error": "Deadline cannot be in the past"}, 400
        except ValueError:
            return {"error": "Invalid deadline format. Use YYYY-MM-DD."}, 400
    
    # SQL injection prevention
    sql_injection_pattern = re.compile(r'(;|--|union|select|insert|update|delete|drop)', re.IGNORECASE)
    for value in data.values():
        if isinstance(value, str) and sql_injection_pattern.search(value):
            return {"error": "Invalid input detected"}, 400
    
    return None

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Routes
@app.route('/tasks', methods=['GET'])
def get_tasks():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, progress, assigned_to, deadline, priority 
                FROM tasks 
                ORDER BY id
            """)
            tasks = cursor.fetchall()
            for task in tasks:
                if task['deadline']:
                    task['deadline'] = task['deadline'].strftime('%Y-%m-%d')
            return jsonify(tasks), 200
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Failed to retrieve tasks"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    validation = validate_task_data(data)
    if validation: 
        return validation

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO tasks (name, progress, assigned_to, deadline, priority)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data['name'],
                data.get('progress', 0),
                data.get('assigned_to'),
                data.get('deadline'),
                data['priority']
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return jsonify({"message": "Task added successfully", "id": new_id}), 201
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        conn.rollback()
        return jsonify({"error": "Failed to create task"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    if 'progress' in data and not (0 <= data['progress'] <= 100):
        return jsonify({"error": "Progress must be between 0-100"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks 
                SET progress = %s 
                WHERE id = %s
            """, (data['progress'], task_id))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Task not found"}), 404
            
            conn.commit()
            return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        conn.rollback()
        return jsonify({"error": "Failed to update task"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Task not found"}), 404
            
            conn.commit()
            return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        conn.rollback()
        return jsonify({"error": "Failed to delete task"}), 500
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
