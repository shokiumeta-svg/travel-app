import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import travel_plan


PLACES = [
    {
        "id": "place-1",
        "displayName": {"text": "城址公園"},
        "formattedAddress": "長野県A市",
        "location": {"latitude": 36.1, "longitude": 138.1},
    },
    {
        "id": "place-2",
        "displayName": {"text": "美術館"},
        "formattedAddress": "長野県B市",
        "location": {"latitude": 36.2, "longitude": 138.2},
    },
]

ORIGIN = {
    "id": "origin",
    "displayName": {"text": "横浜"},
    "formattedAddress": "神奈川県横浜市",
    "location": {"latitude": 35.4, "longitude": 139.6},
}


def make_ai_response():
    plans = []
    for index in range(3):
        plans.append(
            {
                "plan_id": f"plan_{index + 1}",
                "title": f"テストプラン{index + 1}",
                "summary": "2日間のテスト旅行",
                "recommendation_reason": "実在する候補を巡ります。",
                "days": [
                    {
                        "schedule": [
                            {
                                "time": "08:00",
                                "type": "departure",
                                "name": "横浜",
                                "description": "出発",
                                "duration_minutes": None,
                            },
                            {
                                "time": "09:00",
                                "type": "spot",
                                "place_id": "place-1",
                                "name": "城址公園",
                                "description": "園内観光",
                                "duration_minutes": 90,
                            },
                            {
                                "time": "11:00",
                                "type": "spot",
                                "place_id": "invented-place",
                                "name": "存在しない観光地",
                                "description": "採用されない予定",
                                "duration_minutes": 60,
                            },
                        ]
                    },
                    {
                        "schedule": [
                            {
                                "time": "09:30",
                                "type": "spot",
                                "place_id": "place-2",
                                "name": "美術館",
                                "description": "作品鑑賞",
                                "duration_minutes": 120,
                            },
                            {
                                "time": "18:00",
                                "type": "arrival",
                                "name": "横浜",
                                "description": "到着",
                                "duration_minutes": None,
                            },
                        ]
                    },
                ],
            }
        )
    return {"plans": plans}


class TravelPlanServiceTest(unittest.TestCase):
    def test_integrated_response_is_normalized_and_route_failure_is_partial(self):
        request = SimpleNamespace(
            origin="横浜",
            destination="長野",
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 13),
            travelers=2,
            transportation="drive",
            budget=100_000,
            travel_style="sightseeing",
        )

        async def fake_search(query):
            if query == "横浜":
                return {"places": [ORIGIN]}
            return {"places": PLACES}

        async def fake_route(**kwargs):
            if kwargs["destination_lat"] == ORIGIN["location"]["latitude"]:
                raise RuntimeError("route unavailable")
            return {"routes": [{"duration": "7200s", "distanceMeters": 210_400}]}

        with (
            patch.object(travel_plan, "search_places", new=AsyncMock(side_effect=fake_search)),
            patch.object(travel_plan, "get_weather", new=AsyncMock(return_value={"daily": {}})),
            patch.object(travel_plan, "compute_route", new=AsyncMock(side_effect=fake_route)),
            patch.object(travel_plan, "generate_travel_plans", return_value=make_ai_response()),
        ):
            response = asyncio.run(travel_plan.create_travel_plan_data(request))

        self.assertEqual(len(response["plans"]), 3)
        for plan in response["plans"]:
            self.assertEqual([day["date"] for day in plan["days"]], ["2026-09-12", "2026-09-13"])
            self.assertEqual(plan["estimated_cost"], sum(plan["cost_breakdown"].values()))
            self.assertNotIn(
                "存在しない観光地",
                [item["name"] for day in plan["days"] for item in day["schedule"]],
            )
            self.assertTrue(plan["days"][0]["transportation"][0]["route_available"])
            failed_route = plan["days"][1]["transportation"][0]
            self.assertFalse(failed_route["route_available"])
            self.assertIsNone(failed_route["duration_minutes"])
            self.assertIsNone(failed_route["distance_km"])


if __name__ == "__main__":
    unittest.main()
