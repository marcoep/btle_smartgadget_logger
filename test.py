import pygatt
from pygatt.backends import BLEAddressType

import struct

adapter = pygatt.GATTToolBackend()

try:
    adapter.start()
    device = adapter.connect('DA:F0:63:93:BE:97',  address_type=BLEAddressType.random)
    # device.char_write("0000F239-B38D-4985-720E-0F993A68EE41", struct.pack('I', 10000))
    value = device.char_read("0000F239-B38D-4985-720E-0F993A68EE41")
finally:
    adapter.stop()

print(value)
print(struct.unpack('I', value))
