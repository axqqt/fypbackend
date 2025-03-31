import os
from flask import Flask, request, jsonify
from supabase import create_client
from PriceAnalyzer import PriceAnalyzer  # Import the PriceAnalyzer class
from flask_cors import CORS


app = Flask(__name__)
CORS(app) 

# Supabase configuration
SUPABASE_URL = "https://tqjfhsjfcmdphvemqrnr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxamZoc2pmY21kcGh2ZW1xcm5yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM0MjQ3NTUsImV4cCI6MjA1OTAwMDc1NX0.HgRS4IuJBgp303DoHzH7L4zjCoHXa7E6_yLUfLYVcG4"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()


# Endpoint to predict fair price
@app.route('/api/predict-fair-price', methods=['POST'])
def predict_fair_price():
    try:
        # Parse request body
        data = request.json
        category = data.get("category")
        location = data.get("location")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")

        # Validate required fields
        if not all([category, location, area_sqm, complexity_score, material_quality_score]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the predict_fair_price method from PriceAnalyzer
        fair_price = analyzer.predict_fair_price(category, location, area_sqm, complexity_score, material_quality_score)
        return jsonify({"predicted_fair_price": fair_price}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint to get market rates
@app.route('/api/get-market-rates', methods=['POST'])
def get_market_rates():
    try:
        # Parse request body
        data = request.json
        category = data.get("category")
        location = data.get("location")

        # Validate required fields
        if not all([category, location]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the get_market_rates method from PriceAnalyzer
        market_rates = analyzer.get_market_rates(category, location)
        return jsonify(market_rates), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint to evaluate disputes
@app.route('/api/evaluate-dispute', methods=['POST'])
def evaluate_dispute():
    try:
        # Parse request body
        data = request.json
        category = data.get("category")
        location = data.get("location")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")
        contractor_price = data.get("contractor_price")
        client_expectation = data.get("client_expectation")

        # Validate required fields
        if not all([category, location, area_sqm, complexity_score, material_quality_score, contractor_price]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the evaluate_dispute method from PriceAnalyzer
        dispute_result = analyzer.evaluate_dispute(
            category, location, area_sqm, complexity_score, material_quality_score, contractor_price, client_expectation
        )
        return jsonify(dispute_result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint to analyze regional pricing
@app.route('/api/analyze-regional-pricing', methods=['POST'])
def analyze_regional_pricing():
    try:
        # Parse request body
        data = request.json
        category = data.get("category")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")

        # Validate required fields
        if not all([category, area_sqm, complexity_score, material_quality_score]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the analyze_regional_pricing method from PriceAnalyzer
        regional_analysis = analyzer.analyze_regional_pricing(category, area_sqm, complexity_score, material_quality_score)
        return jsonify(regional_analysis), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)