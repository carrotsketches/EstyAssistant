import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.credentials import load_credentials
from etsy_assistant.etsy_api import EtsyCredentials, _api_headers, ETSY_API_BASE

import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


class ListingStats(BaseModel):
    listing_id: str
    title: str
    views: int
    favorites: int
    url: str | None = None


class AnalyticsResponse(BaseModel):
    listings: list[ListingStats]
    total_views: int
    total_favorites: int


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics():
    """Fetch listing stats (views, favorites) from Etsy API."""
    creds_data = load_credentials()
    if not creds_data:
        raise HTTPException(status_code=401, detail="Etsy not connected")

    creds = EtsyCredentials(**creds_data)
    if not creds.shop_id:
        raise HTTPException(status_code=400, detail="No shop ID found")

    try:
        with httpx.Client() as http:
            resp = http.get(
                f"{ETSY_API_BASE}/shops/{creds.shop_id}/listings/active",
                headers=_api_headers(creds),
                params={"limit": 100},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Etsy API error: {e}") from e

    listings = []
    total_views = 0
    total_favorites = 0

    for item in data.get("results", []):
        views = item.get("views", 0)
        favs = item.get("num_favorers", 0)
        listings.append(ListingStats(
            listing_id=str(item["listing_id"]),
            title=item.get("title", ""),
            views=views,
            favorites=favs,
            url=item.get("url"),
        ))
        total_views += views
        total_favorites += favs

    # Sort by views descending
    listings.sort(key=lambda x: x.views, reverse=True)

    return AnalyticsResponse(
        listings=listings,
        total_views=total_views,
        total_favorites=total_favorites,
    )
