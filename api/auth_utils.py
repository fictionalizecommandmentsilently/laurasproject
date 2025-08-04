import os
from functools import wraps
from flask import request, jsonify
from supabase_client import supabase

def get_user_id_from_jwt(jwt_token):
    """Extracts user ID from a Supabase JWT."""
    try:
        # Supabase's auth.api.getUser() requires a valid JWT
        # This will verify the JWT and return the user object
        user_response = supabase.auth.get_user(jwt_token)
        if user_response and user_response.user:
            return user_response.user.id
        return None
    except Exception as e:
        print(f"Error getting user from JWT: {e}")
        return None

def get_user_roles(user_id):
    """Fetches roles for a given user ID from the database."""
    try:
        response = supabase.table('user_roles').select('roles(name)').eq('user_id', user_id).execute()
        if response.data:
            return [role['roles']['name'] for role in response.data]
        return []
    except Exception as e:
        print(f"Error fetching user roles: {e}")
        return []

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization token missing or invalid"}), 401

        jwt_token = auth_header.split(' ')[1]
        user_id = get_user_id_from_jwt(jwt_token)

        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_roles = get_user_roles(user_id)
        if 'admin' not in user_roles:
            return jsonify({"error": "Access denied: Admin role required"}), 403

        return f(*args, **kwargs)
    return decorated_function

def student_or_admin_required(f):
    """Decorator to restrict access to student (their own data) or admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization token missing or invalid"}), 401

        jwt_token = auth_header.split(' ')[1]
        user_id = get_user_id_from_jwt(jwt_token)

        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_roles = get_user_roles(user_id)
        is_admin = 'admin' in user_roles

        # Pass user_id and is_admin to the decorated function
        kwargs['current_user_id'] = user_id
        kwargs['is_admin'] = is_admin

        return f(*args, **kwargs)
    return decorated_function
