import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import bcrypt

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Placeholder PriceAnalyzer class (replace with actual implementation)
class PriceAnalyzer:
    def predict_fair_price(self, category, location, area_sqm, complexity_score, material_quality_score):
        # Placeholder logic for fair price estimation
        base_price = 100 * area_sqm
        complexity_factor = complexity_score * 5
        material_factor = material_quality_score * 10
        location_factor = 1.0  # Adjust based on location
        return base_price + complexity_factor + material_quality_score + location_factor

# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()

# User types
USER_TYPE_CONTRACTOR = "contractor"
USER_TYPE_TRADESMAN = "tradesman"

# Database Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)

class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    area_sqm = db.Column(db.Float, nullable=False)
    complexity_score = db.Column(db.Float, nullable=False)
    material_quality_score = db.Column(db.Float, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    contractor_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="open")
    fair_price_estimate = db.Column(db.Float, nullable=False)
    applications = db.relationship('Application', backref='job', lazy=True)

class Application(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('job.id'), nullable=False)
    tradesman_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="pending")

# Helper function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Helper function to verify passwords
def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

# Endpoint: Register a new user
@app.route('/api/register', methods=['POST'])
def register():
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
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already exists"}), 400
        # Create user object
        hashed_password = hash_password(data['password']).decode('utf-8')
        new_user = User(
            username=data['username'],
            password=hashed_password,
            user_type=data['user_type']
        )
        # Save user to database
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "message": "User registered successfully",
            "user_id": new_user.id,
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "user_type": new_user.user_type
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Endpoint: Login a user
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        # Validate required fields
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        # Find user by username
        user = User.query.filter_by(username=data['username']).first()
        if not user or not verify_password(user.password, data['password']):
            return jsonify({"error": "Invalid username or password"}), 401
        return jsonify({
            "message": "Login successful",
            "user_id": user.id,
            "user_type": user.user_type
        }), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Endpoint: Create a new job listing
@app.route('/api/create-job', methods=['POST'])
def create_job():
    try:
        data = request.json
        # Validate required fields
        required_fields = ['title', 'category', 'location', 'description',
                           'area_sqm', 'complexity_score', 'material_quality_score',
                           'budget', 'deadline', 'contractor_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        # Get fair price estimate
        fair_price = analyzer.predict_fair_price(
            category=data['category'],
            location=data['location'],
            area_sqm=float(data['area_sqm']),
            complexity_score=float(data['complexity_score']),
            material_quality_score=float(data['material_quality_score'])
        )
        # Create job object
        new_job = Job(
            title=data['title'],
            category=data['category'],
            location=data['location'],
            description=data['description'],
            area_sqm=float(data['area_sqm']),
            complexity_score=float(data['complexity_score']),
            material_quality_score=float(data['material_quality_score']),
            budget=float(data['budget']),
            deadline=data['deadline'],
            contractor_id=data['contractor_id'],
            fair_price_estimate=round(fair_price, 2)
        )
        # Save job to database
        db.session.add(new_job)
        db.session.commit()
        return jsonify({
            "message": "Job created successfully",
            "job_id": new_job.id,
            "job": {
                "id": new_job.id,
                "title": new_job.title,
                "category": new_job.category,
                "location": new_job.location,
                "description": new_job.description,
                "area_sqm": new_job.area_sqm,
                "complexity_score": new_job.complexity_score,
                "material_quality_score": new_job.material_quality_score,
                "budget": new_job.budget,
                "deadline": new_job.deadline,
                "contractor_id": new_job.contractor_id,
                "created_at": new_job.created_at.isoformat(),
                "status": new_job.status,
                "fair_price_estimate": new_job.fair_price_estimate
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: List jobs with optional filtering
@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        location = request.args.get('location')
        status = request.args.get('status', 'open')  # Default to open jobs
        user_id = request.args.get('user_id')
        user_type = request.args.get('user_type')
        # Query jobs from the database
        job_query = Job.query
        # Apply filters
        if category:
            job_query = job_query.filter_by(category=category)
        if location:
            job_query = job_query.filter_by(location=location)
        if status:
            job_query = job_query.filter_by(status=status)
        if user_id and user_type == USER_TYPE_CONTRACTOR:
            job_query = job_query.filter_by(contractor_id=user_id)
        # Sort by creation date (newest first)
        jobs_list = job_query.order_by(Job.created_at.desc()).all()
        # Serialize jobs
        serialized_jobs = [{
            "id": job.id,
            "title": job.title,
            "category": job.category,
            "location": job.location,
            "description": job.description,
            "area_sqm": job.area_sqm,
            "complexity_score": job.complexity_score,
            "material_quality_score": job.material_quality_score,
            "budget": job.budget,
            "deadline": job.deadline,
            "contractor_id": job.contractor_id,
            "created_at": job.created_at.isoformat(),
            "status": job.status,
            "fair_price_estimate": job.fair_price_estimate
        } for job in jobs_list]
        return jsonify({
            "jobs": serialized_jobs,
            "count": len(serialized_jobs)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Get details for a specific job
@app.route('/api/jobs/<jobId>', methods=['GET'])
def get_job(jobId):
    try:
        print(f"Fetching job with ID: {jobId}")
        job = Job.query.get(jobId)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({
            "id": job.id,
            "title": job.title,
            "category": job.category,
            "location": job.location,
            "description": job.description,
            "area_sqm": job.area_sqm,
            "complexity_score": job.complexity_score,
            "material_quality_score": job.material_quality_score,
            "budget": job.budget,
            "deadline": job.deadline,
            "contractor_id": job.contractor_id,
            "created_at": job.created_at.isoformat(),
            "status": job.status,
            "fair_price_estimate": job.fair_price_estimate
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Update a job listing
@app.route('/api/jobs/<job_id>', methods=['PUT'])
def update_job(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        data = request.json
        # Fields that cannot be updated
        protected_fields = ['id', 'contractor_id', 'created_at']
        # Update job fields
        for key, value in data.items():
            if key not in protected_fields and hasattr(job, key):
                setattr(job, key, value)
        # If critical parameters changed, update fair price estimate
        if any(key in data for key in ['category', 'location', 'area_sqm', 'complexity_score', 'material_quality_score']):
            fair_price = analyzer.predict_fair_price(
                category=job.category,
                location=job.location,
                area_sqm=job.area_sqm,
                complexity_score=job.complexity_score,
                material_quality_score=job.material_quality_score
            )
            job.fair_price_estimate = round(fair_price, 2)
        # Save changes
        db.session.commit()
        return jsonify({
            "message": "Job updated successfully",
            "job": {
                "id": job.id,
                "title": job.title,
                "category": job.category,
                "location": job.location,
                "description": job.description,
                "area_sqm": job.area_sqm,
                "complexity_score": job.complexity_score,
                "material_quality_score": job.material_quality_score,
                "budget": job.budget,
                "deadline": job.deadline,
                "contractor_id": job.contractor_id,
                "created_at": job.created_at.isoformat(),
                "status": job.status,
                "fair_price_estimate": job.fair_price_estimate
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: Submit an application for a job
@app.route('/api/submit-application', methods=['POST'])
def submit_application():
    try:
        data = request.json
        # Validate required fields
        required_fields = ['job_id', 'tradesman_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        # Check if job exists
        job = Job.query.get(data['job_id'])
        if not job:
            return jsonify({"error": "Job not found"}), 404
        # Check if tradesman exists
        tradesman = User.query.get(data['tradesman_id'])
        if not tradesman or tradesman.user_type != USER_TYPE_TRADESMAN:
            return jsonify({"error": "Invalid tradesman"}), 400
        # Create application object
        new_application = Application(
            job_id=data['job_id'],
            tradesman_id=data['tradesman_id']
        )
        # Save application to database
        db.session.add(new_application)
        db.session.commit()
        return jsonify({
            "message": "Application submitted successfully",
            "application_id": new_application.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: List all applications for a specific job
@app.route('/api/jobs/<job_id>/applications', methods=['GET'])
def list_job_applications(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        # Get applications for the job
        applications_list = Application.query.filter_by(job_id=job_id).order_by(Application.created_at.desc()).all()
        # Serialize applications
        serialized_applications = [{
            "id": app.id,
            "job_id": app.job_id,
            "tradesman_id": app.tradesman_id,
            "created_at": app.created_at.isoformat(),
            "status": app.status
        } for app in applications_list]
        return jsonify({
            "applications": serialized_applications,
            "count": len(serialized_applications)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Update the status of a job application
@app.route('/api/applications/<application_id>', methods=['PUT'])
def update_application_status(application_id):
    try:
        application = Application.query.get(application_id)
        if not application:
            return jsonify({"error": "Application not found"}), 404
        data = request.json
        if 'status' not in data or data['status'] not in ['accepted', 'rejected']:
            return jsonify({"error": "Invalid status. Must be 'accepted' or 'rejected'"}), 400
        # Update application status
        application.status = data['status']
        # If accepting application, update job status and handle other applications
        if data['status'] == 'accepted':
            job = Job.query.get(application.job_id)
            if job:
                job.status = 'assigned'
                # Reject all other pending applications for this job
                pending_apps = Application.query.filter_by(job_id=job.id, status='pending').all()
                for app in pending_apps:
                    app.status = 'rejected'
        # Save changes
        db.session.commit()
        return jsonify({
            "message": f"Application {data['status']} successfully",
            "application": {
                "id": application.id,
                "job_id": application.job_id,
                "tradesman_id": application.tradesman_id,
                "created_at": application.created_at.isoformat(),
                "status": application.status
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: List all applications submitted by a specific tradesman
@app.route('/api/tradesman/<tradesman_id>/applications', methods=['GET'])
def list_tradesman_applications(tradesman_id):
    try:
        # Get applications submitted by the tradesman
        applications_list = Application.query.filter_by(tradesman_id=tradesman_id).order_by(Application.created_at.desc()).all()
        # Serialize applications
        serialized_applications = []
        for app in applications_list:
            job = Job.query.get(app.job_id)
            serialized_applications.append({
                "id": app.id,
                "job_id": app.job_id,
                "tradesman_id": app.tradesman_id,
                "created_at": app.created_at.isoformat(),
                "status": app.status,
                "job_details": {
                    "title": job.title,
                    "category": job.category,
                    "location": job.location,
                    "status": job.status
                } if job else None
            })
        return jsonify({
            "applications": serialized_applications,
            "count": len(serialized_applications)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)