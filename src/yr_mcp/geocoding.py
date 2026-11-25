from typing import TypedDict

import httpx2
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
from geopy.location import Location


async def geocoding(
    user_agent: str,
    location: str | tuple[float, float],
) -> Location | None:

    async with Nominatim(
        user_agent=user_agent,
        adapter_factory=AioHTTPAdapter,
    ) as geocoder:
        match location:
            case str():
                return await geocoder.geocode(location)

            case (latitude, longitude):
                return await geocoder.reverse((latitude, longitude))

            case _:
                raise ValueError("Invalid location")


class GeocodingResult(TypedDict):
    latitude: float
    longitude: float
    source: str


import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from cachetools import TTLCache
from geopy.adapters import AioHTTPAdapter
from geopy.exc import (
    GeocoderRateLimited,
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.extra.rate_limiter import AsyncRateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------


class GeocodingResult(BaseModel):
    """Provider-independent geocoding response."""

    model_config = ConfigDict(frozen=True)

    address: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    attribution: str = "© OpenStreetMap contributors"


class Coordinates(BaseModel):
    """Validated geographical coordinates."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------


class GeocodingError(Exception):
    """Base exception for geocoding failures."""


class GeocodingTimeoutError(GeocodingError):
    """The geocoding request timed out."""


class GeocodingUnavailableError(GeocodingError):
    """The geocoding service is unavailable."""


class GeocodingRateLimitError(GeocodingError):
    """The provider's rate limit has been exceeded."""


# ------------------------------------------------------------------
# Geocoding service
# ------------------------------------------------------------------


class GeocodingService:
    """Asynchronous geocoding service backed by Nominatim."""

    def __init__(
        self,
        geocoder: Nominatim,
        cache_size: int = 1024,
        cache_ttl: int = 86400,
    ) -> None:
        self._geocoder = geocoder

        self._lock = asyncio.Lock()

        self._forward_cache = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl,
        )

        self._reverse_cache = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl,
        )

        # Shared rate limiter for both operations.
        self._rate_limiter = AsyncRateLimiter(
            self._execute,
            min_delay_seconds=1.1,
            max_retries=0,
            swallow_exceptions=False,
        )

    @staticmethod
    def _to_result(location: Location) -> GeocodingResult:
        """Convert GeoPy's Location into our response model."""

        return GeocodingResult(
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
        )

    async def _execute(self, operation, *args, **kwargs):
        """Execute a geocoding request and handle provider errors."""

        try:
            return await operation(*args, **kwargs)

        except GeocoderRateLimited as exc:
            logger.warning("Geocoding rate limit exceeded")
            raise GeocodingRateLimitError("Geocoding rate limit exceeded") from exc

        except GeocoderTimedOut as exc:
            logger.warning("Geocoding request timed out")
            raise GeocodingTimeoutError("Geocoding request timed out") from exc

        except GeocoderUnavailable as exc:
            logger.warning("Geocoding service unavailable")
            raise GeocodingUnavailableError("Geocoding service unavailable") from exc

        except GeocoderServiceError as exc:
            logger.error("Geocoding service request failed")
            raise GeocodingError("Geocoding request failed") from exc

    async def geocode(
        self,
        query: str,
        *,
        limit: int = 5,
        country_code: str | None = None,
    ) -> list[GeocodingResult]:
        """
        Convert a place name or address into coordinates.

        Args:
            query: Place name or street address.
            limit: Maximum number of results.
            country_code: Optional ISO 3166-1 alpha-2 country code.

        Returns:
            A list of matching geographical locations.
            An empty list if no locations are found.
        """

        query = query.strip()

        if not query:
            raise ValueError("Location query cannot be empty")

        if not 1 <= limit <= 40:
            raise ValueError("Limit must be between 1 and 40")

        if country_code is not None:
            country_code = country_code.strip().lower()

            if (
                len(country_code) != 2
                or not country_code.isascii()
                or not country_code.isalpha()
            ):
                raise ValueError("Invalid country code format")

        cache_key = (
            query,
            limit,
            country_code,
        )

        async with self._lock:
            if cache_key in self._forward_cache:
                logger.debug("Forward geocoding cache hit")
                return list(self._forward_cache[cache_key])

            logger.debug("Executing forward geocoding request")

            locations = await self._rate_limiter(
                self._geocoder.geocode,
                query,
                exactly_one=False,
                limit=limit,
                country_codes=country_code,
            )

            results = [self._to_result(location) for location in (locations or [])]

            self._forward_cache[cache_key] = tuple(results)

            return results

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> GeocodingResult | None:
        """
        Convert geographical coordinates into an address.

        Args:
            latitude: Latitude between -90 and 90.
            longitude: Longitude between -180 and 180.

        Returns:
            The closest matching geographical location,
            or None if no location is found.
        """

        coordinates = Coordinates(
            latitude=latitude,
            longitude=longitude,
        )

        cache_key = (
            coordinates.latitude,
            coordinates.longitude,
        )

        async with self._lock:
            if cache_key in self._reverse_cache:
                logger.debug("Reverse geocoding cache hit")
                return self._reverse_cache[cache_key]

            logger.debug("Executing reverse geocoding request")

            location = await self._rate_limiter(
                self._geocoder.reverse,
                cache_key,
                exactly_one=True,
            )

            result = self._to_result(location) if location is not None else None

            self._reverse_cache[cache_key] = result

            return result


# ------------------------------------------------------------------
# Lifecycle management
# ------------------------------------------------------------------


@asynccontextmanager
async def create_geocoding_service(
    user_agent: str | None = None,
    domain: str | None = None,
    timeout: float = 10.0,
    cache_size: int = 1024,
    cache_ttl: int = 86400,
) -> AsyncIterator[GeocodingService]:
    """Create and manage the lifecycle of a geocoding service."""

    user_agent = user_agent or os.getenv("GEOCODING_USER_AGENT")
    domain = domain or os.getenv("GEOCODING_DOMAIN")

    if not user_agent:
        raise ValueError("GEOCODING_USER_AGENT must be configured")

    if not domain:
        raise ValueError("GEOCODING_DOMAIN must be configured")

    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    if cache_size <= 0 or cache_ttl <= 0:
        raise ValueError("Cache settings must be positive")

    async with Nominatim(
        user_agent=user_agent,
        domain=domain,
        timeout=timeout,
        adapter_factory=AioHTTPAdapter,
    ) as geocoder:
        logger.info("Geocoding service initialized")

        try:
            yield GeocodingService(
                geocoder=geocoder,
                cache_size=cache_size,
                cache_ttl=cache_ttl,
            )
        finally:
            logger.info("Geocoding service shutting down")
