#-------------------------------------------------------------------------------
# Name:        test_wanptek
# Purpose:     Usage example of WanptekClient against HelmMagControl.
#
# Author:      ebalvis
#
# Created:     25/09/2025
# Copyright:   (c) ebalvis 2025
# Licence:     MIT
#-------------------------------------------------------------------------------
from wanptek_control import WanptekClient

client = WanptekClient("127.0.0.1", 4444)
client.connect()

# Test communication
print(client.ping())            # -> OK PONG
# Read values
print(client.get_voltage(1))
print(client.get_current(1))
print(client.get_power(1))
# Set channel 1 voltage
print(client.set_voltage(1, 15.9))
# Set channel 1 current
print(client.set_current(1, 9.3))
# Enable outputs
print(client.set_output(1, True))
print(client.set_output(2, True))
print(client.set_output(3, True))


# Full status
print(client.read_all())

# Turn everything off
print(client.all_off())

client.close()
