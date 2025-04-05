import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import bcrypt

# Placeholder PriceAnalyzer class (replace with actual implementation)


class PriceAnalyzer:
    def predict_fair_price(self, category, location, area_sqm, complexity_score, material_quality_score):
        # Placeholder logic for fair price estimation
        base_price = 100 * area_sqm
        complexity_factor = complexity_score * 5
        material_factor = material_quality_score * 10
        location_factor = 1.0  # Adjust based on location
        return base_price + complexity_factor + material_quality_score + location_factor


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()

# In-memory storage for users, jobs, and applications (replace with a database in production)
users = {}  # Stores user data
jobs = {}  # Stores job listings
applications = {}  # Stores job applications

# User types
USER_TYPE_CONTRACTOR = "contractor"
USER_TYPE_TRADESMAN = "tradesman"

# Helper function to generate a unique ID


def generate_user_id():
    return str(uuid.uuid4())

# Helper function to hash passwords


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Helper function to verify passwords


def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

# Endpoint: Register a new user


@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.
    Expects JSON input with 'username', 'password', and 'user_type' (either 'contractor' or 'tradesman').
    """
    try:
        data = request.json
        # Validate required fields
        required_fields = ['username', 'password', 'user_type']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate user type
        if data['user_type'] not in [USER_TYPE_CONTRACTOR, USER_TYPE_TRADESMAN]:
            return jsonify({"error": "Invalid user type. Must be 'contractor' or 'tradesman'"}), 400

        # Check if username already exists
        for user in users.values():
            if user['username'] == data['username']:
                return jsonify({"error": "Username already exists"}), 400

        # Create user object
        user_id = generate_user_id()
        hashed_password = hash_password(data['password'])  # Hash the password

        # Decode the hashed password from bytes to string
        hashed_password_str = hashed_password.decode('utf-8')

        user = {
            'id': user_id,
            'username': data['username'],
            'password': hashed_password_str,  # Store hashed password as a string
            'user_type': data['user_type']
        }

        # Store user
        users[user_id] = user
        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id,
            "user": user
        }), 201
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# Endpoint: Login a user
@app.route('/api/login', methods=['POST'])
def login():
    """
    Authenticate a user.
    Expects JSON input with 'username' and 'password'.
    """
    try:
        data = request.json
        # Validate required fields
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        # Find user by username
        user = None
        for u in users.values():
            if u['username'] == data['username']:
                user = u
                break
        if not user:
            return jsonify({"error": "Invalid username or password"}), 401
        # Verify password
        if not verify_password(user['password'], data['password']):
            return jsonify({"error": "Invalid username or password"}), 401
        return jsonify({
            "message": "Login successful",
            "user_id": user['id'],
            "user_type": user['user_type']
        }), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/api/create-job', methods=['POST'])
def create_job():
    """
    Create a new job listing.
    Expects JSON input with job details including 'title', 'category', 'location', 
    'description', 'area_sqm', 'complexity_score', 'material_quality_score', 
    'budget', 'deadline', and 'contractor_id'.
    """
    try:
        data = request.json
        # Validate required fields
        required_fields = ['title', 'category', 'location', 'description',
                           'area_sqm', 'complexity_score', 'material_quality_score',
                           'budget', 'deadline', 'contractor_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Get fair price estimate
        fair_price = analyzer.predict_fair_price(
            category=data['category'],
            location=data['location'],
            area_sqm=data['area_sqm'],
            complexity_score=data['complexity_score'],
            material_quality_score=data['material_quality_score']
        )

        # Create job object
        job = {
            'id': job_id,
            'title': data['title'],
            'category': data['category'],
            'location': data['location'],
            'description': data['description'],
            'area_sqm': data['area_sqm'],
            'complexity_score': data['complexity_score'],
            'material_quality_score': data['material_quality_score'],
            'budget': data['budget'],
            'deadline': data['deadline'],
            'contractor_id': data['contractor_id'],
            'created_at': datetime.now().isoformat(),
            'status': 'open',
            'fair_price_estimate': round(fair_price, 2),
            'applications': []
        }

        # Store job
        jobs[job_id] = job

        # Return response
        return jsonify({
            "message": "Job created successfully",
            "job_id": job_id,
            "job": job  # Ensure this matches the frontend's expectation
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: List jobs with optional filtering


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List all jobs with optional filtering.
    Supports query parameters for 'category', 'location', 'status', and 'user_id'.
    """
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        location = request.args.get('location')
        status = request.args.get('status', 'open')  # Default to open jobs
        user_id = request.args.get('user_id')
        user_type = request.args.get('user_type')
        # Convert jobs dictionary to list
        job_list = list(jobs.values())
        # Apply filters
        if category:
            job_list = [job for job in job_list if job['category'] == category]
        if location:
            job_list = [job for job in job_list if job['location'] == location]
        if status:
            job_list = [job for job in job_list if job['status'] == status]
        # Filter by user if user_id and user_type are provided
        if user_id and user_type:
            if user_type == USER_TYPE_CONTRACTOR:
                job_list = [
                    job for job in job_list if job['contractor_id'] == user_id]
            elif user_type == USER_TYPE_TRADESMAN:
                # For tradesmen, they can see all open jobs
                pass
        # Sort by creation date (newest first)
        job_list.sort(key=lambda x: datetime.fromisoformat(
            x['created_at']), reverse=True)
        return jsonify({
            "jobs": job_list,
            "count": len(job_list)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Get details for a specific job


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """
    Get details for a specific job.
    """
    try:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(jobs[job_id]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Update a job listing


@app.route('/api/jobs/<job_id>', methods=['PUT'])
def update_job(job_id):
    """
    Update a job listing.
    Expects JSON input with job details to update.
    """
    try:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        data = request.json
        # Fields that cannot be updated
        protected_fields = ['id', 'contractor_id',
                            'created_at', 'applications']
        # Update job fields
        for key, value in data.items():
            if key not in protected_fields:
                jobs[job_id][key] = value
        # If critical parameters changed, update fair price estimate
        if any(key in data for key in ['category', 'location', 'area_sqm', 'complexity_score', 'material_quality_score']):
            fair_price = analyzer.predict_fair_price(
                category=jobs[job_id]['category'],
                location=jobs[job_id]['location'],
                area_sqm=jobs[job_id]['area_sqm'],
                complexity_score=jobs[job_id]['complexity_score'],
                material_quality_score=jobs[job_id]['material_quality_score']
            )
            jobs[job_id]['fair_price_estimate'] = round(fair_price, 2)
        return jsonify({
            "message": "Job updated successfully",
            "job": jobs[job_id]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Submit an application for a job


@app.route('/api/jobs', methods=['GET'], endpoint='list_jobs_endpoint')
def list_jobs():
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        location = request.args.get('location')
        status = request.args.get('status', 'open')  # Default to open jobs
        user_id = request.args.get('user_id')
        user_type = request.args.get('user_type')
        
        # Convert jobs dictionary to list
        job_list = list(jobs.values())
        
        # Apply filters
        if category:
            job_list = [job for job in job_list if job['category'] == category]
        if location:
            job_list = [job for job in job_list if job['location'] == location]
        if status:
            job_list = [job for job in job_list if job['status'] == status]
        
        # Filter by user if user_id and user_type are provided
        if user_id and user_type:
            if user_type == USER_TYPE_CONTRACTOR:
                job_list = [job for job in job_list if job['contractor_id'] == user_id]
            elif user_type == USER_TYPE_TRADESMAN:
                # For tradesmen, they can see all open jobs
                pass
        
        # Sort by creation date (newest first)
        job_list.sort(key=lambda x: datetime.fromisoformat(x['created_at']), reverse=True)
        
        return jsonify({
            "jobs": job_list,
            "count": len(job_list)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Endpoint: List all applications for a specific job


@app.route('/api/jobs/<job_id>/applications', methods=['GET'])
def list_job_applications(job_id):
    """
    List all applications for a specific job.
    """
    try:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        # Get application IDs for the job
        application_ids = jobs[job_id]['applications']
        # Get application details
        job_applications = [applications[app_id]
                            for app_id in application_ids if app_id in applications]
        # Sort by creation date (newest first)
        job_applications.sort(key=lambda x: datetime.fromisoformat(
            x['created_at']), reverse=True)
        return jsonify({
            "applications": job_applications,
            "count": len(job_applications)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Update the status of a job application


@app.route('/api/applications/<application_id>', methods=['PUT'])
def update_application_status(application_id):
    """
    Update the status of a job application (accept or reject).
    Expects JSON input with 'status' set to 'accepted' or 'rejected'.
    """
    try:
        if application_id not in applications:
            return jsonify({"error": "Application not found"}), 404
        data = request.json
        if 'status' not in data or data['status'] not in ['accepted', 'rejected']:
            return jsonify({"error": "Invalid status. Must be 'accepted' or 'rejected'"}), 400
        # Update application status
        applications[application_id]['status'] = data['status']
        # If accepting application, update job status and handle other applications
        if data['status'] == 'accepted':
            job_id = applications[application_id]['job_id']
            jobs[job_id]['status'] = 'assigned'
            # Reject all other pending applications for this job
            for app_id in jobs[job_id]['applications']:
                if app_id != application_id and applications[app_id]['status'] == 'pending':
                    applications[app_id]['status'] = 'rejected'
        return jsonify({
            "message": f"Application {data['status']} successfully",
            "application": applications[application_id]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: List all applications submitted by a specific tradesman


@app.route('/api/tradesman/<tradesman_id>/applications', methods=['GET'])
def list_tradesman_applications(tradesman_id):
    """
    List all applications submitted by a specific tradesman.
    """
    try:
        # Filter applications by tradesman_id
        tradesman_applications = [app for app in applications.values()
                                  if app['tradesman_id'] == tradesman_id]
        # Sort by creation date (newest first)
        tradesman_applications.sort(
            key=lambda x: datetime.fromisoformat(x['created_at']), reverse=True)
        # Add job details to each application
        for app in tradesman_applications:
            job_id = app['job_id']
            if job_id in jobs:
                app['job_details'] = {
                    'title': jobs[job_id]['title'],
                    'category': jobs[job_id]['category'],
                    'location': jobs[job_id]['location'],
                    'status': jobs[job_id]['status']
                }
            else:
                app['job_details'] = None
        return jsonify({
            "applications": tradesman_applications,
            "count": len(tradesman_applications)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run the app
if __name__ == "__main__":
    app.run(debug=True)
