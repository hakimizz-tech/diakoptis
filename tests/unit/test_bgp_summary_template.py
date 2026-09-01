from diakoptis.parsing.parser import OutputParser


def test_bgp_summary_template_parses_real_asterfusion_output():
    parser = OutputParser(templates_root="src/diakoptis/parsing/templates")
    sample = '''IPv4 Unicast Summary (VRF default):
BGP router identifier 10.120.30.2, local AS number 64517 vrf-id 0
BGP table version 421
RIB entries 51, using 9384 bytes of memory
Peers 5, using 3617 KiB of memory

Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
10.120.30.1     4      64517    103739    103691        0    0    0 4d20h19m           11        5 N/A
10.120.30.3     4      64517    103913    103922        0    0    0 06w5d02h            5        5 N/A
10.120.30.4     4      64517    103921    103917        0    0    0 10w2d03h            5        5 N/A
10.120.30.5     4      64517    102570    102595        0    0    0 01w1d04h            5        5 N/A
10.254.255.241  4      65012    119567    103974        0    0    0 10w2d03h            0        6 EBGP-TO-COOP-HOUSE-R

Total number of neighbors 5
'''

    parsed = parser.parse_command(
        sample,
        "show ip bgp summary",
        "asterfusion/sonic_show_ip_bgp_summary.textfsm",
    )

    assert isinstance(parsed, list)
    assert len(parsed) == 5
    assert parsed[0]["NEIGHBOR"] == "10.120.30.1"
    assert parsed[0]["STATE_PFX_RCD"] == "11"
    assert parsed[0]["AS"] == "64517"
