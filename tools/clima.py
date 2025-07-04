import os
import requests
import pyowm
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ACCUWEATHER_API_KEY = os.getenv('ACCUWEATHER_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = 'http://dataservice.accuweather.com'

# Initialize OpenWeatherMap
if OPENWEATHER_API_KEY:
    owm = pyowm.OWM(OPENWEATHER_API_KEY)
    mgr = owm.weather_manager()

# Manual mapping for cities that don't work well with the API
CITY_MANUAL_MAPPING = {
    'vilagarcia de arousa': '308526',  # Location key for Vilagarcía de Arousa, Spain
    'vilagarcía de arousa': '308526',  # With accented á
    'vila garcia de arousa': '308526',  # Alternative spelling
}

def get_location_key(city: str) -> Optional[str]:
    """Get location key for a given city using AccuWeather API."""
    try:
        print(f"\n[get_location_key] Original input: '{city}'")
        
        # Check manual mapping first
        normalized_city = city.lower().strip()
        if normalized_city in CITY_MANUAL_MAPPING:
            location_key = CITY_MANUAL_MAPPING[normalized_city]
            print(f"[get_location_key] Found in manual mapping: {location_key}")
            return location_key
        
        # Clean the city name - preserve accented characters and spaces
        city = city.strip().title()  # Convert to title case for better matching
        print(f"[get_location_key] After strip and title case: '{city}'")
        
        # Common phrases to remove from the beginning of the input
        common_phrases = ['what', 'is', 'the', 'weather', 'in', 'for', 'like',
                        'i', 'would', 'like', 'to', 'know', 'tiempo', 'clima',
                        'el', 'la', 'de', 'del', 'en', 'weather in', 'tiempo en', 'clima en']
        
        # Remove common phrases from the beginning (case-insensitive)
        city_lower = city.lower()
        for phrase in sorted(common_phrases, key=len, reverse=True):
            if city_lower.startswith(phrase):
                city = city[len(phrase):].strip()
                city_lower = city.lower()
                print(f"[get_location_key] Removed phrase: '{phrase}', remaining: '{city}'")
        
        if not city:
            print("[get_location_key] No valid city name after cleaning")
            return None
            
        # Special handling for Spanish/Portuguese cities with 'de' in the name
        # We want to keep 'de' when it's part of the city name (e.g., 'Vilagarcia de Arousa')
        # Only remove 'de' if it's at the beginning of the string
        if city.lower().startswith('de '):
            city = city[3:].strip()
            print(f"[get_location_key] Removed leading 'de', remaining: '{city}'")
            
        print(f"[get_location_key] Final city name: '{city}'")
        
        # Try different search strategies
        search_terms = [
            city,  # Original city name
            city.replace(' de ', ' '),  # Without 'de' in the middle
            ' '.join([word for word in city.split() if word.lower() != 'de'])  # Remove all 'de'
        ]
        
        for search_term in search_terms:
            try:
                # First try the autocomplete endpoint
                autocomplete_url = f"{BASE_URL}/locations/v1/cities/autocomplete"
                params = {
                    'apikey': ACCUWEATHER_API_KEY,
                    'q': search_term,
                    'language': 'es-es'
                }
                
                print(f"[get_location_key] Trying autocomplete with: '{search_term}'")
                response = requests.get(autocomplete_url, params=params, timeout=10)
                response.raise_for_status()
                suggestions = response.json()
                
                if not isinstance(suggestions, list):
                    print("[get_location_key] Invalid response from autocomplete API")
                    continue
                    
                if suggestions:
                    # Try to find an exact match in the suggestions
                    for suggestion in suggestions:
                        if 'Key' in suggestion and 'LocalizedName' in suggestion:
                            print(f"[get_location_key] Found suggestion: {suggestion['LocalizedName']} ({suggestion['Key']})")
                            return suggestion['Key']
                
                # If no suggestions, try the regular search
                search_url = f"{BASE_URL}/locations/v1/cities/search"
                params = {
                    'apikey': ACCUWEATHER_API_KEY,
                    'q': search_term,
                    'language': 'es-es',
                    'details': False
                }
                
                print(f"[get_location_key] Trying direct search with: '{search_term}'")
                response = requests.get(search_url, params=params, timeout=10)
                response.raise_for_status()
                locations = response.json()
                
                if isinstance(locations, list) and locations:
                    for location in locations:
                        if 'Key' in location:
                            print(f"[get_location_key] Found location: {location.get('LocalizedName', 'Unknown')} ({location['Key']})")
                            return location['Key']
                
            except requests.RequestException as e:
                print(f"[get_location_key] Error searching for '{search_term}': {str(e)}")
                continue
        
        print(f"[get_location_key] Could not find location for: {city}")
        return None
        
    except requests.RequestException as e:
        print(f"[get_location_key] Request error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[get_location_key] Response status: {e.response.status_code}")
            print(f"[get_location_key] Response content: {e.response.text}")
    except Exception as e:
        print(f"[get_location_key] Unexpected error: {str(e)}")
        import traceback
        print(f"[get_location_key] Traceback: {traceback.format_exc()}")
    
    return None

def get_weather_accuweather(city: str, language: str = 'en') -> Tuple[bool, dict]:
    """
    Get weather from AccuWeather API.
    
    Returns:
        tuple: (success: bool, result: dict) where result contains weather data or error message
    """
    try:
        if not ACCUWEATHER_API_KEY or ACCUWEATHER_API_KEY == 'your_api_key_here':
            return False, {
                'error': 'AccuWeather API key not configured',
                'type': 'config_error'
            }
            
        # Get location key
        location_key = get_location_key(city)
        if not location_key:
            return False, {
                'error': f'Location not found: {city}',
                'type': 'location_error'
            }
        
        # Get current conditions
        url = f"{BASE_URL}/currentconditions/v1/{location_key}"
        params = {
            'apikey': ACCUWEATHER_API_KEY,
            'language': language,
            'details': True
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data or not isinstance(data, list):
            return False, {
                'error': 'Invalid response from AccuWeather',
                'type': 'api_error'
            }
            
        current = data[0]
        weather_data = {
            'city': city,
            'source': 'AccuWeather',
            'condition': current.get('WeatherText', 'Unknown'),
            'temperature': current.get('Temperature', {}).get('Metric', {}).get('Value'),
            'real_feel': current.get('RealFeelTemperature', {}).get('Metric', {}).get('Value'),
            'humidity': current.get('RelativeHumidity'),
            'wind': current.get('Wind', {}).get('Speed', {}).get('Metric', {}).get('Value'),
            'wind_unit': 'km/h',
            'wind_direction': current.get('Wind', {}).get('Direction', {}).get('Localized'),
            'uv_index': current.get('UVIndex'),
            'visibility': current.get('Visibility', {}).get('Metric', {}).get('Value'),
            'pressure': current.get('Pressure', {}).get('Metric', {}).get('Value'),
            'precipitation': current.get('Precip1hr', {}).get('Metric', {}).get('Value')
        }
        
        # Clean up None values
        weather_data = {k: v for k, v in weather_data.items() if v is not None}
        return True, weather_data
        
    except requests.exceptions.RequestException as e:
        return False, {
            'error': f'Network error: {str(e)}',
            'type': 'network_error'
        }
    except Exception as e:
        return False, {
            'error': f'AccuWeather error: {str(e)}',
            'type': 'api_error'
        }

def get_weather_openweather(city: str, language: str = 'en') -> Tuple[bool, dict]:
    """
    Get weather from OpenWeatherMap API.
    
    Returns:
        tuple: (success: bool, result: dict) where result contains weather data or error message
    """
    try:
        if not OPENWEATHER_API_KEY:
            return False, {
                'error': 'OpenWeatherMap API key not configured',
                'type': 'config_error'
            }
            
        # Search for the city
        observation = mgr.weather_at_place(city)
        weather = observation.weather
        
        # Get temperature in Celsius
        temp = weather.temperature('celsius')
        wind = weather.wind()
        
        weather_data = {
            'city': city,
            'source': 'OpenWeatherMap',
            'condition': weather.detailed_status.capitalize(),
            'temperature': temp.get('temp'),
            'temp_min': temp.get('temp_min'),
            'temp_max': temp.get('temp_max'),
            'real_feel': temp.get('feels_like'),
            'humidity': weather.humidity,
            'pressure': weather.pressure.get('press'),
            'wind': wind.get('speed'),
            'wind_unit': 'm/s',
            'wind_direction': wind.get('deg'),
            'clouds': weather.clouds,
            'rain': weather.rain,
            'snow': weather.snow,
            'sunrise': weather.sunrise_time('iso'),
            'sunset': weather.sunset_time('iso'),
            'reference_time': weather.reference_time('iso')
        }
        
        # Clean up None values
        weather_data = {k: v for k, v in weather_data.items() if v is not None}
        return True, weather_data
        
    except pyowm.commons.exceptions.NotFoundError:
        return False, {
            'error': f'Location not found: {city}',
            'type': 'location_error'
        }
    except pyowm.commons.exceptions.UnauthorizedError:
        return False, {
            'error': 'Invalid OpenWeatherMap API key',
            'type': 'auth_error'
        }
    except requests.exceptions.RequestException as e:
        return False, {
            'error': f'Network error: {str(e)}',
            'type': 'network_error'
        }
    except Exception as e:
        return False, {
            'error': f'OpenWeatherMap error: {str(e)}',
            'type': 'api_error'
        }

def get_weather(city_input: str, language: str = 'en') -> dict:
    """
    Get current weather for a city, with fallback to OpenWeatherMap if AccuWeather fails.
    
    Args:
        city_input: The city name (can include commands like 'weather in' or 'clima en')
        language: Language for the response (default: 'en')
        
    Returns:
        dict: Dictionary containing weather data or error information
    """
    try:
        # Clean the city input
        city = city_input.strip()
        
        # Remove common command prefixes
        prefixes = [
            'weather in', 'clima en', 'weather for', 'clima para',
            'weather at', 'clima en', 'weather', 'clima',
            'temperatura en', 'temperature in', 'tiempo en', 'weather en'
        ]
        
        for prefix in prefixes:
            if city.lower().startswith(prefix.lower()):
                city = city[len(prefix):].strip()
                break
                
        # Remove any remaining quotes and extra spaces
        city = city.strip('\'"').strip()
        
        if not city:
            return {'error': 'Please provide a city name.', 'type': 'validation_error'}
            
        print(f"[get_weather] Processing city: '{city}'")
        
        # Try AccuWeather first
        success, result = get_weather_accuweather(city, language)
        if success:
            print(f"[get_weather] Successfully got data from AccuWeather")
            return result
            
        print(f"[get_weather] AccuWeather failed: {result.get('error', 'Unknown error')}")
        print("[get_weather] Trying OpenWeatherMap...")
        
        # Fall back to OpenWeatherMap
        success, result = get_weather_openweather(city, language)
        if success:
            print(f"[get_weather] Successfully got data from OpenWeatherMap")
            return result
            
        print(f"[get_weather] OpenWeatherMap failed: {result.get('error', 'Unknown error')}")
        return {
            'error': 'Could not retrieve weather information. Both services failed.',
            'type': 'service_unavailable',
            'details': {
                'accuweather_error': result.get('error', 'Unknown error'),
                'openweather_error': result.get('error', 'Unknown error')
            }
        }
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        print(f"[get_weather] {error_msg}")
        return {
            'error': error_msg,
            'type': 'unexpected_error'
        }
        
    except Exception as e:
        return {'error': f"An unexpected error occurred: {str(e)}"}

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
