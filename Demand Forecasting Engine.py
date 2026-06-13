"""
╔══════════════════════════════════════════════════════════╗
║               DEMAND FORECASTING ENGINE                  ║
║  Predicts freight demand indices for the next 7 days.   ║
╚══════════════════════════════════════════════════════════╝

Inputs:
  - Route (origin, destination)
  - Forecast start date
  - Season / festival flags

Outputs:
  - Historical 30-day baseline average
  - 7-day daily demand index predictions
  - Spike alerts (when demand is > 20% above historical average)
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class DemandForecastingEngine:
    def __init__(self):
        # Base demand indices for standard corridors
        self.base_demands = {
            ("Pune", "Delhi"): 120.0,
            ("Mumbai", "Pune"): 85.0,
            ("Delhi", "Agra"): 45.0,
            ("Bangalore", "Chennai"): 70.0,
            ("Mumbai", "Delhi"): 140.0,
        }
        
    def normalize_route(self, origin: str, destination: str) -> Tuple[str, str]:
        return origin.strip().title(), destination.strip().title()

    def _get_base_demand(self, origin: str, destination: str) -> float:
        origin, destination = self.normalize_route(origin, destination)
        key = (origin, destination)
        rev = (destination, origin)
        return self.base_demands.get(key) or self.base_demands.get(rev, 60.0)

    def generate_historical_data(self, origin: str, destination: str, end_date: datetime, days: int = 30) -> List[Dict]:
        """
        Generate synthetic historical daily demand data with realistic variations.
        Used to calculate baselines and provide context.
        """
        history = []
        base = self._get_base_demand(origin, destination)
        origin_title, destination_title = self.normalize_route(origin, destination)

        random.seed(hash(f"{origin_title}-{destination_title}-{end_date.strftime('%Y-%m-%d')}") % 10000)

        for i in range(days, 0, -1):
            date = end_date - timedelta(days=i)
            day_name = date.strftime("%A")

            day_mult = 1.0
            if day_name == "Monday" and origin_title == "Pune" and destination_title == "Delhi":
                day_mult = 1.15
            elif date.weekday() >= 5:
                day_mult = 0.85

            month = date.month
            season_mult = 1.0
            if month in (9, 10, 11):
                season_mult = 1.05
            elif month in (6, 7, 8):
                season_mult = 0.95

            noise = random.uniform(0.92, 1.08)
            volume = base * day_mult * season_mult * noise
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": day_name,
                "volume": round(volume, 1)
            })

        return history

    def calculate_baseline_avg(self, history: List[Dict]) -> float:
        if not history:
            return 0.0
        return round(sum(day["volume"] for day in history) / len(history), 2)

    def calculate_baseline_stddev(self, history: List[Dict]) -> float:
        if len(history) < 2:
            return 0.0
        volumes = [day["volume"] for day in history]
        from statistics import pstdev
        return round(pstdev(volumes), 2)

    def forecast_7_days(
        self, 
        origin: str, 
        destination: str, 
        start_date: datetime, 
        is_festival: bool = False, 
        season: str = "summer"
    ) -> Dict:
        """
        Predict demand volume for the next 7 days.
        Triggers a spike alert if demand is > 20% above historical average.
        """
        history = self.generate_historical_data(origin, destination, start_date, days=30)
        baseline_avg = self.calculate_baseline_avg(history)
        baseline_stddev = self.calculate_baseline_stddev(history)
        forecast = []
        base = self._get_base_demand(origin, destination)

        random.seed(hash(f"predict-{origin}-{destination}-{start_date.strftime('%Y-%m-%d')}") % 10000)
        origin_title, destination_title = self.normalize_route(origin, destination)
        is_agri_route = (origin_title, destination_title) in [("Pune", "Delhi"), ("Bangalore", "Chennai")]

        for i in range(7):
            date = start_date + timedelta(days=i)
            day_name = date.strftime("%A")

            day_mult = 1.0
            if day_name == "Monday" and origin_title == "Pune" and destination_title == "Delhi":
                day_mult = 1.15
            elif date.weekday() >= 5:
                day_mult = 0.85

            fest_mult = 1.35 if is_festival else 1.0
            season_mult = 1.0
            if season.lower() == "harvest" and is_agri_route:
                season_mult = 1.25
            elif season.lower() == "monsoon":
                season_mult = 0.92 if origin_title in ("Mumbai", "Bangalore", "Chennai") else 0.96
            elif season.lower() == "winter":
                season_mult = 1.08 if origin_title in ("Delhi", "Agra") else 1.03

            noise = random.uniform(0.96, 1.04)
            predicted_volume = base * day_mult * fest_mult * season_mult * noise
            predicted_volume = round(predicted_volume, 1)
            spike_threshold = baseline_avg * 1.20
            spike_alert = predicted_volume > spike_threshold
            spike_percentage = round(((predicted_volume - baseline_avg) / baseline_avg) * 100, 1) if baseline_avg > 0 else 0

            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": day_name,
                "predicted_volume": predicted_volume,
                "predicted_index": round((predicted_volume / baseline_avg) * 100, 1) if baseline_avg > 0 else 0,
                "spike_alert": spike_alert,
                "spike_percentage": spike_percentage
            })

        confidence = 1.0
        if baseline_avg > 0:
            confidence = max(0.45, min(1.0, 1.0 - baseline_stddev / baseline_avg))

        return {
            "route": f"{origin_title} → {destination_title}",
            "historical_baseline_avg": baseline_avg,
            "historical_baseline_stddev": baseline_stddev,
            "forecast_confidence": round(confidence, 2),
            "forecast": forecast,
            "params": {
                "season": season,
                "is_festival": is_festival,
                "start_date": start_date.strftime("%Y-%m-%d")
            }
        }

if __name__ == "__main__":
    print("=" * 60)
    print("DEMAND FORECASTING ENGINE - TEST FLIGHT")
    print("=" * 60)
    
    engine = DemandForecastingEngine()
    today = datetime.now()
    
    # Test 1: Standard Pune -> Delhi
    print("Test 1: Pune → Delhi, Regular Day")
    res1 = engine.forecast_7_days("Pune", "Delhi", today, is_festival=False, season="summer")
    print(f"Historical 30-Day Avg: {res1['historical_baseline_avg']}")
    for day in res1['forecast']:
        alert_str = "⚠️ SPIKE ALERT" if day['spike_alert'] else "Normal"
        print(f"  {day['date']} ({day['day_of_week'][:3]}): {day['predicted_volume']} | {alert_str}")
        
    print("\nTest 2: Pune → Delhi, Diwali festival active + Harvest Season")
    res2 = engine.forecast_7_days("Pune", "Delhi", today, is_festival=True, season="harvest")
    print(f"Historical 30-Day Avg: {res2['historical_baseline_avg']}")
    for day in res2['forecast']:
        alert_str = "⚠️ SPIKE ALERT" if day['spike_alert'] else "Normal"
        print(f"  {day['date']} ({day['day_of_week'][:3]}): {day['predicted_volume']} (Change: {day['spike_percentage']}%) | {alert_str}")
    print("=" * 60)
