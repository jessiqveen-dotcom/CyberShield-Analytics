from machine import Pin, SPI
from mfrc522 import MFRC522
import time

spi = SPI(
    0,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(16),
)

reader = MFRC522(spi, Pin(17), Pin(20))

while True:
    status, _ = reader.request(reader.REQIDL)

    if status == reader.OK:
        status, uid = reader.anticoll()
        if status == reader.OK:
            print("Card UID:", ":".join(f"{byte:02X}" for byte in uid))
            time.sleep(1)
            