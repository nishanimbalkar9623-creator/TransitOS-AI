import requests
from typing import Dict, Tuple, Optional


class RouteRiskEngine:
    def __init__(self, weather_api_key: str):
        self.weather_api_key = weather_api_key
        self.weather_base_url = "https://api.openweathermap.org/data/2.5/weather"

        # Historical delay patterns
        self.delay_history = {
            ("Mumbai", "Pune"): 1.5,
            ("Pune", "Bangalore"): 2.0,
            ("Delhi", "Agra"): 0.8,
            ("Bangalore", "Chennai"): 1.2,
            ("Mumbai", "Delhi"): 3.0,
        }

        # Alternate routes
        self.alternate_routes = {
            ("Mumbai", "Pune"): {"alternate": "Mumbai → Kolhapur → Pune", "extra_time_hours": 0.5},
            ("Pune", "Bangalore"): {"alternate": "Pune → Solapur → Bangalore", "extra_time_hours": 1.0},
            ("Delhi", "Agra"): {"alternate": "Delhi → Mathura → Agra", "extra_time_hours": 0.3},
            ("Bangalore", "Chennai"): {"alternate": "Bangalore → Vellore → Chennai", "extra_time_hours": 0.7},
            ("Mumbai", "Delhi"): {"alternate": "Mumbai → Nagpur → Delhi", "extra_time_hours": 2.0},
        }

    def normalize_location(self, location: str) -> str:
        return " ".join(location.strip().title().split())

    def get_route_key(self, origin: str, destination: str) -> Tuple[str, str]:
        origin = self.normalize_location(origin)
        destination = self.normalize_location(destination)
        if (origin, destination) in self.delay_history:
            return origin, destination
        if (destination, origin) in self.delay_history:
            return destination, origin
        return origin, destination

    def get_historical_delay(self, origin: str, destination: str) -> float:
        key = self.get_route_key(origin, destination)
        return self.delay_history.get(key, 1.2)

    def get_simulated_weather(self, origin: str) -> Dict:
        origin = self.normalize_location(origin)
        fallback = {
            "Mumbai": "clouds",
            "Pune": "clear",
            "Bangalore": "rain",
            "Chennai": "clouds",
            "Delhi": "clear",
            "Agra": "clear"
        }
        weather_main = fallback.get(origin, "clear")
        return {"weather": [{"main": weather_main}], "source": "simulated"}

    def get_weather_data(self, origin: str) -> Dict:
        params = {
            "q": origin,
            "appid": self.weather_api_key,
            "units": "metric"
        }

        try:
            response = requests.get(self.weather_base_url, params=params, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                payload["source"] = "api"
                return payload
            else:
                print(f"Warning: Weather API returned status {response.status_code}")
                return self.get_simulated_weather(origin)
        except Exception as e:
            print(f"Warning: Could not fetch weather data: {e}")
            return self.get_simulated_weather(origin)

    def extract_weather_condition(self, weather_data: Dict) -> str:
        try:
            weather_array = weather_data.get("weather")
            if not weather_array:
                return "unknown"
            if isinstance(weather_array, dict):
                weather_array = [weather_array]

            main_condition = weather_array[0].get("main", "unknown").lower()
            weather_map = {
                "rain": "rain",
                "drizzle": "rain",
                "clear": "clear",
                "clouds": "cloud",
                "thunderstorm": "storm",
                "storm": "storm",
                "snow": "snow",
                "ice": "snow",
                "fog": "fog",
                "mist": "fog"
            }
            return weather_map.get(main_condition, main_condition)
        except Exception:
            return "unknown"

    def get_time_risk_factor(self, time_of_day: str, day_of_week: str) -> float:
        time_risk = {
            "morning": 1.0,
            "afternoon": 1.1,
            "evening": 1.3,
            "night": 1.5
        }

        day_risk = {
            "monday": 1.2,
            "tuesday": 1.0,
            "wednesday": 1.0,
            "thursday": 1.0,
            "friday": 1.3,
            "saturday": 1.1,
            "sunday": 1.0
        }

        return time_risk.get(time_of_day.lower(), 1.0) * day_risk.get(day_of_week.lower(), 1.0)

    def calculate_risk_score(
        self,
        weather_condition: str,
        time_of_day: str,
        day_of_week: str,
        historical_delay: float
    ) -> Tuple[str, float]:
        base_score = 0

        weather_scores = {
            "clear": 0,
            "cloud": 1,
            "rain": 3,
            "fog": 3,
            "storm": 5,
            "snow": 4,
            "unknown": 1
        }
        base_score += weather_scores.get(weather_condition, 2)

        time_scores = {
            "morning": 0,
            "afternoon": 1,
            "evening": 2,
            "night": 3
        }
        base_score += time_scores.get(time_of_day.lower(), 1)

        if historical_delay <= 0.5:
            delay_score = 0
        elif historical_delay <= 1.0:
            delay_score = 1
        elif historical_delay <= 2.0:
            delay_score = 2
        else:
            delay_score = 3
        base_score += delay_score

        time_multiplier = self.get_time_risk_factor(time_of_day, day_of_week)
        final_score = base_score * time_multiplier

        if final_score <= 3:
            risk_level = "LOW"
        elif final_score <= 6:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return risk_level, final_score

    def estimate_delay(self, risk_level: str, historical_delay: float, weather_condition: str) -> float:
        estimated_delay = historical_delay

        risk_multipliers = {
            "LOW": 1.0,
            "MEDIUM": 1.5,
            "HIGH": 2.5
        }
        estimated_delay *= risk_multipliers.get(risk_level, 1.0)

        weather_impact = {
            "clear": 0,
            "cloud": 0.1,
            "rain": 0.3,
            "fog": 0.4,
            "storm": 0.6,
            "snow": 0.5,
            "unknown": 0.1
        }
        estimated_delay += weather_impact.get(weather_condition, 0.1)

        return round(estimated_delay, 2)

    def get_alternate_route(self, origin: str, destination: str) -> Optional[Dict]:
        key = self.get_route_key(origin, destination)
        return self.alternate_routes.get(key)

    def assess_route_risk(
        self,
        origin: str,
        destination: str,
        time_of_day: str,
        day_of_week: str
    ) -> Dict:
        normalized_origin = self.normalize_location(origin)
        normalized_destination = self.normalize_location(destination)

        weather_data = self.get_weather_data(normalized_origin)
        weather_condition = self.extract_weather_condition(weather_data)

        historical_delay = self.get_historical_delay(normalized_origin, normalized_destination)

        risk_level, risk_score = self.calculate_risk_score(
            weather_condition,
            time_of_day,
            day_of_week,
            historical_delay
        )

        estimated_delay = self.estimate_delay(risk_level, historical_delay, weather_condition)

        alternate_route = None
        if risk_level == "HIGH":
            alternate_route = self.get_alternate_route(normalized_origin, normalized_destination)

        return {
            "route": f"{normalized_origin} -> {normalized_destination}",
            "risk_level": risk_level,
            "risk_score": round(risk_score, 2),
            "risk_score_numeric": round(risk_score, 2),
            "estimated_delay_hours": estimated_delay,
            "weather_condition": weather_condition,
            "weather_source": weather_data.get("source", "unknown"),
            "time_of_day": time_of_day,
            "day_of_week": day_of_week,
            "alternate_route": alternate_route
        }


def main():
    API_KEY = "e0483c3ca58bcc0079b9cda57f0f8821"

    engine = RouteRiskEngine(API_KEY)

    test_routes = [
        {"origin": "Mumbai", "destination": "Pune", "time_of_day": "night", "day_of_week": "friday"},
        {"origin": "Pune", "destination": "Bangalore", "time_of_day": "evening", "day_of_week": "monday"},
        {"origin": "Delhi", "destination": "Agra", "time_of_day": "morning", "day_of_week": "sunday"},
        {"origin": "Bangalore", "destination": "Chennai", "time_of_day": "afternoon", "day_of_week": "wednesday"},
    ]

    print("=" * 70)
    print("ROUTE RISK ENGINE - Multiple Route Assessments")
    print("=" * 70)

    for i, route in enumerate(test_routes):
        print(f"\n📍 Test Case {i+1}: {route['origin']} → {route['destination']}")
        print(f"   Time: {route['time_of_day']}, Day: {route['day_of_week']}")

        result = engine.assess_route_risk(
            route["origin"],
            route["destination"],
            route["time_of_day"],
            route["day_of_week"]
        )

        print(f"   ⚠️ Risk Score: {result['risk_score']} ({result['risk_score_numeric']})")
        print(f"   ⏱️ Estimated Delay: {result['estimated_delay_hours']} hours")
        print(f"   🌤️ Weather: {result['weather_condition']}")

        if result["alternate_route"]:
            print(f"\n   🔴 HIGH RISK - Alternate Route Suggested:")
            print(f"      {result['alternate_route']['alternate']}")
            print(f"      Extra Time: {result['alternate_route']['extra_time_hours']} hours")
        else:
            print(f"\n   ✅ {'Route is safe' if result['risk_score'] == 'LOW' else 'Route is acceptable'}")

        print("-" * 70)


if __name__ == "__main__":
    main()