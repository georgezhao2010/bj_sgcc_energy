import logging
import asyncio
import async_timeout
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from .sgcc import SGCCData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)


async def async_setup(hass: HomeAssistant, hass_config):
    config = hass_config[DOMAIN]
    openid = config.get("openid")
    if openid is not None:
        coordinator = GJDWCorrdinator(hass, openid)
        hass.data[DOMAIN] = coordinator
        while True:
            await coordinator.async_refresh()
            if coordinator.last_update_success:
                hass.async_create_task(discovery.async_load_platform(
                    hass, "sensor", DOMAIN, config, hass_config))
                break
            await asyncio.sleep(10)
    else:
        _LOGGER.error("The required parameter openid is missing")
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

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(60):
                data = await self._sgcc.async_get_data()
                if not data:
                    raise UpdateFailed("Failed to data update")
                return data
        except asyncio.TimeoutError:
            _LOGGER.warning("Data update timed out")
