# src/core/auth_models.py
class BadgeCard:
    def __init__(self, uid_hex: str, holder_name: str, expected_pin: str):
        self.uid_hex = uid_hex
        self.holder_name = holder_name
        self.expected_pin = expected_pin


class RfidReaderRC522:
    def __init__(self, sck=2, mosi=3, miso=4, cs=5, rst=6):
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.cs = cs
        self.rst = rst

    def is_card_present(self) -> bool:
        # Interfaces with SPI / MFRC522 driver
        return True

    def read_uid(self) -> str:
        # Returns formatted UID string, e.g., '50:9D:39:23'
        return "50:9D:39:23"