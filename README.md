# CyberShield-Analytics
CyberShield Analytics RFID Scanner
RackGuard IoT is an edge-based physical access control terminal and perimeter defense sentinel designed for high-security environments such as data center server racks, colocation suites, and network closets.

While enterprise security teams enforce robust logical access controls (firewalls, zero-trust network policies, EDR agents), direct physical tampering remains an Achilles' heel. An unauthorized intruder with direct chassis access can install rogue keystroke sniffers, extract unencrypted SSD drives, or hijack console ports.

RackGuard bridges this gap by enforcing two-factor physical authentication (RFID Badge + Security PIN), localized latch actuation, and immediate cloud-based security audit streaming via HTTPS webhooks.
Key Features

Multi-Factor Physical Authentication (2FA): Requires a valid 13.56 MHz RFID badge swipe followed by a secondary numeric PIN entry.

Autonomous Mechanical Latch Actuation: Disengages a physical server rack strike latch using a 90° micro servo mechanism.

Auto-Relock Failsafe: Enforces a mandatory 10-second re-lock countdown timer visible on an I2C 1602 LCD.

Active Tamper / Anti-Brute-Force Lockout: After three (3) consecutive failed attempts, the device triggers TAMPER_LOCKOUT:

Mechanical latch locks down immediately.

Piezo buzzer initiates a high-frequency audible siren.

NeoPixels pulse high-intensity alert red.

A high-priority incident webhook payload is transmitted over Wi-Fi to security operations (e.g., Slack, Discord, or SIEM).