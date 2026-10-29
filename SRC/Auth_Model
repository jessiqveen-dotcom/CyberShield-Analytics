# src/core/rackguard_manager.py
from auth_models import BadgeCard, RfidReaderRC522

class RackGuardManager:
    def __init__(self, terminal_id: str):
        self.terminal_id = terminal_id
        self.failed_attempts = 0
        self.max_failed_limit = 3
        self.is_locked_down = False
        self.rfid_reader = RfidReaderRC522()
        
        # Whitelist database of authorized credentials
        self.authorized_badges = {
            "50:9D:39:23": BadgeCard("50:9D:39:23", "Lead Admin", "1234"),
            "77:18:40:05": BadgeCard("77:18:40:05", "Sys Engineer", "5678")
        }

    def authenticate(self, uid: str, pin: str) -> bool:
        if self.is_locked_down:
            return False

        badge = self.authorized_badges.get(uid)
        if badge and badge.expected_pin == pin:
            self.failed_attempts = 0
            self.handle_access_granted()
            return True
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_limit:
                self.trigger_tamper_lockout()
            return False

    def handle_access_granted(self):
        # Trigger servo disengagement & green status
        pass

    def trigger_tamper_lockout(self):
        self.is_locked_down = True
        # Sound alarm, pulse red NeoPixel, dispatch webhook