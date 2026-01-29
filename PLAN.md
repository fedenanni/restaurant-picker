# Restaurant Picker Website - Implementation Plan

## Overview
A simple web app that picks a random letter, lets users choose a country starting with that letter, then finds nearby restaurants serving that country's cuisine.

## Tech Stack
| Component | Choice | Why |
|-----------|--------|-----|
| Backend | **FastAPI** | Simple, modern Python, auto API docs |
| Frontend | **Single HTML + vanilla JS** | No build step, truly simple |
| Restaurant API | **Google Places API** | Best coverage, returns Maps links directly |
| Geocoding | **Google Geocoding API** | Convert address to lat/lng |

## File Structure
```
restaurant-picker/
├── main.py                 # FastAPI app (all backend logic)
├── pyproject.toml          # Dependencies
├── templates/
│   └── index.html          # Single-page frontend
├── data/
│   └── countries.json      # Country → cuisine mapping
├── static/
│   └── style.css           # Minimal styling (optional)
├── .env                    # API key (gitignored)
└── README.md
```

## API Endpoints
```
GET  /                       # Serve HTML page
GET  /api/random-letter      # Returns random A-Z
GET  /api/countries/{letter} # Returns countries for that letter
POST /api/search             # Find restaurants (cuisine, address, radius)
```

## User Flow
```
[Pick Random Letter] or [Enter Letter]
         ↓
[Select Country] → Dropdown (e.g., Japan, Jamaica...)
         ↓
[Enter Location] → "London, UK"
[Set Radius] → Slider 1-25 km
         ↓
[Find Restaurants!]
         ↓
[Results] → List with Google Maps links
         ↓
   (if empty)
         ↓
[No results] → [Try Different Country] [Expand Radius]
```

## Example Flow
1. Pick letter "I" (random or manual input)
2. Select "Italy" from the dropdown
3. Enter location: "London, UK" with 5km radius
4. Get list of Italian restaurants with Google Maps links
5. If none found → buttons to "Try different country" or "Expand radius"

## Implementation Steps

### Phase 1: Setup
1. Update `pyproject.toml` with dependencies:
   - fastapi, uvicorn, httpx, python-dotenv, jinja2
2. Create folder structure: `templates/`, `data/`, `static/`
3. Create `.env` with `GOOGLE_API_KEY=your_key`

### Phase 2: Country Data
4. Create `data/countries.json` mapping letters to countries/cuisines:
   ```json
   {
     "A": [{"country": "Argentina", "cuisine": "Argentinian restaurant"}, ...],
     "I": [{"country": "Italy", "cuisine": "Italian restaurant"}, ...],
     "J": [{"country": "Japan", "cuisine": "Japanese restaurant"}, ...]
   }
   ```

### Phase 3: Backend
5. Implement FastAPI app in `main.py`:
   - Jinja2 templates setup
   - `/api/random-letter` endpoint
   - `/api/countries/{letter}` endpoint
   - Geocoding helper (address → lat/lng via Google Geocoding API)
   - `/api/search` endpoint (calls Google Places Text Search)

### Phase 4: Frontend
6. Create `templates/index.html`:
   - Letter picker section (random button + manual letter input)
   - Country dropdown (appears after letter is selected)
   - Location text input field
   - Radius slider (1-25 km, default 5km)
   - Search button
   - Results area showing restaurant cards with Google Maps links
   - "No results" state with fallback option buttons

### Phase 5: Polish
7. Handle edge cases:
   - Letters with few/no countries (X, Q) → auto-pick new letter or show message
   - No restaurants found → "Expand radius" / "Change country" buttons
   - Invalid address → helpful error message with format hint

## Google API Setup Required
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable these APIs:
   - **Places API (New)**
   - **Geocoding API**
4. Create an API key (Credentials → Create Credentials → API Key)
5. (Optional) Restrict the key by HTTP referrer for production
6. Free tier provides $200/month credit (~10,000 searches)

## Running the App
```bash
# Install dependencies
uv sync

# Set up your API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# Run the development server
uv run uvicorn main:app --reload

# Open in browser
# http://localhost:8000
```

## Verification Checklist
- [ ] Pick random letter → shows the letter
- [ ] Click letter or type one → dropdown shows countries starting with that letter
- [ ] Enter location + set radius → search works
- [ ] Results display restaurant name, address, rating
- [ ] Each result has clickable Google Maps link
- [ ] "No results" shows expand radius and change country options
- [ ] Expanding radius or changing country triggers new search
