import os
import sys
from dotenv import load_dotenv
from langchain.agents import Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from tools.clima import get_weather, recommend_activity

# Cargar variables de entorno
load_dotenv()

# Verificar la clave de API de AccuWeather
if not os.getenv('ACCUWEATHER_API_KEY'):
    print("Error: No se ha configurado la clave de API de AccuWeather.")
    print("Por favor, asegúrate de tener un archivo .env con ACCUWEATHER_API_KEY")
    sys.exit(1)

# Inicializar el modelo LLM
try:
    llm = Ollama(model="llama3", temperature=0.2)
except Exception as e:
    print(f"Error al cargar el modelo de Ollama: {e}")
    print("Asegúrate de tener Ollama instalado y el modelo 'llama3' descargado.")
    sys.exit(1)

# Definir herramientas
tools = [
    Tool(
        name="GetWeather",
        func=get_weather,
        description=(
            "Use this tool to get the current weather in a city. "
            "The input should be the city name and optional language code. "
            "Example: 'Madrid' or 'Madrid es-es'"
        )
    ),
    Tool(
        name="RecommendActivity",
        func=recommend_activity,
        description=(
            "Use this tool to get activity recommendations "
            "based on current weather conditions. "
            "The input should be the weather description and optional target language. "
            "Example: 'sunny, 25°C' or 'sunny, 25°C es-es'"
        )
    )
]

# Configurar memoria
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="output"
)

# Configuración del agente
prefix = """You are a multilingual assistant specialized in providing weather information and activity recommendations.

INSTRUCTIONS:
1. When the user asks about the weather in a city, use EXACTLY THIS ACTION:
   - Tool: GetWeather
   - Input: The city name ONLY (no quotes or additional characters)

2. Then, with the weather information, use:
   - Tool: RecommendActivity
   - Input: The obtained weather description

3. Respond clearly and concisely in the user's preferred language:
   - The weather information
   - Appropriate activity recommendations

4. If the user asks a general question, respond helpfully without using tools.

5. If the user asks for translation or specifies a language, translate your response accordingly.

IMPORTANT:
- Use EXACTLY the tool names as defined.
- Don't add extra text to the tool inputs.
- If you're unsure about something, say it clearly.
"""

# Inicializar agente con configuración mejorada
try:
    agent = initialize_agent(
        agent="zero-shot-react-description",
        tools=tools,
        llm=llm,
        memory=memory,
        verbose=True,  # Cambiado a True para ver el proceso de pensamiento
        handle_parsing_errors=True,
        max_iterations=5,  # Aumentado para permitir más iteraciones
        early_stopping_method="generate",
        agent_kwargs={
            'prefix': prefix,
            'suffix': """
            Respond in the user's preferred language. If the user mentions a city,
            first get the weather and then recommend activities.
            """,
            'input_variables': ['input', 'agent_scratchpad', 'chat_history']
        }
    )
except Exception as e:
    print(f"Error al inicializar el agente: {e}")
    sys.exit(1)

def mostrar_ayuda():
    print("\n=== Comandos disponibles ===")
    print("- 'ayuda': Muestra este mensaje")
    print("- 'salir' o 'exit': Cierra el programa")
    print("- 'limpiar' o 'clear': Limpia la memoria de la conversación")
    print("\nPuedes preguntar por el clima en cualquier ciudad, por ejemplo:")
    print("- ¿Qué tiempo hace en Barcelona?")
    print("- ¿Qué actividades me recomiendas para un día lluvioso?")
    print("=" * 30 + "\n")

def main():
    print("\n" + "=" * 60)
    print("Welcome to the Weather and Activity Assistant!")
    print("Type 'help' to see available commands")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("\nHow can I assist you? (type 'help' to see available commands): ").strip()

            if user_input.lower() in ['help']:
                print("\nAvailable commands:")
                print("- help: Shows this help")
                print("- exit: Exits the program")
                print("- clear: Clears the screen")
                print("- [city]: Gets the weather for a city")
                continue

            if user_input.lower() in ['exit', 'quit']:
                print("\nGoodbye! I hope you found the information useful.")
                break

            if user_input.lower() in ['clear']:
                os.system('clear' if os.name == 'posix' else 'cls')
                print("\nAvailable commands:")
                print("- help: Shows this help")
                print("- exit: Exits the program")
                print("- clear: Clears the screen")
                print("- [city]: Gets the weather for a city")
                continue

            # Process the user's query
            try:
                print("\nPensando...")
                
                # Check if the user is asking about weather
                if any(word in user_input.lower() for word in ['tiempo', 'weather', 'clima']):
                    # Extract city name and language preference
                    parts = user_input.split()
                    city = None
                    language = 'en-us'
                    
                    # Look for language code first
                    for i, word in enumerate(parts):
                        if word.lower() in ['en', 'es', 'fr', 'de', 'it']:
                            # If there's a language code, use the previous word as city
                            city = ' '.join(parts[:i])
                            language = f"{word.lower()}-{'us' if word.lower() == 'en' else 'es'}"
                            break
                    
                    if city is None:  # If no language was found, use the last word as city
                        city = parts[-1] if parts else ''
                    
                    # Get weather using the extracted city and language
                    weather_data = get_weather(city.strip(), language)
                    if "Error" not in weather_data:  # Only recommend activities if we got valid weather data
                        recommendations = recommend_activity(weather_data, language)
                        print(f"\nAsistente: {weather_data}\n{recommendations}")
                    else:
                        print(f"\nAsistente: {weather_data}")
                else:
                    # For other queries, use the agent
                    respuesta = agent.run(user_input)
                    print(f"\nAsistente: {respuesta}")
                
            except Exception as e:
                print(f"\nSorry, an error occurred: {str(e)}")
                print("Try rephrasing your question or type 'help' for more options.")
                
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            print("Please try again or type 'help' to see the options.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n¡Hasta luego!")
    except Exception as e:
        print(f"\nError crítico: {e}")
        sys.exit(1)
