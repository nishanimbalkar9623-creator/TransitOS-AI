


trucks = [
    {
        "id": "TRK001",
        "lat": 18.52,
        "lng": 73.85,
        "capacity": 5000,
        "route": ["Pune", "Mumbai"],
        "reliability": 90
    },
    {
        "id": "TRK002",
        "lat": 19.07,
        "lng": 72.87,
        "capacity": 7000,
        "route": ["Mumbai", "Surat"],
        "reliability": 85
    },
    {
        "id": "TRK003",
        "lat": 18.60,
        "lng": 73.90,
        "capacity": 3000,
        "route": ["Pune", "Nashik"],
        "reliability": 95
    },
    {
        "id": "TRK004",
        "lat": 18.52,
        "lng": 73.85,
        "capacity": 4000,
        "route": ["Pune", "Chennai"],
        "reliability": 92
    },
    {
        "id": "TRK005",
        "lat": 18.52,
        "lng": 73.85,
        "capacity": 6000,
        "route": ["Pune", "Delhi"],
        "reliability": 88
    }
]



#__________________________________
freight = {
    "weight": 2500,
    "pickup": "Pune",
    "dropoff": "Mumbai",
    "pickup_lat": 18.52,
    "pickup_lng": 73.85
}


import math

# Euclidean Distance
def calculate_distance(lat1, lng1, lat2, lng2):
    return math.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2)


def freight_matching(trucks, freight):

    ranked_trucks = []

    for truck in trucks:

        # Capacity Check
        if truck["capacity"] < freight["weight"]:
            continue

        # Capacity Fit Score (0-100)
        capacity_fit = (
            freight["weight"] / truck["capacity"]
        ) * 100

        # Distance Score
        distance = calculate_distance(
            truck["lat"],
            truck["lng"],
            freight["pickup_lat"],
            freight["pickup_lng"]
        )

        distance_score = max(0, 100 - distance * 100)

        # Reliability Score
        reliability_score = truck["reliability"]

        # Route Overlap
        overlap = 0

        if freight["pickup"] in truck["route"]:
            overlap += 50

        if freight["dropoff"] in truck["route"]:
            overlap += 50

        route_overlap = overlap

        # Final Weighted Score
        score = (
            capacity_fit * 0.35 +
            distance_score * 0.30 +
            reliability_score * 0.25 +
            route_overlap * 0.10
        )

        ranked_trucks.append(
            (round(score, 2), truck["id"])
        )

    # Sort Descending
    ranked_trucks.sort(reverse=True)

    return ranked_trucks[:3]
result = freight_matching(trucks, freight)

for rank, truck in enumerate(result, start=1):
    print(rank, truck)






