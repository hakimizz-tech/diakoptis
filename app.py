import ntc_templates
from ntc_templates.parse import parse_output
from pathlib import Path
from src.asterfusion.parsing.parser import OutputParser


NTC_TEMPLATES_DIR = Path(ntc_templates.__file__).parent / "templates"

raw_output = """
show interface status
  Interface    Lanes    Speed    MTU    FEC       Alias    Oper    Admin    Optical Type    Asym PFC    If Type
-----------  -------  -------  -----  -----  ----------  ------  -------  --------------  ----------  ---------
  Ethernet1        0       1G   9216   none   Ethernet1      up       up             N/A         N/A         L3
  Ethernet2        1       1G   9216   none   Ethernet2    down       up             N/A         N/A
  Ethernet3        2       1G   9216   none   Ethernet3    down       up             N/A         N/A
  Ethernet4        3       1G   9216   none   Ethernet4    down       up             N/A         N/A
  Ethernet5        4       1G   9216   none   Ethernet5    down       up             N/A         N/A
  Ethernet6        5       1G   9216   none   Ethernet6    down       up             N/A         N/A
  Ethernet7        6       1G   9216   none   Ethernet7    down       up             N/A         N/A
  Ethernet8        7       1G   9216   none   Ethernet8    down       up             N/A         N/A
  Ethernet9        8       1G   9216   none   Ethernet9    down       up             N/A         N/A
 Ethernet10        9       1G   9216   none  Ethernet10    down       up             N/A         N/A
 Ethernet11       10       1G   9216   none  Ethernet11    down       up             N/A         N/A
 Ethernet12       11       1G   9216   none  Ethernet12    down       up             N/A         N/A
 Ethernet13       12       1G   9216   none  Ethernet13    down       up             N/A         N/A
 Ethernet14       13       1G   9216   none  Ethernet14    down       up             N/A         N/A
 Ethernet15       14       1G   9216   none  Ethernet15    down       up             N/A         N/A
 Ethernet16       15       1G   9216   none  Ethernet16    down       up             N/A         N/A
 Ethernet17       16       1G   9216   none  Ethernet17    down       up             N/A         N/A
 Ethernet18       17       1G   9216   none  Ethernet18    down       up             N/A         N/A
 Ethernet19       18       1G   9216   none  Ethernet19    down       up             N/A         N/A
 Ethernet20       19       1G   9216   none  Ethernet20    down       up             N/A         N/A
 Ethernet21       20       1G   9216   none  Ethernet21    down       up             N/A         N/A
 Ethernet22       21       1G   9216   none  Ethernet22    down       up             N/A         N/A
 Ethernet23       22       1G   9216   none  Ethernet23    down       up             N/A         N/A
 Ethernet24       23       1G   9216   none  Ethernet24    down       up             N/A         N/A
 Ethernet25       48      10G   9216   none  Ethernet25    down       up             N/A         N/A
 Ethernet26       49       1G   9216   none  Ethernet26      up       up  SFP/SFP+/SFP28         N/A         L3
 Ethernet27       50      10G   9216   none  Ethernet27    down       up             N/A         N/A
 Ethernet28       51       1G   9216   none  Ethernet28      up       up  SFP/SFP+/SFP28         N/A         L3
"""


parser = OutputParser()
output = parser.parse(raw_output=raw_output,
              strategy='textfsm:asterfusion/sonic_show_interface_status.textfsm')



print(output)


