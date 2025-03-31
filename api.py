import os
from flask import Flask, request, jsonify
from supabase import create_client
from PriceAnalyzer import PriceAnalyzer  # Import the PriceAnalyzer class

app = Flask(__name__)

# Supabase configuration
SUPABASE_URL = "https://tqjfhsjfcmdphvemqrnr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxamZoc2pmY21kcGh2ZW1xcm5yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM0MjQ3NTUsImV4cCI6MjA1OTAwMDc1NX0.HgRS4IuJBgp303DoHzH7L4zjCoHXa7E6_yLUfLYVcG4"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize PriceAnalyzer
analyzer = PriceAnalyzer()


@app.route('/api/predict-fair-price', methods=['POST'])
def predict_fair_price():
    data = request.json
    try:
        result = analyzer.predict_fair_price(
            data['category'],
            data['location'],
            data['area_sqm'],
            data['complexity_score'],
            data['material_quality_score']
        )
        return jsonify({"predicted_price": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/get-market-rates', methods=['POST'])
def get_market_rates():
    data = request.json
    try:
        result = analyzer.get_market_rates(data['category'], data['location'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/evaluate-dispute', methods=['POST'])
def evaluate_dispute():
    data = request.json
    try:
        result = analyzer.evaluate_dispute(
            data['category'],
            data['location'],
            data['area_sqm'],
            data['complexity_score'],
            data['material_quality_score'],
            data['contractor_price'],
            data.get('client_expectation')
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/analyze-regional-pricing', methods=['POST'])
def analyze_regional_pricing():
    data = request.json
    try:
        result = analyzer.analyze_regional_pricing(
            data['category'],
            data['area_sqm'],
            data['complexity_score'],
            data['material_quality_score']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/save-training-data', methods=['POST'])
def save_training_data():
    try:
        # Generate synthetic training data
        df = analyzer.generate_training_data(size=1000)

        # Save to Supabase
        data = df.to_dict(orient='records')
        response = supabase.table('training_data').insert(data).execute()

        if response:
            return jsonify({"message": "Training data saved successfully"}), 200
        else:
            return jsonify({"error": "Failed to save training data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/load-training-data', methods=['GET'])
def load_training_data():
    try:
        # Fetch training data from Supabase
        response = supabase.table('training_data').select('*').execute()
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"error": "No training data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
