from flask import Flask, render_template, request, jsonify
from tools.clima import get_weather
import os
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

@app.route('/get_weather', methods=['POST'])
def weather():
    city = request.form.get('city')
    print(f"\n=== Received request for city: {city} ===")
    
    if not city:
        error_msg = 'City is required'
        print(f"Error: {error_msg}")
        return jsonify({'error': error_msg}), 400
    
    try:
        print(f"Processing weather request for: '{city}'")
        weather_data = get_weather(city)
        
        if isinstance(weather_data, str):
            print(f"Error from get_weather: {weather_data}")
            return jsonify({'error': weather_data, 'type': 'weather_error'}), 400
            
        print(f"Successfully retrieved weather data for: {weather_data.get('city', 'unknown')}")
        return jsonify(weather_data)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unexpected error: {str(e)}\n{error_details}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e),
            'type': 'unexpected_error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
