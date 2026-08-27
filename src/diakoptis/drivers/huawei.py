

import logging
from typing import Any, Dict, List, Optional

from asterfusion.connection.exceptions import SwitchAuthError, SwitchConnectionError
from asterfusion.drivers.base import SwitchDriver
from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException


class HuaweiDriver(SwitchDriver):

    def __init__(self, hostname: str, host_data: Dict[str, Any], credentials: Dict[str, str]):
        super().__init__(hostname, host_data, credentials)
        self.ip_address = self.host_data.get('host')

        if not self.ip_address:
            raise ValueError(f"Host {self.hostname} is missing an IP address ('host field') in inventory")

        #Huawei device type
        self.device_type = self.host_data.get('device_type', 'huawei')

        #netmiko connection
        self.netmiko_conn : Optional[Any] = None

        #suppress noisy Netmiko/Paramiko background logs unless explicitly needed
        logging.getLogger('netmiko').setLevel(logging.CRITICAL)
        logging.getLogger('paramiko').setLevel(logging.CRITICAL)


    def connect(self) -> None:
        """ Establishes the netmiko ssh session"""

        huawei_device = {
            "device_type": self.device_type,
            "host": self.ip_address,
            "username": self.credentials.get('username'),
            "password": self.credentials.get('password'),
            "global_delay_factor": 2,
            'connection_timeout': 30,
        }

        #add the enable secret if provided
        secret = self.credentials.get('secret')

        if secret:
            huawei_device['secret'] = secret

        try:
            self.netmiko_conn = ConnectHandler(auto_connect=False, **huawei_device)

            # Ensure we are in enable mode if a secret was provided
            if secret and not self.netmiko_conn.check_enable_mode():
                self.netmiko_conn.enable()

        except NetmikoAuthenticationException as e:
            username = self.credentials.get('username', 'unkown_user')
            raise SwitchAuthError(f"Authentication failed for {username} on {self.hostname}") from e
        
        except NetmikoTimeoutException as e:
            raise SwitchConnectionError(f'failed to connect to {self.hostname}: {e} ') from e

    def disconnect(self) -> None:
        if self.is_connected:
            connection = self.netmiko_conn
            if connection is None:
                return

            try:
                connection.disconnect()

            except Exception:
                pass # fail silently on disconnect, the socket is likely dead


    def send_native(self, commands: List[str]) -> Dict[str, str]:
        if not self.is_connected:
            raise SwitchConnectionError(f'cannot send command: Not connected {self.hostname}')

        connection = self.netmiko_conn
        if not connection:
            raise SwitchConnectionError(f'cannot send command: Not connected {self.hostname}')


        result = {}
        for cmd in commands:
            try:

                #return raw text
                output = connection.send_command(cmd)
                result[cmd] = output

            except Exception as  e:
                # If a single command fails, record the error in the output dictionary 
                # instead of crashing the whole batch.
                result[cmd] = f"Error executing command: {str(e)}"
        return result


    @property
    def is_connected(self) -> bool:
        """Checks if the Netmiko socket is active"""
        if not self.netmiko_conn:
            return False

        return self.netmiko_conn.is_alive()
        

