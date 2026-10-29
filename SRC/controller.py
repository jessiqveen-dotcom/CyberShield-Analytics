import time
from peripherals import LockActuator, PiezoBuzzer

class RackGuardController:
    def __init__(self, terminal_id: str, pin_hash: str):
        self.terminal_id = terminal_id
        self.authorized_pin_hash = pin_hash
        self.failed_attempts = 0
        self.max_failed_attempts = 3
        self.auto_relock_delay = 10
        self.current_state = "LOCKED"

        self.lock = LockActuator(pin_id=16)
        self.buzzer = PiezoBuzzer(pin_id=12)

    def validate_pin(self, entered_pin: str) -> bool:
        # In production: replace with secure hashlib comparison
        return entered_pin == self.authorized_pin_hash

    def handle_access_granted(self):
        self.failed_attempts = 0
        self.current_state = "UNLOCKED"
        self.buzzer.play_chime()
        self.lock.unlock()

        # Hold open for 10 seconds before auto-relock
        time.sleep(self.auto_relock_delay)
        self.lock.lock()
        self.current_state = "LOCKED"

    def handle_access_denied(self):
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_failed_attempts:
            self.trigger_tamper_lockout()
        else:
            self.buzzer.play_siren(cycles=2)

    def trigger_tamper_lockout(self):
        self.current_state = "TAMPER_LOCKOUT"
        self.lock.lock()
        self.buzzer.play_siren(cycles=10)
        # Dispatch webhook alert to security team
