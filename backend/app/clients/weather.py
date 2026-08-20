import httpx
from fastapi import HTTPException


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(
    latitude: float,
    longitude: float,
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
        ],
        "timezone": "Asia/Tokyo",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            WEATHER_URL,
            params=params,
            timeout=10.0,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()