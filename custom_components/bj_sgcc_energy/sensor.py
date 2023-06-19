from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.const import UnitOfEnergy, STATE_UNKNOWN
from .const import DOMAIN

SGCC_SENSORS = {
    "balance": {
        "name": "电费余额",
        "icon": "hass:cash-100",
        "unit_of_measurement": "元",
        "attributes": ["last_update"],
    },
    "current_level": {"name": "当前用电阶梯", "icon": "hass:stairs"},
    "current_price": {
        "name": "当前电价",
        "icon": "hass:cash-100",
        "unit_of_measurement": "CNY/kWh",
    },
    "current_level_consume": {
        "name": "当前阶梯用电",
        "device_class": SensorDeviceClass.ENERGY,
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "current_level_remain": {
        "name": "当前阶梯剩余额度",
        "device_class": SensorDeviceClass.ENERGY,
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "year_consume": {
        "name": "本年度用电量",
        "device_class": SensorDeviceClass.ENERGY,
        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "year_consume_bill": {
        "name": "本年度电费",
        "icon": "hass:cash-100",
        "unit_of_measurement": "元",
    },
    "current_pgv_type": {"name": "当前电价类别", "icon": "hass:cash-100"},
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
        for day in range(30):
            sensors.append(SGCCDailyBillSensor(coordinator, cons_no, day))
    async_add_devices(sensors, True)
    return None


class SGCCBaseSensor(CoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._unique_id = None
        return None


    @property
    def unique_id(self):
        return self._unique_id

    @property
    def should_poll(self):
        return False


class SGCCSensor(SGCCBaseSensor):
    def __init__(self, coordinator, cons_no, sensor_key):
        super().__init__(coordinator)
        self._cons_no = cons_no
        self._sensor_key = sensor_key
        self._config = SGCC_SENSORS[self._sensor_key]
        self._attributes = self._config.get("attributes")
        self._coordinator = coordinator
        self._unique_id = f"{DOMAIN}.{cons_no}_{sensor_key}"
        self.entity_id = self._unique_id
        return None

    def get_value(self, attribute=None):
        try:
            if attribute is None:
                return self._coordinator.data.get(self._cons_no).get(self._sensor_key)
            return self._coordinator.data.get(self._cons_no).get(attribute)
        except KeyError:
            return STATE_UNKNOWN

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


class SGCCHistorySensor(SGCCBaseSensor):
    def __init__(self, coordinator, cons_no, index):
        super().__init__(coordinator)
        self._cons_no = cons_no
        self._coordinator = coordinator
        self._index = index
        self._unique_id = f"{DOMAIN}.{cons_no}_history_{index + 1}"
        self.entity_id = self._unique_id

    @property
    def name(self):
        try:
            return (
                self._coordinator.data.get(self._cons_no)
                .get("history")[self._index]
                .get("name")
            )
        except KeyError:
            return STATE_UNKNOWN

    @property
    def state(self):
        try:
            return (
                self._coordinator.data.get(self._cons_no)
                .get("history")[self._index]
                .get("consume")
            )
        except KeyError:
            return STATE_UNKNOWN

    @property
    def extra_state_attributes(self):
        try:
            return {
                "consume_bill": self._coordinator.data.get(self._cons_no)
                .get("history")[self._index]
                .get("consume_bill")
            }
        except KeyError:
            return {"consume_bill": 0.0}

    @property
    def device_class(self):
        return DEVICE_CLASS_ENERGY

    @property
    def unit_of_measurement(self):
        return ENERGY_KILO_WATT_HOUR


class SGCCDailyBillSensor(SGCCBaseSensor):
    def __init__(self, coordinator, cons_no, index):
        super().__init__(coordinator)
        self._cons_no = cons_no
        self._coordinator = coordinator
        self._index = index
        self._unique_id = f"{DOMAIN}.{cons_no}_daily_{index + 1}"
        self.entity_id = self._unique_id

    @property
    def name(self):
        try:
            return (
                self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("bill_date")
            )
        except KeyError:
            return STATE_UNKNOWN

    @property
    def state(self):
        try:
            return (
                self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("day_consume")
            )
        except KeyError:
            return STATE_UNKNOWN

    @property
    def extra_state_attributes(self):
        try:
            return {
                "bill_time": self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("bill_time"),
                "day_consume1": self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("day_consume1"),
                "day_consume2": self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("day_consume2"),
                "day_consume3": self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("day_consume3"),
                "day_consume4": self._coordinator.data.get(self._cons_no)
                .get("daily_bills")[self._index]
                .get("day_consume4"),
            }
        except KeyError:
            return None

    @property
    def device_class(self):
        return DEVICE_CLASS_ENERGY

    @property
    def unit_of_measurement(self):
        return ENERGY_KILO_WATT_HOUR
