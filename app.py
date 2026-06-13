from flask import Flask, request, jsonify, send_from_directory
try:
    from flask_cors import CORS
    has_cors = True
except ImportError:
    has_cors = False
import importlib.util
import os
import re
import sys
from datetime import datetime, timedelta

app = Flask(__name__)
if has_cors:
    CORS(app)
else:
    print("Warning: flask_cors module not found. CORS is disabled.")
    print("If you open index.html directly from a file, browser security blocks request. Access http://127.0.0.1:5000 instead.")


# Helper to import files with spaces in their names dynamically
def load_module(module_name, file_name):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(dir_path, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Module file not found at {file_path}")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def parse_route_string(route_str):
    if not isinstance(route_str, str):
        return 'Mumbai', 'Pune'

    normalized = route_str.strip()
    normalized = normalized.replace('→', '-').replace('->', '-').replace(',', '-').replace('/', '-').replace('|', '-')
    parts = [part.strip() for part in normalized.split('-') if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]

    parts = normalized.split()
    if len(parts) >= 2:
        return parts[0], parts[-1]

    return 'Mumbai', 'Pune'


def parse_copilot_route(prompt: str):
    if not isinstance(prompt, str):
        return None, None

    city_names = [
        "Mumbai", "Pune", "Bangalore", "Chennai", "Delhi", "Agra",
        "Ahmedabad", "Hyderabad", "Kolkata", "Jaipur", "Surat",
        "Nagpur", "Solapur", "Mathura"
    ]

    normalized = prompt.replace('→', ' to ').replace('➔', ' to ').replace('➡', ' to ').replace('->', ' to ')
    normalized = normalized.replace('—', ' ').replace('–', ' ')
    normalized = normalized.lower()

    found = []
    for city in city_names:
        if city.lower() in normalized and city not in found:
            found.append(city)

    if len(found) >= 2:
        ordered = []
        for token in re.split(r'[^A-Za-z]+', prompt):
            token = token.strip().title()
            if token in city_names and token not in ordered:
                ordered.append(token)
        if len(ordered) >= 2:
            return ordered[0], ordered[1]
        return found[0], found[1]

    return None, None


def determine_copilot_intent(prompt: str):
    text = (prompt or "").lower()
    if any(keyword in text for keyword in ["forecast", "demand", "predict", "volume", "season", "holiday"]):
        return "forecast"
    if any(keyword in text for keyword in ["risk", "route risk", "delay", "weather", "congestion", "safe", "hazard"]):
        return "route-risk"
    if any(keyword in text for keyword in ["trust", "reliability", "rating", "cancel", "on time"]):
        return "trust"
    if any(keyword in text for keyword in ["match", "capacity", "truck", "ship", "shipment", "haul"]):
        return "match"
    return "route-risk"


def generate_copilot_response(prompt: str):
    prompt = (prompt or "").strip()
    if not prompt:
        return "Please ask a logistics question, for example: 'Move 800kg Pune to Delhi tomorrow' or 'What is the route risk for Mumbai to Pune?'."

    origin, destination = parse_copilot_route(prompt)
    intent = determine_copilot_intent(prompt)
    tomorrow = datetime.now() + timedelta(days=1)
    day_of_week = datetime.now().strftime('%A').lower()
    if "tomorrow" in prompt.lower():
        day_of_week = tomorrow.strftime('%A').lower()

    time_of_day = "night"
    if "morning" in prompt.lower():
        time_of_day = "morning"
    elif "afternoon" in prompt.lower():
        time_of_day = "afternoon"
    elif "evening" in prompt.lower():
        time_of_day = "evening"

    if intent == "forecast" and origin and destination:
        engine = demand_forecasting_engine.DemandForecastingEngine()
        result = engine.forecast_7_days(
            origin=origin,
            destination=destination,
            start_date=datetime.now(),
            is_festival="festival" in prompt.lower() or "holiday" in prompt.lower(),
            season="harvest" if "harvest" in prompt.lower() or "festival" in prompt.lower() else "summer"
        )
        lines = [f"📊 7-Day Demand Forecast: {origin} → {destination}"]
        lines.append(f"Baseline: {result['historical_baseline_avg']} units | Confidence: {result['forecast_confidence']}%")
        lines.append("")
        for day in result['forecast']:
            spike = "🔴 SPIKE" if day['spike_alert'] else "✓"
            lines.append(f"{day['date']} ({day['day_of_week']}): {day['predicted_volume']} units | Index: {day['predicted_index']} | {spike}")
        return "\n".join(lines)

    if origin and destination:
        route_engine = route_risk_engine.RouteRiskEngine("e0483c3ca58bcc0079b9cda57f0f8821")
        risk = route_engine.assess_route_risk(origin, destination, time_of_day, day_of_week)
        lines = []
        
        risk_emoji = "🟢" if risk['risk_level'] == "LOW" else "🟡" if risk['risk_level'] == "MEDIUM" else "🔴"
        lines.append(f"{risk_emoji} Route Risk Analysis: {risk['route']}")
        lines.append(f"Risk Level: {risk['risk_level']} (Score: {risk['risk_score']}/20)")
        lines.append(f"Estimated Delay: {risk['estimated_delay_hours']} hours")
        lines.append(f"Weather: {risk['weather_condition'].title()} (via {risk['weather_source']})")
        lines.append(f"Time: {risk['time_of_day'].title()} on {risk['day_of_week'].title()}")
        
        if risk.get('alternate_route'):
            lines.append("")
            lines.append(f"⚠️  High Risk - Alternate Route Suggested:")
            lines.append(f"   {risk['alternate_route']['alternate']}")
            lines.append(f"   Extra Time: +{risk['alternate_route']['extra_time_hours']} hours")
        
        return "\n".join(lines)

    if intent == "trust":
        return "I can compute transporter reliability if you provide metrics such as on_time_rate, avg_delay_hours, rating and total_trips. Use /trust-score for a detailed score."

    if intent == "match":
        return "I can help route and freight matching, but this chat currently focuses on route risk and demand forecasting. Please specify origin and destination for a risk or forecast analysis."

    return "Please specify a route, for example: 'Mumbai to Pune' or 'Forecast demand for Pune to Delhi'."

# Load the engine modules
try:
    empty_capacity_optimizer = load_module("empty_capacity_optimizer", "Empty Capacity Optimizer.py")
    freight_matching_engine = load_module("freight_matching_engine", "Freight Matching Engine.py")
    route_risk_engine = load_module("route_risk_engine", "Route Risk Engine.py")
    trust_reliability_engine = load_module("trust_reliability_engine", "Trust & Reliability Engine.py")
    demand_forecasting_engine = load_module("demand_forecasting_engine", "Demand Forecasting Engine.py")
    print("All engine modules loaded successfully!")
except Exception as e:
    print(f"Error loading modules: {e}")

@app.route('/')
def home():
    try:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(dir_path, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error serving index.html: {e}")
    return jsonify({
        "status": "TransitOS ML API running",
        "description": "Please create index.html in the same directory to view the dashboard."
    })

@app.route('/<path:path>')
def serve_static(path):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(dir_path, path)

@app.route('/match', methods=['POST'])
def match():
    data = request.json or {}
    weight = float(data.get('weight', 2500))
    pickup = data.get('pickup', 'Pune')
    dropoff = data.get('dropoff', 'Mumbai')
    pickup_lat = float(data.get('pickup_lat', 18.52))
    pickup_lng = float(data.get('pickup_lng', 73.85))
    
    freight = {
        "weight": weight,
        "pickup": pickup,
        "dropoff": dropoff,
        "pickup_lat": pickup_lat,
        "pickup_lng": pickup_lng
    }
    
    client_trucks = data.get('trucks', freight_matching_engine.trucks)
    
    try:
        raw_results = freight_matching_engine.freight_matching(client_trucks, freight)
        matched_trucks = []
        for score, truck_id in raw_results:
            truck_detail = next((t for t in client_trucks if t["id"] == truck_id), None)
            if truck_detail:
                distance = freight_matching_engine.calculate_distance(
                    truck_detail["lat"], truck_detail["lng"],
                    pickup_lat, pickup_lng
                )
                matched_trucks.append({
                    "id": truck_detail["id"],
                    "score": score,
                    "lat": truck_detail["lat"],
                    "lng": truck_detail["lng"],
                    "capacity": truck_detail["capacity"],
                    "route": truck_detail["route"],
                    "reliability": truck_detail["reliability"],
                    "distance_to_pickup": round(distance * 100, 1)  # scaling distance factor for visualization
                })
        return jsonify({
            "status": "success",
            "freight": freight,
            "matches": matched_trucks
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/optimize-capacity', methods=['POST'])
def optimize():
    data = request.json or {}
    truck_data = data.get('truck', {})
    shipments_data = data.get('pending_shipments', [])
    
    try:
        # Route
        truck_route = empty_capacity_optimizer.Route(
            origin=truck_data.get('origin', 'Pune'),
            destination=truck_data.get('destination', 'Delhi')
        )
        
        # Parse Time
        try:
            dep_time = datetime.fromisoformat(truck_data.get('departure_time', '2025-06-15T08:00:00'))
        except ValueError:
            dep_time = datetime(2025, 6, 15, 8, 0)
            
        truck = empty_capacity_optimizer.Truck(
            truck_id=truck_data.get('truck_id', 'TRK-PNQ-DEL-042'),
            free_capacity_kg=float(truck_data.get('free_capacity_kg', 400)),
            route=truck_route,
            departure_time=dep_time,
            base_trip_cost_inr=float(truck_data.get('base_trip_cost_inr', 12000)),
            distance_km=float(truck_data.get('distance_km', 0.0))
        )
        
        shipments = []
        for s in shipments_data:
            s_route = empty_capacity_optimizer.Route(
                origin=s.get('origin', 'Pune'),
                destination=s.get('destination', 'Delhi')
            )
            
            try:
                earliest_dt = datetime.fromisoformat(s.get('earliest_time', '2025-06-15T06:00:00'))
                latest_dt = datetime.fromisoformat(s.get('latest_time', '2025-06-15T12:00:00'))
            except ValueError:
                earliest_dt = dep_time - timedelta(hours=2)
                latest_dt = dep_time + timedelta(hours=4)
                
            shipment = empty_capacity_optimizer.Shipment(
                shipment_id=s.get('shipment_id'),
                description=s.get('description', 'Cargo'),
                weight_kg=float(s.get('weight_kg', 100)),
                route=s_route,
                time_window=empty_capacity_optimizer.TimeWindow(earliest_dt, latest_dt),
                standalone_cost_inr=float(s.get('standalone_cost_inr', 5000)),
                priority=int(s.get('priority', 1))
            )
            shipments.append(shipment)
            
        result = empty_capacity_optimizer.optimize_empty_capacity(truck, shipments)
        
        selected_serialized = []
        for s in result.selected:
            selected_serialized.append({
                "shipment_id": s.shipment_id,
                "description": s.description,
                "weight_kg": s.weight_kg,
                "priority": s.priority,
                "standalone_cost_inr": s.standalone_cost_inr
            })
            
        return jsonify({
            "status": "success",
            "total_weight_kg": result.total_weight_kg,
            "utilisation_pct": result.utilisation_pct,
            "cost_split": result.cost_split,
            "co2_saved_kg": result.co2_saved_kg,
            "trips_replaced": result.trips_replaced,
            "total_revenue_inr": result.total_revenue_inr,
            "selected": selected_serialized
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/route-risk', methods=['GET', 'POST'])
def route_risk():
    if request.method == 'POST':
        data = request.json or {}
    else:
        data = request.args or {}

    origin = data.get('origin', 'Mumbai')
    destination = data.get('destination', 'Pune')
    time_of_day = data.get('time_of_day', 'night')
    day_of_week = data.get('day_of_week', 'friday')
    api_key = data.get('weather_api_key') or data.get('api_key') or "e0483c3ca58bcc0079b9cda57f0f8821"
    
    try:
        engine = route_risk_engine.RouteRiskEngine(api_key)
        result = engine.assess_route_risk(origin, destination, time_of_day, day_of_week)
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/copilot', methods=['GET'])
def copilot_page():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'copilot.html')

@app.route('/copilot-chat', methods=['POST'])
def copilot_chat():
    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({"status": "error", "message": "Prompt text is required."}), 400
    response_text = generate_copilot_response(prompt)
    return jsonify({"status": "success", "response": response_text})

@app.route('/trust-score', methods=['POST'])
def trust_score():
    data = request.json or {}
    try:
        metrics = trust_reliability_engine.TransporterMetrics(
            on_time_rate=float(data.get('on_time_rate', 90.0)),
            cancellation_rate=float(data.get('cancellation_rate', 0.0)),
            avg_delay_hours=float(data.get('avg_delay_hours', 0.0)),
            rating=float(data.get('rating', 4.0)),
            total_trips=int(data.get('total_trips', 100))
        )
        result = trust_reliability_engine.compute_reliability_score(metrics)
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    if request.method == 'POST':
        data = request.json or {}
    else:
        data = request.args or {}
        
    route_str = data.get('route', 'Mumbai-Pune')
    origin, destination = parse_route_string(route_str)

    start_date_str = data.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.split('T')[0])
        except ValueError:
            start_date = datetime.now()
    else:
        start_date = datetime.now()
        
    is_festival = data.get('is_festival')
    if isinstance(is_festival, str):
        is_festival = is_festival.lower() in ('true', '1', 'yes')
    else:
        is_festival = bool(is_festival)
        
    season = data.get('season', 'summer')
    
    try:
        engine = demand_forecasting_engine.DemandForecastingEngine()
        result = engine.forecast_7_days(
            origin=origin,
            destination=destination,
            start_date=start_date,
            is_festival=is_festival,
            season=season
        )
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    print("Starting server on http://127.0.0.1:5000...")
    app.run(debug=True, port=5000)
