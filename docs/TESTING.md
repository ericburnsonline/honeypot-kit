# Honeypot Kit - Testing Guide

Post-install acceptance checklist. Run through this after every fresh install
or major update. Check off each item as you go. Stop at any failure and note
the error before continuing.

**Script version tested:** v16
**Platform tested:** Raspberry Pi 4, 64-bit Debian Trixie
**Last updated:** 2026-09-15

---

## Before You Start

**Confirm your branch:**
```
honeypot-kit update branch
```
This guide assumes you installed from `main`. If you installed from another
branch, results may differ - non-main branches are works in progress and
may be intentionally incomplete or broken. If you are having unexpected
failures, reinstall from `main` and re-run this checklist before reporting
an issue.

---

**Important: SSH port has changed after install.**

The install script moves real SSH to a new port (default 2222). Reconnect
on the new port before starting tests:

```
ssh -p 2222 pi@<pi-ip-address>
```

**If you get a host key warning** (common when reinstalling on the same IP),
clear the old key first. On Windows, square brackets are required for
non-default ports:

```
# Linux/Mac:
ssh-keygen -R <pi-ip-address>

# Windows or non-default port - square brackets required:
ssh-keygen -R [<pi-ip-address>]:2222

# By hostname:
ssh-keygen -R [<pi-hostname>]:2222
```

**If you accidentally SSH into port 22** (Cowrie honeypot) during testing,
it will trigger the red LED alert. Clear it after:

```
sudo honeypot-kit led clear-alert
sudo honeypot-kit monitor restart
```

---

## Phase 1 - Smoke Test

Run the built-in smoke test first. This catches the most common issues quickly.

```
sudo bash /opt/honeypot/scripts/smoke-test.sh
```

**Expected result:** All items PASS or INFO. No FAILs. WARNs are acceptable
if the relevant module is disabled or not yet connected.

- [ ] Smoke test runs without error
- [ ] Cowrie process running (PASS)
- [ ] Cowrie listening on port 22 (PASS)
- [ ] Real SSH listening on configured port (PASS)
- [ ] Log file active (PASS)
- [ ] Disk OK (PASS)
- [ ] Time synchronized (PASS or WARN - chrony may still be settling)
- [ ] honeypot-kit CLI installed (PASS)
- [ ] I2C enabled (PASS - or WARN if pre-reboot)

---

## Phase 2 - Network Verification

```
sudo nmap -sS localhost
```

- [ ] Port 22 open (Cowrie)
- [ ] Real SSH port open (e.g. 2222 or your chosen port)
- [ ] Note: port 111 (rpcbind) is normal on Pi OS - not a concern
- [ ] No unexpected open ports beyond 22, real SSH port, and 111

```
sudo ufw status
```

- [ ] UFW active
- [ ] Port 22 allowed
- [ ] Real SSH port (2222) allowed
- [ ] IPv6 rules mirror IPv4 - this is expected and correct

```
sudo ufw status | grep 8000
```

Expected output:
```
8000                       DENY        Anywhere
8000                       ALLOW       192.168.x.0/24
8000 (v6)                  DENY        Anywhere (v6)
```

This is correct and intentional. DENY blocks all internet traffic to port
8000. The ALLOW lets your local subnet through. UFW processes rules top to
bottom so local traffic hits the ALLOW before the DENY. If you only see
DENY with no ALLOW, the dashboard subnet was not configured during install.

- [ ] Port 8000 DENY Anywhere present
- [ ] Port 8000 ALLOW from local subnet present

---

## Phase 3 - LED Module

*Skip if LED module not connected. Skip if TFT SPI display is installed
(GPIO pins unavailable - LEDs not compatible with TFT).*

**Step 3.1 - Identify your GPIO pins**

Check which BCM GPIO pins your LED traffic light module is wired to.
Default assignments are Red=17, Yellow=27, Green=22 (Pi pins 11, 13, 15).
If you used different pins, substitute your values in the commands below.

Confirm wiring:

- Red LED → GPIO 17 (Pin 11)
- Yellow LED → GPIO 27 (Pin 13)
- Green LED → GPIO 22 (Pin 15)
- GND → any ground pin (Pin 6, 9, 14, 20, 25, 30, 34, or 39)

**Step 3.2 - Set pins and test:**

```
sudo honeypot-kit led set-pins --red 17 --yellow 27 --green 22
sudo honeypot-kit led test
```

- [ ] Green LED flashes for 1 second
- [ ] Yellow LED flashes for 1 second
- [ ] Red LED flashes for 1 second
- [ ] All LEDs off after test completes

**Step 3.3 - Enable and start monitor:**

```
sudo honeypot-kit led enable
sudo honeypot-kit monitor start
sleep 5
honeypot-kit monitor status
```

The monitor status output shows full systemctl detail. Look for
`Active: active (running)` in the output.

- [ ] Monitor service shows as active (running)
- [ ] Green LED solid (healthy idle state)
- [ ] Yellow LED off
- [ ] Red LED off

**Step 3.4 - Verify monitor persists across reboot:**

```
sudo reboot
```

After reboot, clear the host key if needed and SSH back in on port 2222:

```
ssh-keygen -R [<pi-ip-address>]:2222
ssh -p 2222 pi@<pi-ip-address>
honeypot-kit monitor status
```

- [ ] Monitor service running automatically after reboot
- [ ] Green LED solid

**Step 3.5 - Active session state:**

SSH into port 22 from another machine and leave the session open.

- [ ] Yellow LED starts slow flashing within 5 seconds
- [ ] Green LED remains solid
- [ ] Note: Red LED will also start slow blinking once a successful login
  is recorded (login_history state). This is expected behavior.

Disconnect from the honeypot SSH session.

- [ ] Yellow LED stops within 5-10 seconds
- [ ] Green LED remains solid

**Step 3.6 - Login history state:**

After a successful login to Cowrie, the red LED blinks to indicate a login
was recorded. This persists until manually cleared.

- [ ] Red LED slow single blink every ~3 seconds
- [ ] Green LED solid
- [ ] Yellow LED off

**Step 3.7 - Clear alert:**

```
sudo honeypot-kit led clear-alert
sudo honeypot-kit monitor restart
sleep 5
```

- [ ] Red LED stops blinking
- [ ] Green LED solid (back to healthy idle)

---

## Phase 4 - TFT SPI Display

*Skip if TFT display not installed. The TFT SPI display is incompatible with
the LED module and OLED display - GPIO pins are unavailable when SPI display
is connected.*

**Step 4.1 - Install the display driver**

The goodtft driver must be installed before the display will work. This
modifies `/boot/firmware/config.txt` and reboots the system automatically.

```
sudo honeypot-kit tft install-driver
```

- [ ] Script clones goodtft/LCD-show from your fork at github.com/ericburnsonline/honeypot-kit-tft-driver
- [ ] Driver install runs without error
- [ ] System reboots automatically

After reboot, clear the host key and SSH back in on port 2222:

```
ssh-keygen -R [<pi-ip-address>]:2222
ssh -p 2222 pi@<pi-ip-address>
```

**Step 4.2 - Confirm framebuffer devices**

```
ls -la /dev/fb*
```

- [ ] `/dev/fb0` present (HDMI)
- [ ] `/dev/fb1` present (TFT display)

If `/dev/fb1` is missing the driver did not install correctly. Re-run
`sudo honeypot-kit tft install-driver`.

**Step 4.3 - Disable tty1 autologin**

The goodtft driver causes the Pi desktop to autostart on tty1 via autologin,
which writes to the TFT display and competes with the Honeypot Kit dashboard.
Disable it manually (this will be automated in a future install script update):

```
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
sudo bash -c 'cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --noclear %I \$TERM
EOF'
sudo systemctl daemon-reload
sudo systemctl restart getty@tty1
```

Also disable lightdm if it is enabled:

```
sudo systemctl disable lightdm
sudo systemctl stop lightdm
```

Kill any lingering desktop processes:

```
pkill lxpanel; pkill lxsession; pkill openbox; pkill pcmanfm
```

- [ ] Desktop processes no longer running: `ps aux | grep -E "lxpanel|lxsession" | grep -v grep` returns nothing

**Step 4.4 - Enable and test TFT display**

```
sudo honeypot-kit tft enable
```

If you get a `KeyError: tft` error, the config file predates TFT support.
Add the section manually:

```
sudo nano /opt/honeypot/honeypot-kit.conf
```

Add at the bottom:
```
[tft]
enabled = false
fb_device = /dev/fb1
resolution = 480x320
```

Then re-run `sudo honeypot-kit tft enable`.

```
sudo honeypot-kit tft test
```

- [ ] Test image appears on TFT display showing "Honeypot Kit", device path, and resolution
- [ ] No error output
- [ ] Image visible and readable (not tiled or portrait-oriented)

If display shows tiled content or wrong orientation, confirm resolution:

```
cat /opt/honeypot/honeypot-kit.conf | grep resolution
```

Should show `resolution = 480x320`. If it shows `320x480`, fix it:

```
sudo honeypot-kit tft set-resolution 480x320
```

**Step 4.5 - Start monitor and verify dashboard**

```
sudo honeypot-kit monitor start
sleep 5
cat /opt/honeypot/logs/monitor.log | tail -5
```

- [ ] Log shows `TFT display initialised (480x320 @ /dev/fb1)`
- [ ] Log shows `Monitor running. OLED: False, TFT: True, LED: False`

Check the TFT display:

- [ ] Dashboard visible - two column landscape layout
- [ ] Left column: three LED circles (green lit, yellow and red dark)
- [ ] Left column: attack count and rate
- [ ] Right column top: last attacker IP
- [ ] Right column bottom: disk%, memory%, Cowrie status with bar graphs
- [ ] Title bar: "Honeypot Kit", IP address, uptime, UTC time
- [ ] No desktop UI or flashing text overlaid on dashboard

**Step 4.6 - Verify live data updates**

SSH into port 22 from another machine and disconnect.

- [ ] Attack count increments on TFT display within 5 seconds
- [ ] LED circles update state (yellow lights during session)
- [ ] Red LED circle starts blinking after successful Cowrie login

Clear the alert:

```
sudo honeypot-kit led clear-alert
sudo honeypot-kit monitor restart
```

- [ ] Red LED circle returns to dark (off state)
- [ ] Green LED circle solid

**Step 4.7 - Reboot persistence**

```
sudo reboot
```

After reboot, SSH back in on port 2222:

```
ssh-keygen -R [<pi-ip-address>]:2222
ssh -p 2222 pi@<pi-ip-address>
```

```
cat /opt/honeypot/logs/monitor.log | tail -5
honeypot-kit monitor status
```

- [ ] Monitor started automatically after reboot
- [ ] TFT dashboard visible with no desktop competing for display
- [ ] No lxsession/lxpanel processes: `ps aux | grep lxsession | grep -v grep` returns nothing

---

## Phase 5 - OLED Display

*Skip if OLED not connected. Skip if TFT SPI display is installed (see Phase 4).*

**Step 4.1 - I2C detection:**

```
i2cdetect -y 1
```

- [ ] Display address visible in grid (typically `3c` or `3d`)

**Step 4.2 - Hardware test:**

```
sudo honeypot-kit oled set-address 0x3C
sudo honeypot-kit oled set-resolution 128x64
sudo honeypot-kit oled test
```

- [ ] Test image appears on display (shows "Honeypot Kit", address, resolution)
- [ ] Display clears after 3 seconds
- [ ] Command returns to prompt cleanly

**Step 4.3 - Enable and start monitor:**

```
sudo honeypot-kit oled enable
sudo honeypot-kit monitor restart
sleep 5
```

- [ ] Display shows live data (IP address, attack count, sessions, disk, uptime)
- [ ] Data refreshes every 5 seconds

**Step 4.4 - Session counter:**

SSH into port 22 from another machine.

- [ ] Sessions counter increments on OLED within 5 seconds

Disconnect.

- [ ] Sessions counter returns to 0 within 5-10 seconds


---

## Phase 6 - Cowrie Verification

**Test the fake shell from another machine:**

```
ssh -p 22 root@<pi-ip>
```

- [ ] Connection accepted
- [ ] Banner displayed (generic corporate notice, not "honeypot")
- [ ] Fake shell prompt appears (e.g. `root@server-01:~#`)
- [ ] Fake commands work: `ls`, `pwd`, `whoami`, `cat /etc/passwd`
- [ ] Real Pi filesystem NOT accessible
- [ ] Activity logged in Cowrie JSON log:

```
tail -10 /opt/honeypot/cowrie/var/log/cowrie/cowrie.json
```

- [ ] `cowrie.session.connect` event present
- [ ] `cowrie.login.success` event present (if credentials accepted)
- [ ] `cowrie.session.closed` event present after disconnect

---

## Phase 7 - CLI Verification

Run each command and confirm expected output:

```
honeypot-kit --version
```

- [ ] Shows current version number

```
honeypot-kit status
```

- [ ] Shows OLED status (enabled/disabled, address, resolution)
- [ ] Shows LED status (enabled/disabled, pin assignments)
- [ ] Shows TFT status (enabled/disabled, device, resolution)
- [ ] Shows monitor service status (running/stopped)
- [ ] Shows config file path

```
honeypot-kit integration list
```

- [ ] Shows all integrations with stage and status
- [ ] No error fetching manifest from GitHub

**The following commands are covered by Phases 3 and 4 above - skip if
those phases were completed successfully:**

```
# Already tested in Phase 4 if OLED connected:
sudo honeypot-kit oled set-address 0x3c   # test lowercase acceptance
```

- [ ] Accepts lowercase (0x3c) and normalizes to 0x3C without error

```
# Already tested in Phase 3 if LED connected:
sudo honeypot-kit led set-pins --red 17 --yellow 17 --green 22
```

- [ ] Rejects duplicate pins with clear error message

```
sudo honeypot-kit oled set-address 0x99
```

- [ ] Rejects invalid address with clear error message

```
sudo honeypot-kit led set-pins --red 1 --yellow 27 --green 22
```

- [ ] Rejects reserved pin (below 2) with clear error message

**Root check - run WITHOUT sudo:**

```
honeypot-kit led enable
```

- [ ] Clear error: "Run as: sudo honeypot-kit led enable"
- [ ] Does NOT crash silently

---

## Phase 8 - Auto-Update

*Skip if auto-update was declined at install.*

```
honeypot-kit update status
```

- [ ] Shows enabled
- [ ] Shows schedule (weekly Sunday 03:00)

```
honeypot-kit update branch
```

- [ ] Shows current branch (should be `main` for stable installs)

```
sudo honeypot-kit update now
```

- [ ] Runs without error
- [ ] Completes within 30 seconds

```
cat /opt/honeypot/logs/updates.log
```

- [ ] Shows update check entries (OK: cli.py, OK: monitor.py)
- [ ] No FAILED entries

```
systemctl status honeypot-update.timer
```

- [ ] Timer active and enabled

---

## Phase 9 - Reboot Persistence

*Note: if Phase 3 Step 3.4 was completed, this phase is already partially
verified. Focus on Cowrie and overall system state here.*

Reboot the Pi and verify everything comes back up automatically.

```
sudo reboot
```

After reboot, wait 60 seconds. Clear the host key if needed and SSH in
on the real SSH port:

```
ssh-keygen -R [<pi-ip-address>]:2222
ssh -p 2222 pi@<pi-ip-address>
```

```
sudo nmap -sS localhost
```

- [ ] Port 22 open (Cowrie running after reboot)
- [ ] Real SSH port open

```
honeypot-kit monitor status
```

- [ ] Monitor service running (if OLED, LED, or TFT enabled)

```
honeypot-kit status
```

- [ ] Module config preserved (enabled/disabled state correct)

```
cat /opt/honeypot/monitor-state.json
```

- [ ] login_history state preserved across reboot

---

## Phase 10 - Health Check

Verify the 5-minute health check is installed and functional:

```
cat /etc/cron.d/honeypot-health
```

- [ ] Cron entry present

```
sudo /opt/honeypot/scripts/health-check.sh
```

- [ ] Runs without error
- [ ] No alerts generated (assuming system is healthy)

---

## Timing Reference

| Phase | Expected time |
|-------|--------------|
| Install - questions | ~2 minutes |
| Install - unattended | ~11-13 minutes (varies by network speed) |
| Full test pass (no hardware) | ~15 minutes |
| Full test pass (with OLED + LED) | ~25 minutes |

---

## Known Issues Log

| Date | Version | Issue | Status |
|------|---------|-------|--------|
| 2026-08-21 | v11 | Session tracking missed sessions started before monitor | Fixed v11 |
| 2026-08-21 | v11 | Cowrie JSON log path was wrong (cowrie.log vs cowrie.json) | Fixed v11 |
| 2026-08-21 | v11 | GPIO.HIGH bare reference in _set() | Fixed v11 |
| 2026-08-21 | v11 | click not installed via pip on Trixie | Fixed v12 (apt) |
| 2026-08-21 | v11 | monitor.log permission denied for pi user | Fixed v12 |
| 2026-08-21 | v11 | shebang typo in cli.py (evn vs env) | Fixed v11 |
| 2026-08-23 | v12 | monitor-state.json permission denied for pi user | Fixed v13 |
| 2026-08-23 | v12 | Monitor replays old log events on startup (login_history bug) | Fixed v13 |
| 2026-08-23 | v12 | Cowrie JSON output not enabled by default | Fixed v13 |
| 2026-08-23 | v12 | Monitor service not auto-starting after reboot | Fixed v13 (cli.py) |

---

## Test Sign-Off

| Item | Result | Notes |
|------|--------|-------|
| Install script version | | |
| OS version | RPi OS 64-bit Debian Trixie | |
| Hardware | RPi 4 | |
| RAM | 8GB tested (4GB expected to work, untested) | |
| OLED tested | | |
| LED tested | | |
| TFT tested | | |
| Cowrie verified | | |
| Auto-update verified | | |
| Reboot persistence verified | | |
| Tested by | Eric Burns | |
| Date | | |
