from diakoptis.parsing.parser import OutputParser


def test_disk_template_accepts_integer_percentage():
    parser = OutputParser(templates_root="src/diakoptis/parsing/templates")
    raw = """+----------------+
|   Disk usage % |
|----------------|
|              9 |
+----------------+
+----------------+---------------+----------------+
| total          | used          | free           |
|----------------+---------------+----------------|
| 29357916160(B) | 2511749120(B) | 25331240960(B) |
| 27.34(GB)      | 2.34(GB)      | 23.59(GB)      |
+----------------+---------------+----------------+"""

    parsed = parser.parse_command(
        raw,
        "show system disk-usage",
        "asterfusion/sonic_show_system_disk_usage.textfsm",
    )

    assert parsed[0]["DISK_PCT"] == "9"
    assert parsed[0]["TOTAL_DISK_BYTES"] == "29357916160"
    assert parsed[0]["USED_DISK_BYTES"] == "2511749120"
