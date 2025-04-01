import pandas as pd
from flask import Flask, request, jsonify
from PriceAnalyzer import PriceAnalyzer  # Import the PriceAnalyzer class
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()


@app.route('/api/predict-fair-price', methods=['POST'])
def predict_fair_price():
    """
    Predict the fair price for a construction service.
    Expects JSON input with 'category', 'location', 'area_sqm', 'complexity_score', 
    'material_quality_score', and optionally 'user_type'.
    """
    try:
        data = request.json
        print(f"The data is {data}")
        category = data.get("category")
        location = data.get("location")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")
        # user_type = data.get("user_type", "contractor")  # Default to contractor

        # Validate required fields
        if not all([category, location, area_sqm, complexity_score, material_quality_score]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the predict_fair_price method from PriceAnalyzer
        fair_price = analyzer.predict_fair_price(
            category=category,
            location=location,
            area_sqm=area_sqm,
            complexity_score=complexity_score,
            material_quality_score=material_quality_score,
            # user_type=user_type
        )
        return jsonify({"predicted_fair_price": round(fair_price, 2)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-market-rates', methods=['POST'])
def get_market_rates():
    """
    Get market rate information for a specific category and location.
    Expects JSON input with 'category', 'location', and optionally 'user_type'.
    """
    try:
        data = request.json
        category = data.get("category")
        location = data.get("location")
        # user_type = data.get("user_type", "contractor")  # Default to contractor

        # Validate required fields
        if not all([category, location]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the get_market_rates method from PriceAnalyzer
        market_info = analyzer.get_market_rates(category, location)
        return jsonify(market_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/evaluate-dispute', methods=['POST'])
def evaluate_dispute():
    """
    Evaluate a pricing dispute between contractor and client.
    Expects JSON input with 'category', 'location', 'area_sqm', 'complexity_score',
    'material_quality_score', 'contractor_price', and optionally 'client_expectation' and 'user_type'.
    """
    try:
        print("hello 1")
        data = request.json
        category = data.get("category")
        location = data.get("location")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")
        contractor_price = data.get("contractor_price")
        client_expectation = data.get("client_expectation")
        # user_type = data.get("user_type", "contractor")  # Default to contractor
        print("hello 2")
        # Validate required fields
        if not all([category, location, area_sqm, complexity_score, material_quality_score, contractor_price]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the evaluate_dispute method from PriceAnalyzer
        dispute_result = analyzer.evaluate_dispute(
            category=category,
            location=location,
            area_sqm=area_sqm,
            complexity_score=complexity_score,
            material_quality_score=material_quality_score,
            contractor_price=contractor_price,
            client_expectation=client_expectation,
            # user_type=user_type
        )
        return jsonify(dispute_result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyze-regional-pricing', methods=['POST'])
def analyze_regional_pricing():
    """
    Analyze pricing variations across different regions for the same service.
    Expects JSON input with 'category', 'area_sqm', 'complexity_score', 'material_quality_score', 
    and optionally 'user_type'.
    """
    try:
        data = request.json
        category = data.get("category")
        area_sqm = data.get("area_sqm")
        complexity_score = data.get("complexity_score")
        material_quality_score = data.get("material_quality_score")
        # user_type = data.get("user_type", "contractor")  # Default to contractor

        # Validate required fields
        if not all([category, area_sqm, complexity_score, material_quality_score]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call the analyze_regional_pricing method from PriceAnalyzer
        regional_analysis = analyzer.analyze_regional_pricing(
            category=category,
            area_sqm=area_sqm,
            complexity_score=complexity_score,
            material_quality_score=material_quality_score,
            # user_type=user_type
        )
        return jsonify(regional_analysis), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/fine-tune', methods=['POST'])
def fine_tune():
    """
    Fine-tune the model with new training data.
    Expects JSON input with 'data' containing a list of new training samples.
    """
    try:
        data = request.json.get("data")
        if not data:
            return jsonify({"error": "No fine-tuning data provided"}), 400

        # Convert data to DataFrame
        df = pd.DataFrame(data)

        # Fine-tune the model
        history = analyzer.fine_tune(df)
        return jsonify({"message": "Model fine-tuned successfully", "history": history.history}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/generate-benchmark-report', methods=['POST'])
def generate_benchmark_report():
    """
    Generate a benchmark pricing report for multiple categories and locations.
    Expects JSON input with optional 'categories', 'area_sqm', 'complexity_score', 
    and 'material_quality_score'.
    """
    try:
        data = request.json
        categories = data.get("categories")
        area_sqm = data.get("area_sqm", 100)
        complexity_score = data.get("complexity_score", 5)
        material_quality_score = data.get("material_quality_score", 5)

        # Generate benchmark report
        report = analyzer.generate_benchmark_report(
            categories=categories,
            area_sqm=area_sqm,
            complexity_score=complexity_score,
            material_quality_score=material_quality_score
        )
        return jsonify(report.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
