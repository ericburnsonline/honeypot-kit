# Hardware Setup Guide

This guide covers setting up the optional OLED display and LED status indicator
module for Honeypot Kit. Both are disabled by default and configured via the
`honeypot-kit` CLI after installation.

---

## Required Components

| Component | Description | Approx Cost |
|-----------|-------------|-------------|
| Raspberry Pi 4 (4GB+) | Main board | ~$55-75 |
| OLED display module | SSD1306 or SSD1315, I2C, 128x64 | ~$10-15 |
| LED traffic light module | Red/Yellow/Green with built-in resistors | ~$4-8 |
| Jumper wires (female-female) | For GPIO connections | ~$3-5 |
| Breadboard (optional) | For prototyping connections | ~$5 |

### Supported OLED Displays

| Size | Driver | Resolution | Notes |
|------|--------|------------|-------|
| 0.96" | SSD1306 | 128x64 | Most common, well supported |
| 0.91" | SSD1306 | 128x32 | Smaller, same driver |
| 2.42" | SSD1309 | 128x64 | Larger, same Adafruit library |
| 1.5" | SH1107 | 128x128 | Square layout, extra vertical space |

All of the above use I2C and are supported by the same Adafruit library
that the install script installs automatically.

### LED Traffic Light Module

Use a pre-wired traffic light module with built-in resistors rather than
individual LEDs and resistors. This simplifies wiring and reduces component
count. A good example:
[Yuuhseel Traffic Light Module](https://www.amazon.com/Yuuhseel-Traffic-Compatible-Arduino-Raspberry/dp/B0FX9PF6XQ/)

---

## Wiring

### OLED Display (I2C)

Connect the OLED to the Raspberry Pi I2C pins:

| OLED Pin | Pi Pin | Pi GPIO |
|----------|--------|---------|
| VCC | Pin 1 | 3.3V |
| GND | Pin 6 | Ground |
| SCL | Pin 5 | GPIO 3 (SCL) |
| SDA | Pin 3 | GPIO 2 (SDA) |

### LED Traffic Light Module

Connect the LED module to any available GPIO pins. The defaults used by
Honeypot Kit are:

| LED | Default GPIO (BCM) | Pi Pin |
|-----|--------------------|--------|
| Red | GPIO 17 | Pin 11 |
| Yellow | GPIO 27 | Pin 13 |
| Green | GPIO 22 | Pin 15 |

You can use different pins - see [Changing GPIO Pins](#changing-gpio-pins) below.

---

## Enable I2C on the Raspberry Pi

I2C must be enabled before the OLED will work:

```bash
sudo raspi-config
```

Navigate to: **Interface Options** → **I2C** → **Yes** → **Finish**

Reboot after enabling I2C:

```bash
sudo reboot
```

---

## Verify Hardware is Connected

### OLED Display

After connecting and enabling I2C, confirm the display is detected:

```bash
sudo apt-get install -y i2c-tools
i2cdetect -y 1
```

You should see a device address (typically `3c` or `3d`) in the output grid.
If nothing appears, check your wiring.

### LED Module

No detection tool needed - use the CLI test command after configuring pins.

---

## Configure and Enable via CLI

### OLED Display

```bash
# Set I2C address (default is 0x3C - use i2cdetect to confirm)
honeypot-kit oled set-address 0x3C

# Set resolution to match your display
honeypot-kit oled set-resolution 128x64

# Enable the module
honeypot-kit oled enable

# Test it - should show Honeypot Kit info on screen
honeypot-kit oled test

# Start the monitor daemon
honeypot-kit monitor start
```

### LED Traffic Light Module

```bash
# Set GPIO pins (BCM numbering) if different from defaults
honeypot-kit led set-pins --red 17 --yellow 27 --green 22

# Enable the module
honeypot-kit led enable

# Test it - flashes each LED for 1 second in sequence
sudo honeypot-kit led test

# Start the monitor daemon (if not already running)
honeypot-kit monitor start
```

---

## LED Status Meanings

The monitor daemon drives the LEDs with distinct patterns:

| State | Green | Yellow | Red |
|-------|-------|--------|-----|
| Healthy, idle | Solid | Off | Off |
| Login history (someone was in) | Solid | Off | Slow blink every 3s |
| Active attack session | Solid | Slow flash (1s) | Off |
| High attack rate (>10/min) | Solid | Fast flash (0.25s) | Off |
| Warning (disk >85%, mem >90%) | Off | Solid | Off |
| Cowrie down, restarting | Off | Fast flash | Slow flash |
| Critical (disk >95%) | Off | Off | Solid |
| Critical error | Off | Off | Fast flash |
| Startup sequence | All three flash in sequence | | |

The **login history** state persists even after a session ends, so you
can see at a glance that someone logged in - even if you weren't watching
at the time. It also survives monitor restarts. Clear it once you've
noted the intrusion:

```bash
sudo honeypot-kit led clear-alert
sudo honeypot-kit monitor restart
```

---

## OLED Display Layout

The 128x64 display shows four lines of information:

```
IP: 192.168.1.42
Atk: 1247  Rate: 3/m
Sessions: 1
Disk:42%  Up:2d 4h
```

The 128x128 display adds memory usage and last attacker IP.

---

## Changing GPIO Pins

If the default GPIO pins conflict with other hardware you have connected,
change them via the CLI:

```bash
honeypot-kit led set-pins --red 23 --yellow 24 --green 25
honeypot-kit monitor restart
```

The CLI validates that pins are in the valid BCM range (2-27) and that
no two LEDs share a pin.

---

## Monitor Service

The hardware monitor runs as a systemd service (`honeypot-monitor`).
Manage it via the CLI:

```bash
honeypot-kit monitor start
honeypot-kit monitor stop
honeypot-kit monitor restart
honeypot-kit monitor status
```

Or directly via systemctl:

```bash
sudo systemctl start honeypot-monitor
sudo systemctl status honeypot-monitor
journalctl -u honeypot-monitor -n 50
```

The monitor service is separate from the Cowrie service. Restarting the
monitor does not affect the honeypot.

---

## Troubleshooting

**OLED display is blank after enabling:**
- Confirm I2C is enabled: `raspi-config` → Interface Options → I2C
- Confirm address with: `i2cdetect -y 1`
- Set the correct address: `honeypot-kit oled set-address 0x3D`
- Check monitor service: `honeypot-kit monitor status`

**LEDs not lighting up:**
- Run the test as root: `sudo honeypot-kit led test`
- Confirm GPIO pins are correct and not in use by another service
- Check wiring against the table above

**Monitor service not starting:**
- Check logs: `journalctl -u honeypot-monitor -n 50`
- Confirm at least one module is enabled: `honeypot-kit status`
- Confirm Python libraries are installed: `pip3 show adafruit-circuitpython-ssd1306`

---

## Future Display Support

The monitor daemon uses a pluggable display driver architecture. Future
planned display additions include:

- 3.5" 320x480 resistive touchscreen (SPI)
- 3.5" 320x480 capacitive touchscreen
- 4" 480x800 resistive touchscreen

These will be added as additional drivers without changing the core
daemon or layout code.

---

If you encounter issues not covered here, please open an issue on the
[GitHub repository](https://github.com/ericburnsonline/honeypot-kit).
