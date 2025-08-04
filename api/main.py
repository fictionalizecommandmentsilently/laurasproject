import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase_client import supabase
from auth_utils import get_user_id_from_jwt, get_user_roles
from student_ingestion_route import register_student_ingestion_routes

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Register student ingestion and management routes
register_student_ingestion_routes(app)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello from Python backend!"})

@app.route('/api/auth/user', methods=['GET'])
def get_authenticated_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token missing or invalid"}), 401

    jwt_token = auth_header.split(' ')[1]
    user_id = get_user_id_from_jwt(jwt_token)

    if not user_id:
        return jsonify({"error": "Invalid or expired token"}), 401

    user_roles = get_user_roles(user_id)

    return jsonify({
        "id": user_id,
        "roles": user_roles
    }), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            user_id = response.user.id
            user_roles = get_user_roles(user_id)
            return jsonify({
                "message": "Login successful",
                "access_token": response.session.access_token,
                "user": {
                    "id": user_id,
                    "email": response.user.email,
                    "roles": user_roles
                }
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 401

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            # The 'handle_new_user' trigger in schema.sql will assign the 'student' role
            user_id = response.user.id
            user_roles = get_user_roles(user_id) # Should return ['student']
            return jsonify({
                "message": "Signup successful",
                "access_token": response.session.access_token,
                "user": {
                    "id": user_id,
                    "email": response.user.email,
                    "roles": user_roles
                }
            }), 201
        else:
            return jsonify({"error": "Signup failed"}), 400
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"error": "Signup failed"}), 400

# Vercel specific entry point for serverless functions
# This is typically not needed if using `vc dev` or `vercel deploy` with `vercel.json`
# but can be useful for direct serverless function deployment.
# For this project, vercel.json handles routing to `api/main.py`.
if __name__ == '__main__':
    app.run(debug=True, port=5000)
