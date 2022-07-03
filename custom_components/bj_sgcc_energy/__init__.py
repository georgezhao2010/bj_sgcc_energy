import logging
import asyncio
import async_timeout
import homeassistant.util.dt as dt_util
from homeassistant.helpers.event import async_track_point_in_utc_time
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from .sgcc import SGCCData, AuthFailed, InvalidData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)


async def async_setup(hass: HomeAssistant, hass_config):
    config = hass_config[DOMAIN]
    openid = config.get("openid")
    coordinator = GJDWCorrdinator(hass, openid)
    hass.data[DOMAIN] = coordinator

    async def async_load_entities(hass, config, hass_config, coordinator):
        try:
            await coordinator.async_auth()
            await coordinator.async_refresh()
            if coordinator.last_update_success:
                _LOGGER.debug("Successful to update data, now loading entities")
                hass.async_create_task(discovery.async_load_platform(
                    hass, "sensor", DOMAIN, config, hass_config))
                return
        except AuthFailed as e:
            _LOGGER.error(e)
            return
        except Exception:
            pass
        async_track_point_in_utc_time(hass, async_load_entities, dt_util.utcnow() + 30)

    async_track_point_in_utc_time(hass, async_load_entities, dt_util.utcnow())
    return True


class GJDWCorrdinator(DataUpdateCoordinator):
    def __init__(self, hass, openid):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL
        )
        self._hass = hass
        session = async_create_clientsession(hass)
        self._sgcc = SGCCData(session, openid)

    async def async_auth(self):
        await self._sgcc.async_get_token()

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(60):
                data = await self._sgcc.async_get_data()
                if not data:
                    raise UpdateFailed("Failed to data update")
                return data
        except asyncio.TimeoutError:
            raise UpdateFailed("Data update timed out")
        except Exception:
            raise UpdateFailed("Failed to data update with unknown reason")
