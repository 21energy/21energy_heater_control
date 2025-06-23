"""21energy Heater Control API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout
import re

from .const import LOGGER


class HeaterControlApiClientError(Exception):
    """Exception to indicate a general API error."""


class HeaterControlApiClientCommunicationError(
    HeaterControlApiClientError,
):
    """Exception to indicate a communication error."""


class HeaterControlApiClientAuthenticationError(
    HeaterControlApiClientError,
):
    """Exception to indicate an authentication error."""

class HeaterControlApiClientOutdatedError(
    HeaterControlApiClientError,
):
    """Exception to indicate that an expected endpoint is not available. Most likely due to the ofen being outdated."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise HeaterControlApiClientAuthenticationError(
            msg,
        )
    elif response.status == 404:
        raise HeaterControlApiClientOutdatedError()
    response.raise_for_status()


class HeaterControlApiClient:
    """API Client."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """API Client."""
        self._host = host
        self._session = session
        self._data = {}

    async def async_get_data(self) -> Any:
        """Get all data from the API."""
        data = {}
        data["status"] = await self.async_get_status()
        data["fanspeed"] = int(float(await self._async_get_value("heater/status/fan")))
        data["powertarget"] = await self._async_get_value("heater/powerTarget")
        data["powertarget_watt"] = str(
            await self._async_get_value("heater/powerTarget/watt")
        ).replace("W", "")
        data["status_temperature"] = await self._async_get_value(
            "heater/status/temperature"
        )
        data["network_status"] = await self.async_get_networkStatus()
        data["pool_config"] = await self.async_get_poolConfig()

        status_summary = await self._async_get_value("heater/status/summary")
        for key in status_summary:
            if key in ["foundBlocks", "poolStatus"]:
                data[key.lower()] = status_summary[key]
            elif key == "power":
                data["power_limit"] = status_summary[key]["limitW"]
                data["power_consumption"] = status_summary[key]["approxConsumptionW"]
            elif key == "realHashrate":
                data["hashrate_5s"] = status_summary[key]["mhs5S"]
                data["hashrate_1m"] = status_summary[key]["mhs1M"]
                data["hashrate_5m"] = status_summary[key]["mhs5M"]
                data["hashrate_15m"] = status_summary[key]["mhs15M"]
                data["hashrate_24h"] = status_summary[key]["mhs24H"]
                data["hashrate_av"] = status_summary[key]["mhsAv"]

        data["status_running"] = (
            data["status"] == True and "tunerStatus" in status_summary
        )
        data["enable"] = data["status_running"]
        data["heater"] = self._data

        return data

    async def async_set_powerTarget(self, value: int) -> None:
        """Set the Power target. Values must between 0 and 4."""
        if value > 4 or value < 0:
            msg = f"Value must be between 0 and 4, but was {value}"
            raise HeaterControlApiClientError(msg)

        await self._api_wrapper(
            method="post",
            url=f"http://{self._host}/21control/heater/powerTarget/{value}",
            headers={"Content-type": "application/json; charset=UTF-8"},
        )

    async def async_set_enable(self, value: bool) -> None:
        """Enable or disable the Heater."""
        try:
            await self._api_wrapper(
                method="post",
                url=f"http://{self._host}/21control/heater/enable",
                data={"enabled": value},
                headers={"Content-type": "application/json; charset=UTF-8"},
            )
            return None
        except:
            return None

    async def async_get_status(self) -> bool:
        """Get data from the API."""
        ret = await self._api_wrapper(
            method="get",
            url=f"http://{self._host}/21control/status",
        )
        LOGGER.debug(f"typof ret:{type(ret)}")
        if "operational" in ret:
            return ret["operational"]
        return False

    async def async_get_device(self) -> Any:
        """Get heater data from the API."""
        ret = await self._api_wrapper(
            method="get",
            url=f"http://{self._host}/21control/status/system",
        )

        data = {
            "model": ret["model"],
            "is_paired": ret["isPaired"],
            "product_id": ret["productId"],
            "version": ret["version"],
        }
        self._data = data
        return data

    async def async_get_poolConfig(self) -> Any:
        """Get heater pool config from the API."""
        ret = await self._api_wrapper(
            method="get",
            url=f"http://{self._host}/21control/heater/poolConfig",
        )

        data = {
            "poolUrl1": ret["poolUrl1"],
            "poolUser1": ret["username1"],
            "poolUrl2": ret["poolUrl2"],
            "poolUser2": ret["username2"],
        }
        return data

    async def async_get_networkStatus(self) -> Any:
        """Get network status from the API."""
        ret = await self._api_wrapper(
            method="get",
            url=f"http://{self._host}/21control/heater/networkStatus",
        )
        data = {
            "type": re.sub(r"\d", "", ret["interface"]),
            "ssid": ret["essid"],
            "quality": ret["min_quality"],
            "max_quality": ret["maxQuality"],
            "signal_level": ret["signalLevel"],
        }
        return data

    async def _async_get_value(self, arg: str) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="get",
            url=f"http://{self._host}/21control/{arg}",
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                responseType = "text"
                if "Content-Type" in response.headers:
                    if "application/json" in response.headers["Content-Type"]:
                        responseType = "json"
                if responseType == "json":
                    try:
                        ret = await response.json()
                    except:
                        ret = await response.text()
                else:
                    ret = await response.text()
                LOGGER.debug(f"_api_wrapper => url:{url} => response:{ret}")
                return ret

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise HeaterControlApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise HeaterControlApiClientCommunicationError(
                msg,
            ) from exception
        except HeaterControlApiClientError as e:
            raise e
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise HeaterControlApiClientError(
                msg,
            ) from exception
