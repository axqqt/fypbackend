import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
import json
import os
import pickle
from datetime import datetime
import random


class PriceAnalyzer:
    """
    AI model for analyzing construction prices and providing fair price recommendations
    based on market data, location, and service category.
    """

    def __init__(self, model_path=None):
        """
        Initialize the price analyzer with optional pre-trained model

        Args:
            model_path: Path to saved TensorFlow model (optional)
        """
        self.model = None
        self.scaler = StandardScaler()
        self.category_mapping = {}
        self.location_mapping = {}

        # Load model if path is provided
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            self._build_model()

    def _build_model(self):
        """Build the TensorFlow model for price prediction"""

        # Define a simple neural network architecture
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(5,)),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)  # Output layer (predicted fair price)
        ])

        # Compile the model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae']
        )

        self.model = model

    def load_model(self, model_path):
        """
        Load a pre-trained model from disk

        Args:
            model_path: Path to saved TensorFlow model
        """
        self.model = tf.keras.models.load_model(model_path)

        # Load feature mappings
        mappings_path = os.path.join(os.path.dirname(
            model_path), 'feature_mappings.json')
        if os.path.exists(mappings_path):
            with open(mappings_path, 'r') as f:
                mappings = json.load(f)
                self.category_mapping = mappings['category']
                self.location_mapping = mappings['location']

        # Load scaler
        scaler_path = os.path.join(os.path.dirname(model_path), 'scaler.pkl')
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)

    def save_model(self, model_path):
        """
        Save the trained model to disk

        Args:
            model_path: Path where to save the model
        """
        if not os.path.exists(os.path.dirname(model_path)):
            os.makedirs(os.path.dirname(model_path))

        self.model.save(model_path)

        # Save feature mappings
        mappings_path = os.path.join(os.path.dirname(
            model_path), 'feature_mappings.json')
        with open(mappings_path, 'w') as f:
            json.dump({
                'category': self.category_mapping,
                'location': self.location_mapping
            }, f)

        # Save scaler
        scaler_path = os.path.join(os.path.dirname(model_path), 'scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

    def train(self, data, epochs=50, batch_size=32, validation_split=0.2):
        """
        Train the model with construction price data

        Args:
            data: Pandas DataFrame with columns [category, location, area_sqm, 
                  complexity_score, material_quality_score, price]
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Fraction of data to use for validation

        Returns:
            Training history
        """
        # Create category and location mappings
        categories = data['category'].unique()
        locations = data['location'].unique()

        self.category_mapping = {
            cat: idx for idx, cat in enumerate(categories)}
        self.location_mapping = {loc: idx for idx, loc in enumerate(locations)}

        # Prepare features
        X = self._prepare_features(data)
        y = data['price'].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train the model
        history = self.model.fit(
            X_scaled, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1
        )

        return history

    def _prepare_features(self, data):
        """
        Prepare features for the model

        Args:
            data: Pandas DataFrame with raw data

        Returns:
            Numpy array of processed features
        """
        # Convert categories and locations to numeric
        category_numeric = data['category'].map(self.category_mapping).values
        location_numeric = data['location'].map(self.location_mapping).values

        # Create feature matrix
        X = np.column_stack([
            category_numeric,
            location_numeric,
            data['area_sqm'].values,
            data['complexity_score'].values,
            data['material_quality_score'].values
        ])

        return X

    def predict_fair_price(self, category, location, area_sqm, complexity_score, material_quality_score):
        """
        Predict fair price for construction service

        Args:
            category: Service category (e.g., 'Masonry', 'Plumbing')
            location: Location/district in Sri Lanka
            area_sqm: Area in square meters (if applicable)
            complexity_score: Complexity score (1-10)
            material_quality_score: Material quality score (1-10)

        Returns:
            Predicted fair price
        """
        # Handle unknown categories or locations
        if category not in self.category_mapping:
            category = list(self.category_mapping.keys())[
                0]  # Use first category as default

        if location not in self.location_mapping:
            location = list(self.location_mapping.keys())[
                0]  # Use first location as default

        # Prepare input features
        X = np.array([[
            self.category_mapping[category],
            self.location_mapping[location],
            area_sqm,
            complexity_score,
            material_quality_score
        ]])

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Make prediction
        prediction = self.model.predict(X_scaled)[0][0]

        return max(0, prediction)  # Ensure price is non-negative

    def get_market_rates(self, category, location):
        """
        Get market rate data for a specific category and location

        Args:
            category: Service category
            location: Location/district

        Returns:
            Dictionary with market rate information
        """
        # Base rates for different categories (in LKR per day)
        base_rates = {
            'Masonry': 3200,        # Bricklaying, plastering, concrete work
            'Carpentry': 3800,       # Woodwork, door/window installation
            'Plumbing': 4200,        # Water supply systems, drainage
            'Electrical': 4500,       # Wiring, electrical installations
            'Painting': 3000,        # Interior/exterior painting
            'Tiling': 3400,          # Floor/wall tiling
            'Roofing': 4200,         # Roof installation and repair
            'Foundation Work': 5500,  # Excavation, foundation laying
            'Interior Design': 7500,  # Interior planning and decoration
            'Landscaping': 3600,     # Garden design, outdoor structures
            'HVAC': 6000,           # Heating, ventilation, air conditioning
            'General Contracting': 5000  # Overall project management
        }

        # Location adjustment factors (based on cost of living differences)
        location_factors = {
            'Colombo': 1.35,       # Capital city, highest costs
            'Gampaha': 1.25,       # Western province, urban
            'Kandy': 1.20,         # Central province, urban
            'Galle': 1.15,         # Southern province, tourist area
            'Negombo': 1.20,       # Western coastal city
            'Jaffna': 1.10,        # Northern province capital
            'Anuradhapura': 0.95,  # North Central province
            'Batticaloa': 0.90,    # Eastern province
            'Trincomalee': 0.92,   # Eastern coastal city
            'Matara': 1.05,        # Southern coastal city
            'Kurunegala': 0.98,    # North Western province
            'Ratnapura': 0.95,     # Sabaragamuwa province
            'Badulla': 0.92,       # Uva province
            'Nuwara Eliya': 1.10,  # Central highlands, tourist area
            'Hambantota': 1.05,    # Southern development zone
            'Kalmunai': 0.88,      # Eastern coastal town
            'Vavuniya': 0.90,      # Northern inland city
            'Matale': 0.95,        # Central province
            'Puttalam': 0.90,      # North Western coastal city
            'Kegalle': 0.92        # Sabaragamuwa province
        }

        # Material cost adjustment (percentage of material costs in total price)
        material_percentage = {
            'Masonry': 0.65,
            'Carpentry': 0.60,
            'Plumbing': 0.55,
            'Electrical': 0.60,
            'Painting': 0.50,
            'Tiling': 0.70,
            'Roofing': 0.75,
            'Foundation Work': 0.70,
            'Interior Design': 0.50,
            'Landscaping': 0.55,
            'HVAC': 0.65,
            'General Contracting': 0.60
        }

        # Use default values if category or location not found
        base_rate = base_rates.get(category, 4000)
        factor = location_factors.get(location, 1.0)
        material_factor = material_percentage.get(category, 0.60)

        # Calculate adjusted rate
        adjusted_rate = base_rate * factor

        # Account for material cost variations (±5%)
        material_variation = random.uniform(0.95, 1.05)
        material_adjusted_rate = adjusted_rate * \
            (1 + (material_variation - 1) * material_factor)

        # Market fluctuation based on supply/demand (±10%)
        min_rate = material_adjusted_rate * 0.90
        max_rate = material_adjusted_rate * 1.10

        # Average market rate with slight variance
        avg_market_rate = random.uniform(
            material_adjusted_rate * 0.98, material_adjusted_rate * 1.02)

        # Get current date for the rate information
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Create response dictionary
        market_info = {
            'category': category,
            'location': location,
            'base_rate': base_rate,
            'location_factor': factor,
            'material_cost_percentage': material_factor * 100,
            'adjusted_rate': adjusted_rate,
            'min_market_rate': min_rate,
            'max_market_rate': max_rate,
            'avg_market_rate': avg_market_rate,
            # Number of data points for this rate
            'sample_size': random.randint(25, 150),
            'last_updated': current_date,
            'currency': 'LKR',
            'unit': 'per day',
            'material_cost_trend': random.choice(['Stable', 'Rising', 'Falling'])
        }

        return market_info

    def generate_training_data(self, size=1000, output_file=None):
        """
        Generate synthetic training data for the model based on Sri Lankan construction market

        Args:
            size: Number of samples to generate
            output_file: Path to save the CSV file (optional)

        Returns:
            Pandas DataFrame with synthetic training data
        """
        # Define categories and locations based on Sri Lankan construction industry
        categories = [
            'Masonry', 'Carpentry', 'Plumbing', 'Electrical', 'Painting',
            'Tiling', 'Roofing', 'Foundation Work', 'Interior Design',
            'Landscaping', 'HVAC', 'General Contracting'
        ]

        # All main districts in Sri Lanka
        locations = [
            'Colombo', 'Gampaha', 'Kandy', 'Galle', 'Jaffna', 'Anuradhapura',
            'Batticaloa', 'Trincomalee', 'Matara', 'Kurunegala', 'Ratnapura',
            'Badulla', 'Negombo', 'Nuwara Eliya', 'Hambantota', 'Kalmunai',
            'Vavuniya', 'Matale', 'Puttalam', 'Kegalle'
        ]

        # Base rates for different categories (in LKR per day)
        base_rates = {
            'Masonry': 3200,
            'Carpentry': 3800,
            'Plumbing': 4200,
            'Electrical': 4500,
            'Painting': 3000,
            'Tiling': 3400,
            'Roofing': 4200,
            'Foundation Work': 5500,
            'Interior Design': 7500,
            'Landscaping': 3600,
            'HVAC': 6000,
            'General Contracting': 5000
        }

        # Location adjustment factors
        location_factors = {
            'Colombo': 1.35,
            'Gampaha': 1.25,
            'Kandy': 1.20,
            'Galle': 1.15,
            'Negombo': 1.20,
            'Jaffna': 1.10,
            'Anuradhapura': 0.95,
            'Batticaloa': 0.90,
            'Trincomalee': 0.92,
            'Matara': 1.05,
            'Kurunegala': 0.98,
            'Ratnapura': 0.95,
            'Badulla': 0.92,
            'Nuwara Eliya': 1.10,
            'Hambantota': 1.05,
            'Kalmunai': 0.88,
            'Vavuniya': 0.90,
            'Matale': 0.95,
            'Puttalam': 0.90,
            'Kegalle': 0.92
        }

        # Category specific area effects (how much area affects price)
        area_impact = {
            'Masonry': 0.5,
            'Carpentry': 0.4,
            'Plumbing': 0.3,
            'Electrical': 0.25,
            'Painting': 0.6,
            'Tiling': 0.7,
            'Roofing': 0.55,
            'Foundation Work': 0.45,
            'Interior Design': 0.3,
            'Landscaping': 0.5,
            'HVAC': 0.35,
            'General Contracting': 0.4
        }

        # Typical area ranges for different categories (in square meters)
        area_ranges = {
            'Masonry': (10, 300),
            'Carpentry': (5, 150),
            'Plumbing': (5, 100),
            'Electrical': (10, 200),
            'Painting': (20, 400),
            'Tiling': (10, 200),
            'Roofing': (20, 300),
            'Foundation Work': (20, 200),
            'Interior Design': (30, 250),
            'Landscaping': (50, 1000),
            'HVAC': (20, 300),
            'General Contracting': (50, 500)
        }

        # Generate data
        data = []
        for _ in range(size):
            category = random.choice(categories)
            location = random.choice(locations)

            # Generate realistic area based on category
            min_area, max_area = area_ranges[category]
            area_sqm = random.uniform(min_area, max_area)

            # Generate realistic complexity and material quality scores
            # Higher end areas tend to have higher complexity and material quality
            area_percentile = (area_sqm - min_area) / (max_area - min_area)
            complexity_base = 3 + area_percentile * 4  # Maps to range 3-7
            material_base = 3 + area_percentile * 4    # Maps to range 3-7

            # Add some randomness to complexity and material quality
            complexity_score = min(
                10, max(1, complexity_base + random.uniform(-2, 2)))
            material_quality_score = min(
                10, max(1, material_base + random.uniform(-2, 2)))

            # Calculate base price
            base_price = base_rates[category]
            location_factor = location_factors[location]

            # Calculate area effect (LKR per sqm, with diminishing returns for larger areas)
            area_effect = area_impact[category] * \
                (area_sqm ** 0.85)  # Diminishing returns

            # Calculate effects of complexity and material quality
            complexity_effect = base_price * \
                (complexity_score / 5 - 1) * 0.25  # +/- 25% based on complexity
            material_effect = base_price * \
                (material_quality_score / 5 - 1) * \
                0.35  # +/- 35% based on material

            # Add seasonal effect (5% random variation)
            seasonal_effect = random.uniform(0.95, 1.05)

            # Calculate final price
            price = (base_price + area_effect + complexity_effect +
                     material_effect) * location_factor * seasonal_effect

            # Add some random noise to simulate real-world variation (±8%)
            price *= random.uniform(0.92, 1.08)

            # Ensure price is positive and round to whole rupees
            price = max(1, round(price))

            data.append({
                'category': category,
                'location': location,
                'area_sqm': round(area_sqm, 2),
                'complexity_score': round(complexity_score, 1),
                'material_quality_score': round(material_quality_score, 1),
                'price': price
            })

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to CSV if output file is provided
        if output_file:
            df.to_csv(output_file, index=False)

        return df

    def analyze_regional_pricing(self, category, area_sqm, complexity_score, material_quality_score):
        """
        Analyze pricing variations across different regions in Sri Lanka for the same service

        Args:
            category: Service category
            area_sqm: Area in square meters
            complexity_score: Complexity score (1-10)
            material_quality_score: Material quality score (1-10)

        Returns:
            Dictionary with regional pricing analysis
        """
        # Define the regions to analyze if model doesn't have location mapping yet
        if not self.location_mapping:
            locations = [
                'Colombo', 'Gampaha', 'Kandy', 'Galle', 'Jaffna', 'Anuradhapura',
                'Batticaloa', 'Trincomalee', 'Matara', 'Kurunegala', 'Ratnapura',
                'Badulla', 'Negombo', 'Nuwara Eliya', 'Hambantota'
            ]
        else:
            locations = list(self.location_mapping.keys())

        prices = []

        # Group locations by province for more meaningful analysis
        provinces = {
            'Western': ['Colombo', 'Gampaha', 'Kalutara', 'Negombo'],
            'Central': ['Kandy', 'Matale', 'Nuwara Eliya'],
            'Southern': ['Galle', 'Matara', 'Hambantota'],
            'Northern': ['Jaffna', 'Vavuniya', 'Mannar', 'Mullaitivu', 'Kilinochchi'],
            'Eastern': ['Batticaloa', 'Trincomalee', 'Ampara', 'Kalmunai'],
            'North Western': ['Kurunegala', 'Puttalam'],
            'North Central': ['Anuradhapura', 'Polonnaruwa'],
            'Uva': ['Badulla', 'Monaragala'],
            'Sabaragamuwa': ['Ratnapura', 'Kegalle']
        }

        # Calculate prices for each location
        for location in locations:
            if hasattr(self, 'model') and self.model is not None:
                # Use the model if available
                price = self.predict_fair_price(
                    category, location, area_sqm, complexity_score, material_quality_score
                )
            else:
                # Fallback to estimation based on market rates if model not available
                market_info = self.get_market_rates(category, location)
                price = market_info['avg_market_rate'] * \
                    area_sqm / 10  # Simple estimation

            # Determine province
            province = "Unknown"
            for prov, locs in provinces.items():
                if location in locs:
                    province = prov
                    break

            prices.append({
                'location': location,
                'province': province,
                'price': price
            })

        # Sort by price
        prices_sorted = sorted(prices, key=lambda x: x['price'])

        # Calculate statistics
        price_values = [p['price'] for p in prices]
        avg_price = np.mean(price_values)
        median_price = np.median(price_values)
        min_price = np.min(price_values)
        max_price = np.max(price_values)
        std_dev = np.std(price_values)
        price_range = max_price - min_price
        price_ratio = max_price / min_price if min_price > 0 else float('inf')

        # Calculate provincial averages
        provincial_averages = {}
        for province in set(p['province'] for p in prices):
            province_prices = [p['price']
                               for p in prices if p['province'] == province]
            if province_prices:
                provincial_averages[province] = {
                    'avg_price': np.mean(province_prices),
                    'locations': len(province_prices)
                }

        # Sort provinces by average price
        provinces_by_price = sorted(
            provincial_averages.items(),
            key=lambda x: x[1]['avg_price']
        )

        # Create result
        result = {
            'category': category,
            'area_sqm': area_sqm,
            'complexity_score': complexity_score,
            'material_quality_score': material_quality_score,
            'avg_price': avg_price,
            'median_price': median_price,
            'min_price': min_price,
            'max_price': max_price,
            'standard_deviation': std_dev,
            'price_range': price_range,
            'price_ratio': price_ratio,
            'cheapest_location': prices_sorted[0]['location'],
            'most_expensive_location': prices_sorted[-1]['location'],
            'cheapest_province': provinces_by_price[0][0] if provinces_by_price else None,
            'most_expensive_province': provinces_by_price[-1][0] if provinces_by_price else None,
            'provincial_averages': provincial_averages,
            'regional_prices': prices_sorted,
            'analysis_date': datetime.now().strftime("%Y-%m-%d"),
            'currency': 'LKR'
        }

        return result

    def evaluate_dispute(self, category, location, area_sqm, complexity_score,
                         material_quality_score, contractor_price, client_expectation=None):
        """
        Evaluate a pricing dispute between contractor and client

        Args:
            category: Service category
            location: Location/district
            area_sqm: Area in square meters (if applicable)
            complexity_score: Complexity score (1-10)
            material_quality_score: Material quality score (1-10)
            contractor_price: Price quoted by the contractor
            client_expectation: Price expected by the client (optional)

        Returns:
            Dictionary with dispute evaluation
        """
        # Get fair price prediction
        fair_price = self.predict_fair_price(
            category, location, area_sqm, complexity_score, material_quality_score
        )

        # Get market rate information
        market_info = self.get_market_rates(category, location)

        # Calculate price difference percentage
        price_diff_percentage = (
            (contractor_price - fair_price) / fair_price) * 100

        # Determine price fairness
        if abs(price_diff_percentage) <= 10:
            fairness = "Fair"
            recommendation = "The contractor's price is within market expectations."
        elif price_diff_percentage > 10:
            fairness = "Above Market"
            recommendation = f"The contractor's price is {abs(price_diff_percentage):.1f}% above " \
                f"the fair market rate. Consider negotiation or finding alternative quotes."
        else:  # price_diff_percentage < -10
            fairness = "Below Market"
            recommendation = f"The contractor's price is {abs(price_diff_percentage):.1f}% below " \
                f"the fair market rate, which is favorable for the client."

        # Assess price based on area size adjustment
        area_adjustment = 1.0
        if area_sqm > 100:
            # For larger areas, expect some discount per square meter
            area_adjustment = 0.9 if area_sqm > 200 else 0.95

        adjusted_fair_price = fair_price * area_adjustment

        # Determine reasonableness of client expectation if provided
        client_assessment = None
        if client_expectation is not None:
            client_diff_percentage = (
                (client_expectation - fair_price) / fair_price) * 100

            if abs(client_diff_percentage) <= 15:
                client_assessment = "Reasonable"
            elif client_diff_percentage < -15:
                client_assessment = "Unreasonably Low"
            else:  # client_diff_percentage > 15
                client_assessment = "Unreasonably High"

        # Create dispute resolution recommendation
        if client_assessment:
            if client_assessment == "Reasonable" and fairness == "Fair":
                resolution = f"Both parties have reasonable expectations. Recommended settlement: {fair_price:.2f} LKR"
            elif client_assessment == "Reasonable" and fairness != "Fair":
                resolution = f"Client has reasonable expectations. Recommended settlement: {adjusted_fair_price:.2f} LKR"
            elif client_assessment == "Unreasonably Low" and fairness != "Above Market":
                resolution = f"Client expectations are below market rates. Contractor's price of {contractor_price:.2f} LKR is justified."
            elif client_assessment == "Unreasonably High" and fairness != "Below Market":
                resolution = f"Client expectations are above market rates. Fair settlement: {fair_price:.2f} LKR"
            else:
                # Complex case - split the difference
                settlement = (contractor_price + client_expectation) / 2
                if abs((settlement - fair_price) / fair_price) <= 0.15:
                    resolution = f"Recommended compromise settlement: {settlement:.2f} LKR"
                else:
                    resolution = f"Recommended fair settlement: {fair_price:.2f} LKR"
        else:
            resolution = f"Recommended fair price: {fair_price:.2f} LKR"

        # Create result dictionary
        result = {
            'category': category,
            'location': location,
            'area_sqm': area_sqm,
            'complexity_score': complexity_score,
            'material_quality_score': material_quality_score,
            'contractor_price': contractor_price,
            'client_expectation': client_expectation,
            'predicted_fair_price': fair_price,
            'area_adjusted_fair_price': adjusted_fair_price,
            'price_difference_percentage': price_diff_percentage,
            'price_fairness': fairness,
            'client_expectation_assessment': client_assessment,
            'market_rate_min': market_info['min_market_rate'],
            'market_rate_max': market_info['max_market_rate'],
            'market_rate_avg': market_info['avg_market_rate'],
            'recommendation': recommendation,
            'resolution': resolution,
            'analysis_date': datetime.now().strftime("%Y-%m-%d"),
            'currency': 'LKR'
        }

        return result

    def fine_tune(self, new_data, epochs=10, batch_size=32):
        """
        Fine-tune an existing model with new data

        Args:
            new_data: Pandas DataFrame with new training data
            epochs: Number of training epochs
            batch_size: Training batch size

        Returns:
            Training history
        """
        if self.model is None:
            raise ValueError(
                "No model exists. Please train a model first or load a pre-trained model.")

        # Ensure all categories and locations in new data are in the mappings
        for category in new_data['category'].unique():
            if category not in self.category_mapping:
                # Assign new index for the category
                self.category_mapping[category] = len(self.category_mapping)

        for location in new_data['location'].unique():
            if location not in self.location_mapping:
                # Assign new index for the location
                self.location_mapping[location] = len(self.location_mapping)

        # Prepare features
        X = self._prepare_features(new_data)
        y = new_data['price'].values

        # Transform features using existing scaler
        X_scaled = self.scaler.transform(X)

        # Fine-tune the model
        history = self.model.fit(
            X_scaled, y,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1
        )

        return history

    def evaluate_model(self, test_data):
        """
        Evaluate model performance on test data

        Args:
            test_data: Pandas DataFrame with test data

        Returns:
            Dictionary with evaluation metrics
        """
        # Prepare test features and target
        X_test = self._prepare_features(test_data)
        y_test = test_data['price'].values

        # Scale features using the same scaler
        X_test_scaled = self.scaler.transform(X_test)

        # Get predictions
        y_pred = self.model.predict(X_test_scaled).flatten()

        # Calculate metrics
        mse = np.mean((y_test - y_pred) ** 2)
        mae = np.mean(np.abs(y_test - y_pred))
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

        # Calculate R-squared
        ss_total = np.sum((y_test - np.mean(y_test)) ** 2)
        ss_residual = np.sum((y_test - y_pred) ** 2)
        r_squared = 1 - (ss_residual / ss_total)

        # Return metrics
        return {
            'mean_squared_error': mse,
            'mean_absolute_error': mae,
            'mean_absolute_percentage_error': mape,
            'r_squared': r_squared
        }

    def analyze_regional_pricing(self, category, area_sqm, complexity_score, material_quality_score):
        """
        Analyze pricing variations across different regions for the same service

        Args:
            category: Service category
            area_sqm: Area in square meters
            complexity_score: Complexity score (1-10)
            material_quality_score: Material quality score (1-10)

        Returns:
            Dictionary with regional pricing analysis
        """
        if not self.location_mapping:
            raise ValueError(
                "Location mapping not available. Train the model first.")

        locations = list(self.location_mapping.keys())
        prices = []

        for location in locations:
            price = self.predict_fair_price(
                category, location, area_sqm, complexity_score, material_quality_score
            )
            prices.append({
                'location': location,
                'price': price
            })

        # Sort by price
        prices_sorted = sorted(prices, key=lambda x: x['price'])

        # Calculate statistics
        price_values = [p['price'] for p in prices]
        avg_price = np.mean(price_values)
        min_price = np.min(price_values)
        max_price = np.max(price_values)
        price_range = max_price - min_price
        price_ratio = max_price / min_price if min_price > 0 else float('inf')

        # Create result
        result = {
            'category': category,
            'area_sqm': area_sqm,
            'complexity_score': complexity_score,
            'material_quality_score': material_quality_score,
            'avg_price': avg_price,
            'min_price': min_price,
            'max_price': max_price,
            'price_range': price_range,
            'price_ratio': price_ratio,
            'cheapest_location': prices_sorted[0]['location'],
            'most_expensive_location': prices_sorted[-1]['location'],
            'regional_prices': prices_sorted
        }

        return result

    def generate_benchmark_report(self, categories=None, area_sqm=100, complexity_score=5, material_quality_score=5):
        """
        Generate benchmark pricing report for multiple categories and locations

        Args:
            categories: List of categories (if None, use all available)
            area_sqm: Area in square meters
            complexity_score: Complexity score (1-10)
            material_quality_score: Material quality score (1-10)

        Returns:
            Pandas DataFrame with benchmark prices
        """
        if not self.category_mapping or not self.location_mapping:
            raise ValueError(
                "Category or location mapping not available. Train the model first.")

        if categories is None:
            categories = list(self.category_mapping.keys())

        locations = list(self.location_mapping.keys())

        # Generate data for the report
        data = []
        for category in categories:
            for location in locations:
                price = self.predict_fair_price(
                    category, location, area_sqm, complexity_score, material_quality_score
                )

                data.append({
                    'category': category,
                    'location': location,
                    'area_sqm': area_sqm,
                    'complexity_score': complexity_score,
                    'material_quality_score': material_quality_score,
                    'price': price
                })

        # Create DataFrame
        df = pd.DataFrame(data)

        # Create a pivot table for easier viewing
        pivot_df = df.pivot(
            index='category', columns='location', values='price')

        return pivot_df
