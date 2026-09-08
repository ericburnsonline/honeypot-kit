#!/usr/bin/env python3
"""
Honeypot Kit - Hardware Monitor Daemon
Version: 3

Drives the OLED display and LED status indicators based on live
honeypot state. Reads Cowrie's JSON log and system metrics, updates
all configured output devices on a regular interval.

Display architecture: all output is rendered to a PIL Image object
first. Each display driver receives that Image and handles its own
hardware output. Layouts and data logic are written once; drivers
are swappable.

LED state table:
  Healthy, idle              Green solid, Yellow off,  Red off
  Active attack session      Green solid, Yellow slow flash (1s)
  High attack rate >10/min   Green solid, Yellow fast flash (0.25s)
  Cowrie warning/disk >85%   Green off,   Yellow solid, Red off
  Cowrie down, restarting    Green off,   Yellow fast flash, Red slow flash
  Cowrie failed/disk >95%    Green off,   Yellow off,  Red solid
  Critical error             Green off,   Yellow off,  Red fast flash
  Startup sequence           All three slow flash in sequence
  Shutdown                   All off

Run as a systemd service. See honeypot-monitor.service.
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import configparser
import subprocess
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONF_FILE    = "/opt/honeypot/honeypot-kit.conf"
COWRIE_LOG   = "/opt/honeypot/cowrie/var/log/cowrie/cowrie.json"
LOG_FILE     = "/opt/honeypot/logs/monitor.log"
STATE_FILE   = "/opt/honeypot/monitor-state.json"  # persists login_history across restarts
UPDATE_SECS  = 5      # how often to refresh display and LEDs
ATTACK_WINDOW = 60    # seconds to look back when calculating attack rate
HIGH_RATE_THRESHOLD = 10  # attacks per minute to trigger fast flash

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("honeypot-monitor")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown = threading.Event()

def _handle_signal(signum, frame):
    log.info(f"Signal {signum} received - shutting down.")
    _shutdown.set()

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config():
    config = configparser.ConfigParser()
    config.read(CONF_FILE)
    return config

# ---------------------------------------------------------------------------
# Honeypot state
# ---------------------------------------------------------------------------

class HoneypotState:
    """
    Reads Cowrie's JSON log and system metrics.
    Maintains a rolling window of recent events.
    """

    def __init__(self):
        self.attack_count    = 0
        self.active_sessions = 0
        self.last_attacker   = "none"
        self.recent_events   = deque()   # (timestamp, event_id) tuples
        self._active_sessions = set()    # persistent across calls
        self.login_history   = self._load_login_history()
        self.cowrie_running  = False
        self.disk_pct        = 0
        self.mem_pct         = 0
        self.uptime_str      = "unknown"
        self.ip_address      = "unknown"
        self._log_pos        = os.path.getsize(COWRIE_LOG) if os.path.exists(COWRIE_LOG) else 0
        self._last_read      = 0

    def _load_login_history(self):
        """Load login_history from state file so it persists across restarts."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    data = json.load(f)
                return data.get("login_history", False)
        except Exception:
            pass
        return False

    def _save_login_history(self):
        """Persist login_history to state file."""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"login_history": self.login_history}, f)
        except Exception as e:
            log.warning(f"Could not save state: {e}")

    def refresh(self):
        self._check_cowrie()
        self._check_system()
        self._read_log()
        self._prune_events()

    def _check_cowrie(self):
        try:
            result = subprocess.run(
                ["pgrep", "-u", "cowrie"],
                capture_output=True
            )
            self.cowrie_running = result.returncode == 0
        except Exception:
            self.cowrie_running = False

    def _check_system(self):
        # Disk
        try:
            result = subprocess.run(
                ["df", "/", "--output=pcent"],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                self.disk_pct = int(lines[1].strip().rstrip("%"))
        except Exception:
            self.disk_pct = 0

        # Memory
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            meminfo = {}
            for line in lines:
                parts = line.split()
                meminfo[parts[0].rstrip(":")] = int(parts[1])
            total = meminfo.get("MemTotal", 1)
            avail = meminfo.get("MemAvailable", 1)
            self.mem_pct = int((1 - avail / total) * 100)
        except Exception:
            self.mem_pct = 0

        # Uptime
        try:
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            td = timedelta(seconds=int(secs))
            hours, rem = divmod(td.seconds, 3600)
            mins  = rem // 60
            days  = td.days
            if days > 0:
                self.uptime_str = f"{days}d {hours}h"
            else:
                self.uptime_str = f"{hours}h {mins}m"
        except Exception:
            self.uptime_str = "unknown"

        # IP address
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True
            )
            ips = result.stdout.strip().split()
            self.ip_address = ips[0] if ips else "unknown"
        except Exception:
            self.ip_address = "unknown"

    def _read_log(self):
        """Tail the Cowrie JSON log for new events."""
        log_path = Path(COWRIE_LOG)
        if not log_path.exists():
            log.warning(f"Cowrie JSON log not found: {COWRIE_LOG}")
            return

        try:
            with open(log_path, "r") as f:
                f.seek(self._log_pos)
                lines = f.readlines()
                self._log_pos = f.tell()

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_id = event.get("eventid", "")
                src_ip   = event.get("src_ip", "")
                session  = event.get("session", "")

                # Count login attempts
                if "login" in event_id:
                    self.attack_count += 1
                    self.recent_events.append((time.time(), event_id))
                    if src_ip:
                        self.last_attacker = src_ip
                    if event_id == "cowrie.login.success":
                        if not self.login_history:
                            self.login_history = True
                            self._save_login_history()

                # Track active sessions persistently
                # Also add on login.success in case session.connect was missed
                if event_id in ("cowrie.session.connect", "cowrie.login.success") and session:
                    self._active_sessions.add(session)
                if event_id in ("cowrie.session.closed", "cowrie.session.close") and session:
                    self._active_sessions.discard(session)

            self.active_sessions = len(self._active_sessions)

        except Exception as e:
            log.warning(f"Log read error: {e}")

    def _prune_events(self):
        """Remove events older than the attack window."""
        cutoff = time.time() - ATTACK_WINDOW
        while self.recent_events and self.recent_events[0][0] < cutoff:
            self.recent_events.popleft()

    @property
    def attack_rate(self):
        """Attacks per minute in the recent window."""
        return len(self.recent_events)

    @property
    def led_state(self):
        """
        Returns a string token describing the current LED state.
        Used by the LED controller to decide flash patterns.
        """
        if not self.cowrie_running:
            if self.disk_pct >= 95:
                return "critical"
            return "cowrie_down"
        if self.disk_pct >= 95:
            return "critical"
        if self.disk_pct >= 85 or self.mem_pct >= 90:
            return "warning"
        if self.attack_rate >= HIGH_RATE_THRESHOLD:
            return "high_rate"
        if self.active_sessions > 0:
            return "active_session"
        if self.login_history:
            return "login_history"
        return "healthy"


# ---------------------------------------------------------------------------
# LED Controller
# ---------------------------------------------------------------------------

class LEDController:
    """
    Drives Red/Yellow/Green LEDs with solid and flash patterns.
    Runs flash timing on a background thread so the main loop
    is not blocked.
    """

    FLASH_SLOW = 1.0    # seconds per cycle
    FLASH_FAST = 0.25

    def __init__(self, pin_red, pin_yellow, pin_green):
        self.pin_red    = pin_red
        self.pin_yellow = pin_yellow
        self.pin_green  = pin_green
        self._thread    = None
        self._stop      = threading.Event()
        self._gpio_ok   = False
        self._init_gpio()

    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in (self.pin_red, self.pin_yellow, self.pin_green):
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            self._GPIO    = GPIO
            self._gpio_ok = True
            log.info("GPIO initialised for LEDs.")
        except ImportError:
            log.warning("RPi.GPIO not available - LED output disabled.")
        except Exception as e:
            log.warning(f"GPIO init failed: {e}")

    def _set(self, red, yellow, green):
        if not self._gpio_ok:
            return
        self._GPIO.output(self.pin_red,    self._GPIO.HIGH if red    else self._GPIO.LOW)
        self._GPIO.output(self.pin_yellow, self._GPIO.HIGH if yellow else self._GPIO.LOW)
        self._GPIO.output(self.pin_green,  self._GPIO.HIGH if green  else self._GPIO.LOW)

    def startup_sequence(self):
        """Flash each LED in sequence to show hardware is alive."""
        if not self._gpio_ok:
            return
        for pin in (self.pin_green, self.pin_yellow, self.pin_red):
            self._GPIO.output(pin, self._GPIO.HIGH)
            time.sleep(0.4)
            self._GPIO.output(pin, self._GPIO.LOW)
            time.sleep(0.1)

    def all_off(self):
        if not self._gpio_ok:
            return
        self._set(False, False, False)

    def _stop_thread(self):
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=2)
            self._stop.clear()

    def apply_state(self, state):
        """
        Apply LED pattern for a given state token.
        Stops any running flash thread first.
        """
        self._stop_thread()

        patterns = {
            # state             red             yellow          green
            "healthy":         (False,          False,          "solid"),
            "login_history":   ("alert_blink",  False,          "solid"),
            "active_session":  (False,          "slow",         "solid"),
            "high_rate":       (False,          "fast",         "solid"),
            "warning":         (False,          "solid",        False),
            "cowrie_down":     ("slow",         "fast",         False),
            "critical":        ("fast",         False,          False),
        }

        pattern = patterns.get(state, ("fast", False, False))
        red_p, yel_p, grn_p = pattern

        # Set solid pins immediately
        self._set(
            red_p    == "solid",
            yel_p    == "solid",
            grn_p    == "solid",
        )

        # Determine if any flashing is needed
        flash_pins = []
        if red_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_red,    red_p))
        if yel_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_yellow, yel_p))
        if grn_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_green,  grn_p))

        if flash_pins and self._gpio_ok:
            self._thread = threading.Thread(
                target=self._flash_loop,
                args=(flash_pins,),
                daemon=True
            )
            self._thread.start()

    def _flash_loop(self, flash_pins):
        """Run flash patterns until _stop is set."""
        states = {pin: False for pin, _ in flash_pins}
        while not self._stop.is_set() and not _shutdown.is_set():
            for pin, speed in flash_pins:
                if speed == "alert_blink":
                    # Short blink: on 0.2s, off 2.8s
                    self._GPIO.output(pin, self._GPIO.HIGH)
                    self._stop.wait(0.2)
                    if self._stop.is_set() or _shutdown.is_set():
                        break
                    self._GPIO.output(pin, self._GPIO.LOW)
                    self._stop.wait(2.8)
                else:
                    states[pin] = not states[pin]
                    self._GPIO.output(
                        pin,
                        self._GPIO.HIGH if states[pin] else self._GPIO.LOW
                    )
            if not any(s == "alert_blink" for _, s in flash_pins):
                interval = self.FLASH_FAST if any(
                    s == "fast" for _, s in flash_pins
                ) else self.FLASH_SLOW
                self._stop.wait(interval / 2)

    def cleanup(self):
        self._stop_thread()
        self.all_off()
        if self._gpio_ok:
            try:
                self._GPIO.cleanup()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Display Driver Base
# ---------------------------------------------------------------------------

class DisplayDriver:
    """Abstract base class for all display drivers."""

    def render(self, image):
        raise NotImplementedError

    def cleanup(self):
        pass


# ---------------------------------------------------------------------------
# SSD1306 / SSD1315 / SSD1309 I2C OLED Driver
# ---------------------------------------------------------------------------

class OLEDDriver(DisplayDriver):
    """
    Supports SSD1306 and SSD1315 (0.96" 128x64, 0.91" 128x32) and
    SSD1309 (2.42" 128x64) via adafruit-circuitpython-ssd1306.
    All use the same Adafruit library; driver is selected by resolution.
    """

    def __init__(self, i2c_address, resolution):
        self._display = None
        self._width   = 128
        self._height  = 64
        self._addr    = int(i2c_address, 16)

        w, h = map(int, resolution.split("x"))
        self._width  = w
        self._height = h

        self._init_display()

    def _init_display(self):
        # Check I2C is available before attempting to import hardware libs
        if not os.path.exists("/dev/i2c-1"):
            log.warning(
                "I2C not detected (/dev/i2c-1 missing). "
                "OLED disabled. Reboot if I2C was just enabled, or run: "
                "sudo raspi-config -> Interface Options -> I2C -> Yes"
            )
            return
        try:
            import board
            import busio
            import adafruit_ssd1306

            i2c = busio.I2C(board.SCL, board.SDA)
            self._display = adafruit_ssd1306.SSD1306_I2C(
                self._width, self._height, i2c, addr=self._addr
            )
            self._display.fill(0)
            self._display.show()
            log.info(f"OLED initialised ({self._width}x{self._height} @ 0x{self._addr:02X}).")
        except ImportError as e:
            log.warning(f"OLED library not available: {e}")
        except Exception as e:
            log.warning(f"OLED init failed: {e}")

    def render(self, image):
        if not self._display:
            return
        try:
            # Scale image to display resolution if needed
            if image.size != (self._width, self._height):
                image = image.resize(
                    (self._width, self._height)
                )
            # Convert to 1-bit for monochrome OLED
            mono = image.convert("1")
            self._display.image(mono)
            self._display.show()
        except Exception as e:
            log.warning(f"OLED render error: {e}")

    def cleanup(self):
        if self._display:
            try:
                self._display.fill(0)
                self._display.show()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# ILI9486 / SPI TFT Framebuffer Driver (320x480)
# ---------------------------------------------------------------------------

class TFTDriver(DisplayDriver):
    """
    Driver for SPI TFT displays that appear as a Linux framebuffer device.
    Tested with ILI9486-based 3.5" 320x480 displays (e.g. MHS-3.5inch RPi Display).

    The display must have its kernel driver installed first. The display will
    appear as /dev/fb1. Install the driver following the manufacturer guide:
    http://www.lcdwiki.com/MHS-3.5inch_RPi_Display

    IMPORTANT: When this SPI display is connected, the GPIO header pins used
    by the LED traffic light module are unavailable. You cannot use both
    the TFT display and LED module simultaneously.

    Rendering path: PIL Image -> numpy array -> /dev/fb1 framebuffer
    The framebuffer uses 16-bit RGB565 color format.
    """

    def __init__(self, fb_device="/dev/fb1", width=320, height=480):
        self._fb_device = fb_device
        self._width     = width
        self._height    = height
        self._available = False
        self._init_fb()

    def _init_fb(self):
        if not os.path.exists(self._fb_device):
            log.warning(
                f"TFT framebuffer {self._fb_device} not found. "
                f"Install the display driver first. "
                f"See: http://www.lcdwiki.com/MHS-3.5inch_RPi_Display"
            )
            return
        try:
            # Test write access
            with open(self._fb_device, "wb"):
                pass
            self._available = True
            log.info(f"TFT display initialised ({self._width}x{self._height} @ {self._fb_device}).")
        except PermissionError:
            log.warning(
                f"Permission denied on {self._fb_device}. "
                f"Add user to video group: sudo usermod -a -G video $USER"
            )
        except Exception as e:
            log.warning(f"TFT init failed: {e}")

    def _image_to_rgb565(self, image):
        """Convert PIL Image to RGB565 bytes for framebuffer."""
        try:
            import numpy as np
        except ImportError:
            log.warning("numpy not installed - TFT output disabled. Run: sudo apt-get install python3-numpy")
            return None

        # Ensure correct size
        if image.size != (self._width, self._height):
            image = image.resize((self._width, self._height))

        rgb = image.convert("RGB")
        arr = np.array(rgb, dtype=np.uint16)

        # RGB888 -> RGB565
        r = (arr[:, :, 0] >> 3).astype(np.uint16)
        g = (arr[:, :, 1] >> 2).astype(np.uint16)
        b = (arr[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = (r << 11) | (g << 5) | b

        return rgb565.tobytes()

    def render(self, image):
        if not self._available:
            return
        try:
            data = self._image_to_rgb565(image)
            if data:
                with open(self._fb_device, "wb") as fb:
                    fb.write(data)
        except Exception as e:
            log.warning(f"TFT render error: {e}")

    def cleanup(self):
        if not self._available:
            return
        try:
            # Clear display to black
            size = self._width * self._height * 2  # 2 bytes per pixel (RGB565)
            with open(self._fb_device, "wb") as fb:
                fb.write(b"\x00" * size)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Layout renderer
# ---------------------------------------------------------------------------

def render_small_layout(state, width=128, height=64):
    """
    Renders honeypot state to a PIL Image for small OLED displays.
    Returns a PIL Image object in RGB mode.
    Display drivers convert to their required format.

    Layout (128x64):
      Line 0 (y=0):  IP address
      Line 1 (y=16): Attack count + rate
      Line 2 (y=32): Active sessions
      Line 3 (y=48): Disk % and uptime
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.warning("Pillow not available - display output disabled.")
        return None

    image = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw  = ImageDraw.Draw(image)

    # Use default bitmap font - always available, no file path needed
    font = ImageFont.load_default()

    white = (255, 255, 255)
    grey  = (180, 180, 180)

    # Line 0 - IP
    draw.text((0, 0),  f"IP: {state.ip_address}",     font=font, fill=white)

    # Line 1 - attacks
    draw.text((0, 16), f"Atk: {state.attack_count}  Rate: {state.attack_rate}/m",
              font=font, fill=white)

    # Line 2 - sessions
    session_text = f"Sessions: {state.active_sessions}"
    if state.active_sessions > 0:
        draw.text((0, 32), session_text, font=font, fill=(255, 200, 0))
    else:
        draw.text((0, 32), session_text, font=font, fill=grey)

    # Line 3 - disk and uptime
    draw.text((0, 48), f"Disk:{state.disk_pct}%  Up:{state.uptime_str}",
              font=font, fill=grey)

    return image


def render_square_layout(state, width=128, height=128):
    """
    Renders honeypot state to a PIL Image for square OLED displays (SH1107).
    More vertical space allows additional metrics.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    image = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw  = ImageDraw.Draw(image)
    font  = ImageFont.load_default()
    white = (255, 255, 255)
    grey  = (180, 180, 180)
    amber = (255, 200, 0)

    draw.text((0, 0),   "Honeypot Kit",               font=font, fill=white)
    draw.text((0, 16),  f"IP: {state.ip_address}",    font=font, fill=white)
    draw.text((0, 32),  f"Attacks: {state.attack_count}", font=font, fill=white)
    draw.text((0, 48),  f"Rate: {state.attack_rate}/min", font=font, fill=white)

    session_color = amber if state.active_sessions > 0 else grey
    draw.text((0, 64),  f"Sessions: {state.active_sessions}",
              font=font, fill=session_color)

    draw.text((0, 80),  f"Disk: {state.disk_pct}%",   font=font, fill=grey)
    draw.text((0, 96),  f"Mem:  {state.mem_pct}%",    font=font, fill=grey)
    draw.text((0, 112), f"Up: {state.uptime_str}",    font=font, fill=grey)

    return image


def _draw_led(draw, cx, cy, radius, color_on, color_off, state, label, font):
    """
    Draw a circular LED indicator with glow effect.
    state: True=on, False=off, 'blink'=half-bright
    """
    if state is True:
        # Lit LED - draw glow ring then bright center
        glow_color = tuple(min(255, int(c * 0.3)) for c in color_on)
        draw.ellipse(
            [(cx - radius - 4, cy - radius - 4),
             (cx + radius + 4, cy + radius + 4)],
            fill=glow_color
        )
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=color_on
        )
        # Specular highlight
        draw.ellipse(
            [(cx - radius // 3, cy - radius // 2),
             (cx + radius // 5, cy - radius // 4)],
            fill=tuple(min(255, c + 80) for c in color_on)
        )
    elif state == "blink":
        # Half-brightness blink state
        dim = tuple(c // 3 for c in color_on)
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=dim
        )
    else:
        # Off LED - dark with subtle rim
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=color_off
        )
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            outline=tuple(c + 20 for c in color_off),
            width=1
        )
    # Label below LED
    draw.text((cx - 12, cy + radius + 4), label, font=font, fill=(160, 160, 180))


def _led_states_from_honeypot_state(led_state):
    """
    Return (green_on, yellow_on, red_on) display states
    based on current honeypot LED state token.
    Maps state machine to visual representation.
    'blink' means show dim/half-lit for animated states.
    """
    states = {
        # state          green   yellow    red
        "healthy":      (True,   False,    False),
        "login_history":(True,   False,    "blink"),
        "active_session":(True,  "blink",  False),
        "high_rate":    (True,   True,     False),
        "warning":      (False,  True,     False),
        "cowrie_down":  (False,  "blink",  "blink"),
        "critical":     (False,  False,    True),
    }
    return states.get(led_state, (False, False, "blink"))


def render_large_layout(state, width=320, height=480):
    """
    Renders honeypot state to a PIL Image for large color TFT displays.
    Portrait layout (320x480) with:
      - Title bar with IP and uptime
      - Attack stats panel
      - System health panel
      - LED emulation panel (three circles: Green/Yellow/Red)
      - Status description
      - Timestamp footer

    Designed for ILI9486-based 3.5" SPI displays that occupy GPIO
    and cannot run physical LEDs simultaneously.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    from datetime import datetime, timezone

    # Color palette
    BG          = (12,  12,  22)
    PANEL_BG    = (22,  22,  40)
    PANEL_EDGE  = (40,  40,  70)
    WHITE       = (240, 240, 250)
    GREEN_ON    = (50,  220, 80)
    GREEN_OFF   = (10,  35,  15)
    YELLOW_ON   = (230, 190, 0)
    YELLOW_OFF  = (35,  30,  5)
    RED_ON      = (220, 50,  50)
    RED_OFF     = (35,  10,  10)
    GREY        = (110, 110, 135)
    CYAN        = (0,   190, 215)
    AMBER       = (255, 160, 0)

    image = Image.new("RGB", (width, height), color=BG)
    draw  = ImageDraw.Draw(image)
    font  = ImageFont.load_default()

    # ---------------------------------------------------------------------------
    # Title bar
    # ---------------------------------------------------------------------------
    draw.rectangle([(0, 0), (width, 26)], fill=(25, 25, 55))
    draw.text((8, 6),   "🍯 Honeypot Kit", font=font, fill=CYAN)
    draw.text((width - 70, 6), f"up {state.uptime_str}", font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # IP + time row
    # ---------------------------------------------------------------------------
    now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    draw.text((8, 32),          f"IP: {state.ip_address}", font=font, fill=WHITE)
    draw.text((width - 60, 32), now_str,                   font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # LED emulation panel
    # ---------------------------------------------------------------------------
    led_panel_y = 52
    led_panel_h = 90
    draw.rectangle(
        [(6, led_panel_y), (width - 6, led_panel_y + led_panel_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, led_panel_y + 5), "STATUS INDICATORS", font=font, fill=GREY)

    led_state  = state.led_state
    g_on, y_on, r_on = _led_states_from_honeypot_state(led_state)

    led_y   = led_panel_y + 35
    led_r   = 18
    spacing = width // 4

    _draw_led(draw, spacing,       led_y, led_r, GREEN_ON,  GREEN_OFF,  g_on, "GRN", font)
    _draw_led(draw, spacing * 2,   led_y, led_r, YELLOW_ON, YELLOW_OFF, y_on, "YLW", font)
    _draw_led(draw, spacing * 3,   led_y, led_r, RED_ON,    RED_OFF,    r_on, "RED", font)

    # State description under LEDs
    state_labels = {
        "healthy":        ("Healthy - idle",           WHITE),
        "login_history":  ("Login alert - clear?",     RED_ON),
        "active_session": ("Active attack session",    YELLOW_ON),
        "high_rate":      ("High attack rate!",        RED_ON),
        "warning":        ("Warning - check system",   YELLOW_ON),
        "cowrie_down":    ("Cowrie not running!",      RED_ON),
        "critical":       ("CRITICAL ERROR",           RED_ON),
    }
    state_text, state_color = state_labels.get(led_state, (led_state, WHITE))
    text_x = max(8, (width - len(state_text) * 6) // 2)
    draw.text((text_x, led_panel_y + led_panel_h - 16), state_text, font=font, fill=state_color)

    # ---------------------------------------------------------------------------
    # Attack stats panel
    # ---------------------------------------------------------------------------
    atk_y = led_panel_y + led_panel_h + 8
    atk_h = 85
    draw.rectangle(
        [(6, atk_y), (width - 6, atk_y + atk_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, atk_y + 5), "ATTACK DATA", font=font, fill=GREY)

    atk_color  = RED_ON  if state.attack_count > 100 else \
                 AMBER   if state.attack_count > 10  else WHITE
    rate_color = RED_ON  if state.attack_rate >= 10  else \
                 AMBER   if state.attack_rate > 0    else GREEN_ON
    sess_color = AMBER   if state.active_sessions > 0 else GREY

    draw.text((12, atk_y + 20), f"Total attacks  : {state.attack_count}", font=font, fill=atk_color)
    draw.text((12, atk_y + 36), f"Rate/min       : {state.attack_rate}",  font=font, fill=rate_color)
    draw.text((12, atk_y + 52), f"Active sessions: {state.active_sessions}", font=font, fill=sess_color)

    last_ip = state.last_attacker if state.last_attacker and state.last_attacker != "none" else "none yet"
    draw.text((12, atk_y + 68), f"Last attacker  : {last_ip[:20]}", font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # System health panel
    # ---------------------------------------------------------------------------
    sys_y = atk_y + atk_h + 8
    sys_h = 85
    draw.rectangle(
        [(6, sys_y), (width - 6, sys_y + sys_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, sys_y + 5), "SYSTEM HEALTH", font=font, fill=GREY)

    disk_color   = RED_ON  if state.disk_pct > 85 else AMBER if state.disk_pct > 70 else GREEN_ON
    mem_color    = RED_ON  if state.mem_pct  > 90 else AMBER if state.mem_pct  > 75 else GREEN_ON
    cowrie_color = GREEN_ON if state.cowrie_running else RED_ON
    cowrie_text  = "RUNNING" if state.cowrie_running else "STOPPED"

    draw.text((12, sys_y + 20), f"Disk     : {state.disk_pct}%",   font=font, fill=disk_color)
    draw.text((12, sys_y + 36), f"Memory   : {state.mem_pct}%",    font=font, fill=mem_color)
    draw.text((12, sys_y + 52), f"Cowrie   : {cowrie_text}",       font=font, fill=cowrie_color)
    draw.text((12, sys_y + 68), f"I2C OLED : {'active' if False else 'N/A (SPI mode)'}",
              font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # Mini bar graphs for disk and memory
    # ---------------------------------------------------------------------------
    bar_x     = 160
    bar_w     = width - bar_x - 14
    bar_h_px  = 6

    # Disk bar
    bar_y = sys_y + 23
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h_px)], fill=(40, 40, 60))
    fill_w = int(bar_w * state.disk_pct / 100)
    draw.rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h_px)], fill=disk_color)

    # Memory bar
    bar_y = sys_y + 39
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h_px)], fill=(40, 40, 60))
    fill_w = int(bar_w * state.mem_pct / 100)
    draw.rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h_px)], fill=mem_color)

    # ---------------------------------------------------------------------------
    # Footer
    # ---------------------------------------------------------------------------
    footer_y = height - 20
    draw.rectangle([(0, footer_y), (width, height)], fill=(25, 25, 55))
    draw.text((8, footer_y + 4), "github.com/ericburnsonline/honeypot-kit", font=font, fill=(60, 60, 90))

    return image


def render_for_resolution(state, resolution):
    """Select layout based on configured resolution."""
    w, h = map(int, resolution.split("x"))
    if w >= 320 or h >= 320:
        return render_large_layout(state, w, h)
    if h >= 128:
        return render_square_layout(state, w, h)
    return render_small_layout(state, w, h)


# ---------------------------------------------------------------------------
# Main monitor loop
# ---------------------------------------------------------------------------

def main():
    log.info("Honeypot monitor daemon starting.")

    config = load_config()

    oled_enabled = config.get("oled", "enabled", fallback="false").lower() == "true"
    led_enabled  = config.get("led",  "enabled", fallback="false").lower() == "true"
    tft_enabled  = config.get("tft",  "enabled", fallback="false").lower() == "true"

    # Initialise hardware
    oled_driver = None
    tft_driver  = None
    led_ctrl    = None

    if oled_enabled:
        addr = config.get("oled", "i2c_address", fallback="0x3C")
        res  = config.get("oled", "resolution",  fallback="128x64")
        oled_driver = OLEDDriver(addr, res)

    if tft_enabled:
        fb  = config.get("tft", "fb_device",   fallback="/dev/fb1")
        res = config.get("tft", "resolution",  fallback="320x480")
        w, h = map(int, res.split("x"))
        tft_driver = TFTDriver(fb, w, h)
        if tft_enabled and led_enabled:
            log.warning(
                "TFT SPI display and LED module both enabled. "
                "GPIO pins are unavailable when SPI display is connected - "
                "LED output will be disabled."
            )
            led_enabled = False

    if led_enabled:
        pin_red    = int(config.get("led", "pin_red",    fallback="17"))
        pin_yellow = int(config.get("led", "pin_yellow", fallback="27"))
        pin_green  = int(config.get("led", "pin_green",  fallback="22"))
        led_ctrl   = LEDController(pin_red, pin_yellow, pin_green)
        led_ctrl.startup_sequence()

    state = HoneypotState()
    last_led_state = None

    log.info(f"Monitor running. OLED: {oled_enabled}, TFT: {tft_enabled}, LED: {led_enabled}.")

    while not _shutdown.is_set():
        try:
            state.refresh()

            # Update OLED
            if oled_driver:
                res   = config.get("oled", "resolution", fallback="128x64")
                image = render_for_resolution(state, res)
                if image:
                    oled_driver.render(image)

            # Update TFT
            if tft_driver:
                res   = config.get("tft", "resolution", fallback="320x480")
                image = render_for_resolution(state, res)
                if image:
                    tft_driver.render(image)

            # Update LEDs only when state changes
            if led_ctrl:
                current_led_state = state.led_state
                if current_led_state != last_led_state:
                    led_ctrl.apply_state(current_led_state)
                    last_led_state = current_led_state
                    log.info(f"LED state: {current_led_state}")

        except Exception as e:
            log.error(f"Monitor loop error: {e}")

        _shutdown.wait(UPDATE_SECS)

    # Shutdown
    log.info("Shutting down hardware monitor.")
    if oled_driver:
        oled_driver.cleanup()
    if tft_driver:
        tft_driver.cleanup()
    if led_ctrl:
        led_ctrl.cleanup()
    log.info("Hardware monitor stopped.")


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
Honeypot Kit - Hardware Monitor Daemon
Version: 3

Drives the OLED display and LED status indicators based on live
honeypot state. Reads Cowrie's JSON log and system metrics, updates
all configured output devices on a regular interval.

Display architecture: all output is rendered to a PIL Image object
first. Each display driver receives that Image and handles its own
hardware output. Layouts and data logic are written once; drivers
are swappable.

LED state table:
  Healthy, idle              Green solid, Yellow off,  Red off
  Active attack session      Green solid, Yellow slow flash (1s)
  High attack rate >10/min   Green solid, Yellow fast flash (0.25s)
  Cowrie warning/disk >85%   Green off,   Yellow solid, Red off
  Cowrie down, restarting    Green off,   Yellow fast flash, Red slow flash
  Cowrie failed/disk >95%    Green off,   Yellow off,  Red solid
  Critical error             Green off,   Yellow off,  Red fast flash
  Startup sequence           All three slow flash in sequence
  Shutdown                   All off

Run as a systemd service. See honeypot-monitor.service.
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import configparser
import subprocess
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONF_FILE    = "/opt/honeypot/honeypot-kit.conf"
COWRIE_LOG   = "/opt/honeypot/cowrie/var/log/cowrie/cowrie.json"
LOG_FILE     = "/opt/honeypot/logs/monitor.log"
STATE_FILE   = "/opt/honeypot/monitor-state.json"  # persists login_history across restarts
UPDATE_SECS  = 5      # how often to refresh display and LEDs
ATTACK_WINDOW = 60    # seconds to look back when calculating attack rate
HIGH_RATE_THRESHOLD = 10  # attacks per minute to trigger fast flash

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("honeypot-monitor")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown = threading.Event()

def _handle_signal(signum, frame):
    log.info(f"Signal {signum} received - shutting down.")
    _shutdown.set()

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config():
    config = configparser.ConfigParser()
    config.read(CONF_FILE)
    return config

# ---------------------------------------------------------------------------
# Honeypot state
# ---------------------------------------------------------------------------

class HoneypotState:
    """
    Reads Cowrie's JSON log and system metrics.
    Maintains a rolling window of recent events.
    """

    def __init__(self):
        self.attack_count    = 0
        self.active_sessions = 0
        self.last_attacker   = "none"
        self.recent_events   = deque()   # (timestamp, event_id) tuples
        self._active_sessions = set()    # persistent across calls
        self.login_history   = self._load_login_history()
        self.cowrie_running  = False
        self.disk_pct        = 0
        self.mem_pct         = 0
        self.uptime_str      = "unknown"
        self.ip_address      = "unknown"
        self._log_pos        = os.path.getsize(COWRIE_LOG) if os.path.exists(COWRIE_LOG) else 0
        self._last_read      = 0

    def _load_login_history(self):
        """Load login_history from state file so it persists across restarts."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    data = json.load(f)
                return data.get("login_history", False)
        except Exception:
            pass
        return False

    def _save_login_history(self):
        """Persist login_history to state file."""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"login_history": self.login_history}, f)
        except Exception as e:
            log.warning(f"Could not save state: {e}")

    def refresh(self):
        self._check_cowrie()
        self._check_system()
        self._read_log()
        self._prune_events()

    def _check_cowrie(self):
        try:
            result = subprocess.run(
                ["pgrep", "-u", "cowrie"],
                capture_output=True
            )
            self.cowrie_running = result.returncode == 0
        except Exception:
            self.cowrie_running = False

    def _check_system(self):
        # Disk
        try:
            result = subprocess.run(
                ["df", "/", "--output=pcent"],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                self.disk_pct = int(lines[1].strip().rstrip("%"))
        except Exception:
            self.disk_pct = 0

        # Memory
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            meminfo = {}
            for line in lines:
                parts = line.split()
                meminfo[parts[0].rstrip(":")] = int(parts[1])
            total = meminfo.get("MemTotal", 1)
            avail = meminfo.get("MemAvailable", 1)
            self.mem_pct = int((1 - avail / total) * 100)
        except Exception:
            self.mem_pct = 0

        # Uptime
        try:
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            td = timedelta(seconds=int(secs))
            hours, rem = divmod(td.seconds, 3600)
            mins  = rem // 60
            days  = td.days
            if days > 0:
                self.uptime_str = f"{days}d {hours}h"
            else:
                self.uptime_str = f"{hours}h {mins}m"
        except Exception:
            self.uptime_str = "unknown"

        # IP address
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True
            )
            ips = result.stdout.strip().split()
            self.ip_address = ips[0] if ips else "unknown"
        except Exception:
            self.ip_address = "unknown"

    def _read_log(self):
        """Tail the Cowrie JSON log for new events."""
        log_path = Path(COWRIE_LOG)
        if not log_path.exists():
            log.warning(f"Cowrie JSON log not found: {COWRIE_LOG}")
            return

        try:
            with open(log_path, "r") as f:
                f.seek(self._log_pos)
                lines = f.readlines()
                self._log_pos = f.tell()

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_id = event.get("eventid", "")
                src_ip   = event.get("src_ip", "")
                session  = event.get("session", "")

                # Count login attempts
                if "login" in event_id:
                    self.attack_count += 1
                    self.recent_events.append((time.time(), event_id))
                    if src_ip:
                        self.last_attacker = src_ip
                    if event_id == "cowrie.login.success":
                        if not self.login_history:
                            self.login_history = True
                            self._save_login_history()

                # Track active sessions persistently
                # Also add on login.success in case session.connect was missed
                if event_id in ("cowrie.session.connect", "cowrie.login.success") and session:
                    self._active_sessions.add(session)
                if event_id in ("cowrie.session.closed", "cowrie.session.close") and session:
                    self._active_sessions.discard(session)

            self.active_sessions = len(self._active_sessions)

        except Exception as e:
            log.warning(f"Log read error: {e}")

    def _prune_events(self):
        """Remove events older than the attack window."""
        cutoff = time.time() - ATTACK_WINDOW
        while self.recent_events and self.recent_events[0][0] < cutoff:
            self.recent_events.popleft()

    @property
    def attack_rate(self):
        """Attacks per minute in the recent window."""
        return len(self.recent_events)

    @property
    def led_state(self):
        """
        Returns a string token describing the current LED state.
        Used by the LED controller to decide flash patterns.
        """
        if not self.cowrie_running:
            if self.disk_pct >= 95:
                return "critical"
            return "cowrie_down"
        if self.disk_pct >= 95:
            return "critical"
        if self.disk_pct >= 85 or self.mem_pct >= 90:
            return "warning"
        if self.attack_rate >= HIGH_RATE_THRESHOLD:
            return "high_rate"
        if self.active_sessions > 0:
            return "active_session"
        if self.login_history:
            return "login_history"
        return "healthy"


# ---------------------------------------------------------------------------
# LED Controller
# ---------------------------------------------------------------------------

class LEDController:
    """
    Drives Red/Yellow/Green LEDs with solid and flash patterns.
    Runs flash timing on a background thread so the main loop
    is not blocked.
    """

    FLASH_SLOW = 1.0    # seconds per cycle
    FLASH_FAST = 0.25

    def __init__(self, pin_red, pin_yellow, pin_green):
        self.pin_red    = pin_red
        self.pin_yellow = pin_yellow
        self.pin_green  = pin_green
        self._thread    = None
        self._stop      = threading.Event()
        self._gpio_ok   = False
        self._init_gpio()

    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in (self.pin_red, self.pin_yellow, self.pin_green):
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            self._GPIO    = GPIO
            self._gpio_ok = True
            log.info("GPIO initialised for LEDs.")
        except ImportError:
            log.warning("RPi.GPIO not available - LED output disabled.")
        except Exception as e:
            log.warning(f"GPIO init failed: {e}")

    def _set(self, red, yellow, green):
        if not self._gpio_ok:
            return
        self._GPIO.output(self.pin_red,    self._GPIO.HIGH if red    else self._GPIO.LOW)
        self._GPIO.output(self.pin_yellow, self._GPIO.HIGH if yellow else self._GPIO.LOW)
        self._GPIO.output(self.pin_green,  self._GPIO.HIGH if green  else self._GPIO.LOW)

    def startup_sequence(self):
        """Flash each LED in sequence to show hardware is alive."""
        if not self._gpio_ok:
            return
        for pin in (self.pin_green, self.pin_yellow, self.pin_red):
            self._GPIO.output(pin, self._GPIO.HIGH)
            time.sleep(0.4)
            self._GPIO.output(pin, self._GPIO.LOW)
            time.sleep(0.1)

    def all_off(self):
        if not self._gpio_ok:
            return
        self._set(False, False, False)

    def _stop_thread(self):
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=2)
            self._stop.clear()

    def apply_state(self, state):
        """
        Apply LED pattern for a given state token.
        Stops any running flash thread first.
        """
        self._stop_thread()

        patterns = {
            # state             red             yellow          green
            "healthy":         (False,          False,          "solid"),
            "login_history":   ("alert_blink",  False,          "solid"),
            "active_session":  (False,          "slow",         "solid"),
            "high_rate":       (False,          "fast",         "solid"),
            "warning":         (False,          "solid",        False),
            "cowrie_down":     ("slow",         "fast",         False),
            "critical":        ("fast",         False,          False),
        }

        pattern = patterns.get(state, ("fast", False, False))
        red_p, yel_p, grn_p = pattern

        # Set solid pins immediately
        self._set(
            red_p    == "solid",
            yel_p    == "solid",
            grn_p    == "solid",
        )

        # Determine if any flashing is needed
        flash_pins = []
        if red_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_red,    red_p))
        if yel_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_yellow, yel_p))
        if grn_p in ("slow", "fast", "alert_blink"):
            flash_pins.append((self.pin_green,  grn_p))

        if flash_pins and self._gpio_ok:
            self._thread = threading.Thread(
                target=self._flash_loop,
                args=(flash_pins,),
                daemon=True
            )
            self._thread.start()

    def _flash_loop(self, flash_pins):
        """Run flash patterns until _stop is set."""
        states = {pin: False for pin, _ in flash_pins}
        while not self._stop.is_set() and not _shutdown.is_set():
            for pin, speed in flash_pins:
                if speed == "alert_blink":
                    # Short blink: on 0.2s, off 2.8s
                    self._GPIO.output(pin, self._GPIO.HIGH)
                    self._stop.wait(0.2)
                    if self._stop.is_set() or _shutdown.is_set():
                        break
                    self._GPIO.output(pin, self._GPIO.LOW)
                    self._stop.wait(2.8)
                else:
                    states[pin] = not states[pin]
                    self._GPIO.output(
                        pin,
                        self._GPIO.HIGH if states[pin] else self._GPIO.LOW
                    )
            if not any(s == "alert_blink" for _, s in flash_pins):
                interval = self.FLASH_FAST if any(
                    s == "fast" for _, s in flash_pins
                ) else self.FLASH_SLOW
                self._stop.wait(interval / 2)

    def cleanup(self):
        self._stop_thread()
        self.all_off()
        if self._gpio_ok:
            try:
                self._GPIO.cleanup()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Display Driver Base
# ---------------------------------------------------------------------------

class DisplayDriver:
    """Abstract base class for all display drivers."""

    def render(self, image):
        raise NotImplementedError

    def cleanup(self):
        pass


# ---------------------------------------------------------------------------
# SSD1306 / SSD1315 / SSD1309 I2C OLED Driver
# ---------------------------------------------------------------------------

class OLEDDriver(DisplayDriver):
    """
    Supports SSD1306 and SSD1315 (0.96" 128x64, 0.91" 128x32) and
    SSD1309 (2.42" 128x64) via adafruit-circuitpython-ssd1306.
    All use the same Adafruit library; driver is selected by resolution.
    """

    def __init__(self, i2c_address, resolution):
        self._display = None
        self._width   = 128
        self._height  = 64
        self._addr    = int(i2c_address, 16)

        w, h = map(int, resolution.split("x"))
        self._width  = w
        self._height = h

        self._init_display()

    def _init_display(self):
        # Check I2C is available before attempting to import hardware libs
        if not os.path.exists("/dev/i2c-1"):
            log.warning(
                "I2C not detected (/dev/i2c-1 missing). "
                "OLED disabled. Reboot if I2C was just enabled, or run: "
                "sudo raspi-config -> Interface Options -> I2C -> Yes"
            )
            return
        try:
            import board
            import busio
            import adafruit_ssd1306

            i2c = busio.I2C(board.SCL, board.SDA)
            self._display = adafruit_ssd1306.SSD1306_I2C(
                self._width, self._height, i2c, addr=self._addr
            )
            self._display.fill(0)
            self._display.show()
            log.info(f"OLED initialised ({self._width}x{self._height} @ 0x{self._addr:02X}).")
        except ImportError as e:
            log.warning(f"OLED library not available: {e}")
        except Exception as e:
            log.warning(f"OLED init failed: {e}")

    def render(self, image):
        if not self._display:
            return
        try:
            # Scale image to display resolution if needed
            if image.size != (self._width, self._height):
                image = image.resize(
                    (self._width, self._height)
                )
            # Convert to 1-bit for monochrome OLED
            mono = image.convert("1")
            self._display.image(mono)
            self._display.show()
        except Exception as e:
            log.warning(f"OLED render error: {e}")

    def cleanup(self):
        if self._display:
            try:
                self._display.fill(0)
                self._display.show()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# ILI9486 / SPI TFT Framebuffer Driver (320x480)
# ---------------------------------------------------------------------------

class TFTDriver(DisplayDriver):
    """
    Driver for SPI TFT displays that appear as a Linux framebuffer device.
    Tested with ILI9486-based 3.5" 320x480 displays (e.g. MHS-3.5inch RPi Display).

    The display must have its kernel driver installed first. The display will
    appear as /dev/fb1. Install the driver following the manufacturer guide:
    http://www.lcdwiki.com/MHS-3.5inch_RPi_Display

    IMPORTANT: When this SPI display is connected, the GPIO header pins used
    by the LED traffic light module are unavailable. You cannot use both
    the TFT display and LED module simultaneously.

    Rendering path: PIL Image -> numpy array -> /dev/fb1 framebuffer
    The framebuffer uses 16-bit RGB565 color format.
    """

    def __init__(self, fb_device="/dev/fb1", width=320, height=480):
        self._fb_device = fb_device
        self._width     = width
        self._height    = height
        self._available = False
        self._init_fb()

    def _init_fb(self):
        if not os.path.exists(self._fb_device):
            log.warning(
                f"TFT framebuffer {self._fb_device} not found. "
                f"Install the display driver first. "
                f"See: http://www.lcdwiki.com/MHS-3.5inch_RPi_Display"
            )
            return
        try:
            # Test write access
            with open(self._fb_device, "wb"):
                pass
            self._available = True
            log.info(f"TFT display initialised ({self._width}x{self._height} @ {self._fb_device}).")
        except PermissionError:
            log.warning(
                f"Permission denied on {self._fb_device}. "
                f"Add user to video group: sudo usermod -a -G video $USER"
            )
        except Exception as e:
            log.warning(f"TFT init failed: {e}")

    def _image_to_rgb565(self, image):
        """Convert PIL Image to RGB565 bytes for framebuffer."""
        try:
            import numpy as np
        except ImportError:
            log.warning("numpy not installed - TFT output disabled. Run: sudo apt-get install python3-numpy")
            return None

        # Ensure correct size
        if image.size != (self._width, self._height):
            image = image.resize((self._width, self._height))

        rgb = image.convert("RGB")
        arr = np.array(rgb, dtype=np.uint16)

        # RGB888 -> RGB565
        r = (arr[:, :, 0] >> 3).astype(np.uint16)
        g = (arr[:, :, 1] >> 2).astype(np.uint16)
        b = (arr[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = (r << 11) | (g << 5) | b

        return rgb565.tobytes()

    def render(self, image):
        if not self._available:
            return
        try:
            data = self._image_to_rgb565(image)
            if data:
                with open(self._fb_device, "wb") as fb:
                    fb.write(data)
        except Exception as e:
            log.warning(f"TFT render error: {e}")

    def cleanup(self):
        if not self._available:
            return
        try:
            # Clear display to black
            size = self._width * self._height * 2  # 2 bytes per pixel (RGB565)
            with open(self._fb_device, "wb") as fb:
                fb.write(b"\x00" * size)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Layout renderer
# ---------------------------------------------------------------------------

def render_small_layout(state, width=128, height=64):
    """
    Renders honeypot state to a PIL Image for small OLED displays.
    Returns a PIL Image object in RGB mode.
    Display drivers convert to their required format.

    Layout (128x64):
      Line 0 (y=0):  IP address
      Line 1 (y=16): Attack count + rate
      Line 2 (y=32): Active sessions
      Line 3 (y=48): Disk % and uptime
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.warning("Pillow not available - display output disabled.")
        return None

    image = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw  = ImageDraw.Draw(image)

    # Use default bitmap font - always available, no file path needed
    font = ImageFont.load_default()

    white = (255, 255, 255)
    grey  = (180, 180, 180)

    # Line 0 - IP
    draw.text((0, 0),  f"IP: {state.ip_address}",     font=font, fill=white)

    # Line 1 - attacks
    draw.text((0, 16), f"Atk: {state.attack_count}  Rate: {state.attack_rate}/m",
              font=font, fill=white)

    # Line 2 - sessions
    session_text = f"Sessions: {state.active_sessions}"
    if state.active_sessions > 0:
        draw.text((0, 32), session_text, font=font, fill=(255, 200, 0))
    else:
        draw.text((0, 32), session_text, font=font, fill=grey)

    # Line 3 - disk and uptime
    draw.text((0, 48), f"Disk:{state.disk_pct}%  Up:{state.uptime_str}",
              font=font, fill=grey)

    return image


def render_square_layout(state, width=128, height=128):
    """
    Renders honeypot state to a PIL Image for square OLED displays (SH1107).
    More vertical space allows additional metrics.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    image = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw  = ImageDraw.Draw(image)
    font  = ImageFont.load_default()
    white = (255, 255, 255)
    grey  = (180, 180, 180)
    amber = (255, 200, 0)

    draw.text((0, 0),   "Honeypot Kit",               font=font, fill=white)
    draw.text((0, 16),  f"IP: {state.ip_address}",    font=font, fill=white)
    draw.text((0, 32),  f"Attacks: {state.attack_count}", font=font, fill=white)
    draw.text((0, 48),  f"Rate: {state.attack_rate}/min", font=font, fill=white)

    session_color = amber if state.active_sessions > 0 else grey
    draw.text((0, 64),  f"Sessions: {state.active_sessions}",
              font=font, fill=session_color)

    draw.text((0, 80),  f"Disk: {state.disk_pct}%",   font=font, fill=grey)
    draw.text((0, 96),  f"Mem:  {state.mem_pct}%",    font=font, fill=grey)
    draw.text((0, 112), f"Up: {state.uptime_str}",    font=font, fill=grey)

    return image


def _draw_led(draw, cx, cy, radius, color_on, color_off, state, label, font):
    """
    Draw a circular LED indicator with glow effect.
    state: True=on, False=off, 'blink'=half-bright
    """
    if state is True:
        # Lit LED - draw glow ring then bright center
        glow_color = tuple(min(255, int(c * 0.3)) for c in color_on)
        draw.ellipse(
            [(cx - radius - 4, cy - radius - 4),
             (cx + radius + 4, cy + radius + 4)],
            fill=glow_color
        )
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=color_on
        )
        # Specular highlight
        draw.ellipse(
            [(cx - radius // 3, cy - radius // 2),
             (cx + radius // 5, cy - radius // 4)],
            fill=tuple(min(255, c + 80) for c in color_on)
        )
    elif state == "blink":
        # Half-brightness blink state
        dim = tuple(c // 3 for c in color_on)
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=dim
        )
    else:
        # Off LED - dark with subtle rim
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            fill=color_off
        )
        draw.ellipse(
            [(cx - radius, cy - radius),
             (cx + radius, cy + radius)],
            outline=tuple(c + 20 for c in color_off),
            width=1
        )
    # Label below LED
    draw.text((cx - 12, cy + radius + 4), label, font=font, fill=(160, 160, 180))


def _led_states_from_honeypot_state(led_state):
    """
    Return (green_on, yellow_on, red_on) display states
    based on current honeypot LED state token.
    Maps state machine to visual representation.
    'blink' means show dim/half-lit for animated states.
    """
    states = {
        # state          green   yellow    red
        "healthy":      (True,   False,    False),
        "login_history":(True,   False,    "blink"),
        "active_session":(True,  "blink",  False),
        "high_rate":    (True,   True,     False),
        "warning":      (False,  True,     False),
        "cowrie_down":  (False,  "blink",  "blink"),
        "critical":     (False,  False,    True),
    }
    return states.get(led_state, (False, False, "blink"))


def render_large_layout(state, width=320, height=480):
    """
    Renders honeypot state to a PIL Image for large color TFT displays.
    Portrait layout (320x480) with:
      - Title bar with IP and uptime
      - Attack stats panel
      - System health panel
      - LED emulation panel (three circles: Green/Yellow/Red)
      - Status description
      - Timestamp footer

    Designed for ILI9486-based 3.5" SPI displays that occupy GPIO
    and cannot run physical LEDs simultaneously.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    from datetime import datetime, timezone

    # Color palette
    BG          = (12,  12,  22)
    PANEL_BG    = (22,  22,  40)
    PANEL_EDGE  = (40,  40,  70)
    WHITE       = (240, 240, 250)
    GREEN_ON    = (50,  220, 80)
    GREEN_OFF   = (10,  35,  15)
    YELLOW_ON   = (230, 190, 0)
    YELLOW_OFF  = (35,  30,  5)
    RED_ON      = (220, 50,  50)
    RED_OFF     = (35,  10,  10)
    GREY        = (110, 110, 135)
    CYAN        = (0,   190, 215)
    AMBER       = (255, 160, 0)

    image = Image.new("RGB", (width, height), color=BG)
    draw  = ImageDraw.Draw(image)
    font  = ImageFont.load_default()

    # ---------------------------------------------------------------------------
    # Title bar
    # ---------------------------------------------------------------------------
    draw.rectangle([(0, 0), (width, 26)], fill=(25, 25, 55))
    draw.text((8, 6),   "🍯 Honeypot Kit", font=font, fill=CYAN)
    draw.text((width - 70, 6), f"up {state.uptime_str}", font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # IP + time row
    # ---------------------------------------------------------------------------
    now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    draw.text((8, 32),          f"IP: {state.ip_address}", font=font, fill=WHITE)
    draw.text((width - 60, 32), now_str,                   font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # LED emulation panel
    # ---------------------------------------------------------------------------
    led_panel_y = 52
    led_panel_h = 90
    draw.rectangle(
        [(6, led_panel_y), (width - 6, led_panel_y + led_panel_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, led_panel_y + 5), "STATUS INDICATORS", font=font, fill=GREY)

    led_state  = state.led_state
    g_on, y_on, r_on = _led_states_from_honeypot_state(led_state)

    led_y   = led_panel_y + 35
    led_r   = 18
    spacing = width // 4

    _draw_led(draw, spacing,       led_y, led_r, GREEN_ON,  GREEN_OFF,  g_on, "GRN", font)
    _draw_led(draw, spacing * 2,   led_y, led_r, YELLOW_ON, YELLOW_OFF, y_on, "YLW", font)
    _draw_led(draw, spacing * 3,   led_y, led_r, RED_ON,    RED_OFF,    r_on, "RED", font)

    # State description under LEDs
    state_labels = {
        "healthy":        ("Healthy - idle",           WHITE),
        "login_history":  ("Login alert - clear?",     RED_ON),
        "active_session": ("Active attack session",    YELLOW_ON),
        "high_rate":      ("High attack rate!",        RED_ON),
        "warning":        ("Warning - check system",   YELLOW_ON),
        "cowrie_down":    ("Cowrie not running!",      RED_ON),
        "critical":       ("CRITICAL ERROR",           RED_ON),
    }
    state_text, state_color = state_labels.get(led_state, (led_state, WHITE))
    text_x = max(8, (width - len(state_text) * 6) // 2)
    draw.text((text_x, led_panel_y + led_panel_h - 16), state_text, font=font, fill=state_color)

    # ---------------------------------------------------------------------------
    # Attack stats panel
    # ---------------------------------------------------------------------------
    atk_y = led_panel_y + led_panel_h + 8
    atk_h = 85
    draw.rectangle(
        [(6, atk_y), (width - 6, atk_y + atk_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, atk_y + 5), "ATTACK DATA", font=font, fill=GREY)

    atk_color  = RED_ON  if state.attack_count > 100 else \
                 AMBER   if state.attack_count > 10  else WHITE
    rate_color = RED_ON  if state.attack_rate >= 10  else \
                 AMBER   if state.attack_rate > 0    else GREEN_ON
    sess_color = AMBER   if state.active_sessions > 0 else GREY

    draw.text((12, atk_y + 20), f"Total attacks  : {state.attack_count}", font=font, fill=atk_color)
    draw.text((12, atk_y + 36), f"Rate/min       : {state.attack_rate}",  font=font, fill=rate_color)
    draw.text((12, atk_y + 52), f"Active sessions: {state.active_sessions}", font=font, fill=sess_color)

    last_ip = state.last_attacker if state.last_attacker and state.last_attacker != "none" else "none yet"
    draw.text((12, atk_y + 68), f"Last attacker  : {last_ip[:20]}", font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # System health panel
    # ---------------------------------------------------------------------------
    sys_y = atk_y + atk_h + 8
    sys_h = 85
    draw.rectangle(
        [(6, sys_y), (width - 6, sys_y + sys_h)],
        fill=PANEL_BG, outline=PANEL_EDGE
    )
    draw.text((12, sys_y + 5), "SYSTEM HEALTH", font=font, fill=GREY)

    disk_color   = RED_ON  if state.disk_pct > 85 else AMBER if state.disk_pct > 70 else GREEN_ON
    mem_color    = RED_ON  if state.mem_pct  > 90 else AMBER if state.mem_pct  > 75 else GREEN_ON
    cowrie_color = GREEN_ON if state.cowrie_running else RED_ON
    cowrie_text  = "RUNNING" if state.cowrie_running else "STOPPED"

    draw.text((12, sys_y + 20), f"Disk     : {state.disk_pct}%",   font=font, fill=disk_color)
    draw.text((12, sys_y + 36), f"Memory   : {state.mem_pct}%",    font=font, fill=mem_color)
    draw.text((12, sys_y + 52), f"Cowrie   : {cowrie_text}",       font=font, fill=cowrie_color)
    draw.text((12, sys_y + 68), f"I2C OLED : {'active' if False else 'N/A (SPI mode)'}",
              font=font, fill=GREY)

    # ---------------------------------------------------------------------------
    # Mini bar graphs for disk and memory
    # ---------------------------------------------------------------------------
    bar_x     = 160
    bar_w     = width - bar_x - 14
    bar_h_px  = 6

    # Disk bar
    bar_y = sys_y + 23
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h_px)], fill=(40, 40, 60))
    fill_w = int(bar_w * state.disk_pct / 100)
    draw.rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h_px)], fill=disk_color)

    # Memory bar
    bar_y = sys_y + 39
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h_px)], fill=(40, 40, 60))
    fill_w = int(bar_w * state.mem_pct / 100)
    draw.rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h_px)], fill=mem_color)

    # ---------------------------------------------------------------------------
    # Footer
    # ---------------------------------------------------------------------------
    footer_y = height - 20
    draw.rectangle([(0, footer_y), (width, height)], fill=(25, 25, 55))
    draw.text((8, footer_y + 4), "github.com/ericburnsonline/honeypot-kit", font=font, fill=(60, 60, 90))

    return image


def render_for_resolution(state, resolution):
    """Select layout based on configured resolution."""
    w, h = map(int, resolution.split("x"))
    if w >= 320 or h >= 320:
        return render_large_layout(state, w, h)
    if h >= 128:
        return render_square_layout(state, w, h)
    return render_small_layout(state, w, h)


# ---------------------------------------------------------------------------
# Main monitor loop
# ---------------------------------------------------------------------------

def main():
    log.info("Honeypot monitor daemon starting.")

    config = load_config()

    oled_enabled = config.get("oled", "enabled", fallback="false").lower() == "true"
    led_enabled  = config.get("led",  "enabled", fallback="false").lower() == "true"
    tft_enabled  = config.get("tft",  "enabled", fallback="false").lower() == "true"

    # Initialise hardware
    oled_driver = None
    tft_driver  = None
    led_ctrl    = None

    if oled_enabled:
        addr = config.get("oled", "i2c_address", fallback="0x3C")
        res  = config.get("oled", "resolution",  fallback="128x64")
        oled_driver = OLEDDriver(addr, res)

    if tft_enabled:
        fb  = config.get("tft", "fb_device",   fallback="/dev/fb1")
        res = config.get("tft", "resolution",  fallback="320x480")
        w, h = map(int, res.split("x"))
        tft_driver = TFTDriver(fb, w, h)
        if tft_enabled and led_enabled:
            log.warning(
                "TFT SPI display and LED module both enabled. "
                "GPIO pins are unavailable when SPI display is connected - "
                "LED output will be disabled."
            )
            led_enabled = False

    if led_enabled:
        pin_red    = int(config.get("led", "pin_red",    fallback="17"))
        pin_yellow = int(config.get("led", "pin_yellow", fallback="27"))
        pin_green  = int(config.get("led", "pin_green",  fallback="22"))
        led_ctrl   = LEDController(pin_red, pin_yellow, pin_green)
        led_ctrl.startup_sequence()

    state = HoneypotState()
    last_led_state = None

    log.info(f"Monitor running. OLED: {oled_enabled}, TFT: {tft_enabled}, LED: {led_enabled}.")

    while not _shutdown.is_set():
        try:
            state.refresh()

            # Update OLED
            if oled_driver:
                res   = config.get("oled", "resolution", fallback="128x64")
                image = render_for_resolution(state, res)
                if image:
                    oled_driver.render(image)

            # Update TFT
            if tft_driver:
                res   = config.get("tft", "resolution", fallback="320x480")
                image = render_for_resolution(state, res)
                if image:
                    tft_driver.render(image)

            # Update LEDs only when state changes
            if led_ctrl:
                current_led_state = state.led_state
                if current_led_state != last_led_state:
                    led_ctrl.apply_state(current_led_state)
                    last_led_state = current_led_state
                    log.info(f"LED state: {current_led_state}")

        except Exception as e:
            log.error(f"Monitor loop error: {e}")

        _shutdown.wait(UPDATE_SECS)

    # Shutdown
    log.info("Shutting down hardware monitor.")
    if oled_driver:
        oled_driver.cleanup()
    if tft_driver:
        tft_driver.cleanup()
    if led_ctrl:
        led_ctrl.cleanup()
    log.info("Hardware monitor stopped.")


if __name__ == "__main__":
    main()
