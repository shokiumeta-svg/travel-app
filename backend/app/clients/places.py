import os

import httpx
from fastapi import HTTPException


PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


async def search_places(query: str):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_MAPS_API_KEY is not configured",
        )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location"
        ),
    }

    body = {
        "textQuery": query,
        "languageCode": "ja",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            PLACES_URL,
            headers=headers,
            json=body,
            timeout=10.0,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()