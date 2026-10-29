from machine import Pin, PWM
import time

class AbstractPeripheral:
    def __init__(self, pin_id: int):
        self.pin_id = pin_id
        self.is_enabled = False

    def initialize(self) -> bool:
        self.is_enabled = True
        return True

    def reset(self):
        self.is_enabled = False


class LockActuator(AbstractPeripheral):
    def __init__(self, pin_id: int):
        super().__init__(pin_id)
        self.pwm = PWM(Pin(pin_id))
        self.pwm.freq(50)
        self.locked = True
        self.lock()

    def lock(self):
        # Move servo to locked angle (0 degrees, ~0.5ms duty)
        self.pwm.duty_u16(1638)
        self.locked = True

    def unlock(self):
        # Move servo to unlocked angle (90 degrees, ~1.5ms duty)
        self.pwm.duty_u16(4915)
        self.locked = False

    def is_locked(self) -> bool:
        return self.locked


class PiezoBuzzer(AbstractPeripheral):
    def __init__(self, pin_id: int):
        super().__init__(pin_id)
        self.buzzer_pin = Pin(pin_id, Pin.OUT)

    def play_chime(self):
        # Short success beep pattern
        self.buzzer_pin.value(1)
        time.sleep_ms(150)
        self.buzzer_pin.value(0)

    def play_siren(self, cycles: int = 5):
        for _ in range(cycles):
            self.buzzer_pin.value(1)
            time.sleep_ms(100)
            self.buzzer_pin.value(0)
            time.sleep_ms(100)
