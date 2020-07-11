import pygatt
from pygatt.backends import BLEAddressType

import struct

adapter = pygatt.GATTToolBackend()

try:
    adapter.start()
    device = adapter.connect('DA:F0:63:93:BE:97',  address_type=BLEAddressType.random)
    value = device.char_read("00002235-b38d-4985-720e-0f993a68ee41")
finally:
    adapter.stop()

print(value)
print(struct.unpack('f', value))
