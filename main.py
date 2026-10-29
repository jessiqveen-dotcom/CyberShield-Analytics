"""
main.py - RackGuard IoT Central Controller
Course Project: CyberShield Analytics
Target: Raspberry Pi Pico / Pico W
"""

import time
from machine import Pin, PWM
import neopixel

# Import course-provided object-oriented classes
from Displays import LCDDisplay
from Buzzer import PassiveBuzzer, tones, DO, MI, SO, DO2
from Button import Button
from Counters import SoftwareTimer
from Log import Log

# ==============================================================================
# PIN DEFINITIONS (Matching Wokwi & Breadboard Schematic)
# ==============================================================================
PIN_LCD_SDA    = 0     # I2C0 SDA for LCD 1602
PIN_LCD_SCL    = 1     # I2C0 SCL for LCD 1602
PIN_RFID_SCK   = 2     # SPI0 SCK
PIN_RFID_MOSI  = 3     # SPI0 TX
PIN_RFID_MISO  = 4     # SPI0 RX
PIN_RFID_CS    = 5     # SPI0 CS
PIN_RFID_RST   = 6     # Module Reset
PIN_NEOPIXEL   = 10    # WS2812B Status Indicator
PIN_BUZZER     = 12    # Passive Buzzer (PWM)
PIN_EXIT_BTN   = 13    # Manual Interior Exit / Release Button
PIN_SERVO      = 16    # SG90 Door Latch Actuator (PWM)

# ==============================================================================
# ACTUATOR & INDICATOR SUB-CLASSES
# ==============================================================================
class ServoLatch:
    """Controls the physical cabinet latch strike via 50Hz PWM."""
    def __init__(self, pin_num: int):
        self._pwm = PWM(Pin(pin_num))
        self._pwm.freq(50)
        self.lock()

    def lock(self):
        # 0 degrees (~1.0 ms pulse)
        self._set_angle(0)
        self.is_locked = True

    def unlock(self):
        # 90 degrees (~1.5 ms pulse)
        self._set_angle(90)
        self.is_locked = False

    def _set_angle(self, angle: int):
        # Duty cycle calculation for standard SG90 (1000us - 2000us)
        duty = int(1638 + (angle / 180.0) * 6554)
        self._pwm.duty_u16(duty)


class StatusNeoPixel:
    """Manages visual status feedback via WS2812B NeoPixel."""
    COLOR_OFF    = (0, 0, 0)
    COLOR_STANDBY= (0, 0, 40)     # Soft Blue
    COLOR_PASS   = (0, 80, 0)     # Green
    COLOR_ALERT  = (100, 0, 0)    # Red
    COLOR_WARN   = (80, 40, 0)    # Amber

    def __init__(self, pin_num: int, num_pixels: int = 1):
        self._np = neopixel.NeoPixel(Pin(pin_num), num_pixels)
        self.set_color(self.COLOR_STANDBY)

    def set_color(self, rgb_tuple):
        for i in range(len(self._np)):
            self._np[i] = rgb_tuple
        self._np.write()


# ==============================================================================
# RFID HARDWARE READER (SPI MFRC522 Abstraction)
# ==============================================================================
class RC522Reader:
    """
    Interfaces with the RC522 badge module via hardware SPI.
    Employs duplicate suppression logic matching the simulation model.
    """
    def __init__(self, sck=PIN_RFID_SCK, mosi=PIN_RFID_MOSI, miso=PIN_RFID_MISO, cs=PIN_RFID_CS, rst=PIN_RFID_RST):
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.last_uid = ""
        self.last_seen_ms = 0
        self.suppress_window_ms = 3000

        # Attempt to import low-level driver if present on device flash
        try:
            from mfrc522 import MFRC522
            self._driver = MFRC522(sck=sck, mosi=mosi, miso=miso, cs=cs, rst=rst)
        except ImportError:
            self._driver = None
            Log.w("mfrc522.py not found on flash. Operating in simulated loop mode.")

    def scan_uid(self) -> str:
        """Polls for cards and returns formatted UID hex string, or empty string."""
        now = time.ticks_ms()

        if self._driver:
            (status, tag_type) = self._driver.request(self._driver.REQIDL)
            if status == self._driver.OK:
                (status, raw_uid) = self._driver.anticoll()
                if status == self._driver.OK:
                    uid_str = ":".join([f"{b:02X}" for b in raw_uid[:4]])
                    if uid_str == self.last_uid and time.ticks_diff(now, self.last_seen_ms) < self.suppress_window_ms:
                        return ""
                    self.last_uid = uid_str
                    self.last_seen_ms = now
                    return uid_str
        return ""


# ==============================================================================
# MAIN ACCESS CONTROLLER
# ==============================================================================
class RackGuardController:
    """
    Central Coordinator: Handles state transitions, multi-factor credential
    validation, countdown relock timers, and tamper lockdowns.
    """
    # Authorized UID whitelist (from system requirements)
    ALLOWED_UIDS = {
        "50:9D:39:23": "Lead Admin",
        "77:18:40:05": "Sys Engineer",
        "9F:D6:B1:BD": "DB Admin",
        "0A:1B:2C:3D": "Security Lead",
        "F1:E2:D3:C4": "DevOps Lead"
    }

    def __init__(self):
        Log.i("Initializing RackGuard System...")

        # Initialize hardware devices using provided modules
        self.lcd = LCDDisplay(sda=PIN_LCD_SDA, scl=PIN_LCD_SCL)
        self.buzzer = PassiveBuzzer(PIN_BUZZER, name="RackGuardBuzzer")
        self.latch = ServoLatch(PIN_SERVO)
        self.pixel = StatusNeoPixel(PIN_NEOPIXEL)
        self.reader = RC522Reader()

        # Exit button with interrupt callback via Button.py
        self.exit_button = Button(PIN_EXIT_BTN, "ExitButton", handler=self, lowActive=True)

        # 10-second non-blocking auto-relock timer from Counters.py
        self.relock_timer = SoftwareTimer("RelockTimer", handler=self)

        # State tracking
        self.failed_attempts = 0
        self.max_failed = 3
        self.is_locked_down = False
        self.door_open = False

        self.reset_to_standby()

    def reset_to_standby(self):
        """Restores terminal to secure standby state."""
        self.door_open = False
        self.latch.lock()
        self.pixel.set_color(StatusNeoPixel.COLOR_STANDBY)
        self.lcd.clear()
        self.lcd.showText("RackGuard Sentry", row=0, col=0)
        self.lcd.showText("TAP CARD BADGE", row=1, col=1)
        Log.i("Perimeter ARMED - Waiting for badge scan.")

    # --------------------------------------------------------------------------
    # Button.py Callback Handlers
    # --------------------------------------------------------------------------
    def buttonPressed(self, name):
        Log.i(f"Physical override button pressed: {name}")
        if not self.is_locked_down and not self.door_open:
            Log.i("Manual egress triggered.")
            self.grant_access(user_label="Manual Egress")

    def buttonReleased(self, name):
        pass

    # --------------------------------------------------------------------------
    # Counters.py Callback Handlers
    # --------------------------------------------------------------------------
    def timeout(self, timer_name):
        """Called automatically when the 10-second SoftwareTimer expires."""
        Log.i(f"{timer_name} expired: Re-engaging electronic perimeter lock.")
        self.buzzer.beep(tone=tones['A4'], duration=150)
        self.reset_to_standby()

    # --------------------------------------------------------------------------
    # Security State Logic
    # --------------------------------------------------------------------------
    def grant_access(self, user_label: str):
        """Disengages latch, updates UI, and arms the relock countdown."""
        self.door_open = True
        self.failed_attempts = 0
        self.latch.unlock()
        self.pixel.set_color(StatusNeoPixel.COLOR_PASS)

        self.lcd.clear()
        self.lcd.showText("ACCESS GRANTED", row=0, col=1)
        self.lcd.showText(user_label[:16], row=1, col=0)

        # Melodic success chime
        self.buzzer.play(DO)
        time.sleep(0.1)
        self.buzzer.play(MI)
        time.sleep(0.1)
        self.buzzer.play(SO)
        time.sleep(0.1)
        self.buzzer.play(DO2)
        time.sleep(0.15)
        self.buzzer.stop()

        # Start 10-second non-blocking countdown timer
        self.relock_timer.start(10)

    def deny_access(self, uid_scanned: str):
        """Handles unauthorized credential presentation."""
        self.failed_attempts += 1
        Log.w(f"UNAUTHORIZED CARD: {uid_scanned} (Attempt {self.failed_attempts}/{self.max_failed})")

        self.pixel.set_color(StatusNeoPixel.COLOR_ALERT)
        self.lcd.clear()
        self.lcd.showText("ACCESS DENIED", row=0, col=1)
        self.lcd.showText(f"BADGE: {uid_scanned[:10]}", row=1, col=0)

        # Low-frequency error buzz
        self.buzzer.beep(tone=tones['C2'], duration=600)
        time.sleep(1.0)

        if self.failed_attempts >= self.max_failed:
            self.trigger_tamper_lockout()
        else:
            self.reset_to_standby()

    def trigger_tamper_lockout(self):
        """Locks terminal down upon 3 invalid attempts."""
        self.is_locked_down = True
        self.latch.lock()
        Log.e("SECURITY BREACH: Tamper threshold exceeded! System in LOCKDOWN.")

        self.lcd.clear()
        self.lcd.showText("** SECURITY **", row=0, col=1)
        self.lcd.showText("LOCKDOWN ACTIVE", row=1, col=0)

        # Audible siren & flashing LED alarm
        for _ in range(6):
            self.pixel.set_color(StatusNeoPixel.COLOR_ALERT)
            self.buzzer.play(tones['A6'])
            time.sleep(0.2)
            self.pixel.set_color(StatusNeoPixel.COLOR_OFF)
            self.buzzer.play(tones['D6'])
            time.sleep(0.2)

        self.buzzer.stop()
        self.pixel.set_color(StatusNeoPixel.COLOR_ALERT)

    # --------------------------------------------------------------------------
    # Main Polling Loop
    # --------------------------------------------------------------------------
    def run(self):
        Log.i("Entering operational event loop...")
        while True:
            # 1. Check countdown timer (Polls SoftwareTimer from Counters.py)
            self.relock_timer.check()

            # 2. Check RFID sensor if terminal is armed and not locked down
            if not self.is_locked_down and not self.door_open:
                scanned_uid = self.reader.scan_uid()
                if scanned_uid != "":
                    Log.i(f"Badge detected on SPI bus: {scanned_uid}")
                    if scanned_uid in self.ALLOWED_UIDS:
                        user = self.ALLOWED_UIDS[scanned_uid]
                        self.grant_access(user)
                    else:
                        self.deny_access(scanned_uid)

            # Prevent CPU lockup & yield to background scheduler
            time.sleep_ms(50)


# ==============================================================================
# SYSTEM ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    controller = RackGuardController()
    try:
        controller.run()
    except KeyboardInterrupt:
        Log.i("System terminated by user. Shutting down peripherals...")
        controller.buzzer.stop()
        controller.pixel.set_color(StatusNeoPixel.COLOR_OFF)
        controller.latch.lock()
        controller.lcd.clear()
        