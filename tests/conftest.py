"""Fixtures for AQUAmatrix SMSnet tests."""
from __future__ import annotations

from unittest.mock import patch
import pytest

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    hass.data.pop("custom_components", None)
    yield

@pytest.fixture
def mock_smsnet_client():
    """Mock SMSNetClient."""
    with patch("custom_components.smsnet_aquamatrix.api.SMSNetClient", autospec=True) as mock_client:
        instance = mock_client.return_value
        instance.login.return_value = None
        instance.login_basic.return_value = None
        instance.get_last_reading.return_value = {"Value": "123,45", "Date": "2024-01-01"}
        instance.get_consumptions_graph.return_value = {"Values": [{"Label": "Jan", "Value": "10,5"}]}
        instance.get_billed_graph.return_value = [{"Label": "Jan", "Value": "25,0"}]
        instance.get_billing_info.return_value = {"totalDebt": "0,0", "nextInvoice": {"limitDate": "2024-02-01", "debt": "25,0"}}
        yield instance
