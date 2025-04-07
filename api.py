import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import bcrypt
import requests  # For integrating with Resend API
import logging
# Assuming you have a PriceAnalyzer class
from PriceAnalyzer import PriceAnalyzer


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logging.basicConfig(level=logging.INFO)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Placeholder PriceAnalyzer class (replace with actual implementation)


# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()

# User types
USER_TYPE_CONTRACTOR = "contractor"
USER_TYPE_TRADESMAN = "tradesman"

# Database Models


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)


class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    area_sqm = db.Column(db.Float, nullable=False)
    complexity_score = db.Column(db.Float, nullable=False)
    material_quality_score = db.Column(db.Float, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    contractor_id = db.Column(
        db.String(36), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="open")
    fair_price_estimate = db.Column(db.Float, nullable=False)
    applications = db.relationship('Application', backref='job', lazy=True)


class Application(db.Model):
    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('job.id'), nullable=False)
    tradesman_id = db.Column(
        db.String(36), db.ForeignKey('user.id'), nullable=False)
    price_quote = db.Column(db.Float, nullable=False)  # Added field
    estimated_days = db.Column(db.Integer, nullable=False)  # Added field
    cover_letter = db.Column(db.Text)  # Optional field
    availability_date = db.Column(db.String(50))  # Optional field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="pending")

# Helper function to hash passwords


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Helper function to verify passwords


def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))


@app.route('/api/contractors/<contractor_id>/tasks', methods=['GET'])
def get_contractor_tasks(contractor_id):
    try:
        # Verify the contractor exists
        contractor = User.query.get(contractor_id)
        if not contractor or contractor.user_type != USER_TYPE_CONTRACTOR:
            return jsonify({"error": "Invalid contractor"}), 400

        # Get all jobs posted by this contractor
        jobs = Job.query.filter_by(contractor_id=contractor_id).all()

        # jobs = Job.query.all()
        logging.info("jobs =>>")
        for job in jobs:
            logging.info(job.contractor_id + " : " + job.id)
        # print(jobs)

        # Prepare response data
        tasks = []
        for job in jobs:
            # Find the accepted application for this job (if any)
            # accepted_app = Application.query.filter_by(
            #     job_id=job.id, status='accepted').first()

            accepted_app = Application.query.filter_by(
                job_id=job.id).first()

            task_data = {
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
                "created_at": job.created_at.isoformat()
            }

            # if accepted_app is not None:
            #     task_data["status"] = accepted_app.status
            if accepted_app:
                task_data["application_id"] = accepted_app.id
                task_data["status"] = accepted_app.status
                task_data["tradesman_id"] = accepted_app.tradesman_id
                task_data["price_quote"] = accepted_app.price_quote
                task_data["estimated_days"] = accepted_app.estimated_days

            tasks.append(task_data)

        return jsonify({"tasks": tasks}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Get tasks for a tradesman (jobs they've been assigned to)


@app.route('/api/tradesman/<tradesman_id>/tasks', methods=['GET'])
def get_tradesman_tasks(tradesman_id):
    try:
        # Verify the tradesman exists
        tradesman = User.query.get(tradesman_id)
        if not tradesman or tradesman.user_type != USER_TYPE_TRADESMAN:
            return jsonify({"error": "Invalid tradesman"}), 400

        # Get all accepted applications for this tradesman
        applications = Application.query.filter_by(
            tradesman_id=tradesman_id
        ).all()
        logging.info(f"applications: {applications}")
        # Prepare response data
        tasks = []
        for app in applications:
            job = Job.query.get(app.job_id)
            if job:
                tasks.append({
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
                    "status": app.status,
                    "created_at": job.created_at.isoformat(),
                    "price_quote": app.price_quote,
                    "estimated_days": app.estimated_days
                })

        return jsonify({"tasks": tasks}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: Update job status


@app.route('/api/jobs/<job_id>/status', methods=['PUT'])
def update_job_status(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        data = request.json
        if 'status' not in data or data['status'] not in ['ongoing', 'dispute', 'completed']:
            return jsonify({"error": "Invalid status. Must be 'ongoing', 'dispute', or 'completed'"}), 400

        # Update job status
        job.status = data['status']
        db.session.commit()

        return jsonify({
            "message": f"Job status updated to {data['status']} successfully",
            "job_id": job.id,
            "status": job.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: Report a dispute for a job


@app.route('/api/jobs/<job_id>/dispute', methods=['POST'])
def report_job_dispute(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        data = request.json
        if 'reported_by' not in data or 'reason' not in data:
            return jsonify({"error": "Missing required fields: reported_by, reason"}), 400

        # Update job status to dispute
        job.status = 'dispute'

        # Here you could add more logic to store dispute details in a separate table
        # For example, create a new DisputeReport model and store the data there

        db.session.commit()

        return jsonify({
            "message": "Dispute reported successfully",
            "job_id": job.id,
            "status": job.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: Resolve a dispute for a job


@app.route('/api/jobs/<job_id>/resolve-dispute', methods=['POST'])
def resolve_job_dispute(job_id):
    try:
        job = Job.query.get(job_id)
        if not job or job.status != 'dispute':
            return jsonify({"error": "Job not found or not in dispute status"}), 404

        data = request.json
        if 'resolution' not in data or 'resolved_by' not in data:
            return jsonify({"error": "Missing required fields: resolution, resolved_by"}), 400

        # Update job status back to ongoing
        job.status = 'ongoing'

        # Here you could add more logic to store resolution details

        db.session.commit()

        return jsonify({
            "message": "Dispute resolved successfully",
            "job_id": job.id,
            "status": job.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: Mark a job as completed


@app.route('/api/jobs/<job_id>/complete', methods=['POST'])
def complete_job(job_id):
    try:
        job = Job.query.get(job_id)
        if not job or job.status not in ['ongoing', 'assigned']:
            return jsonify({"error": "Job not found or not in appropriate status"}), 404

        data = request.json
        if 'completed_by' not in data:
            return jsonify({"error": "Missing required field: completed_by"}), 400

        # Update job status to completed
        job.status = 'completed'

        # Here you could add more logic like recording completion date,
        # final payment details, etc.

        db.session.commit()

        return jsonify({
            "message": "Job marked as completed successfully",
            "job_id": job.id,
            "status": job.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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
        print(data)
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


@app.route('/api/users', methods=['GET'])
def list_usrs():
    try:

        user_query = User.query.all()

        serialized_users = [{
            "id": user.id,
            "username": user.username,
            "user_type": user.user_type
        }for user in user_query]
        return jsonify({
            "jobs": serialized_users,
            "count": len(serialized_users)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/applications', methods=['GET'])
def list_applications():
    try:
        apps_query = Application.query.all()
        serialized_apps = [{
            "id": apps.id,
            "tradesman_id": apps.tradesman_id,
            "job_id": apps.job_id,
            "status": apps.status
        }for apps in apps_query]
        return jsonify({
            "jobs": serialized_apps,
            "count": len(serialized_apps)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


@app.route('/api/send-dispute-report', methods=['POST'])
def send_dispute_report():
    try:
        data = request.json

        # Validate required fields
        required_fields = ['phoneNumber', 'jobTitle',
                           'jobLocation', 'issueDate', 'additionalNotes']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Extract data
        phone_number = data['phoneNumber']
        job_title = data['jobTitle']
        job_location = data['jobLocation']
        issue_date = data['issueDate']
        additional_notes = data['additionalNotes']

        # Construct email content
        email_subject = "Dispute Report"
        email_to = "recipient@example.com"  # Replace with the recipient's email address
        email_from = "your-email@example.com"  # Replace with your verified sender email
        email_body = (
            f"Dispute Report:\n\n"
            f"Job Title: {job_title}\n"
            f"Location: {job_location}\n"
            f"Issue Date: {issue_date}\n"
            f"Phone Number: {phone_number}\n"
            f"Additional Notes: {additional_notes}"
        )

        # Send email using Resend API
        resend_api_key = "your_resend_api_key"  # Replace with your Resend API key
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": email_from,
            "to": email_to,
            "subject": email_subject,
            "text": email_body
        }

        response = requests.post(
            "https://api.resend.com/emails", json=payload, headers=headers)

        # Check if the email was sent successfully
        if response.status_code == 200:
            return jsonify({"message": "Dispute report sent successfully!"}), 200
        else:
            return jsonify({"error": "Failed to send dispute report via email."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint: List all applications for a specific job


@app.route('/api/jobs/<job_id>/applications', methods=['GET'])
def list_job_applications(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        # Get applications for the job
        applications_list = Application.query.filter_by(
            job_id=job_id).order_by(Application.created_at.desc()).all()
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

# Endpoint: Submit an application for a job with price quote and estimated days


@app.route('/api/jobs/<job_id>/applications', methods=['POST'])
def submit_job_application(job_id):
    try:
        # Get job and validate it exists
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        data = request.json
        # Validate required fields
        required_fields = ['tradesman_id', 'price_quote', 'estimated_days']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate data types
        if not isinstance(data['price_quote'], (int, float)) or data['price_quote'] <= 0:
            return jsonify({"error": "Price quote must be a positive number"}), 400

        if not isinstance(data['estimated_days'], int) or data['estimated_days'] <= 0:
            return jsonify({"error": "Estimated days must be a positive integer"}), 400

        # Check if tradesman exists
        tradesman = User.query.get(data['tradesman_id'])
        if not tradesman or tradesman.user_type != USER_TYPE_TRADESMAN:
            return jsonify({"error": "Invalid tradesman"}), 400

        # Check if tradesman has already applied for this job
        existing_application = Application.query.filter_by(
            job_id=job_id,
            tradesman_id=data['tradesman_id']
        ).first()

        if existing_application:
            return jsonify({"error": "You have already applied for this job"}), 400

        # Create application object with additional fields
        new_application = Application(
            job_id=job_id,
            tradesman_id=data['tradesman_id'],
            price_quote=data['price_quote'],
            estimated_days=data['estimated_days'],
            status="applied"
        )

        # Add optional fields if provided
        if 'cover_letter' in data:
            new_application.cover_letter = data['cover_letter']

        if 'availability_date' in data:
            new_application.availability_date = data['availability_date']

        # Save application to database
        db.session.add(new_application)
        db.session.commit()

        return jsonify({
            "message": "Application submitted successfully",
            "application_id": new_application.id,
            "application": {
                "id": new_application.id,
                "job_id": new_application.job_id,
                "tradesman_id": new_application.tradesman_id,
                "price_quote": new_application.price_quote,
                "estimated_days": new_application.estimated_days,
                "created_at": new_application.created_at.isoformat(),
                "status": new_application.status
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint: Update the status of a job application


@app.route('/api/applications/<application_id>', methods=['PUT'])
def update_application_status(application_id):

    try:
        application = Application.query.get(application_id)

        if not application:
            return jsonify({"error": "Application not found"}), 404
        data = request.json

        if 'status' not in data or data['status'] not in ['approved', 'rejected', 'closed', 'dispute']:
            return jsonify({"error": "Invalid status. Must be 'accepted' or 'rejected'"}), 400
        # Update application status
        application.status = data['status']
        logging.info(f"application.status ===>>: {application.status}")

        # If accepting application, update job status and handle other applications
        # if data['status'] == 'accepted':
        #     job = Job.query.get(application.job_id)
        #     if job:
        #         job.status = 'assigned'
        #         # Reject all other pending applications for this job
        #         pending_apps = Application.query.filter_by(
        #             job_id=job.id, status='applied').all()
        #         for app in pending_apps:
        #             app.status = 'rejected'

        # if data['status'] == 'accepted':
        #     pending_apps = Application.query.filter_by(id=)

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
        applications_list = Application.query.filter_by(
            tradesman_id=tradesman_id).order_by(Application.created_at.desc()).all()
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
