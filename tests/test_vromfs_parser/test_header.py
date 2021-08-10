import pytest
from formats.vromfs_parser import vromfs_header, ZSTD_PACKED, NOT_PACKED


@pytest.mark.parametrize(['bs', 'm'], [
    pytest.param(bytes.fromhex('56524673 00005043 98070000 07030040'), {
        'magic': 'vrfs',
        'platform': 'pc',
        'original_size': 0x798,
        'packed_size': 0x307,
        'vromfs_packed_type': ZSTD_PACKED,
    }, id='grp_hdr'),
    pytest.param(bytes.fromhex('56524673 00005043 50EF2101 00000080'), {
        'magic': 'vrfs',
        'platform': 'pc',
        'original_size': 0x121ef50,
        'packed_size': 0x0,
        'vromfs_packed_type': NOT_PACKED,
    }, id='fonts'),
    pytest.param(bytes.fromhex('56524678 00005043 801C0900 38EF08C0'), {
        'magic': 'vrfx',
        'platform': 'pc',
        'original_size': 0x91c80,
        'packed_size': 0x8ef38,
        'vromfs_packed_type': ZSTD_PACKED,
    }, id='char'),
])
def test_parse_vromfs_header(bs, m):
    ns = vromfs_header.parse(bs)
    assert all(ns[k] == m[k] for k in m)
