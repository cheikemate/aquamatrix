"""Sensor platform for AQUAmatrix SMASVFX."""

from __future__ import annotations

import contextlib
import datetime
import logging
import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SMASVFXCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SMASVFXCoordinator = data["coordinator"]

    entities = [
        # Compatível com Energy (contador cumulativo)
        SMASVFXSensor(
            coordinator,
            entry,
            "last_reading_value",
            unit="m³",
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        SMASVFXSensor(
            coordinator, entry, "last_reading_date", unit=None, device_class=SensorDeviceClass.DATE
        ),
        # Consumos mensais (medição)
        SMASVFXSensor(
            coordinator,
            entry,
            "consumption_current_month",
            unit="m³",
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL,
        ),
        SMASVFXSensor(
            coordinator,
            entry,
            "consumption_previous_month",
            unit="m³",
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL,
        ),
        SMASVFXSensor(coordinator, entry, "consumption_current_month_label", unit=None),
        # Faturação / dívida
        SMASVFXSensor(
            coordinator,
            entry,
            "billed_last_value",
            unit="EUR",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
        ),
        SMASVFXSensor(coordinator, entry, "billed_last_label", unit=None),
        SMASVFXSensor(
            coordinator,
            entry,
            "billed_total",
            unit="EUR",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
        ),
        SMASVFXSensor(
            coordinator,
            entry,
            "debt_total",
            unit="EUR",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
        ),
        SMASVFXSensor(
            coordinator, entry, "next_due_date", unit=None, device_class=SensorDeviceClass.DATE
        ),
    ]
    async_add_entities(entities)


class SMASVFXSensor(CoordinatorEntity[SMASVFXCoordinator], SensorEntity):
    """AQUAmatrix SMASVFX Sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SMASVFXCoordinator,
        entry: ConfigEntry,
        key: str,
        unit: str | None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class
        if state_class:
            self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Portal AQUAmatrix",
            manufacturer="Quinzico",
            model="SMASVFX",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        last = data.get("last_reading") or {}
        cons = data.get("consumptions") or {}
        billed = data.get("billed") or {}
        billinfo = data.get("billing_info") or {}

        if self._key == "last_reading_value":
            v = last.get("Value") or last.get("LastReadingValue") or "0"
            try:
                parsed_str = re.sub(r"\s", "", str(v)).replace(",", ".")
                return float(parsed_str)
            except (ValueError, TypeError):
                _LOGGER.error("Error parsing last reading value: %s", v)
                return None

        if self._key == "last_reading_date":
            v = last.get("LastReadingDate") or last.get("Date")
            if not v:
                return None
            try:
                return datetime.datetime.strptime(v, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                _LOGGER.error("Error parsing last reading date: %s", v)
                return None

        if self._key in (
            "consumption_current_month",
            "consumption_previous_month",
            "consumption_current_month_label",
        ):
            arr: list[dict[str, Any]] = []
            if isinstance(cons, dict) and "Values" in cons:
                arr = cons.get("Values") or []
            elif isinstance(cons, list):
                arr = cons
            if not arr:
                return None
            idx = -1 if self._key != "consumption_previous_month" else -2
            try:
                item = arr[idx]
            except IndexError:
                return None
            if self._key == "consumption_current_month_label":
                return item.get("Label", "")
            val = item.get("FirstValue", item.get("Value", 0))
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                return None

        if self._key in ("billed_last_value", "billed_last_label", "billed_total"):
            if not isinstance(billed, list) or not billed:
                return None
            if self._key == "billed_total":
                total = 0.0
                for item in billed:
                    with contextlib.suppress(ValueError, TypeError):
                        total += float(str(item.get("Value", 0)).replace(",", "."))
                return total
            last_item = billed[-1]
            if self._key == "billed_last_label":
                return last_item.get("Label", "")
            val = last_item.get("Value", 0)
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                return None

        if self._key == "debt_total":
            for k in ("totalDebt", "valorEmDivida", "debt", "TotalDebt", "ValorEmDivida"):
                if k in billinfo:
                    try:
                        return float(str(billinfo[k]).replace(",", "."))
                    except (ValueError, TypeError):
                        return None
            inv = billinfo.get("nextInvoice") or billinfo.get("proximaFatura") or {}
            for k in ("debt", "valor", "amount"):
                if k in inv:
                    try:
                        return float(str(inv[k]).replace(",", "."))
                    except (ValueError, TypeError):
                        return None
            return None

        if self._key == "next_due_date":
            inv = billinfo.get("nextInvoice") or billinfo.get("proximaFatura") or {}
            v = (
                inv.get("limitDate")
                or inv.get("dataLimite")
                or billinfo.get("limitDate")
                or billinfo.get("dataLimite")
            )
            if not v:
                return None
            try:
                return datetime.datetime.strptime(v, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None

        return None
