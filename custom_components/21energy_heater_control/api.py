"""21energy Heater Control API Client."""

from __future__ import annotations

import re
import socket
from typing import Any

import aiohttp
import async_timeout

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
        data["powertarget_watt"] = float(str(
            await self._async_get_value("heater/powerTarget/watt")
        ).replace("W", "")) / 3
        data["status_temperature"] = await self._async_get_value(
            "heater/status/temperature"
        )
        data["network_status"] = await self.async_get_networkStatus()
        data["pool_config"] = await self.async_get_poolConfig()

        status_summary = await self._async_get_value("heater/status/summary")

        # v0.4.x and up
        if "forge" in status_summary:
            # keep existing status check but guard for missing keys
            data["status_running"] = (
                    data.get("status") is True and status_summary.get("miningDevices", {}).get("enabled") == 1
            )

            mining = status_summary.get("miningDevices", {})
            last_summaries = mining.get("lastSummaries") or []
            last = last_summaries[0] if len(last_summaries) > 0 else {}

            # --- Mining device top-level values ---
            # power target / consumption at device level
            if "powerTargetW" in mining:
                data["power_limit"] = mining.get("powerTargetW") / 3
            if "powerConsumptionW" in mining:
                data["power_consumption"] = mining.get("powerConsumptionW")

            # overall hash rate (device-level reported as gigahash/s) -> convert to MH/s
            if "hashRate" in mining and mining["hashRate"] is not None:
                try:
                    data["hashrate_overall_mhs"] = float(mining["hashRate"]) * 1000.0
                except Exception:
                    data["hashrate_overall_mhs"] = mining.get("hashRate")

            # chip temps (top-level)
            if "maxChipTemperature" in mining:
                data["max_chip_temp"] = mining.get("maxChipTemperature")
            if "minChipTemperature" in mining:
                data["min_chip_temp"] = mining.get("minChipTemperature")

            # device id (from last summary if present)
            if "id" in last:
                data["device_id"] = last.get("id")

            # --- Parse last summary blocks if present ---
            # Pool stats
            pool = last.get("pool_stats") or {}
            if pool:
                data["accepted_shares"] = pool.get("accepted_shares")
                data["rejected_shares"] = pool.get("rejected_shares")
                data["stale_shares"] = pool.get("stale_shares")
                data["last_difficulty"] = pool.get("last_difficulty")
                data["best_share"] = pool.get("best_share")
                data["generated_work"] = pool.get("generated_work")
                # last_share_time -> convert to ms epoch if present
                lst = pool.get("last_share_time")
                if isinstance(lst, dict) and "seconds" in lst:
                    try:
                        data["last_share_time_ms"] = int(lst.get("seconds", 0)) * 1000 + int(
                            lst.get("nanos", 0)) // 1_000_000
                    except Exception:
                        data["last_share_time"] = lst

            # Miner stats
            miner = last.get("miner_stats") or {}
            if miner:
                # found blocks
                if "found_blocks" in miner:
                    data["found_blocks"] = miner.get("found_blocks")

                # real_hashrate provides multiple windows in GH/s -> convert to MH/s
                real = miner.get("real_hashrate") or {}

                def _gh_to_mh(d, path_keys):
                    # safe accessor: returns value*1000 if present
                    cur = d
                    try:
                        for k in path_keys:
                            cur = cur[k]
                        return float(cur)
                    except Exception:
                        return None

                # Map windows (examples from response: last_5s, last_1m, last_5m, last_15m, last_24h, since_restart)
                v = _gh_to_mh(real, ["last_5s", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_5s"] = v
                v = _gh_to_mh(real, ["last_1m", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_1m"] = v
                v = _gh_to_mh(real, ["last_5m", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_5m"] = v
                v = _gh_to_mh(real, ["last_15m", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_15m"] = v
                v = _gh_to_mh(real, ["last_24h", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_24h"] = v
                # a reasonable "average" fallback: since_restart
                v = _gh_to_mh(real, ["since_restart", "gigahash_per_second"])
                if v is not None:
                    data["hashrate_av"] = v

            # Power stats (from the summary block)
            power = last.get("power_stats") or {}
            approxs = power.get("approximated_consumption") or {}
            if "watt" in approxs:
                data["power_consumption"] = approxs.get("watt")
            eff = power.get("efficiency") or {}
            if "joule_per_terahash" in eff:
                data["efficiency_j_per_th"] = eff.get("joule_per_terahash")

            # Fans / temps
            fans = last.get("fans")
            if isinstance(fans, list):
                # list of rpms and target ratios
                data["fan_rpms"] = [f.get("rpm") for f in fans]
                data["fan_target_speed_ratios"] = [f.get("target_speed_ratio") for f in fans]

            highest_temp = last.get("highest_temperature") or {}
            if "temperature" in highest_temp and isinstance(highest_temp["temperature"], dict):
                data["highest_chip_temp_c"] = highest_temp["temperature"].get("degree_c")

        # end if "forge" in status_summary
        else:
            for key in status_summary:
                if key in ["foundBlocks", "poolStatus"]:
                    data[key.lower()] = status_summary[key]
                elif key == "power":
                    data["power_limit"] = status_summary[key]["limitW"] / 3
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
            "product_id": ret["productId"].split()[-1],
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
        LOGGER.debug(f"received poolConfig:{ret}")
        data = {
            "poolUrl1": ret["url1"],
            "poolUser1": ret["user1"],
            "poolUrl2": ret["url2"],
            "poolUser2": ret["user2"],
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
            "quality": ret["minQuality"],
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
