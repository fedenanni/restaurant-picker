import json
import os
import random
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Restaurant Picker")

# Setup static files and templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Load country data
with open(BASE_DIR / "data" / "countries.json") as f:
    COUNTRIES = json.load(f)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class SearchRequest(BaseModel):
    cuisine: str
    address: str
    radius_km: float = 5.0


class Restaurant(BaseModel):
    name: str
    address: str
    rating: float | None = None
    maps_url: str


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/random-letter")
async def random_letter():
    """Return a random letter A-Z."""
    return {"letter": random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}


@app.get("/api/countries/{letter}")
async def get_countries(letter: str):
    """Return countries starting with the given letter."""
    letter = letter.upper()
    if letter not in COUNTRIES:
        raise HTTPException(status_code=400, detail="Invalid letter")
    return {"countries": COUNTRIES.get(letter, [])}


async def geocode_address(address: str) -> tuple[float, float] | None:
    """Convert an address to lat/lng coordinates using Google Geocoding API."""
    if not GOOGLE_API_KEY:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    if data.get("status") == "OK" and data.get("results"):
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return None


async def search_restaurants(
    cuisine: str, lat: float, lng: float, radius_meters: float
) -> list[Restaurant]:
    """Search for restaurants using Google Places API."""
    if not GOOGLE_API_KEY:
        return []

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.googleMapsUri",
    }
    body = {
        "textQuery": cuisine,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
        "maxResultCount": 10,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        data = response.json()

    if "error" in data:
        return []

    restaurants = []
    for place in data.get("places", []):
        restaurants.append(
            Restaurant(
                name=place.get("displayName", {}).get("text", "Unknown"),
                address=place.get("formattedAddress", ""),
                rating=place.get("rating"),
                maps_url=place.get("googleMapsUri", ""),
            )
        )
    return restaurants


@app.post("/api/search")
async def search(request: SearchRequest):
    """Search for restaurants based on cuisine, location, and radius."""
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Google API key not configured. Please set GOOGLE_API_KEY in .env file.",
        )

    # Geocode the address
    coords = await geocode_address(request.address)
    if not coords:
        raise HTTPException(
            status_code=400,
            detail="Could not find location. Try a format like 'London, UK' or 'New York, USA'.",
        )

    lat, lng = coords
    radius_meters = request.radius_km * 1000

    # Search for restaurants
    restaurants = await search_restaurants(
        request.cuisine, lat, lng, radius_meters
    )

    return {
        "success": True,
        "restaurants": [r.model_dump() for r in restaurants],
        "count": len(restaurants),
        "location": {"lat": lat, "lng": lng},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
