"""Source-dimension and topology checks for the standalone MSAP connector."""

import math

import pytest

import flowmeter_electronic_interconnect as FEI


@pytest.fixture(scope="module")
def connector():
    return FEI.make_interconnect()


def test_connector_valid_and_source_envelope(connector):
    assert connector.is_valid
    bb = connector.bounding_box()
    # OEM STEP extremes in the documented local frame; includes grip ribs.
    assert bb.min.X == pytest.approx(-9.7, abs=1e-5)
    assert bb.max.X == pytest.approx(29.848554617228, abs=1e-5)
    assert bb.size.Y == pytest.approx(19.0, abs=1e-5)
    assert bb.min.Z == pytest.approx(-27.0, abs=1e-5)
    assert bb.max.Z == pytest.approx(9.5, abs=1e-5)


def test_a_code_key_is_open_and_opposite_side_is_solid(connector):
    assert not connector.is_inside((-9.5, 0, 3.4))
    assert connector.is_inside((-9.5, 0, -3.4))
    assert connector.is_inside((-9.5, 0.8, 3.4))


def test_four_socket_entries_on_five_mm_pitch_circle(connector):
    offset = 2.5 / math.sqrt(2)
    for y in (-offset, offset):
        for z in (-offset, offset):
            # Socket entrance is open, with material just outside the bore.
            assert not connector.is_inside((-9.0, y, z))
            assert connector.is_inside((-9.0, y + 0.7, z))
    assert connector.is_inside((-9.0, 0, 0))  # no invented fifth socket


def test_gland_cable_entry(connector):
    assert not connector.is_inside((20.598554617228, 0, -26.0))
    assert connector.is_inside((20.598554617228, 6, -26.0))
