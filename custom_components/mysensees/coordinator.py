from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthError, MySenseesApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MySenseesDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate polling for MySensees gateway data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MySenseesApiClient,
        gateway_id: str,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{gateway_id}",
            update_interval=update_interval,
        )
        self.client = client
        self.gateway_id = gateway_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest gateway payload."""
        try:
            return await self.client.async_get_gateway(self.gateway_id)
        except (ApiError, AuthError) as err:
            raise UpdateFailed(str(err)) from err
