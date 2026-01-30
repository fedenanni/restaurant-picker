import json
import math
import os
import random
from datetime import datetime, timedelta
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
    recent_rating: float | None = None
    recent_review_count: int = 0
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


def calculate_recent_rating(reviews: list[dict]) -> tuple[float | None, int]:
    """Calculate average rating from reviews in the last 3 months."""
    if not reviews:
        return None, 0

    three_months_ago = datetime.now() - timedelta(days=90)
    recent_ratings = []

    for review in reviews:
        publish_time = review.get("publishTime")
        if publish_time:
            try:
                review_date = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
                if review_date.replace(tzinfo=None) >= three_months_ago:
                    if "rating" in review:
                        recent_ratings.append(review["rating"])
            except (ValueError, TypeError):
                continue

    if not recent_ratings:
        return None, 0

    return round(sum(recent_ratings) / len(recent_ratings), 1), len(recent_ratings)


def radius_to_bounds(lat: float, lng: float, radius_km: float) -> dict:
    """Convert a center point and radius to a bounding box rectangle."""
    # Earth's radius in km
    earth_radius_km = 6371.0
    # Calculate latitude delta (1 degree latitude ≈ 111 km)
    delta_lat = radius_km / 111.0
    # Calculate longitude delta (varies with latitude)
    delta_lng = radius_km / (111.0 * math.cos(math.radians(lat)))

    return {
        "low": {"latitude": lat - delta_lat, "longitude": lng - delta_lng},
        "high": {"latitude": lat + delta_lat, "longitude": lng + delta_lng},
    }


async def search_restaurants(
    cuisine: str, lat: float, lng: float, radius_meters: float
) -> list[Restaurant]:
    """Search for restaurants using Google Places API."""
    if not GOOGLE_API_KEY:
        return []

    radius_km = radius_meters / 1000.0
    bounds = radius_to_bounds(lat, lng, radius_km)

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.googleMapsUri,places.reviews",
    }
    body = {
        "textQuery": cuisine,
        "locationRestriction": {"rectangle": bounds},
        "maxResultCount": 10,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        data = response.json()

    if "error" in data:
        return []

    restaurants = []
    for place in data.get("places", []):
        reviews = place.get("reviews", [])
        recent_rating, recent_count = calculate_recent_rating(reviews)
        restaurants.append(
            Restaurant(
                name=place.get("displayName", {}).get("text", "Unknown"),
                address=place.get("formattedAddress", ""),
                rating=place.get("rating"),
                recent_rating=recent_rating,
                recent_review_count=recent_count,
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
