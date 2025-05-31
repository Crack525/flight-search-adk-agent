import logging
from vertexai.generative_models import FunctionDeclaration, Tool, Part # Assuming these are the correct imports for Vertex AI
from typing import Optional
import os
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- Sky Scrapper API Tool Definition ---
async def search_flights_sky_scrapper(
    originSkyId: str,
    destinationSkyId: str,
    originEntityId: str,
    destinationEntityId: str,
    departure_date: str,
    return_date: Optional[str] = None,
    cabinClass: str = "economy",
    adults: int = 1,
    sortBy: str = "best",
    currency: str = "USD",
    market: str = "en-US",
    countryCode: str = "US",
    preferences: Optional[list[str]] = None
):
    """
    Real: Searches for flights using the Sky Scrapper API (RapidAPI).
    """
    logger.info(f"SKY SCRAPPER called with: originSkyId={originSkyId}, destinationSkyId={destinationSkyId}, originEntityId={originEntityId}, destinationEntityId={destinationEntityId}, departure_date={departure_date}, return_date={return_date}, adults={adults}, cabinClass={cabinClass}, sortBy={sortBy}, currency={currency}, market={market}, countryCode={countryCode}, preferences={preferences}")
    api_key = os.getenv("FLIGHTS_SCRAPER_SKY_API_KEY")
    if not api_key:
        return {"error": "Sky Scrapper API key not set in .env"}
    url = f"https://sky-scrapper.p.rapidapi.com/api/v2/flights/searchFlights?originSkyId={originSkyId}&destinationSkyId={destinationSkyId}&originEntityId={originEntityId}&destinationEntityId={destinationEntityId}&cabinClass={cabinClass}&adults={adults}&sortBy={sortBy}&currency={currency}&market={market}&countryCode={countryCode}&date={departure_date}"
    if return_date:
        url += f"&returnDate={return_date}"
    headers = {
        "x-rapidapi-host": "sky-scrapper.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {"error": f"Sky Scrapper API error: {resp.text}"}
        data = resp.json()
        # Defensive: if data is a string, return error
        if not isinstance(data, dict):
            logger.error(f"Sky Scrapper API returned non-JSON or string: {data}")
            return {"error": f"Sky Scrapper API returned non-JSON or string: {data}"}
        # Defensive: if 'data' key is missing or not a list, log and return error
        if "data" not in data or not isinstance(data["data"], list):
            logger.error(f"Sky Scrapper API response missing 'data' list: {data}")
            return {"error": f"Sky Scrapper API response missing 'data' list: {data}"}
        flights = []
        for f in data.get("data", []):
            flights.append({
                "airline": f.get("airline", "N/A"),
                "origin": f.get("origin", "N/A"),
                "destination": f.get("destination", "N/A"),
                "departure_time": f.get("departureTime", "N/A"),
                "arrival_time": f.get("arrivalTime", "N/A"),
                "duration_hours": f.get("duration", None),
                "stops": f.get("stops", 0),
                "price_usd": f.get("price", None),
                "currency": f.get("currency", "USD"),
                "notes": f.get("flightNumber", "")
            })
        summary = f"Found {len(flights)} flights from {originSkyId} to {destinationSkyId} on {departure_date}."
        return {"flights": flights, "summary": summary}
    except Exception as e:
        logger.error(f"Sky Scrapper API exception: {e}")
        return {"error": f"Sky Scrapper API exception: {e}"}

# --- Sky Scrapper Location Lookup Tool Definition ---
def lookup_sky_scrapper_location(query: str):
    """
    Looks up Sky Scrapper Sky ID and entity ID for a given airport/city name or IATA code.
    Tries uppercase IATA, then title-case city name if IATA fails.
    Logs full API response for debugging.
    """
    logger.info(f"Looking up Sky Scrapper location for: {query}")
    api_key = os.getenv("FLIGHTS_SCRAPER_SKY_API_KEY")
    if not api_key:
        return {"error": "Sky Scrapper API key not set in .env"}
    tried = []
    # Try IATA code uppercased first
    queries = [query.strip().upper()]
    # If it's a 3-letter code, also try city name (title case, no code)
    if len(query.strip()) == 3 and query.isalpha():
        queries.append(query.strip().title())
    else:
        queries.append(query.strip().title())
    for q in queries:
        # Use the correct endpoint for airport/city lookup (with version prefix and locale)
        url = f"https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchAirport?query={q}&locale=en-US"
        headers = {
            "x-rapidapi-host": "sky-scrapper.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            logger.info(f"Sky Scrapper location lookup for '{q}' response: {resp.text}")
            if resp.status_code != 200:
                tried.append(q)
                continue
            data = resp.json()
            results = []
            for loc in data.get("data", []):
                results.append({
                    "name": loc.get("name"),
                    "iata": loc.get("iata"),
                    "skyId": loc.get("skyId"),
                    "entityId": loc.get("entityId"),
                    "type": loc.get("type")
                })
            if results:
                return {"results": results}
            tried.append(q)
        except Exception as e:
            logger.error(f"Sky Scrapper location lookup exception for '{q}': {e}")
            tried.append(q)
    return {"error": f"Sky Scrapper could not find location for: {query} (tried: {tried})"}

# --- Helper: Get Sky IDs and Entity IDs for origin/destination if only IATA or name is provided ---
def get_sky_ids_for_airports(origin: str, destination: str):
    """
    Given origin and destination as IATA code or city/airport name, returns dict with skyId/entityId for both.
    """
    origin_info = lookup_sky_scrapper_location(origin)
    destination_info = lookup_sky_scrapper_location(destination)
    if "error" in origin_info or not origin_info.get("results"):
        return {"error": f"Could not find Sky Scrapper location for origin: {origin}"}
    if "error" in destination_info or not destination_info.get("results"):
        return {"error": f"Could not find Sky Scrapper location for destination: {destination}"}
    # Take the first result for each (could be improved with better matching)
    o = origin_info["results"][0]
    d = destination_info["results"][0]
    return {
        "originSkyId": o["skyId"],
        "originEntityId": o["entityId"],
        "destinationSkyId": d["skyId"],
        "destinationEntityId": d["entityId"]
    }

# --- Vertex AI Tool Configuration ---
search_flights_tool_declaration = FunctionDeclaration(
    name='search_flights',
    description='Searches for flights using the Sky Scrapper API. Accepts IATA code or city/airport name for origin and destination.',
    parameters={
        "type": "object",
        "properties": {
            'origin': {"type": "string", "description": 'The origin airport/city (IATA code or name, e.g., "FRA" or "Frankfurt").'},
            'destination': {"type": "string", "description": 'The destination airport/city (IATA code or name, e.g., "DAC" or "Dhaka").'},
            'departure_date': {"type": "string", "description": 'The departure date in YYYY-MM-DD format.'},
            'return_date': {"type": "string", "description": 'The return date in YYYY-MM-DD format. Empty or null if one-way.'},
            'cabinClass': {"type": "string", "description": 'Cabin class (e.g., "economy").', "default": "economy"},
            'adults': {"type": "integer", "description": 'Number of adults.', "default": 1},
            'sortBy': {"type": "string", "description": 'Sort by (e.g., "best").', "default": "best"},
            'currency': {"type": "string", "description": 'Currency code (e.g., "USD").', "default": "USD"},
            'market': {"type": "string", "description": 'Market (e.g., "en-US").', "default": "en-US"},
            'countryCode': {"type": "string", "description": 'Country code (e.g., "US").', "default": "US"},
            'preferences': {
                "type": "array",
                "items": {"type": "string"},
                "description": 'List of user preferences (e.g., "cheapest", "non-stop", "business class").'
            }
        },
        "required": ['origin', 'destination', 'departure_date']
    }
)

SEARCH_FLIGHTS_VERTEX_TOOL = Tool(
    function_declarations=[search_flights_tool_declaration]
)

# --- Google Flights (SerpApi) Tool Definition ---
async def search_google_flights_serpapi(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    currency: str = "USD",
    hl: str = "en",
    gl: str = "us",
    preferences: Optional[list[str]] = None
):
    """
    Searches for flights using SerpApi's Google Flights API.
    """
    logger.info(f"SERPAPI Google Flights called with: origin={origin}, destination={destination}, departure_date={departure_date}, return_date={return_date}, adults={adults}, currency={currency}, hl={hl}, gl={gl}, preferences={preferences}")
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"error": "SerpApi API key not set in .env"}
    params = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "adults": adults,
        "currency": currency,
        "hl": hl,
        "gl": gl,
        "output": "json"
    }
    if return_date:
        params["return_date"] = return_date
        params["type"] = 1  # round trip
    else:
        params["type"] = 2  # one way
    # Optionally add preferences mapping here
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
        if resp.status_code != 200:
            return {"error": f"SerpApi error: {resp.text}"}
        data = resp.json()
        if data.get("search_metadata", {}).get("status") != "Success":
            return {"error": f"SerpApi search failed: {data.get('search_metadata', {}).get('status', 'Unknown error')}"}
        # Parse best_flights and other_flights into unified format
        flights = []
        for group in (data.get("best_flights", []) + data.get("other_flights", [])):
            for f in group.get("flights", []):
                flights.append({
                    "airline": f.get("airline", "N/A"),
                    "origin": f.get("departure_airport", {}).get("id", "N/A"),
                    "destination": f.get("arrival_airport", {}).get("id", "N/A"),
                    "departure_time": f.get("departure_airport", {}).get("time", "N/A"),
                    "arrival_time": f.get("arrival_airport", {}).get("time", "N/A"),
                    "duration_hours": round(f.get("duration", 0) / 60, 2) if f.get("duration") else None,
                    "stops": len(group.get("layovers", [])),
                    "price_usd": group.get("price"),
                    "currency": currency,
                    "notes": f.get("flight_number", "")
                })
        summary = f"Found {len(flights)} flights from {origin} to {destination} on {departure_date} (Google Flights)."
        return {"flights": flights, "summary": summary}
    except Exception as e:
        logger.error(f"SerpApi Google Flights exception: {e}")
        return {"error": f"SerpApi Google Flights exception: {e}"}

# --- Google Flights Tool Declaration ---
search_google_flights_tool_declaration = FunctionDeclaration(
    name='search_google_flights',
    description='Searches for flights using Google Flights via SerpApi. Accepts IATA code for origin and destination.',
    parameters={
        "type": "object",
        "properties": {
            'origin': {"type": "string", "description": 'The origin airport/city (IATA code, e.g., "FRA").'},
            'destination': {"type": "string", "description": 'The destination airport/city (IATA code, e.g., "DAC").'},
            'departure_date': {"type": "string", "description": 'The departure date in YYYY-MM-DD format.'},
            'return_date': {"type": "string", "description": 'The return date in YYYY-MM-DD format. Empty or null if one-way.'},
            'adults': {"type": "integer", "description": 'Number of adults.', "default": 1},
            'currency': {"type": "string", "description": 'Currency code (e.g., "USD").', "default": "USD"},
            'hl': {"type": "string", "description": 'Language code (e.g., "en").', "default": "en"},
            'gl': {"type": "string", "description": 'Country code (e.g., "us").', "default": "us"},
            'preferences': {
                "type": "array",
                "items": {"type": "string"},
                "description": 'List of user preferences (e.g., "cheapest", "non-stop", "business class").'
            }
        },
        "required": ['origin', 'destination', 'departure_date']
    }
)

SEARCH_GOOGLE_FLIGHTS_VERTEX_TOOL = Tool(
    function_declarations=[search_google_flights_tool_declaration]
)

# --- Unified Flight Search: Accepts IATA or name, does lookup, then searches flights ---
async def unified_search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    cabinClass: str = "economy",
    adults: int = 1,
    sortBy: str = "best",
    currency: str = "USD",
    market: str = "en-US",
    countryCode: str = "US",
    preferences: Optional[list[str]] = None
):
    """
    Accepts IATA code or name for origin/destination, does lookup, then calls Sky Scrapper search.
    """
    ids = get_sky_ids_for_airports(origin, destination)
    if "error" in ids:
        return {"error": ids["error"]}
    return await search_flights_sky_scrapper(
        originSkyId=ids["originSkyId"],
        destinationSkyId=ids["destinationSkyId"],
        originEntityId=ids["originEntityId"],
        destinationEntityId=ids["destinationEntityId"],
        departure_date=departure_date,
        return_date=return_date,
        cabinClass=cabinClass,
        adults=adults,
        sortBy=sortBy,
        currency=currency,
        market=market,
        countryCode=countryCode,
        preferences=preferences
    )

AVAILABLE_FLIGHT_TOOLS = {
    # Use unified_search_flights so users can provide IATA or name, no entity IDs needed
    "search_flights": unified_search_flights,
    "search_google_flights": search_google_flights_serpapi,
}
