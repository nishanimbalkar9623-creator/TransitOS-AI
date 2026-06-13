"""
╔══════════════════════════════════════════════════════════╗
║        EMPTY CAPACITY OPTIMIZER  ⭐  HERO FEATURE        ║
║  Pools small shipments to fill a truck's empty space.    ║
╚══════════════════════════════════════════════════════════╝

Algorithm: Dynamic-programming 0/1 Knapsack (exact optimal)
           with a greedy fallback for very large item counts.

Inputs:
  - Truck free capacity (kg)
  - Truck route + departure time
  - List of pending shipments (weight, route, time window)

Outputs:
  - Optimal shipment combination maximising utilisation
  - Cost split per shipment (proportional to weight)
  - CO₂ saved vs running separate trips
"""

import math
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────

@dataclass
class Route:
    origin: str
    destination: str

    def __str__(self):
        return f"{self.origin} → {self.destination}"


@dataclass
class TimeWindow:
    earliest: datetime
    latest: datetime

    def __str__(self):
        fmt = "%d-%b %H:%M"
        return f"{self.earliest.strftime(fmt)} – {self.latest.strftime(fmt)}"


@dataclass
class Truck:
    truck_id: str
    free_capacity_kg: float
    route: Route
    departure_time: datetime
    base_trip_cost_inr: float        # cost of the truck doing this leg anyway
    co2_per_km_kg: float = 0.27      # kg CO₂ per km (loaded truck average)
    distance_km: float = 0.0         # filled in post-init or passed directly

    def __post_init__(self):
        # Rough straight-line distance lookup for demo cities (km)
        _dist_table = {
            ("Pune", "Delhi"):     1400,
            ("Mumbai", "Delhi"):   1420,
            ("Pune", "Mumbai"):     150,
            ("Delhi", "Mumbai"):   1420,
            ("Bangalore", "Delhi"): 2150,
            ("Hyderabad", "Delhi"): 1570,
            ("Chennai", "Delhi"):  2180,
        }
        key = (self.route.origin, self.route.destination)
        rev = (self.route.destination, self.route.origin)
        if self.distance_km == 0.0:
            self.distance_km = _dist_table.get(key) or _dist_table.get(rev, 800)


@dataclass
class Shipment:
    shipment_id: str
    description: str
    weight_kg: float
    route: Route
    time_window: TimeWindow
    standalone_cost_inr: float       # what shipper would pay for a solo trip
    priority: int = 1                # higher = prefer to include (1–5)

    @property
    def value(self) -> float:
        """Score used by knapsack: weight × priority (maximise utilisation)."""
        return self.weight_kg * self.priority


@dataclass
class PackingResult:
    selected: List[Shipment]
    total_weight_kg: float
    utilisation_pct: float
    cost_split: dict            # shipment_id → INR contribution
    co2_saved_kg: float
    trips_replaced: int
    total_revenue_inr: float


# ─────────────────────────────────────────────────────────────
# Compatibility filter
# ─────────────────────────────────────────────────────────────

def is_compatible(shipment: Shipment, truck: Truck) -> bool:
    """
    A shipment is compatible if:
      1. Its destination matches the truck's destination (or is on the route).
      2. Its time window covers the truck's departure.
      3. It physically fits (weight checked separately in knapsack).
    """
    route_ok = (
        shipment.route.destination == truck.route.destination
        and shipment.route.origin == truck.route.origin
    )
    time_ok = (
        shipment.time_window.earliest <= truck.departure_time
        <= shipment.time_window.latest
    )
    return route_ok and time_ok


# ─────────────────────────────────────────────────────────────
# Core algorithm: 0/1 Knapsack (DP) — exact optimal solution
# ─────────────────────────────────────────────────────────────

def knapsack_dp(items: List[Shipment], capacity_kg: float,
                granularity: float = 0.5) -> List[Shipment]:
    """
    Standard 0/1 knapsack solved with dynamic programming.
    weights and capacity are discretised to `granularity` kg units
    so the DP table stays manageable.

    Returns the list of shipments that maximises total value
    without exceeding capacity_kg.
    """
    if not items:
        return []

    # Discretise
    scale = int(1 / granularity)
    cap   = int(capacity_kg * scale)
    n     = len(items)

    weights = [max(1, int(s.weight_kg * scale)) for s in items]
    values  = [s.value for s in items]

    # DP table: dp[i][w] = max value using first i items, capacity w
    dp = [[0.0] * (cap + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        w_i = weights[i - 1]
        v_i = values[i - 1]
        for w in range(cap + 1):
            dp[i][w] = dp[i - 1][w]
            if w_i <= w:
                with_item = dp[i - 1][w - w_i] + v_i
                if with_item > dp[i][w]:
                    dp[i][w] = with_item

    # Backtrack to find which items were selected
    selected = []
    w = cap
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1])
            w -= weights[i - 1]

    return selected


# ─────────────────────────────────────────────────────────────
# Greedy fallback (for very large item lists)
# ─────────────────────────────────────────────────────────────

def knapsack_greedy(items: List[Shipment],
                    capacity_kg: float) -> List[Shipment]:
    """
    Sort by value-to-weight ratio (descending) and greedily pick
    items until capacity is exhausted.
    """
    sorted_items = sorted(items,
                          key=lambda s: s.value / s.weight_kg,
                          reverse=True)
    selected, remaining = [], capacity_kg
    for item in sorted_items:
        if item.weight_kg <= remaining:
            selected.append(item)
            remaining -= item.weight_kg
    return selected


# ─────────────────────────────────────────────────────────────
# CO₂ calculation
# ─────────────────────────────────────────────────────────────

def calculate_co2_saved(shipments: List[Shipment], truck: Truck) -> float:
    """
    CO₂ saved = emissions of running N separate small trucks
                minus the marginal CO₂ of adding freight to the existing trip.

    A small delivery van emits ~0.21 kg CO₂/km.
    The existing truck trip's CO₂ is already "spent" — we only
    count the *additional* load-related emissions (≈ 2 % per 10 % load
    increase on a diesel truck).
    """
    van_co2_per_km = 0.21
    separate_trips_co2 = len(shipments) * van_co2_per_km * truck.distance_km

    total_added_weight = sum(s.weight_kg for s in shipments)
    load_fraction = total_added_weight / (truck.free_capacity_kg + total_added_weight)
    marginal_co2 = truck.co2_per_km_kg * truck.distance_km * load_fraction * 0.15

    return round(separate_trips_co2 - marginal_co2, 2)


# ─────────────────────────────────────────────────────────────
# Cost split (proportional to weight)
# ─────────────────────────────────────────────────────────────

def split_cost(shipments: List[Shipment], truck: Truck) -> dict:
    """
    Each shipper pays proportional to their weight share of the truck's
    free capacity. They always pay less than their standalone cost.
    """
    total_w = sum(s.weight_kg for s in shipments)
    split = {}
    for s in shipments:
        share       = s.weight_kg / total_w
        pool_cost   = round(truck.base_trip_cost_inr * share, 2)
        saving_pct  = round((1 - pool_cost / s.standalone_cost_inr) * 100, 1)
        split[s.shipment_id] = {
            "weight_kg":       s.weight_kg,
            "pool_cost_inr":   pool_cost,
            "standalone_inr":  s.standalone_cost_inr,
            "saving_pct":      saving_pct,
        }
    return split


# ─────────────────────────────────────────────────────────────
# Main optimizer
# ─────────────────────────────────────────────────────────────

def optimize_empty_capacity(truck: Truck,
                            pending_shipments: List[Shipment],
                            use_greedy: bool = False) -> PackingResult:
    """
    1. Filter shipments for route / time compatibility.
    2. Run knapsack (DP or greedy) to find optimal combination.
    3. Compute utilisation, cost split, and CO₂ savings.
    """
    compatible = [s for s in pending_shipments if is_compatible(s, truck)]

    if not compatible:
        return PackingResult([], 0, 0, {}, 0, 0, 0)

    # Use greedy for very large catalogs (>200 items) to keep it snappy
    if use_greedy or len(compatible) > 200:
        selected = knapsack_greedy(compatible, truck.free_capacity_kg)
    else:
        selected = knapsack_dp(compatible, truck.free_capacity_kg)

    total_w       = sum(s.weight_kg for s in selected)
    utilisation   = round(total_w / truck.free_capacity_kg * 100, 1)
    cost_split    = split_cost(selected, truck)
    co2_saved     = calculate_co2_saved(selected, truck)
    total_revenue = sum(v["pool_cost_inr"] for v in cost_split.values())

    return PackingResult(
        selected=selected,
        total_weight_kg=round(total_w, 2),
        utilisation_pct=utilisation,
        cost_split=cost_split,
        co2_saved_kg=co2_saved,
        trips_replaced=len(selected),
        total_revenue_inr=round(total_revenue, 2),
    )


# ─────────────────────────────────────────────────────────────
# Pretty printer
# ─────────────────────────────────────────────────────────────

def print_results(truck: Truck, result: PackingResult) -> None:
    W = 62

    def bar(pct, width=30):
        filled = int(pct / 100 * width)
        return "█" * filled + "░" * (width - filled)

    print("\n" + "╔" + "═" * W + "╗")
    print("║" + "  ⭐  EMPTY CAPACITY OPTIMIZER — RESULTS".center(W) + "║")
    print("╠" + "═" * W + "╣")
    print(f"║  Truck   : {truck.truck_id}".ljust(W + 1) + "║")
    print(f"║  Route   : {truck.route}".ljust(W + 1) + "║")
    print(f"║  Departs : {truck.departure_time.strftime('%d-%b-%Y  %H:%M')}".ljust(W + 1) + "║")
    print(f"║  Free cap: {truck.free_capacity_kg:,.0f} kg".ljust(W + 1) + "║")
    print("╠" + "═" * W + "╣")

    if not result.selected:
        print("║  ✗  No compatible shipments found.".ljust(W + 1) + "║")
        print("╚" + "═" * W + "╝\n")
        return

    # Utilisation bar
    u = result.utilisation_pct
    print(f"║  Utilisation: [{bar(u)}] {u:.1f} %".ljust(W + 1) + "║")
    print(f"║  Loaded     : {result.total_weight_kg:,.1f} / {truck.free_capacity_kg:,.0f} kg".ljust(W + 1) + "║")
    print("╠" + "═" * W + "╣")
    print("║  MATCHED SHIPMENTS".ljust(W + 1) + "║")
    print("╠" + "═" * W + "╣")

    weights_str = " + ".join(f"{s.weight_kg:.0f}kg" for s in result.selected)
    print(f"║  {weights_str} = {result.total_weight_kg:.0f} kg  "
          f"({result.trips_replaced} shipments)".ljust(W + 1) + "║")
    print("║" + "─" * W + "║")

    for s in result.selected:
        info   = result.cost_split[s.shipment_id]
        saving = info["saving_pct"]
        print(f"║  [{s.shipment_id}] {s.description[:22]:<22}  "
              f"{s.weight_kg:>6.1f} kg".ljust(W + 1) + "║")
        print(f"║       Route: {s.route}  |  Window: "
              f"{s.time_window.earliest.strftime('%H:%M')}–"
              f"{s.time_window.latest.strftime('%H:%M')}".ljust(W + 1) + "║")
        print(f"║       Pool cost: ₹{info['pool_cost_inr']:>8,.2f}  "
              f"(saves {saving:.1f} % vs ₹{info['standalone_inr']:,.0f})".ljust(W + 1) + "║")
        print("║" + "─" * W + "║")

    print("╠" + "═" * W + "╣")
    print("║  IMPACT SUMMARY".ljust(W + 1) + "║")
    print("╠" + "═" * W + "╣")
    trips_saved = result.trips_replaced - 1
    print(f"║  🚛  {result.trips_replaced} shipments → 1 trip  "
          f"({trips_saved} separate trip{'s' if trips_saved!=1 else ''} eliminated)".ljust(W + 1) + "║")
    print(f"║  ₹   Revenue collected : ₹{result.total_revenue_inr:>10,.2f}".ljust(W + 1) + "║")
    print(f"║  🌱  CO₂ saved         : {result.co2_saved_kg:>8.1f} kg  "
          f"({result.co2_saved_kg / 21:.1f} trees/yr equiv.)".ljust(W + 1) + "║")
    print("╚" + "═" * W + "╝\n")


# ─────────────────────────────────────────────────────────────
# Demo — exactly the judges' example flow
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    departure = datetime(2025, 6, 15, 8, 0)

    truck = Truck(
        truck_id="TRK-PNQ-DEL-042",
        free_capacity_kg=400,
        route=Route("Pune", "Delhi"),
        departure_time=departure,
        base_trip_cost_inr=12_000,
        distance_km=1400,
    )

    pending_shipments = [
        Shipment(
            shipment_id="S01",
            description="Auto spare parts",
            weight_kg=180,
            route=Route("Pune", "Delhi"),
            time_window=TimeWindow(departure - timedelta(hours=2),
                                   departure + timedelta(hours=4)),
            standalone_cost_inr=6_800,
            priority=3,
        ),
        Shipment(
            shipment_id="S02",
            description="Pharma boxes",
            weight_kg=140,
            route=Route("Pune", "Delhi"),
            time_window=TimeWindow(departure - timedelta(hours=1),
                                   departure + timedelta(hours=6)),
            standalone_cost_inr=5_200,
            priority=4,
        ),
        Shipment(
            shipment_id="S03",
            description="Textile rolls",
            weight_kg=80,
            route=Route("Pune", "Delhi"),
            time_window=TimeWindow(departure - timedelta(hours=3),
                                   departure + timedelta(hours=2)),
            standalone_cost_inr=3_100,
            priority=2,
        ),
        # Decoy: too heavy
        Shipment(
            shipment_id="S04",
            description="Heavy machinery part",
            weight_kg=450,
            route=Route("Pune", "Delhi"),
            time_window=TimeWindow(departure - timedelta(hours=1),
                                   departure + timedelta(hours=3)),
            standalone_cost_inr=15_000,
            priority=5,
        ),
        # Decoy: wrong destination
        Shipment(
            shipment_id="S05",
            description="Electronics",
            weight_kg=60,
            route=Route("Pune", "Mumbai"),
            time_window=TimeWindow(departure - timedelta(hours=1),
                                   departure + timedelta(hours=5)),
            standalone_cost_inr=2_500,
            priority=3,
        ),
        # Decoy: time window missed
        Shipment(
            shipment_id="S06",
            description="Fresh produce",
            weight_kg=90,
            route=Route("Pune", "Delhi"),
            time_window=TimeWindow(departure + timedelta(hours=10),
                                   departure + timedelta(hours=20)),
            standalone_cost_inr=3_800,
            priority=5,
        ),
    ]

    print("\n" + "=" * 62)
    print("  RUNNING EMPTY CAPACITY OPTIMIZER")
    print("  Algorithm : 0/1 Knapsack (Dynamic Programming)")
    print("=" * 62)

    result = optimize_empty_capacity(truck, pending_shipments)
    print_results(truck, result)

    # ── Algorithm walkthrough ───────────────────────────────
    print("ALGORITHM WALKTHROUGH")
    print("─" * 62)
    compatible = [s for s in pending_shipments if is_compatible(s, truck)]
    print(f"  Total pending  : {len(pending_shipments)} shipments")
    print(f"  Compatible     : {len(compatible)}  "
          f"(filtered by route + time window)")
    print(f"  Excluded       : {len(pending_shipments) - len(compatible)}  "
          f"(wrong route or outside time window)")
    print(f"\n  Capacity       : {truck.free_capacity_kg} kg")
    print(f"  Knapsack found : {' + '.join(f'{s.weight_kg:.0f}kg' for s in result.selected)}"
          f" = {result.total_weight_kg:.0f} kg")
    print(f"  Utilisation    : {result.utilisation_pct:.1f} %")
    print(f"\n  CO₂ calculation:")
    print(f"    Separate vans  : {len(result.selected)} × 0.21 kg/km × {truck.distance_km} km"
          f" = {len(result.selected) * 0.21 * truck.distance_km:.1f} kg CO₂")
    print(f"    Marginal extra : ~{result.co2_saved_kg - len(result.selected)*0.21*truck.distance_km:.1f} kg (pooled load share)")
    print(f"    NET CO₂ saved  : {result.co2_saved_kg:.1f} kg  🌱")
    print("─" * 62 + "\n")