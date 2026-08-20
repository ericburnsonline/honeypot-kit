#!/usr/bin/env python3
"""
Honeypot Kit CLI
Manage hardware modules (OLED display, status LEDs) for Honeypot Kit.

Usage:
  honeypot-kit status
  honeypot-kit oled enable
  honeypot-kit oled disable
  honeypot-kit oled set-address 0x3C
  honeypot-kit oled set-resolution 128x64
  honeypot-kit oled test
  honeypot-kit led enable
  honeypot-kit led disable
  honeypot-kit led set-pins --red 17 --yellow 27 --green 22
  honeypot-kit led test
  honeypot-kit monitor start
  honeypot-kit monitor stop
  honeypot-kit monitor status
"""

import sys
import configparser
import os
import subprocess

try:
    import click
except ImportError:
    print("ERROR: click not installed. Run: pip3 install click")
    sys.exit(1)

CONF_FILE  = "/opt/honeypot/honeypot-kit.conf"
SERVICE    = "honeypot-monitor"

SUPPORTED_RESOLUTIONS = ["128x64", "128x32", "96x16", "128x128"]
VALID_I2C_ADDRESSES   = ["0x3C", "0x3D"]
VALID_GPIO_PINS       = list(range(2, 28))


def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONF_FILE):
        config.read(CONF_FILE)
    if "oled" not in config:
        config["oled"] = {
            "enabled":     "false",
            "i2c_address": "0x3C",
            "resolution":  "128x64",
        }
    if "led" not in config:
        config["led"] = {
            "enabled":    "false",
            "pin_red":    "17",
            "pin_yellow": "27",
            "pin_green":  "22",
        }
    return config


def save_config(config):
    os.makedirs(os.path.dirname(CONF_FILE), exist_ok=True)
    with open(CONF_FILE, "w") as f:
        config.write(f)


def _systemctl(action, service=SERVICE):
    try:
        result = subprocess.run(
            ["systemctl", action, service],
            capture_output=True, text=True
        )
        return result.returncode == 0, result.stderr.strip()
    except Exception as e:
        return False, str(e)


@click.group()
def cli():
    """Honeypot Kit - hardware module manager."""
    pass


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

@cli.command()
def status():
    """Show current hardware module configuration."""
    config = load_config()

    click.echo("")
    click.echo("=== Honeypot Kit Hardware Status ===")
    click.echo("")

    # OLED
    oled_enabled = config["oled"].get("enabled", "false").lower() == "true"
    oled_addr    = config["oled"].get("i2c_address", "0x3C")
    oled_res     = config["oled"].get("resolution",  "128x64")
    oled_status  = click.style("ENABLED",  fg="green")  if oled_enabled \
                   else click.style("disabled", fg="yellow")

    click.echo(f"  OLED Display    : {oled_status}")
    click.echo(f"    I2C address   : {oled_addr}")
    click.echo(f"    Resolution    : {oled_res}")
    click.echo("")

    # LED
    led_enabled  = config["led"].get("enabled",    "false").lower() == "true"
    pin_red      = config["led"].get("pin_red",    "17")
    pin_yellow   = config["led"].get("pin_yellow", "27")
    pin_green    = config["led"].get("pin_green",  "22")
    led_status   = click.style("ENABLED",  fg="green")  if led_enabled \
                   else click.style("disabled", fg="yellow")

    click.echo(f"  LED Indicators  : {led_status}")
    click.echo(f"    Red pin       : GPIO {pin_red}")
    click.echo(f"    Yellow pin    : GPIO {pin_yellow}")
    click.echo(f"    Green pin     : GPIO {pin_green}")
    click.echo("")

    # Monitor service
    ok, _ = _systemctl("is-active")
    svc_status = click.style("running", fg="green") if ok \
                 else click.style("stopped", fg="yellow")
    click.echo(f"  Monitor service : {svc_status}")
    click.echo(f"  Config file     : {CONF_FILE}")
    click.echo("")


# ---------------------------------------------------------------------------
# OLED
# ---------------------------------------------------------------------------

@cli.group()
def oled():
    """Manage the OLED display module."""
    pass


@oled.command()
def enable():
    """Enable the OLED display."""
    config = load_config()
    config["oled"]["enabled"] = "true"
    save_config(config)
    click.echo("OLED display enabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@oled.command()
def disable():
    """Disable the OLED display."""
    config = load_config()
    config["oled"]["enabled"] = "false"
    save_config(config)
    click.echo("OLED display disabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@oled.command("set-address")
@click.argument("address")
def oled_set_address(address):
    """Set the I2C address (0x3C or 0x3D)."""
    if address not in VALID_I2C_ADDRESSES:
        click.echo(f"ERROR: Invalid I2C address '{address}'.")
        click.echo(f"  Valid options : {', '.join(VALID_I2C_ADDRESSES)}")
        click.echo("  Tip: run 'i2cdetect -y 1' to find your display's address.")
        sys.exit(1)
    config = load_config()
    config["oled"]["i2c_address"] = address
    save_config(config)
    click.echo(f"OLED I2C address set to {address}.")


@oled.command("set-resolution")
@click.argument("resolution")
def oled_set_resolution(resolution):
    """Set the display resolution (128x64, 128x32, 96x16, 128x128)."""
    if resolution not in SUPPORTED_RESOLUTIONS:
        click.echo(f"ERROR: Unsupported resolution '{resolution}'.")
        click.echo(f"  Supported: {', '.join(SUPPORTED_RESOLUTIONS)}")
        sys.exit(1)
    config = load_config()
    config["oled"]["resolution"] = resolution
    save_config(config)
    click.echo(f"OLED resolution set to {resolution}.")


@oled.command()
def test():
    """Test the OLED display with a status screen."""
    config = load_config()
    addr_str = config["oled"].get("i2c_address", "0x3C")
    res      = config["oled"].get("resolution",  "128x64")

    try:
        import board
        import busio
        import adafruit_ssd1306
        from PIL import Image, ImageDraw, ImageFont

        w, h = map(int, res.split("x"))
        addr = int(addr_str, 16)

        i2c     = busio.I2C(board.SCL, board.SDA)
        display = adafruit_ssd1306.SSD1306_I2C(w, h, i2c, addr=addr)
        display.fill(0)
        display.show()

        image = Image.new("1", (w, h))
        draw  = ImageDraw.Draw(image)
        font  = ImageFont.load_default()

        draw.text((0, 0),  "Honeypot Kit",      fill=255, font=font)
        draw.text((0, 12), "OLED test OK",       fill=255, font=font)
        draw.text((0, 24), f"Addr: {addr_str}",  fill=255, font=font)
        draw.text((0, 36), f"Res:  {res}",       fill=255, font=font)

        display.image(image)
        display.show()
        click.echo(f"OLED test OK - check your display ({res} @ {addr_str}).")

    except ImportError as e:
        click.echo(f"ERROR: Missing library - {e}")
        click.echo("  Run: pip3 install adafruit-circuitpython-ssd1306 pillow adafruit-blinka")
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: Could not communicate with OLED - {e}")
        click.echo("  Check wiring and confirm I2C is enabled (raspi-config).")
        click.echo(f"  Run 'i2cdetect -y 1' to verify {addr_str} is visible.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# LED
# ---------------------------------------------------------------------------

@cli.group()
def led():
    """Manage the LED status indicator module."""
    pass


@led.command()
def enable():
    """Enable the LED status indicators."""
    config = load_config()
    config["led"]["enabled"] = "true"
    save_config(config)
    click.echo("LED indicators enabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@led.command()
def disable():
    """Disable the LED status indicators."""
    config = load_config()
    config["led"]["enabled"] = "false"
    save_config(config)
    click.echo("LED indicators disabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@led.command("set-pins")
@click.option("--red",    type=int, required=True, help="BCM GPIO pin for red LED")
@click.option("--yellow", type=int, required=True, help="BCM GPIO pin for yellow LED")
@click.option("--green",  type=int, required=True, help="BCM GPIO pin for green LED")
def led_set_pins(red, yellow, green):
    """Set GPIO pins for each LED (BCM numbering)."""
    pins = {"red": red, "yellow": yellow, "green": green}
    for name, pin in pins.items():
        if pin not in VALID_GPIO_PINS:
            click.echo(f"ERROR: Invalid GPIO pin {pin} for {name}.")
            click.echo(f"  Valid BCM pins: {VALID_GPIO_PINS[0]}-{VALID_GPIO_PINS[-1]}")
            sys.exit(1)

    if len(set(pins.values())) != len(pins):
        click.echo("ERROR: Each LED must use a different GPIO pin.")
        sys.exit(1)

    config = load_config()
    config["led"]["pin_red"]    = str(red)
    config["led"]["pin_yellow"] = str(yellow)
    config["led"]["pin_green"]  = str(green)
    save_config(config)
    click.echo(f"LED pins set - Red: GPIO {red}, Yellow: GPIO {yellow}, Green: GPIO {green}.")


@led.command()
def test():
    """Test LEDs by flashing each one in sequence."""
    config = load_config()
    pin_red    = int(config["led"].get("pin_red",    "17"))
    pin_yellow = int(config["led"].get("pin_yellow", "27"))
    pin_green  = int(config["led"].get("pin_green",  "22"))

    try:
        import RPi.GPIO as GPIO
        import time

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in (pin_red, pin_yellow, pin_green):
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        click.echo("Testing LEDs - each will flash for 1 second...")
        for pin, name in [
            (pin_green,  "Green"),
            (pin_yellow, "Yellow"),
            (pin_red,    "Red"),
        ]:
            click.echo(f"  {name} (GPIO {pin})...")
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(1)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(0.2)

        GPIO.cleanup()
        click.echo("LED test complete.")

    except ImportError:
        click.echo("ERROR: RPi.GPIO not installed. Run: pip3 install RPi.GPIO")
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"ERROR: GPIO error - {e}")
        click.echo("  Run as root (sudo) or add user to gpio group.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# MONITOR SERVICE
# ---------------------------------------------------------------------------

@cli.group()
def monitor():
    """Manage the hardware monitor daemon."""
    pass


@monitor.command()
def start():
    """Start the hardware monitor service."""
    ok, err = _systemctl("start")
    if ok:
        click.echo("Monitor service started.")
    else:
        click.echo(f"ERROR: Could not start monitor service.")
        if err:
            click.echo(f"  {err}")
        click.echo("  Check: journalctl -u honeypot-monitor -n 20")
        sys.exit(1)


@monitor.command()
def stop():
    """Stop the hardware monitor service."""
    ok, err = _systemctl("stop")
    if ok:
        click.echo("Monitor service stopped.")
    else:
        click.echo(f"ERROR: Could not stop monitor service. {err}")
        sys.exit(1)


@monitor.command()
def restart():
    """Restart the hardware monitor service."""
    ok, err = _systemctl("restart")
    if ok:
        click.echo("Monitor service restarted.")
    else:
        click.echo(f"ERROR: Could not restart monitor service.")
        if err:
            click.echo(f"  {err}")
        sys.exit(1)


@monitor.command("status")
def monitor_status():
    """Show hardware monitor service status."""
    try:
        result = subprocess.run(
            ["systemctl", "status", SERVICE, "--no-pager"],
            capture_output=True, text=True
        )
        click.echo(result.stdout)
    except Exception as e:
        click.echo(f"ERROR: {e}")
        sys.exit(1)



# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@cli.group()
def update():
    """Manage Honeypot Kit module auto-updates."""
    pass


@update.command()
def status():
    """Show auto-update status and last update log entries."""
    import configparser
    config = configparser.ConfigParser()
    config.read(CONF_FILE)

    enabled = config.get("updates", "enabled", fallback="false").lower() == "true"
    status_str = click.style("enabled", fg="green") if enabled \
                 else click.style("disabled", fg="yellow")

    click.echo("")
    click.echo(f"  Auto-update      : {status_str}")
    click.echo(f"  Schedule         : weekly, Sunday at 03:00")
    click.echo("")

    log_file = "/opt/honeypot/logs/updates.log"
    if os.path.exists(log_file):
        click.echo("  Last 10 log entries:")
        with open(log_file) as f:
            lines = f.readlines()
        for line in lines[-10:]:
            click.echo(f"    {line.rstrip()}")
    else:
        click.echo("  No update log found yet.")
    click.echo("")


@update.command()
def now():
    """Run an update check immediately."""
    update_script = "/opt/honeypot/scripts/honeypot-update.sh"
    if not os.path.exists(update_script):
        click.echo("ERROR: Update script not found.")
        click.echo("  Auto-update may not have been enabled at install time.")
        click.echo("  Re-run the install script and choose yes for auto-updates.")
        sys.exit(1)
    click.echo("Running update check...")
    try:
        result = subprocess.run(
            ["bash", update_script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            click.echo("Update check complete. See: honeypot-kit update status")
        else:
            click.echo(f"Update script returned an error.")
            if result.stderr:
                click.echo(f"  {result.stderr.strip()}")
    except Exception as e:
        click.echo(f"ERROR: {e}")
        sys.exit(1)


@update.command()
def enable():
    """Enable automatic weekly updates."""
    ok, err = _systemctl("enable", "honeypot-update.timer")
    ok2, _  = _systemctl("start",  "honeypot-update.timer")
    if ok and ok2:
        # Update config
        import configparser
        config = configparser.ConfigParser()
        config.read(CONF_FILE)
        if "updates" not in config:
            config["updates"] = {}
        config["updates"]["enabled"] = "true"
        with open(CONF_FILE, "w") as f:
            config.write(f)
        click.echo("Auto-update enabled. Runs weekly Sunday at 03:00.")
    else:
        click.echo(f"ERROR: Could not enable update timer. {err}")
        click.echo("  Check: systemctl status honeypot-update.timer")
        sys.exit(1)


@update.command()
def disable():
    """Disable automatic weekly updates."""
    ok, err = _systemctl("disable", "honeypot-update.timer")
    _systemctl("stop", "honeypot-update.timer")
    if ok:
        import configparser
        config = configparser.ConfigParser()
        config.read(CONF_FILE)
        if "updates" not in config:
            config["updates"] = {}
        config["updates"]["enabled"] = "false"
        with open(CONF_FILE, "w") as f:
            config.write(f)
        click.echo("Auto-update disabled.")
    else:
        click.echo(f"ERROR: Could not disable update timer. {err}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
