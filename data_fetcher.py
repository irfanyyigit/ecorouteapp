import requests

class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.uv_url = "https://api.openweathermap.org/data/2.5/uvi" # UV indeksi için farklı endpoint

    def get_wind_data(self, lat, lon):
        params = {
            'lat': lat, 'lon': lon,
            'appid': self.api_key, 'units': 'metric'
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                'speed': data['wind'].get('speed', 0),
                'deg': data['wind'].get('deg', 0)
            }
        return None

    def get_full_weather(self, lat, lon):
        """Tüm detaylı hava durumu verilerini çeker."""
        params = {
            'lat': lat, 'lon': lon,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'tr' # Açıklamaların Türkçe gelmesi için
        }
        
        # Ana hava durumu verisi
        response = requests.get(self.base_url, params=params)
        
        # UV İndeksi verisi (OpenWeather bazen bunu ayrı endpoint'ten verir)
        uv_response = requests.get(self.uv_url, params={'lat': lat, 'lon': lon, 'appid': self.api_key})
        uv_index = uv_response.json().get('value', 'N/A') if uv_response.status_code == 200 else "N/A"

        if response.status_code == 200:
            data = response.json()
            # İstediğin tüm verileri sözlük yapısında döndürüyoruz
            return {
                'temp': data['main'].get('temp'),
                'feels_like': data['main'].get('feels_like'),
                'humidity': data['main'].get('humidity'),
                'pressure': data['main'].get('pressure'),
                'visibility': data.get('visibility'),
                'description': data['weather'][0].get('description'),
                'sunrise': data['sys'].get('sunrise'),
                'sunset': data['sys'].get('sunset'),
                'wind_speed': data['wind'].get('speed'),
                'uv_index': uv_index,
                'clouds': data['clouds'].get('all') # Bulutluluk oranı %
            }
        else:
            print(f"Hata: {response.status_code}")
            return None