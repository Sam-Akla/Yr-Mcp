import httpx2
from geopy.geocoders import Nominatim


async def geocoding(user_agent, location: str | list[float]):
    geocoder = Nominatim(user_agent=user_agent)

    if location == str:
        geo_location = geocoder.geocode(location)
    elif location == list[float]:
        geo_location = geocoder.reverse(location)
