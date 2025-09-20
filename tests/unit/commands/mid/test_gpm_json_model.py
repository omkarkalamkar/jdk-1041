"""Module to test GPM json model"""
import pytest

from ska_tmc_centralnode.manager.gpm_json_model import GPMJsonModel


def test_gpm():
    gpm = {"version": "1.0", "receptors": {"MKT000": ["Band_1"]}}
    assert GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"MK001": ["Band_1"]}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"ska000": ["Band_1"]}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"sak000": ["Band_1"]}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"sak001": ["and_1"]}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"sak001": "and_1"}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": {"and_1"}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptors": "and_1"}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)

    gpm = {"version": "1.0", "receptor": {"MKT000": ["Band_1"]}}
    with pytest.raises(ValueError):
        GPMJsonModel(**gpm)
