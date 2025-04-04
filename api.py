import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime

# Assuming PriceAnalyzer is a custom class you have defined elsewhere
# Import the PriceAnalyzer class from its module
from PriceAnalyzer import PriceAnalyzer

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()

# In-memory storage for jobs and applications (replace with database in production)
jobs = {}
applications = {}

# User types
USER_TYPE_CONTRACTOR = "contractor"
USER_TYPE_TRADESMAN = "tradesman"

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
        
        return jsonify({
            "message": "Job created successfully",
            "job_id": job_id,
            "job": job
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
                job_list = [job for job in job_list if job['contractor_id'] == user_id]
            elif user_type == USER_TYPE_TRADESMAN:
                # For tradesmen, they can see all open jobs
                pass
        
        # Sort by creation date (newest first)
        job_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            "jobs": job_list,
            "count": len(job_list)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        protected_fields = ['id', 'contractor_id', 'created_at', 'applications']
        
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

@app.route('/api/jobs/<job_id>/applications', methods=['POST'])
def apply_for_job(job_id):
    """
    Submit an application for a job.
    Expects JSON input with 'tradesman_id', 'price_quote', and 'message'.
    """
    try:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        
        if jobs[job_id]['status'] != 'open':
            return jsonify({"error": "This job is not open for applications"}), 400
        
        data = request.json
        
        # Validate required fields
        required_fields = ['tradesman_id', 'price_quote', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate application ID
        application_id = str(uuid.uuid4())
        
        # Create application object
        application = {
            'id': application_id,
            'job_id': job_id,
            'tradesman_id': data['tradesman_id'],
            'price_quote': data['price_quote'],
            'message': data['message'],
            'created_at': datetime.now().isoformat(),
            'status': 'pending'  # pending, accepted, rejected
        }
        
        # Store application
        applications[application_id] = application
        
        # Add application ID to job's applications list
        jobs[job_id]['applications'].append(application_id)
        
        # Compare with fair price
        fair_price = jobs[job_id]['fair_price_estimate']
        price_difference = ((data['price_quote'] - fair_price) / fair_price) * 100
        price_assessment = ""
        if price_difference <= -15:
            price_assessment = "significantly below market rate"
        elif -15 < price_difference <= -5:
            price_assessment = "below market rate"
        elif -5 < price_difference <= 5:
            price_assessment = "at market rate"
        elif 5 < price_difference <= 15:
            price_assessment = "above market rate"
        else:
            price_assessment = "significantly above market rate"
        
        return jsonify({
            "message": "Application submitted successfully",
            "application_id": application_id,
            "application": application,
            "price_assessment": price_assessment,
            "price_difference_percentage": round(price_difference, 2)
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        job_applications = [applications[app_id] for app_id in application_ids if app_id in applications]
        
        # Sort by creation date (newest first)
        job_applications.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            "applications": job_applications,
            "count": len(job_applications)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        tradesman_applications.sort(key=lambda x: x['created_at'], reverse=True)
        
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

if __name__ == "__main__":
    app.run(debug=True)