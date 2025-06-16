from flask import Flask, render_template, request, jsonify, send_from_directory
from tools.clima import get_weather, recommend_activity
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug: Check if API key is loaded
print("\n=== Environment Variables ===")
print(f"ACCUWEATHER_API_KEY: {'*' * 8 + os.getenv('ACCUWEATHER_API_KEY', '')[-4:] if os.getenv('ACCUWEATHER_API_KEY') else 'Not set'}")
print("==========================\n")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/get_weather', methods=['POST'])
def weather():
    city = request.form.get('city')
    if not city:
        return jsonify({'error': 'No city provided', 'type': 'validation_error'}), 400
    
    try:
        print(f"\n=== Received request for city: {city} ===")
        print(f"Processing weather request for: '{city}'")
        
        # Get weather data from our service
        weather_data = get_weather(city)
        
        # Log the received data for debugging
        print(f"Received weather data: {json.dumps(weather_data, indent=2)}")
        
        # Check for error in the response
        if 'error' in weather_data:
            error_type = weather_data.get('type', 'weather_error')
            print(f"Error in weather data: {weather_data['error']} (type: {error_type})")
            return jsonify({
                'error': weather_data['error'],
                'type': error_type,
                'details': weather_data.get('details', {})
            }), 400 if error_type != 'not_found' else 404
            
        # If we have valid weather data
        if weather_data and (weather_data.get('temperature') is not None or weather_data.get('condition')):
            source = weather_data.get('source', 'Unknown source')
            print(f"Successfully retrieved weather data for: {weather_data.get('city', 'unknown')} from {source}")
            
            # Add timestamp
            from datetime import datetime
            weather_data['last_updated'] = datetime.utcnow().isoformat()
            
            # Ensure all required fields are present with defaults if needed
            weather_data.setdefault('city', city)
            weather_data.setdefault('condition', 'Unknown')
            weather_data.setdefault('humidity', 0)
            weather_data.setdefault('wind', 0)
            weather_data.setdefault('wind_unit', 'km/h')
            weather_data.setdefault('real_feel', weather_data.get('temperature'))
            
            return jsonify(weather_data), 200
            
        # If we get here, we have no valid data
        return jsonify({
            'error': 'No weather data available for the specified location',
            'type': 'no_data',
            'city': city
        }), 404
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unexpected error: {error_details}")
        
        return jsonify({
            'error': 'An unexpected error occurred while processing your request',
            'type': 'server_error',
            'details': str(e)
        }), 500

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    data = request.get_json()
    weather_description = data.get('weather_description', '')
    language = data.get('language', 'en-us')
    
    if not weather_description:
        return jsonify({'error': 'No weather description provided'}), 400
    
    try:
        # Get recommendations from LLM
        recommendations = recommend_activity(weather_description, language)
        return jsonify({
            'recommendations': recommendations,
            'source': 'LLM Weather Assistant'
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate recommendations',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
