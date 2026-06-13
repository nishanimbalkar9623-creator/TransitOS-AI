from dataclasses import dataclass

@dataclass
class TransporterMetrics:
    on_time_rate: float        # percent, 0-100
    cancellation_rate: float   # percent, 0-100 (not used directly but validated)
    avg_delay_hours: float     # hours (not used directly but validated)
    rating: float              # 1-5
    total_trips: int           # >=0

def compute_experience_bonus(total_trips: int) -> float:
    """
    Map total_trips to an experience bonus in the range 0-100 (percent scale).
    Adjust thresholds as desired for your fleet size.
    Example mapping:
      0 trips -> 0
      50 trips -> 25
      200 trips -> 60
      1000+ trips -> 100
    Returns a value between 0 and 100.
    """
    if total_trips <= 0:
        return 0.0
    if total_trips >= 1000:
        return 100.0
    # piecewise linear mapping
    if total_trips < 50:
        return (total_trips / 50.0) * 25.0
    if total_trips < 200:
        return 25.0 + ((total_trips - 50) / (200 - 50)) * (60.0 - 25.0)
    # 200..999 maps 60..100
    return 60.0 + ((total_trips - 200) / (1000 - 200)) * (100.0 - 60.0)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def compute_delay_penalty(avg_delay_hours: float) -> float:
    """
    Convert average delay into a penalty score on a 0-100 scale.
    Lower delays yield higher reliability contribution, while longer delays reduce score.
    """
    delay_hours = clamp(avg_delay_hours, 0.0, 10.0)
    return round(max(0.0, 100.0 - delay_hours * 10.0), 2)


def compute_reliability_score(metrics: TransporterMetrics) -> dict:
    """
    Uses a reliability formula that combines:
      - on-time performance
      - customer rating
      - cancellation/completion rate
      - transporter experience
      - average delay penalty
    """
    on_time = clamp(metrics.on_time_rate, 0.0, 100.0)
    cancel = clamp(metrics.cancellation_rate, 0.0, 100.0)
    rating = clamp(metrics.rating, 1.0, 5.0)
    trips = max(0, int(metrics.total_trips))
    avg_delay = max(0.0, float(metrics.avg_delay_hours))

    completion_rate = 100.0 - cancel
    rating_percent = ((rating - 1.0) / 4.0) * 100.0
    exp_bonus = compute_experience_bonus(trips)
    delay_penalty = compute_delay_penalty(avg_delay)

    w_on_time = 0.30
    w_rating = 0.25
    w_completion = 0.20
    w_experience = 0.15
    w_delay = 0.10

    score = (
        on_time * w_on_time +
        rating_percent * w_rating +
        completion_rate * w_completion +
        exp_bonus * w_experience +
        delay_penalty * w_delay
    )

    score = clamp(score, 0.0, 100.0)

    if score >= 85:
        badge = "GOLD"
    elif score >= 70:
        badge = "SILVER"
    else:
        badge = "BRONZE"

    return {
        "score": round(score, 2),
        "badge": badge,
        "components": {
            "on_time_rate": on_time,
            "rating": rating,
            "rating_percent": round(rating_percent, 2),
            "completion_rate": round(completion_rate, 2),
            "experience_bonus": round(exp_bonus, 2),
            "delay_penalty": round(delay_penalty, 2),
            "avg_delay_hours": round(avg_delay, 2),
            "weights": {
                "on_time": w_on_time,
                "rating": w_rating,
                "completion": w_completion,
                "experience": w_experience,
                "delay": w_delay
            }
        }
    }

# Example usage
if __name__ == "__main__":
    # Example transporter
    m = TransporterMetrics(
        on_time_rate=92.0,
        cancellation_rate=2.0,
        avg_delay_hours=1.2,
        rating=4.4,
        total_trips=320
    )

    result = compute_reliability_score(m)
    print("Reliability Score:", result["score"])
    print("Badge:", result["badge"])
    print("Components:", result["components"])