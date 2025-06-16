class WeatherApp {
    constructor() {
        this.searchBtn = document.getElementById('searchBtn');
        this.cityInput = document.getElementById('cityInput');
        this.weatherInfo = document.getElementById('weatherInfo');
        this.errorMessage = document.getElementById('errorMessage');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.searchBtn.addEventListener('click', () => this.handleSearch());
        this.cityInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });
    }

    async handleSearch() {
        const city = this.cityInput.value.trim();
        if (!city) {
            this.showError('Please enter a city name');
            return;
        }
        
        await this.fetchWeather(city);
    }

    async fetchWeather(city) {
        this.showLoadingState();
        
        try {
            console.log(`Fetching weather for city: ${city}`);
            const response = await fetch('/get_weather', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `city=${encodeURIComponent(city)}`
            });

            let data;
            try {
                data = await response.json();
                console.log('API Response:', data);
            } catch (parseError) {
                console.error('Error parsing JSON:', parseError);
                throw new Error('Invalid response from server');
            }
            
            // If we have any weather data at all, try to display it
            const hasWeatherData = data && (
                data.temperature !== undefined || 
                data.condition || 
                data.city ||
                data.humidity !== undefined ||
                data.wind !== undefined
            );
            
            if (hasWeatherData) {
                console.log('Displaying weather data:', data);
                this.updateWeatherDisplay(data);
                return;
            }
            
            // If we have an error but no data, throw it
            if (data.error) {
                console.warn('API returned error:', data.error);
                throw new Error(data.error);
            }
            
            // If we get here, we have no usable data
            throw new Error('No valid weather data received');
            
        } catch (error) {
            console.error('Error in fetchWeather:', error);
            this.showError('Weather service returned an error. Showing standard recommendations.');
            this.showStandardRecommendations();
        }
    }

    showLoadingState() {
        this.weatherInfo.style.display = 'none';
        this.errorMessage.style.display = 'none';
        this.showLoadingRecommendations();
    }
    
    showLoadingRecommendations() {
        const container = document.getElementById('recommendations');
        if (container) {
            container.innerHTML = `
                <div class="text-center my-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2 text-muted">Getting personalized recommendations...</p>
                </div>`;
        }
    }

    async updateWeatherDisplay(data) {
        console.log('Updating weather display with data:', data);
        
        // Basic validation
        if (!data) {
            console.error('No data provided to updateWeatherDisplay');
            this.showError('No weather data received');
            return;
        }

        try {
            // Safely extract values with defaults
            const weatherData = {
                city: data.city || 'Unknown location',
                temperature: data.temperature !== undefined ? Math.round(data.temperature) : 'N/A',
                realFeel: data.real_feel !== undefined ? Math.round(data.real_feel) : null,
                condition: data.condition || 'Unknown',
                humidity: data.humidity !== undefined ? data.humidity : 'N/A',
                wind: data.wind !== undefined ? data.wind : 'N/A',
                windUnit: data.wind_unit || 'km/h',
                source: data.source || 'Weather Service',
                lastUpdated: data.last_updated ? new Date(data.last_updated).toLocaleString() : 'Just now'
            };

            console.log('Processed weather data:', weatherData);

            // Update the DOM
            document.getElementById('cityName').textContent = weatherData.city;
            document.getElementById('temperature').textContent = `${weatherData.temperature}°C`;
            document.getElementById('condition').textContent = weatherData.condition;
            document.getElementById('feelsLike').textContent = weatherData.realFeel !== null ? 
                `${weatherData.realFeel}°C` : 'N/A';
            document.getElementById('humidity').textContent = `${weatherData.humidity}%`;
            document.getElementById('wind').textContent = `${weatherData.wind} ${weatherData.windUnit}`;
            
            // Show loading state for recommendations
            this.showLoadingRecommendations();
            
            // Format weather data for LLM
            const weatherDescription = `Temperature: ${weatherData.temperature}°C, Condition: ${weatherData.condition}, Humidity: ${weatherData.humidity}%, Wind: ${weatherData.wind} ${weatherData.windUnit}`;
            
            // Get LLM-based recommendations
            try {
                const response = await fetch('/get_recommendations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        weather_description: weatherDescription,
                        language: 'en-us'
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.recommendations) {
                        // Format the recommendations to match our expected structure
                        const formattedRecs = data.recommendations
                            .split('\n')
                            .filter(r => r.trim() !== '')
                            .map(r => r.trim());
                        
                        this.updateRecommendations({
                            recommendations: formattedRecs,
                            source: data.source || 'Weather Assistant'
                        });
                        return;
                    }
                }
                // Fall back to standard recommendations if LLM call fails
                console.warn('Falling back to standard recommendations');
                this.showStandardRecommendations();
            } catch (error) {
                console.error('Error fetching LLM recommendations:', error);
                this.showStandardRecommendations();
            }
            
            // Update weather icon
            this.updateWeatherIcon(weatherData.condition);
            
            // Show the weather info and hide any error messages
            this.weatherInfo.style.display = 'block';
            this.errorMessage.style.display = 'none';
            
        } catch (error) {
            console.error('Error updating weather display:', error);
            this.showError('Error displaying weather data. Please try again.');
            this.showStandardRecommendations();
        }
    }

    getRecommendations(weatherData) {
        // Start with an empty result set
        const result = {
            recommendations: [],
            source: weatherData?.source || 'Weather Service'
        };
        
        try {
            // If we have valid weather data, create relevant recommendations
            if (weatherData && typeof weatherData === 'object' && 
                (weatherData.temperature !== undefined || weatherData.condition)) {
                
                const temp = parseFloat(weatherData.temperature) || 20;
                const condition = (weatherData.condition || '').toLowerCase();
                const recommendations = [];
                
                // Temperature-based recommendations (pick 1-2 most relevant)
                if (temp > 30) {
                    recommendations.push('Stay hydrated and avoid the sun during peak hours');
                    if (condition.includes('sun') || condition.includes('clear')) {
                        recommendations.push('Seek shade and wear a wide-brimmed hat');
                    }
                } else if (temp > 20) {
                    recommendations.push('Perfect weather for outdoor activities');
                } else if (temp < 10) {
                    recommendations.push('Dress in warm layers');
                    if (temp < 0) {
                        recommendations.push('Protect exposed skin from frostbite');
                    }
                }

                // Weather condition-based recommendations (pick 1-2 most relevant)
                if (condition.includes('rain') || condition.includes('drizzle')) {
                    recommendations.push('Carry an umbrella or wear a waterproof jacket');
                } 
                if (condition.includes('snow') || condition.includes('sleet')) {
                    recommendations.push('Wear boots with good traction');
                } 
                if (condition.includes('thunder') || condition.includes('storm')) {
                    recommendations.push('Consider postponing outdoor activities');
                }

                // Wind-based recommendations (only if significant)
                if (weatherData.wind && weatherData.wind !== 'N/A') {
                    const windSpeed = parseFloat(weatherData.wind);
                    if (!isNaN(windSpeed)) {
                        if (windSpeed > 30) {
                            recommendations.push('Be cautious of strong wind gusts');
                        } else if (windSpeed > 20) {
                            recommendations.push('Hold onto hats and light objects');
                        }
                    }
                }

                // If we have specific recommendations, use them; otherwise fall back to standard
                if (recommendations.length > 0) {
                    // Remove duplicates and limit to 3 most relevant
                    result.recommendations = [...new Set(recommendations)].slice(0, 3);
                } else {
                    // Fall back to standard recommendations if none were generated
                    const standard = this.getStandardRecommendations();
                    result.recommendations = standard.recommendations.slice(0, 3);
                }
                
                return result;
            }
        } catch (error) {
            console.error('Error generating recommendations:', error);
        }
        
        // If we get here, return standard recommendations
        const standard = this.getStandardRecommendations();
        standard.recommendations = standard.recommendations.slice(0, 3);
        return standard;
    }

    addUnique(recommendations, recommendation) {
        if (!recommendations.includes(recommendation)) {
            recommendations.push(recommendation);
        }
    }

    ensureMinimumRecommendations(recommendations, standardRecommendations, minCount) {
        const availableRecommendations = [...standardRecommendations];
        
        // Remove any standard recommendations that are already in the list
        for (const rec of recommendations) {
            const index = availableRecommendations.indexOf(rec);
            if (index > -1) {
                availableRecommendations.splice(index, 1);
            }
        }
        
        // Add recommendations until we reach the minimum count
        while (recommendations.length < minCount && availableRecommendations.length > 0) {
            const randomIndex = Math.floor(Math.random() * availableRecommendations.length);
            const recommendation = availableRecommendations.splice(randomIndex, 1)[0];
            recommendations.push(recommendation);
        }
    }

    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendations');
        if (!container) return;

        // Handle case where recommendations is just an array
        if (Array.isArray(recommendations)) {
            recommendations = {
                recommendations: recommendations,
                source: 'Weather Service'
            };
        }

        // Handle case where recommendations is a string (from LLM)
        let recs = [];
        if (typeof recommendations.recommendations === 'string') {
            // Split by newlines and bullet points, filter out empty lines
            recs = recommendations.recommendations
                .split(/\n|•/)
                .map(r => r.trim())
                .filter(r => r.length > 0);
        } else if (Array.isArray(recommendations.recommendations)) {
            recs = recommendations.recommendations;
        }

        // If no recommendations, fall back to standard ones
        if (recs.length === 0) {
            this.showStandardRecommendations();
            return;
        }

        // Limit to 3 recommendations
        const limitedRecs = recs.slice(0, 3);

        // Create HTML for recommendations
        const recommendationsHtml = `
            <div class="recommendations-container">
                <h5 class="mb-2">Recommended Activities</h5>
                <ul class="list-unstyled ps-3">
                    ${limitedRecs.map(rec => `<li class="mb-1">• ${rec}</li>`).join('')}
                </ul>
                <div class="text-muted small mt-2">
                    Source: ${recommendations.source || 'Weather Service'}
                </div>
            </div>`;

        // Update the container and ensure it's visible
        container.innerHTML = recommendationsHtml;
        container.style.display = 'block';
        this.weatherInfo.style.display = 'block';
    }

    updateWeatherIcon(condition) {
        const icon = document.getElementById('weatherIcon');
        if (!icon) return;
        
        const lowerCondition = condition.toLowerCase();
        
        if (lowerCondition.includes('sun') || lowerCondition.includes('clear')) {
            icon.className = 'fas fa-sun';
        } else if (lowerCondition.includes('cloud')) {
            icon.className = 'fas fa-cloud';
        } else if (lowerCondition.includes('rain')) {
            icon.className = 'fas fa-cloud-rain';
        } else if (lowerCondition.includes('snow')) {
            icon.className = 'far fa-snowflake';
        } else {
            icon.className = 'fas fa-cloud-sun';
        }
        
        // Ensure the weather info container is visible
        const weatherInfo = document.getElementById('weatherInfo');
        if (weatherInfo) {
            weatherInfo.style.display = 'block';
        }
    }

    getStandardRecommendations() {
        const recommendations = {
            sunny: [
                'Wear sunscreen and a hat',
                'Stay hydrated throughout the day',
                'Great day for outdoor activities',
                'Wear sunglasses to protect your eyes',
                'Consider going to the beach'
            ],
            cloudy: [
                'A light jacket might be needed',
                'Good day for a walk',
                'Perfect weather for photography',
                'Great day for exploring the city',
                'Ideal for outdoor sports'
            ],
            rainy: [
                'Don\'t forget your umbrella',
                'Wear waterproof shoes',
                'Great day for indoor activities',
                'Be cautious on wet surfaces',
                'Perfect weather for reading a book'
            ],
            snowy: [
                'Dress in warm layers',
                'Wear boots with good traction',
                'Great day for winter sports',
                'Be cautious on icy surfaces',
                'Perfect for hot chocolate by the fire'
            ],
            default: [
                'Check the weather forecast',
                'Dress appropriately for the conditions',
                'Stay safe and enjoy your day',
                'Be prepared for changing weather',
                'We\'re experiencing technical difficulties'
            ]
        };

        const weatherTypes = ['sunny', 'cloudy', 'rainy', 'snowy'];
        const randomType = weatherTypes[Math.floor(Math.random() * weatherTypes.length)];
        
        return {
            recommendations: [...(recommendations[randomType] || recommendations.default)],
            source: 'Weather Service',
            type: randomType
        };
    }

    showError(message) {
        if (this.errorMessage) {
            this.errorMessage.textContent = message;
            this.errorMessage.style.display = 'block';
        } else {
            console.error('Error message element not found:', message);
        }
        if (this.weatherInfo) {
            this.weatherInfo.style.display = 'none';
        }
    }

    showStandardRecommendations() {
        try {
            console.log('Showing standard recommendations');
            const recommendations = this.getStandardRecommendations();
            
            // Ensure we have recommendations to show
            if (!recommendations || !Array.isArray(recommendations.recommendations) || recommendations.recommendations.length === 0) {
                console.error('No recommendations available');
                document.getElementById('recommendations').innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        No recommendations available at the moment.
                    </div>`;
                return;
            }
            
            // Create the recommendations HTML
            const recommendationsHtml = `
                <div class="mt-4 pt-3">
                    <h4 class="text-center mb-3">
                        <i class="fas fa-lightbulb me-2"></i>Suggested Activities
                    </h4>
                    <div class="row justify-content-center">
                        ${recommendations.recommendations.slice(0, 4).map(rec => `
                            <div class="col-md-6 mb-2">
                                <div class="alert alert-info p-2">
                                    <i class="fas fa-check-circle me-2"></i>${rec}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <p class="text-muted small mt-2">
                        <i class="fas fa-info-circle me-1"></i>
                        Showing general recommendations
                    </p>
                </div>`;
                
            // Update the DOM
            const recommendationsEl = document.getElementById('recommendations');
            if (recommendationsEl) {
                recommendationsEl.innerHTML = recommendationsHtml;
            } else {
                console.error('Recommendations element not found');
            }
            
        } catch (error) {
            console.error('Error showing standard recommendations:', error);
            const errorHtml = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error loading recommendations. Please try again later.
                </div>`;
                
            const recommendationsEl = document.getElementById('recommendations');
            if (recommendationsEl) {
                recommendationsEl.innerHTML = errorHtml;
            }
        }
    }
}

// Initialize the app when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new WeatherApp();
});
