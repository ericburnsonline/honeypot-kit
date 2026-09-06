# Frequently Asked Questions

- [Installation](#installation)
- [CLI Tool](#cli-tool)
- [OLED Display](#oled-display)
- [LED Indicators](#led-indicators)
- [Hardware Monitor](#hardware-monitor)
- [OpenAI Integration](#openai-integration)
- [General](#general)

---

## Installation

**How long does the install take?**

About 2 minutes for the configuration questions, then approximately 11 minutes
unattended. Once you answer the prompts you can walk away.

**The install script says "must be run with bash" but I am running it as bash.**

Make sure you are running it as:
```bash
sudo bash install-honeypot.sh
```
Not `sh install-honeypot.sh` or `./install-honeypot.sh`.

**Should I reboot after install?**

Yes. The install script prompts you to reboot. Several changes (I2C, hostname,
Cowrie on port 22) do not take full effect until after a reboot.

**The install says it enabled I2C but i2cdetect doesn't find my display.**

Reboot first. The I2C enable in `/boot/firmware/config.txt` takes effect
after reboot, not immediately.

---

## CLI Tool

**`honeypot-kit` says "click not installed".**

On Debian Trixie, pip3 is blocked by PEP 668. Install via apt instead:
```bash
sudo apt-get install -y python3-click python3-rpi.gpio python3-pil python3-numpy
```

**`honeypot-kit` says "externally-managed-environment".**

Same issue as above - use apt, not pip3, for packages that are available
via apt on Trixie. See answer above.

**`honeypot-kit oled set-resolution` ran without sudo and gave a permission error.**

Correct behavior - the config file is root-owned. All commands that write
to config or touch hardware require sudo:
```bash
sudo honeypot-kit oled set-resolution 128x64
```

**`honeypot-kit` says "no such command 'test'" for led or oled.**

You have an older version of cli.py. Update it:
```bash
sudo honeypot-kit update now
honeypot-kit --version
```
Should show version 8 or higher. If update now fails, check GitHub has the
latest cli.py committed.

**How do I know which version of the CLI I have?**

```bash
honeypot-kit --version
```

---

## OLED Display

**The OLED display is blank after enabling it.**

Work through these in order:

1. Confirm I2C is enabled: `i2cdetect -y 1` should show `3c` or `3d`
2. If `i2cdetect` command not found: `sudo apt-get install -y i2c-tools`
3. If nothing shows in the grid: reboot (I2C may not be active yet)
4. Confirm address: `sudo honeypot-kit oled set-address 0x3C`
5. Test the display directly: `sudo honeypot-kit oled test`
6. Check the monitor is running: `honeypot-kit monitor status`

**`i2cdetect` shows `3c` but the display doesn't respond.**

The SSD1315 sometimes uses `0x3D`. Try:
```bash
sudo honeypot-kit oled set-address 0x3D
sudo honeypot-kit oled test
```

**The Adafruit OLED library won't install via pip.**

The `adafruit-circuitpython-ssd1306` package may not be available for
Python 3.13 on Trixie via pip. Install what's needed first:
```bash
sudo pip3 install --break-system-packages --ignore-installed adafruit-circuitpython-ssd1306 adafruit-blinka
```
The `--ignore-installed` flag is required to avoid conflicts with
Debian-managed packages like `typing_extensions`.

**The OLED test works but nothing shows when the monitor is running.**

The monitor reads from `/opt/honeypot/cowrie/var/log/cowrie/cowrie.json`.
If Cowrie JSON output is not enabled, the monitor has no data. Check:
```bash
grep "output_jsonlog" /opt/honeypot/cowrie/etc/cowrie.cfg
```
It should show `enabled = true`. If not, add it and restart Cowrie.

---

## LED Indicators

**The red LED won't stop blinking even after `honeypot-kit led clear-alert`.**

The monitor replays log history on startup and re-sets the login alert.
Fix sequence:
```bash
sudo honeypot-kit monitor stop
echo '{"login_history": false}' | sudo tee /opt/honeypot/monitor-state.json
sudo honeypot-kit monitor start
```

**The LEDs and OLED are not showing anything after a reboot.**

The monitor service needs to be enabled to start on boot. This happens
automatically when you run `honeypot-kit led enable` or
`honeypot-kit oled enable` in cli.py v4 or higher. If you enabled hardware
with an older version, enable the service manually:
```bash
sudo systemctl enable honeypot-monitor
sudo honeypot-kit monitor start
```

**The LED test works but the monitor doesn't drive the LEDs.**

Check the monitor log:
```bash
cat /opt/honeypot/logs/monitor.log | tail -20
```
Common causes:
- `monitor.log` permission denied - fix: `sudo chmod 666 /opt/honeypot/logs/monitor.log`
- `monitor-state.json` permission denied - fix: `sudo chmod 666 /opt/honeypot/monitor-state.json`
- GPIO error - make sure you are not running the TFT SPI display and LEDs simultaneously

**GPIO pins are unavailable after installing the SPI TFT display.**

This is expected. The SPI display uses the GPIO header. Physical LEDs
cannot be used at the same time. The TFT display shows virtual LED
indicators on screen instead.

---

## Hardware Monitor

**The monitor service starts then immediately stops ("deactivated successfully").**

Check the journal:
```bash
journalctl -u honeypot-monitor -n 30 --no-pager
```
Common causes:
- `Wants=cowrie.service` in the service file causing systemd to SIGTERM
  the monitor if Cowrie isn't confirmed running. Fixed in v13 of the
  install script - the monitor service now only depends on `network.target`.
- The monitor.py file is empty or corrupt. Check: `wc -l /opt/honeypot/modules/monitor.py`
  If 0 bytes, re-download: `sudo honeypot-kit update now`

**The monitor.log shows "GPIO not available" but the LED module is connected.**

Run the monitor as root or add the user to the gpio group:
```bash
sudo usermod -a -G gpio $USER
```
Then log out and back in, or just run the monitor as root via systemd
(the service file uses `User=pi` or equivalent - check it matches your user).

**How do I check what version of monitor.py is running?**

```bash
head -5 /opt/honeypot/modules/monitor.py
```

---

## OpenAI Integration

**`honeypot-kit integration install openai` gives a pip error about typing_extensions.**

Use `--ignore-installed` to avoid conflicts with Debian-managed packages:
```bash
sudo pip3 install --break-system-packages --ignore-installed openai
```

**`honeypot-kit ai test` gives a 401 permission error.**

The API key either isn't set or has insufficient permissions. Check:

1. Open the config: `cat /opt/honeypot/integrations/openai/config.json`
2. Confirm `api_key` is set and not empty
3. Confirm `enabled` is `true`
4. If using a restricted key, delete it and create a new one with
   **All** permissions - scope changes on existing keys don't always take effect
5. Fix file permissions if needed:
   ```bash
   sudo chown "root:$(logname)" /opt/honeypot/integrations/openai/config.json
   sudo chmod 640 /opt/honeypot/integrations/openai/config.json
   ```

**`honeypot-kit ai status` gives a permission denied error on config.json.**

The config file was created by root but needs to be readable by your user:
```bash
sudo chown "root:$(logname)" /opt/honeypot/integrations/openai/config.json
sudo chmod 640 /opt/honeypot/integrations/openai/config.json
```

**The AI analysis gives a schema error (400 Invalid schema).**

You have an older version of analyzer.py. The structured output schema
required `additionalProperties: false` on nested objects. Update:
```bash
sudo honeypot-kit update now
```
Or re-download manually from GitHub.

**No completed sessions found when running `honeypot-kit ai analyze --latest`.**

Sessions only appear after an attacker connects AND disconnects. Sessions
in progress are not analyzed. Wait for a session to complete, or trigger
one by SSH-ing into port 22 from another machine and then disconnecting.

**I analyzed a session but the results look wrong - it says AI unavailable.**

The integration may not be enabled. Check:
```bash
cat /opt/honeypot/integrations/openai/config.json | grep enabled
```
Should show `"enabled": true`. Also check the API key is set.

---

## General

**Port 111 (rpcbind) shows up in nmap. Is that a problem?**

No. rpcbind is normal on Raspberry Pi OS and is not exposed to the internet
by the firewall. It is an internal service.

**How do I completely wipe all collected attack data?**

```bash
sudo systemctl stop cowrie
sudo rm -f /opt/honeypot/cowrie/var/log/cowrie/cowrie.json
sudo rm -f /opt/honeypot/cowrie/var/log/cowrie/cowrie.log
echo '{"login_history": false}' | sudo tee /opt/honeypot/monitor-state.json
sudo systemctl start cowrie
sudo honeypot-kit monitor restart
```

**How do I check if Cowrie is actually capturing attacks?**

```bash
tail -f /opt/honeypot/cowrie/var/log/cowrie/cowrie.json
```
Leave it running and SSH into port 22 from another machine. You should
see JSON events appear in real time.

**The auto-update says "no change" but I know there's a newer version.**

The update compares checksums. If the file on the Pi matches GitHub byte
for byte, it correctly reports no change. Verify what's on GitHub by
checking the version number:
```bash
curl -s https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main/modules/cli.py | head -5
```
Compare to: `head -5 /usr/local/bin/honeypot-kit`

**Where do I report bugs or ask questions?**

Open an issue on GitHub:
https://github.com/ericburnsonline/honeypot-kit/issues
