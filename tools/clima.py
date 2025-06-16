import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variable
ACCUWEATHER_API_KEY = os.getenv('ACCUWEATHER_API_KEY')
BASE_URL = 'http://dataservice.accuweather.com'

def get_location_key(city: str) -> Optional[str]:
    """Get location key for a given city using AccuWeather API."""
    try:
        # Clean the city name
        city = city.strip()
        
        # Try to find the first word that isn't a common phrase
        words = city.split()
        for i, word in enumerate(words):
            if word.lower() not in ['what', 'is', 'the', 'weather', 'in', 'for', 'like',
                                  'i', 'would', 'like', 'to', 'know', 'tiempo', 'clima']:
                # Take all words from this point to the end as the city name
                city_name = ' '.join(words[i:]).strip()
                break
        else:
            # If no valid word found, use the last word as city name
            city_name = words[-1] if words else ''
        
        # Search for the city
        url = f"{BASE_URL}/locations/v1/cities/search"
        params = {
            'apikey': ACCUWEATHER_API_KEY,
            'q': city_name,
            'language': 'es-es',
            'details': False
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        locations = response.json()
        if not isinstance(locations, list):
            return None
            
        if len(locations) > 0:
            return locations[0].get('Key')
        return None
    except (requests.RequestException, (KeyError, IndexError)) as e:
        print(f"Error getting location key: {e}")
        return None

def get_weather(city_input: str, language: str = 'en-us') -> str:
    """
    Get current weather for a city using the AccuWeather API.
    
    Args:
        city_input (str): City name to search for
        language (str): Language code for weather description (default: 'en-us')
        
    Returns:
        str: Formatted weather information or error message
    """
    try:
        if not ACCUWEATHER_API_KEY or ACCUWEATHER_API_KEY == 'your_api_key_here':
            return "Error: AccuWeather API key is not properly configured."

        # Clean input
        city = (
            city_input.split("=", 1)[-1] 
            if "=" in city_input 
            else city_input
        ).strip().strip('"\' ')
        
        if not city:
            return "Please provide a city name."

        # Get location key
        location_key = get_location_key(city)
        if not location_key:
            return f"Could not find location: {city}. Please check the city name."

        # Get current conditions
        url = f"{BASE_URL}/currentconditions/v1/{location_key}"
        params = {
            'apikey': ACCUWEATHER_API_KEY,
            'language': language,
            'details': True
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if not isinstance(data, list) or len(data) == 0:
            return f"No weather data found for {city}."
            
        current_weather = data[0]
        
        # Extract weather information
        weather_info = {
            'city': city,
            'condition': current_weather.get('WeatherText', 'Not available'),
            'temperature': current_weather.get('Temperature', {}).get('Metric', {}).get('Value', 'N/A'),
            'real_feel': current_weather.get('RealFeelTemperature', {}).get('Metric', {}).get('Value', 'N/A'),
            'humidity': current_weather.get('RelativeHumidity', 'N/A'),
            'wind': current_weather.get('Wind', {}).get('Speed', {}).get('Metric', {}).get('Value', 'N/A'),
            'wind_unit': current_weather.get('Wind', {}).get('Speed', {}).get('Metric', {}).get('Unit', 'km/h')
        }
        
        # Validate temperature values
        if weather_info['temperature'] != 'N/A':
            try:
                weather_info['temperature'] = float(weather_info['temperature'])
            except (ValueError, TypeError):
                weather_info['temperature'] = 'N/A'
        
        if weather_info['real_feel'] != 'N/A':
            try:
                weather_info['real_feel'] = float(weather_info['real_feel'])
            except (ValueError, TypeError):
                weather_info['real_feel'] = 'N/A'
        
        if weather_info['wind'] != 'N/A':
            try:
                weather_info['wind'] = float(weather_info['wind'])
            except (ValueError, TypeError):
                weather_info['wind'] = 'N/A'
        
        # Format output
        return (
            f"=== Current Conditions in {weather_info['city'].title()} ===\n"
            f"• Condition: {weather_info['condition']}\n"
            f"• Temperature: {weather_info['temperature']}°C\n"
            f"• Real Feel: {weather_info['real_feel']}°C\n"
            f"• Humidity: {weather_info['humidity']}%\n"
            f"• Wind: {weather_info['wind']} {weather_info['wind_unit']}"
        )
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error connecting to weather service: {str(e)}"
    except (KeyError, IndexError) as e:
        error_msg = f"Error processing weather data: {str(e)}"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
    
    print(f"Error in get_weather: {error_msg}")
    return f"Could not retrieve weather information. {error_msg}"

def recommend_activity(weather: str, target_language: str = 'en-us') -> str:
    """
    Provides activity recommendations based on weather conditions.
    
    Args:
        weather (str): Weather description obtained from get_weather()
        target_language (str): Language code for recommendations (default: 'en-us')
        
    Returns:
        str: Formatted activity recommendations
    """
    if not weather or not isinstance(weather, str):
        return "No recommendations could be generated. Weather information not available."
    
    weather_lower = weather.lower()
    recommendations = []
    
    # Extract temperature if available
    temp_match = next((s for s in weather.split('\n') if 'temperature' in s.lower()), None)
    if temp_match and ':' in temp_match:
        try:
            temperature = float(temp_match.split(':')[1].replace('°C', '').strip())
        except (ValueError, TypeError):
            temperature = None
    else:
        temperature = None
    
    # Determine weather type
    if any(cond in weather_lower for cond in ['sunny', 'clear', 'sun']):
        recommendations.append("Great day to enjoy outdoors! ")
        if temperature is not None:
            if temperature > 30:
                recommendations.extend([
                    "• Wear sunscreen and a hat",
                    "• Visit a pool or beach",
                    "• Enjoy a shaded terrace"
                ])
            elif temperature > 20:
                recommendations.extend([
                    "• Take a walk in the park or city",
                    "• Have a picnic outdoors",
                    "• Practice outdoor sports"
                ])
            else:
                recommendations.extend([
                    "• Take a pleasant walk",
                    "• Visit a botanical garden",
                    "• Enjoy some sun on a terrace"
                ])
                
    elif any(cond in weather_lower for cond in ['cloudy', 'overcast', 'clouds']):
        recommendations.append("Cloudy day, but many options! ")
        recommendations.extend([
            "• Visit museums or art galleries",
            "• Explore shops and malls",
            "• Enjoy coffee at a cozy café",
            "• Take advantage of that exhibition you had pending"
        ])
        
    elif any(cond in weather_lower for cond in ['rain', 'raining', 'rainy']):
        recommendations.append("Rainy day, perfect for indoor activities! ")
        recommendations.extend([
            "• Movie or series marathon",
            "• Try a new recipe at home",
            "• Read that book you have pending",
            "• Board games with friends or family"
        ])
        
    elif any(cond in weather_lower for cond in ['snow', 'snowing', 'snowy']):
        recommendations.append("Snow day! ")
        recommendations.extend([
            "• Build a snowman",
            "• Have hot chocolate with churros",
            "• If you're in the mountains, ski or snowboard",
            "• Photograph the winter landscape"
        ])
        
    elif any(cond in weather_lower for cond in ['storm', 'stormy', 'thunder', 'lightning']):
        recommendations.append("Be careful with the storm! ")
        recommendations.extend([
            "• Better stay in a safe place",
            "• Disconnect electrical appliances",
            "• Have flashlights handy for possible power outages",
            "• Take advantage of organizing at home"
        ])
    else:
        # Generic recommendations based on temperature if weather type not identified
        if temperature is not None:
            if temperature > 25:
                recommendations.append("Hot day, stay hydrated ")
                recommendations.extend([
                    "• Visit places with air conditioning",
                    "• Enjoy a cold drink on the terrace",
                    "• Go to the pool or beach"
                ])
            elif temperature < 10:
                recommendations.append("It's cold! Dress warmly ")
                recommendations.extend([
                    "• Enjoy a hot drink",
                    "• Plan indoor activities",
                    "• Prepare a hot soup or stew"
                ])
    
    # Add general recommendations
    if not recommendations:
        recommendations.append("No specific recommendations, but here are some ideas:")
        recommendations.extend([
            "• Take a short walk",
            "• Take advantage of learning something new",
            "• Organize your plans for the coming days"
        ])
    
    # Join recommendations and add language note
    recommendations_text = '\n'.join(recommendations)
    if target_language != 'en-us':
        return f"{recommendations_text}\n\n(Recommendations in English)"
    return recommendations_text
