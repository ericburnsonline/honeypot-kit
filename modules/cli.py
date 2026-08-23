#!/usr/bin/env python3
"""
Honeypot Kit CLI
Version: 3
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
import json
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


def require_root():
    """Exit with a clear message if not running as root."""
    if os.geteuid() != 0:
        click.echo("")
        click.echo("ERROR: This command requires root.")
        click.echo("  Run as: sudo honeypot-kit " + " ".join(sys.argv[1:]))
        click.echo("")
        sys.exit(1)


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


VERSION = "3"


@click.group()
@click.version_option(version=VERSION, prog_name="honeypot-kit")
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


@oled.command("enable")
def oled_enable():
    """Enable the OLED display."""
    require_root()
    if not os.path.exists("/dev/i2c-1"):
        click.echo("WARNING: I2C not detected (/dev/i2c-1 missing).")
        click.echo("  Reboot if I2C was just enabled by the install script.")
        click.echo("  Or enable manually: sudo raspi-config -> Interface Options -> I2C")
        click.echo("")
    config = load_config()
    config["oled"]["enabled"] = "true"
    save_config(config)
    click.echo("OLED display enabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@oled.command("disable")
def oled_disable():
    """Disable the OLED display."""
    require_root()
    config = load_config()
    config["oled"]["enabled"] = "false"
    save_config(config)
    click.echo("OLED display disabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@oled.command("set-address")
@click.argument("address")
def oled_set_address(address):
    """Set the I2C address (0x3C or 0x3D)."""
    require_root()
    # Normalize: accept 0x3c or 0x3C, store as 0x3C
    try:
        normalized = "0x" + format(int(address, 16), "02X")
    except ValueError:
        click.echo(f"ERROR: '{address}' is not a valid hex address.")
        click.echo("  Examples: 0x3C or 0x3D")
        sys.exit(1)
    if normalized not in VALID_I2C_ADDRESSES:
        click.echo(f"ERROR: Invalid I2C address '{normalized}'.")
        click.echo(f"  Valid options : {', '.join(VALID_I2C_ADDRESSES)}")
        click.echo("  Tip: run 'i2cdetect -y 1' to find your display's address.")
        sys.exit(1)
    address = normalized
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


@oled.command("test")
@click.option("--keep", is_flag=True, default=False,
              help="Leave test image on screen instead of clearing after 3 seconds.")
def oled_test(keep):
    """Test the OLED display with a status screen."""
    require_root()
    if not os.path.exists("/dev/i2c-1"):
        click.echo("ERROR: I2C not detected (/dev/i2c-1 missing).")
        click.echo("  Reboot if I2C was just enabled by the install script.")
        click.echo("  Or enable manually: sudo raspi-config -> Interface Options -> I2C")
        sys.exit(1)
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

        if not keep:
            import time as _time
            _time.sleep(3)
            display.fill(0)
            display.show()
            click.echo("Display cleared.")
        else:
            click.echo("Test image kept on screen (--keep). Restart monitor to resume live display.")

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


@led.command("enable")
def led_enable():
    """Enable the LED status indicators."""
    require_root()
    config = load_config()
    config["led"]["enabled"] = "true"
    save_config(config)
    click.echo("LED indicators enabled.")
    click.echo("Restart the monitor service: honeypot-kit monitor restart")


@led.command("disable")
def led_disable():
    """Disable the LED status indicators."""
    require_root()
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
    require_root()
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


@led.command("clear-alert")
def led_clear_alert():
    """Clear the persistent login alert (stops red blink)."""
    require_root()
    state_file = "/opt/honeypot/monitor-state.json"
    try:
        with open(state_file, "w") as f:
            json.dump({"login_history": False}, f)
        click.echo("Login alert cleared.")
        click.echo("Restart the monitor to apply: honeypot-kit monitor restart")
    except Exception as e:
        click.echo(f"ERROR: Could not clear alert - {e}")
        sys.exit(1)


@led.command("test")
def led_test():
    """Test LEDs by flashing each one in sequence."""
    require_root()
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


@monitor.command("start")
def monitor_start():
    """Start the hardware monitor service."""
    require_root()
    ok, err = _systemctl("start")
    if ok:
        click.echo("Monitor service started.")
    else:
        click.echo(f"ERROR: Could not start monitor service.")
        if err:
            click.echo(f"  {err}")
        click.echo("  Check: journalctl -u honeypot-monitor -n 20")
        sys.exit(1)


@monitor.command("stop")
def monitor_stop():
    """Stop the hardware monitor service."""
    require_root()
    ok, err = _systemctl("stop")
    if ok:
        click.echo("Monitor service stopped.")
    else:
        click.echo(f"ERROR: Could not stop monitor service. {err}")
        sys.exit(1)


@monitor.command("restart")
def monitor_restart():
    """Restart the hardware monitor service."""
    require_root()
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


@update.command("status")
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


@update.command("now")
def now():
    """Run an update check immediately."""
    require_root()
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


@update.command("enable")
def update_enable():
    """Enable automatic weekly updates."""
    require_root()
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


@update.command("disable")
def update_disable():
    """Disable automatic weekly updates."""
    require_root()
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



# ---------------------------------------------------------------------------
# INTEGRATION MANAGER
# ---------------------------------------------------------------------------

GITHUB_RAW      = "https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main"
MANIFEST_URL    = f"{GITHUB_RAW}/integrations/manifest.json"
INTEGRATIONS_DIR = "/opt/honeypot/integrations"


def fetch_manifest():
    """Download and parse the integration manifest from GitHub."""
    try:
        import urllib.request
        with urllib.request.urlopen(MANIFEST_URL, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        click.echo(f"ERROR: Could not fetch integration manifest - {e}")
        click.echo(f"  Check network and try again.")
        sys.exit(1)


def installed_integrations():
    """Return set of integration names that are installed locally."""
    installed = set()
    if not os.path.exists(INTEGRATIONS_DIR):
        return installed
    for name in os.listdir(INTEGRATIONS_DIR):
        marker = os.path.join(INTEGRATIONS_DIR, name, ".installed")
        if os.path.exists(marker):
            installed.add(name)
    return installed


@cli.group()
def integration():
    """Manage Honeypot Kit integrations."""
    pass


@integration.command("list")
def integration_list():
    """List available integrations and their status."""
    manifest = fetch_manifest()
    installed = installed_integrations()

    click.echo("")
    click.echo("=== Honeypot Kit Integrations ===")
    click.echo(f"  Manifest version : {manifest.get('manifest_version', '?')}")
    click.echo(f"  Updated          : {manifest.get('updated', '?')}")
    click.echo("")

    stage_labels = {1: "Stage 1 - Doc", 2: "Stage 2 - Install", 3: "Stage 3 - DIY"}

    for intg in manifest.get("integrations", []):
        name         = intg["name"]
        display      = intg["display_name"]
        description  = intg["description"]
        stage        = intg.get("stage", 1)
        status       = intg.get("status", "planned")
        notes        = intg.get("notes", "")
        is_installed = name in installed
        can_install  = stage >= 2 and status == "available"

        if is_installed:
            state = click.style("INSTALLED", fg="green")
        elif can_install:
            state = click.style("available", fg="cyan")
        else:
            state = click.style("planned", fg="yellow")

        click.echo(f"  {display:<30} {state}")
        click.echo(f"    {description}")
        click.echo(f"    {stage_labels.get(stage, 'Unknown')}  |  {notes}")
        click.echo("")


@integration.command("install")
@click.argument("name")
def integration_install(name):
    """Install an integration by name."""
    require_root()
    manifest = fetch_manifest()
    installed = installed_integrations()

    # Find the integration in the manifest
    intg = next((i for i in manifest.get("integrations", []) if i["name"] == name), None)

    if not intg:
        click.echo(f"ERROR: Unknown integration '{name}'.")
        click.echo("  Run: honeypot-kit integration list")
        sys.exit(1)

    if intg.get("stage", 1) < 2:
        click.echo(f"ERROR: '{name}' is Stage 1 only - no installable files yet.")
        click.echo(f"  Read the overview doc first:")
        if intg.get("doc"):
            click.echo(f"  https://github.com/ericburnsonline/honeypot-kit/blob/main/{intg['doc']}")
        sys.exit(1)

    if intg.get("status") != "available":
        click.echo(f"ERROR: '{name}' is not yet available for install (status: {intg.get('status')}).")
        sys.exit(1)

    if name in installed:
        click.echo(f"'{name}' is already installed.")
        click.echo(f"  To reinstall: remove /opt/honeypot/integrations/{name}/.installed first.")
        sys.exit(0)

    click.echo(f"Installing {intg['display_name']}...")

    # Create integration directory
    intg_dir = os.path.join(INTEGRATIONS_DIR, name)
    os.makedirs(intg_dir, exist_ok=True)

    # Download integration files
    import urllib.request
    files = intg.get("files", [])
    for file_entry in files:
        src_path = file_entry["src"]
        dst_path = os.path.join(intg_dir, file_entry["dst"])
        url = f"{GITHUB_RAW}/{src_path}"
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        try:
            urllib.request.urlretrieve(url, dst_path)
            click.echo(f"  Downloaded: {file_entry['dst']}")
        except Exception as e:
            click.echo(f"  ERROR downloading {file_entry['dst']}: {e}")
            sys.exit(1)

    # Install any Python requirements
    req_file = os.path.join(intg_dir, "requirements.txt")
    if os.path.exists(req_file):
        click.echo("  Installing Python dependencies...")
        import subprocess as sp
        result = sp.run(
            ["pip3", "install", "--break-system-packages", "--quiet", "-r", req_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            click.echo(f"  WARNING: Some dependencies may not have installed cleanly.")
            click.echo(f"  {result.stderr.strip()}")

    # Run integration setup script if present
    setup_script = os.path.join(intg_dir, "install.sh")
    if os.path.exists(setup_script):
        click.echo("  Running setup script...")
        os.chmod(setup_script, 0o755)
        result = subprocess.run(["bash", setup_script], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"  ERROR in setup script:")
            click.echo(f"  {result.stderr.strip()}")
            sys.exit(1)

    # Write installed marker
    with open(os.path.join(intg_dir, ".installed"), "w") as f:
        f.write(f"installed: {__import__('datetime').datetime.now().isoformat()}\n")
        f.write(f"version: {intg.get('stage', 1)}\n")

    click.echo(f"\n{intg['display_name']} installed successfully.")

    # Show next steps
    if intg.get("cli_subcommand"):
        click.echo(f"  New CLI command: honeypot-kit {intg['cli_subcommand']} --help")
    click.echo(f"  Restart monitor if needed: honeypot-kit monitor restart")


@integration.command("status")
def integration_status():
    """Show installed integrations and their configuration."""
    installed = installed_integrations()

    click.echo("")
    click.echo("=== Installed Integrations ===")
    click.echo("")

    if not installed:
        click.echo("  No integrations installed.")
        click.echo("  Run: honeypot-kit integration list")
        click.echo("")
        return

    for name in sorted(installed):
        intg_dir = os.path.join(INTEGRATIONS_DIR, name)
        marker   = os.path.join(intg_dir, ".installed")
        click.echo(f"  {name}")
        try:
            with open(marker) as f:
                for line in f:
                    click.echo(f"    {line.rstrip()}")
        except Exception:
            pass
        click.echo("")


@integration.command("uninstall")
@click.argument("name")
def integration_uninstall(name):
    """Remove an installed integration."""
    require_root()
    intg_dir = os.path.join(INTEGRATIONS_DIR, name)
    marker   = os.path.join(intg_dir, ".installed")

    if not os.path.exists(marker):
        click.echo(f"ERROR: '{name}' is not installed.")
        sys.exit(1)

    import shutil
    try:
        shutil.rmtree(intg_dir)
        click.echo(f"'{name}' uninstalled.")
    except Exception as e:
        click.echo(f"ERROR: Could not remove {intg_dir}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
