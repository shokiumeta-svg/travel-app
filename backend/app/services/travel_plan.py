from datetime import datetime, timedelta

from app.clients.openai_client import generate_travel_plans
from app.clients.places import search_places
from app.clients.routes import compute_route
from app.clients.weather import get_weather


# MVP用の概算単価。価格APIを導入した際は、この定数と計算関数を置き換える。
COST_RULES = {
    "budget": {
        "accommodation_per_person_per_night": 6_000,
        "food_per_person_per_meal": 900,
        "activity_per_person_per_spot": 700,
        "other_per_person_per_day": 400,
    },
    "sightseeing": {
        "accommodation_per_person_per_night": 9_000,
        "food_per_person_per_meal": 1_500,
        "activity_per_person_per_spot": 1_200,
        "other_per_person_per_day": 700,
    },
    "gourmet": {
        "accommodation_per_person_per_night": 10_000,
        "food_per_person_per_meal": 2_500,
        "activity_per_person_per_spot": 1_000,
        "other_per_person_per_day": 800,
    },
}

# 3案に少し幅を持たせる。すべての金額は下のPythonロジックで再計算する。
PLAN_COST_FACTORS = (0.9, 1.0, 1.1)
DRIVE_COST_PER_KM = 30
TRANSIT_COST_PER_PERSON_PER_KM = 20
FALLBACK_TRANSPORTATION_PER_PERSON_PER_DAY = 1_500
FALLBACK_TRANSPORTATION_PER_PERSON_PER_ROUTE = 1_000

ROUTE_MODES = {
    "drive": ("DRIVE", "drive"),
    "transit": ("TRANSIT", "transit"),
    "auto": ("DRIVE", "drive"),
}


def _place_name(place):
    display_name = place.get("displayName", {})
    if isinstance(display_name, dict):
        return display_name.get("text", "")
    return str(display_name or "")


def _public_place(place):
    return {
        "id": place.get("id", ""),
        "name": _place_name(place),
        "address": place.get("formattedAddress", ""),
    }


def _trip_dates(request):
    number_of_days = (request.end_date - request.start_date).days + 1
    return [request.start_date + timedelta(days=index) for index in range(number_of_days)]


def _round_to_hundred(value):
    return int(round(value / 100.0) * 100)


def _parse_minutes(value):
    if isinstance(value, (int, float)) and value >= 0:
        return int(round(value))

    if isinstance(value, str):
        value = value.strip()
        try:
            if value.endswith("s"):
                return int(round(float(value[:-1]) / 60))
            return int(round(float(value)))
        except ValueError:
            return None

    return None


def _normalize_route_response(route_response):
    routes = route_response.get("routes", []) if isinstance(route_response, dict) else []
    if not routes:
        return None, None

    route = routes[0]
    duration_minutes = _parse_minutes(route.get("duration"))
    distance_meters = route.get("distanceMeters")
    distance_km = None

    if isinstance(distance_meters, (int, float)):
        distance_km = round(distance_meters / 1000, 1)

    return duration_minutes, distance_km


def _minutes_from_time(value):
    try:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.hour * 60 + parsed.minute
    except (TypeError, ValueError):
        return None


def _time_from_minutes(value):
    # 日付をまたぐ無理な時刻を出さないよう、当日の最終時刻に収める。
    value = max(0, min(int(value), 23 * 60 + 59))
    return f"{value // 60:02d}:{value % 60:02d}"


def _candidate_for_item(item, places_by_id, places_by_name):
    place_id = item.get("place_id")
    if place_id and place_id in places_by_id:
        return places_by_id[place_id]

    name = str(item.get("name", "")).strip()
    return places_by_name.get(name)


def _fallback_schedule(day_index, number_of_days, request, selected_places, plan_index):
    schedule = []

    if day_index == 0:
        schedule.append(
            {
                "time": "08:00",
                "type": "departure",
                "name": request.origin,
                "description": "出発",
                "duration_minutes": None,
                "_location_key": "__origin__",
            }
        )

    if selected_places:
        place = selected_places[(day_index + plan_index) % len(selected_places)]
        schedule.append(
            {
                "time": "10:00" if day_index == 0 else "09:30",
                "type": "spot",
                "name": _place_name(place),
                "description": "観光を楽しみます。",
                "duration_minutes": 90,
                "place_id": place.get("id", ""),
                "_location_key": place.get("id", ""),
            }
        )

    if day_index == number_of_days - 1:
        schedule.append(
            {
                "time": "18:00",
                "type": "arrival",
                "name": request.origin,
                "description": "到着",
                "duration_minutes": None,
                "_location_key": "__origin__",
            }
        )

    return schedule


def _normalize_schedule(
    raw_schedule,
    day_index,
    number_of_days,
    request,
    selected_places,
    places_by_id,
    places_by_name,
    plan_index,
):
    schedule = []

    if isinstance(raw_schedule, list):
        for item in raw_schedule:
            if not isinstance(item, dict):
                continue

            item_type = str(item.get("type", "spot")).strip().lower()
            name = str(item.get("name", "")).strip()
            candidate = _candidate_for_item(item, places_by_id, places_by_name)

            # 観光地はGoogle Placesの候補に存在するものだけを採用する。
            if item_type == "spot":
                if candidate is None:
                    continue
                name = _place_name(candidate)

            normalized = {
                "time": str(item.get("time", "09:00")),
                "type": item_type,
                "name": name or "予定",
                "description": str(item.get("description", "")),
                "duration_minutes": _parse_minutes(item.get("duration_minutes")),
            }

            if candidate is not None:
                normalized["place_id"] = candidate.get("id", "")
                normalized["_location_key"] = candidate.get("id", "")
            elif name == request.origin or item_type in {"departure", "arrival"}:
                normalized["name"] = request.origin
                normalized["_location_key"] = "__origin__"

            schedule.append(normalized)

    if not schedule:
        return _fallback_schedule(
            day_index,
            number_of_days,
            request,
            selected_places,
            plan_index,
        )

    if day_index == 0 and schedule[0].get("_location_key") != "__origin__":
        schedule.insert(
            0,
            {
                "time": "08:00",
                "type": "departure",
                "name": request.origin,
                "description": "出発",
                "duration_minutes": None,
                "_location_key": "__origin__",
            },
        )

    if day_index == number_of_days - 1 and schedule[-1].get("_location_key") != "__origin__":
        schedule.append(
            {
                "time": "18:00",
                "type": "arrival",
                "name": request.origin,
                "description": "到着",
                "duration_minutes": None,
                "_location_key": "__origin__",
            }
        )

    return schedule


def _normalize_ai_plans(ai_result, request, selected_places):
    raw_plans = ai_result.get("plans", []) if isinstance(ai_result, dict) else []
    dates = _trip_dates(request)
    places_by_id = {place.get("id"): place for place in selected_places if place.get("id")}
    places_by_name = {_place_name(place): place for place in selected_places if _place_name(place)}
    plans = []

    for plan_index in range(3):
        raw_plan = raw_plans[plan_index] if plan_index < len(raw_plans) else {}
        if not isinstance(raw_plan, dict):
            raw_plan = {}

        raw_days = raw_plan.get("days", [])
        if not isinstance(raw_days, list):
            raw_days = []

        days = []
        for day_index, trip_date in enumerate(dates):
            raw_day = raw_days[day_index] if day_index < len(raw_days) else {}
            if not isinstance(raw_day, dict):
                raw_day = {}

            schedule = _normalize_schedule(
                raw_day.get("schedule", []),
                day_index,
                len(dates),
                request,
                selected_places,
                places_by_id,
                places_by_name,
                plan_index,
            )
            days.append(
                {
                    "day": day_index + 1,
                    "date": trip_date.isoformat(),
                    "schedule": schedule,
                    "transportation": [],
                }
            )

        plans.append(
            {
                "plan_id": str(raw_plan.get("plan_id") or f"plan_{plan_index + 1}"),
                "title": str(raw_plan.get("title") or f"旅行プラン {plan_index + 1}"),
                "summary": str(raw_plan.get("summary") or "入力条件に合わせた旅行プランです。"),
                "recommendation_reason": str(raw_plan.get("recommendation_reason") or ""),
                "days": days,
            }
        )

    return plans


async def _find_origin_place(origin):
    try:
        result = await search_places(origin)
        places = result.get("places", []) if isinstance(result, dict) else []
        return places[0] if places else None
    except Exception:
        # 出発地の座標が取れなくても、観光プラン自体は生成する。
        return None


async def _route_for_locations(from_place, to_place, google_mode):
    from_location = from_place.get("location", {}) if from_place else {}
    to_location = to_place.get("location", {}) if to_place else {}
    coordinates = (
        from_location.get("latitude"),
        from_location.get("longitude"),
        to_location.get("latitude"),
        to_location.get("longitude"),
    )

    if any(value is None for value in coordinates):
        return None, None, False

    try:
        response = await compute_route(
            origin_lat=coordinates[0],
            origin_lng=coordinates[1],
            destination_lat=coordinates[2],
            destination_lng=coordinates[3],
            travel_mode=google_mode,
        )
        duration_minutes, distance_km = _normalize_route_response(response)
        return duration_minutes, distance_km, duration_minutes is not None or distance_km is not None
    except Exception:
        # 区間単位の失敗として扱い、他の日程やプランの生成は続ける。
        return None, None, False


def _update_destination_time(schedule, from_index, to_index, duration_minutes):
    if duration_minutes is None:
        return

    departure_minutes = _minutes_from_time(schedule[from_index].get("time"))
    current_duration = schedule[from_index].get("duration_minutes") or 0
    destination_minutes = _minutes_from_time(schedule[to_index].get("time"))

    if departure_minutes is None:
        return

    earliest_arrival = departure_minutes + current_duration + duration_minutes
    if destination_minutes is None or destination_minutes < earliest_arrival:
        schedule[to_index]["time"] = _time_from_minutes(earliest_arrival)


async def _attach_routes(plans, request, selected_places, origin_place):
    google_mode, public_mode = ROUTE_MODES[request.transportation]
    place_lookup = {place.get("id"): place for place in selected_places if place.get("id")}
    place_lookup["__origin__"] = origin_place
    route_cache = {}

    for plan in plans:
        for day in plan["days"]:
            schedule = day["schedule"]
            located_items = [
                (index, item)
                for index, item in enumerate(schedule)
                if item.get("_location_key")
            ]

            for pair_index in range(len(located_items) - 1):
                from_index, from_item = located_items[pair_index]
                to_index, to_item = located_items[pair_index + 1]
                from_key = from_item["_location_key"]
                to_key = to_item["_location_key"]

                if from_key == to_key:
                    continue

                cache_key = (from_key, to_key, google_mode)
                if cache_key not in route_cache:
                    route_cache[cache_key] = await _route_for_locations(
                        place_lookup.get(from_key),
                        place_lookup.get(to_key),
                        google_mode,
                    )

                duration_minutes, distance_km, route_available = route_cache[cache_key]
                day["transportation"].append(
                    {
                        "from": from_item["name"],
                        "to": to_item["name"],
                        "mode": public_mode,
                        "duration_minutes": duration_minutes,
                        "distance_km": distance_km,
                        "route_available": route_available,
                        "from_schedule_index": from_index,
                        "to_schedule_index": to_index,
                    }
                )
                _update_destination_time(schedule, from_index, to_index, duration_minutes)


def _calculate_cost_breakdown(plan, request, plan_index):
    rules = COST_RULES[request.travel_style]
    factor = PLAN_COST_FACTORS[plan_index]
    number_of_days = len(plan["days"])
    nights = max(0, number_of_days - 1)
    meals = max(1, number_of_days * 3 - 2)
    spot_count = sum(
        1
        for day in plan["days"]
        for item in day["schedule"]
        if item.get("type") == "spot"
    )

    all_routes = [
        route
        for day in plan["days"]
        for route in day["transportation"]
    ]
    distances = [route["distance_km"] for route in all_routes if route.get("distance_km") is not None]
    unavailable_route_count = sum(
        1 for route in all_routes if route.get("distance_km") is None
    )
    total_distance_km = sum(distances)

    if distances:
        if request.transportation == "transit":
            transportation = total_distance_km * TRANSIT_COST_PER_PERSON_PER_KM * request.travelers
        else:
            transportation = total_distance_km * DRIVE_COST_PER_KM

        transportation += (
            unavailable_route_count
            * FALLBACK_TRANSPORTATION_PER_PERSON_PER_ROUTE
            * request.travelers
        )
    else:
        transportation = (
            FALLBACK_TRANSPORTATION_PER_PERSON_PER_DAY
            * number_of_days
            * request.travelers
        )

    breakdown = {
        "transportation": _round_to_hundred(transportation),
        "accommodation": _round_to_hundred(
            rules["accommodation_per_person_per_night"]
            * nights
            * request.travelers
            * factor
        ),
        "food": _round_to_hundred(
            rules["food_per_person_per_meal"]
            * meals
            * request.travelers
            * factor
        ),
        "activities": _round_to_hundred(
            rules["activity_per_person_per_spot"]
            * spot_count
            * request.travelers
            * factor
        ),
        "other": _round_to_hundred(
            rules["other_per_person_per_day"]
            * number_of_days
            * request.travelers
            * factor
        ),
    }
    return breakdown


def _finalize_plans(plans, request, selected_places):
    places_by_id = {place.get("id"): place for place in selected_places if place.get("id")}

    for plan_index, plan in enumerate(plans):
        used_place_ids = []
        for day in plan["days"]:
            for item in day["schedule"]:
                place_id = item.get("place_id")
                if place_id in places_by_id and place_id not in used_place_ids:
                    used_place_ids.append(place_id)
                item.pop("_location_key", None)

        if not used_place_ids:
            used_place_ids = list(places_by_id)[:3]

        plan["main_spots"] = [_public_place(places_by_id[place_id]) for place_id in used_place_ids]
        plan["cost_breakdown"] = _calculate_cost_breakdown(plan, request, plan_index)
        plan["estimated_cost"] = sum(plan["cost_breakdown"].values())

    return {"plans": plans}


async def create_travel_plan_data(request):
    places_data = await search_places(f"{request.destination} 観光地")
    places = places_data.get("places", [])

    if not places:
        return {
            "plans": [],
            "message": "観光地候補を取得できませんでした。",
        }

    selected_places = places[:6]
    first_location = selected_places[0].get("location", {})
    latitude = first_location.get("latitude")
    longitude = first_location.get("longitude")
    weather_data = {}

    if latitude is not None and longitude is not None:
        weather_data = await get_weather(latitude=latitude, longitude=longitude)

    # OpenAIは構成と説明を担当する。経路値と費用は、この後Python側で付与する。
    ai_result = generate_travel_plans(
        request=request,
        places=selected_places,
        weather=weather_data,
        routes=[],
    )
    plans = _normalize_ai_plans(ai_result, request, selected_places)
    origin_place = await _find_origin_place(request.origin)
    await _attach_routes(plans, request, selected_places, origin_place)
    return _finalize_plans(plans, request, selected_places)
