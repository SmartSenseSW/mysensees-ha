from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from aiohttp import ClientResponseError, ClientSession
import async_timeout

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


class MySenseesError(Exception):
    """Base exception for the MySensees client."""


class AuthError(MySenseesError):
    """Raised when authentication fails."""


class ApiError(MySenseesError):
    """Raised for generic API failures."""


@dataclass
class MySenseesApiClient:
    """Async API client for MySensees cloud endpoints."""

    session: ClientSession
    base_url: str
    username: str
    password: str
    token: str | None = None

    async def async_login(self) -> None:
        """Authenticate and store the bearer token."""
        url = f"{self.base_url.rstrip('/')}/api/login/jwt?cookie=&captcha="
        payload = {"username": self.username, "password": self.password}

        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                response = await self.session.post(url, json=payload)
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            _LOGGER.warning("MySensees login failed with HTTP %s for %s", err.status, url)
            if err.status in (401, 403):
                raise AuthError("Invalid username or password") from err
            raise ApiError(f"Login failed with status {err.status}") from err
        except TimeoutError as err:
            _LOGGER.warning("MySensees login timed out for %s", url)
            raise ApiError("Login timed out") from err
        except Exception as err:
            _LOGGER.exception("MySensees login request failed for %s", url)
            raise ApiError("Login request failed") from err

        token = (
            data.get("token")
            or data.get("access_token")
            or data.get("accessToken")
        )
        if not token:
            _LOGGER.error("MySensees login response for %s did not contain token fields", url)
            raise ApiError("Login response did not include a token")

        self.token = token

    async def async_get_gateway(self, gateway_id: str) -> dict[str, Any]:
        """Fetch gateway data, refreshing auth once on 401."""
        if not self.token:
            await self.async_login()

        try:
            return await self._async_get_gateway(gateway_id)
        except AuthError:
            _LOGGER.debug("Gateway fetch returned unauthorized, retrying login once")
            await self.async_login()
            return await self._async_get_gateway(gateway_id)

    async def _async_get_gateway(self, gateway_id: str) -> dict[str, Any]:
        """Fetch gateway data with the current token."""
        url = f"{self.base_url.rstrip('/')}/api/v2/config/gateway/{gateway_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                response = await self.session.get(url, headers=headers)
                if response.status == 401:
                    raise AuthError("Token is no longer valid")
                response.raise_for_status()
                return await response.json()
        except AuthError:
            raise
        except ClientResponseError as err:
            _LOGGER.warning(
                "MySensees gateway fetch failed with HTTP %s for %s",
                err.status,
                url,
            )
            raise ApiError(f"Gateway fetch failed with status {err.status}") from err
        except TimeoutError as err:
            _LOGGER.warning("MySensees gateway fetch timed out for %s", url)
            raise ApiError("Gateway fetch timed out") from err
        except Exception as err:
            _LOGGER.exception("MySensees gateway request failed for %s", url)
            raise ApiError("Gateway request failed") from err
