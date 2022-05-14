from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import(
    DEVICE_CLASS_ENERGY,
    ENERGY_KILO_WATT_HOUR,
    STATE_UNKNOWN
)
from .const import DOMAIN

SGCC_SENSORS = {
    "balance": {
        "name": "电费余额",
        "icon": "hass:cash-100",
        "unit_of_measurement": "元",
        "attributes": ["last_update"]
    },
    "current_level": {
        "name": "当前用电阶梯",
        "icon": "hass:stairs"
    },
    "current_price": {
        "name": "当前电价",
        "icon": "hass:cash-100",
        "unit_of_measurement": "CNY/kWh"
    },
    "current_level_consume": {
        "name": "当前阶梯用电",
        "device_class": DEVICE_CLASS_ENERGY,
        "unit_of_measurement": ENERGY_KILO_WATT_HOUR
    },
    "current_level_remain": {
        "name": "当前阶梯剩余额度",
        "device_class": DEVICE_CLASS_ENERGY,
        "unit_of_measurement": ENERGY_KILO_WATT_HOUR
    },
    "year_consume": {
        "name": "本年度用电量",
        "device_class": DEVICE_CLASS_ENERGY,
        "unit_of_measurement": ENERGY_KILO_WATT_HOUR
    },
    "year_consume_bill": {
        "name": "本年度电费",
        "icon": "hass:cash-100",
        "unit_of_measurement": "元"
    },
    "current_pgv_type": {
        "name": "当前电价类别",
        "icon": "hass:cash-100"
    }
}


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    sensors = []
    coordinator = hass.data[DOMAIN]
    data = coordinator.data
    for cons_no, values in data.items():
        for key in SGCC_SENSORS.keys():
            if key in values.keys():
                sensors.append(SGCCSensor(coordinator, cons_no, key))
        for month in range(12):
            sensors.append(SGCCHistorySensor(coordinator, cons_no, month))
    async_add_devices(sensors, True)


class SGCCSensor(CoordinatorEntity):
    def __init__(self, coordinator, cons_no, sensor_key):
        super().__init__(coordinator)
        self._cons_no = cons_no
        self._sensor_key = sensor_key
        self._config = SGCC_SENSORS[self._sensor_key]
        self._attributes = self._config.get("attributes")
        self._coordinator = coordinator
        self._unique_id = f"{DOMAIN}.{cons_no}_{sensor_key}"
        self.entity_id = self._unique_id

    def get_value(self, attribute = None):
        try:
            if attribute is None:
                return self._coordinator.data.get(self._cons_no).get(self._sensor_key)
            return self._coordinator.data.get(self._cons_no).get(attribute)
        except KeyError:
            return STATE_UNKNOWN

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._config.get("name")

    @property
    def state(self):
        return self.get_value()

    @property
    def icon(self):
        return self._config.get("icon")

    @property
    def device_class(self):
        return self._config.get("device_class")

    @property
    def unit_of_measurement(self):
        return self._config.get("unit_of_measurement")

    @property
    def extra_state_attributes(self):
        attributes = {}
        if self._attributes is not None:
            try:
                for attribute in self._attributes:
                    attributes[attribute] = self.get_value(attribute)
            except KeyError:
                pass
        return attributes


class SGCCHistorySensor(CoordinatorEntity):
    def __init__(self, coordinator, cons_no, index):
        super().__init__(coordinator)
        self._cons_no = cons_no
        self._coordinator = coordinator
        self._index = index
        self._unique_id = f"{DOMAIN}.{cons_no}_history_{index + 1}"
        self.entity_id = self._unique_id

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        try:
            return self._coordinator.data.get(self._cons_no).get("history")[self._index].get("name")
        except KeyError:
            return STATE_UNKNOWN

    @property
    def state(self):
        try:
            return self._coordinator.data.get(self._cons_no).get("history")[self._index].get("consume")
        except KeyError:
            return STATE_UNKNOWN

    @property
    def extra_state_attributes(self):
        try:
            return {
                "consume_bill": self._coordinator.data.get(self._cons_no).get("history")[self._index].get("consume_bill")
            }
        except KeyError:
            return {"consume_bill": 0.0}

    @property
    def device_class(self):
        return DEVICE_CLASS_ENERGY

    @property
    def unit_of_measurement(self):
        return ENERGY_KILO_WATT_HOUR
