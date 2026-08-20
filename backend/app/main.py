from datetime import date
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
import os
import httpx
from app.clients.places import search_places
from app.clients.routes import compute_route
from app.clients.weather import get_weather
from app.clients.openai_client import generate_test_response
from app.services.travel_plan import create_travel_plan_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TravelPlanRequest(BaseModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)

    start_date: date
    end_date: date

    travelers: int = Field(ge=1)
    budget: int = Field(gt=0)

    transportation: Literal["transit", "drive", "auto"]

    travel_style: Literal[
        "sightseeing",
        "budget",
        "gourmet",
    ]

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")

        return self


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/travel-plans")
async def create_travel_plans(request: TravelPlanRequest):
    return await create_travel_plan_data(request)

@app.get("/api/test/places")
async def test_places():
    return await search_places("長野県 観光地")

@app.get("/api/test/routes")
async def test_routes():
    return await compute_route(
        origin_lat=36.238653,
        origin_lng=137.9688674,
        destination_lat=36.3392598,
        destination_lng=137.9084423,
        travel_mode="DRIVE",
    )

@app.get("/api/test/weather")
async def test_weather():
    return await get_weather(
        latitude=36.238653,
        longitude=137.9688674,
    )

@app.get("/api/test/openai")
def test_openai():
    return generate_test_response()