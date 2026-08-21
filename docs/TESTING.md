# Honeypot Kit - Testing Guide

Post-install acceptance checklist. Run through this after every fresh install
or major update. Check off each item as you go. Stop at any failure and note
the error before continuing.

**Platform tested:** Raspberry Pi 4, 64-bit Debian Trixie  
**Last updated:** 2026-08-21

---

## Phase 1 - Smoke Test

Run the built-in smoke test first. This catches the most common issues quickly.

```bash
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

```bash
sudo nmap -sS localhost
```

- [ ] Port 22 open (Cowrie)
- [ ] Real SSH port open (e.g. 2222 or your chosen port)
- [ ] No unexpected open ports

```bash
sudo ufw status
```

- [ ] UFW active
- [ ] Port 22 allowed
- [ ] Real SSH port allowed
- [ ] Port 8000 restricted to dashboard subnet only

---

## Phase 3 - Cowrie Verification

**Test the fake shell from another machine:**

```bash
ssh -p 22 root@<pi-ip>
```

- [ ] Connection accepted
- [ ] Banner displayed (generic corporate notice, not "honeypot")
- [ ] Fake shell prompt appears (e.g. `root@server-01:~#`)
- [ ] Fake commands work: `ls`, `pwd`, `whoami`, `cat /etc/passwd`
- [ ] Real Pi filesystem NOT accessible
- [ ] Activity logged in Cowrie JSON log:

```bash
tail -10 /opt/honeypot/cowrie/var/log/cowrie/cowrie.json
```

- [ ] `cowrie.session.connect` event present
- [ ] `cowrie.login.success` event present (if credentials accepted)
- [ ] `cowrie.session.closed` event present after disconnect

---

## Phase 4 - LED Module

*Skip if LED module not connected.*

**Step 4.1 - Hardware test:**
```bash
sudo honeypot-kit led test
```
- [ ] Green LED flashes for 1 second
- [ ] Yellow LED flashes for 1 second
- [ ] Red LED flashes for 1 second
- [ ] All LEDs off after test completes

**Step 4.2 - Enable and start monitor:**
```bash
sudo honeypot-kit led enable
sudo honeypot-kit monitor start
sleep 5
honeypot-kit monitor status
```
- [ ] Monitor service shows as running
- [ ] Green LED solid (healthy idle state)
- [ ] Yellow LED off
- [ ] Red LED off

**Step 4.3 - Active session state:**

SSH into port 22 from another machine and leave the session open.

- [ ] Yellow LED starts slow flashing within 5 seconds
- [ ] Green LED remains solid

Disconnect from the honeypot SSH session.

- [ ] Yellow LED stops within 5-10 seconds
- [ ] Green LED remains solid

**Step 4.4 - Login history state:**

The red LED blink every 3 seconds should now be active (login.success was seen).

- [ ] Red LED slow single blink every ~3 seconds
- [ ] Green LED solid
- [ ] Yellow LED off

**Step 4.5 - Clear alert:**
```bash
sudo honeypot-kit led clear-alert
sudo honeypot-kit monitor restart
sleep 5
```
- [ ] Red LED stops blinking
- [ ] Green LED solid (back to healthy idle)

---

## Phase 5 - OLED Display

*Skip if OLED not connected.*

**Step 5.1 - I2C detection:**
```bash
i2cdetect -y 1
```
- [ ] Display address visible in grid (typically `3c` or `3d`)

**Step 5.2 - Hardware test:**
```bash
sudo honeypot-kit oled set-address 0x3C
sudo honeypot-kit oled test
```
- [ ] Test image appears on display (shows "Honeypot Kit", address, resolution)
- [ ] Display clears after 3 seconds
- [ ] Command returns to prompt cleanly

**Step 5.3 - Enable and start monitor:**
```bash
sudo honeypot-kit oled enable
sudo honeypot-kit monitor restart
sleep 5
```
- [ ] Display shows live data (IP address, attack count, sessions, disk, uptime)
- [ ] Data refreshes every 5 seconds

**Step 5.4 - Session counter:**

SSH into port 22 from another machine.

- [ ] Sessions counter increments on OLED within 5 seconds

Disconnect.

- [ ] Sessions counter returns to 0 within 5-10 seconds

---

## Phase 6 - CLI Verification

Run each command and confirm expected output:

```bash
honeypot-kit status
```
- [ ] Shows OLED status (enabled/disabled, address, resolution)
- [ ] Shows LED status (enabled/disabled, pin assignments)
- [ ] Shows monitor service status (running/stopped)
- [ ] Shows config file path

```bash
honeypot-kit oled set-address 0x3c
```
- [ ] Accepts lowercase (0x3c) and normalizes to 0x3C without error

```bash
honeypot-kit led set-pins --red 17 --yellow 27 --green 22
```
- [ ] Accepts pin assignment without error

```bash
honeypot-kit led set-pins --red 17 --yellow 17 --green 22
```
- [ ] Rejects duplicate pins with clear error message

```bash
honeypot-kit oled set-address 0x99
```
- [ ] Rejects invalid address with clear error message

```bash
honeypot-kit led set-pins --red 1 --yellow 27 --green 22
```
- [ ] Rejects reserved pin (below 2) with clear error message

**Root check - run WITHOUT sudo:**
```bash
honeypot-kit led enable
```
- [ ] Clear error: "Run as: sudo honeypot-kit led enable"
- [ ] Does NOT crash silently

---

## Phase 7 - Auto-Update

*Skip if auto-update was declined at install.*

```bash
honeypot-kit update status
```
- [ ] Shows enabled
- [ ] Shows schedule (weekly Sunday 03:00)

```bash
sudo honeypot-kit update now
```
- [ ] Runs without error
- [ ] Completes within 30 seconds

```bash
cat /opt/honeypot/logs/updates.log
```
- [ ] Shows update check entries (OK: cli.py, OK: monitor.py)
- [ ] No FAILED entries

```bash
systemctl status honeypot-update.timer
```
- [ ] Timer active and enabled

---

## Phase 8 - Reboot Persistence

Reboot the Pi and verify everything comes back up automatically.

```bash
sudo reboot
```

After reboot, wait 60 seconds then SSH in on the real SSH port.

```bash
sudo nmap -sS localhost
```
- [ ] Port 22 open (Cowrie running after reboot)
- [ ] Real SSH port open

```bash
honeypot-kit monitor status
```
- [ ] Monitor service running (if OLED or LED enabled)

```bash
honeypot-kit status
```
- [ ] Module config preserved (enabled/disabled state correct)

```bash
cat /opt/honeypot/monitor-state.json
```
- [ ] login_history state preserved across reboot

---

## Phase 9 - Health Check

Verify the 5-minute health check is installed and functional:

```bash
cat /etc/cron.d/honeypot-health
```
- [ ] Cron entry present

```bash
sudo /opt/honeypot/scripts/health-check.sh
```
- [ ] Runs without error
- [ ] No alerts generated (assuming system is healthy)

---

## Known Issues Log

Track issues found during testing here before they are fixed.

| Date | Version | Issue | Status |
|------|---------|-------|--------|
| 2026-08-21 | v11 | Session tracking missed sessions started before monitor | Fixed v11 |
| 2026-08-21 | v11 | Cowrie JSON log path was wrong (cowrie.log vs cowrie.json) | Fixed v11 |
| 2026-08-21 | v11 | GPIO.HIGH bare reference in _set() | Fixed v11 |
| 2026-08-21 | v11 | click not installed via pip on Trixie | Fixed v12 (apt) |
| 2026-08-21 | v11 | monitor.log permission denied for pi user | Fixed v12 |
| 2026-08-21 | v11 | shebang typo in cli.py (evn vs env) | Fixed v11 |

---

## Test Sign-Off

| Item | Result | Notes |
|------|--------|-------|
| Install script version | | |
| OS version | RPi OS 64-bit Debian Trixie | |
| Hardware | RPi 4 | |
| OLED tested | | |
| LED tested | | |
| Cowrie verified | | |
| Auto-update verified | | |
| Reboot persistence verified | | |
| Tested by | Eric Burns | |
| Date | | |
