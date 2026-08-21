#!/bin/bash
###############################################################################
# Honeypot Kit - Install Script
# Version: 12
# Educational SSH honeypot (Cowrie) with health checks and OPSEC hardening
#
# Tested on: Raspberry Pi 4, 64-bit Raspberry Pi OS Debian Trixie (2026-06-18)
#
# Usage: sudo bash install-honeypot.sh
#
# v12 CHANGES:
#   - configure_i2c(): enables I2C automatically via /boot/firmware/config.txt
#     (no raspi-config needed); installs i2c-tools; loads i2c modules for
#     current session; takes full effect after reboot
###############################################################################

VERSION="12"
GITHUB_RAW="https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
HONEYPOT_HOME="/opt/honeypot"
COWRIE_HOME="$HONEYPOT_HOME/cowrie"
LOG_DIR="$HONEYPOT_HOME/logs"
COWRIE_USER="cowrie"
CLI_SCRIPT="/usr/local/bin/honeypot-kit"
CONF_FILE="$HONEYPOT_HOME/honeypot-kit.conf"

# Timing
SCRIPT_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
SCRIPT_START_EPOCH=$(date +%s)

###############################################################################
# UTILITY FUNCTIONS
###############################################################################

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

fmt_secs() { printf '%dm %02ds' $(( $1 / 60 )) $(( $1 % 60 )); }

###############################################################################
# INVOCATION CHECK
###############################################################################

check_invocation() {
    if [ -z "$BASH_VERSION" ]; then
        echo ""
        echo "ERROR: This script must be run with bash."
        echo ""
        echo "  Correct usage:  sudo bash install-honeypot.sh"
        echo ""
        exit 1
    fi

    if [[ $EUID -ne 0 ]]; then
        echo ""
        echo "ERROR: This script must be run as root."
        echo ""
        echo "  Correct usage:  sudo bash install-honeypot.sh"
        echo ""
        exit 1
    fi
}

###############################################################################
# HOSTNAME POOL
###############################################################################

suggest_hostname() {
    local WEB=(web01 web02 web03 web04 web05 web06 web07 web08 web09 web10 web11 web12)
    local MAIL=(mail01 mail02 mail03 mail04 mail05)
    local DB=(db01 db02 db03 db04 db05)
    local SRV=(srv01 srv02 srv03 srv04 srv05 srv06 srv07 srv08 srv09 srv10)
    local APP=(app01 app02 app03 app04 app05 app06 app07 app08)
    local PROD=(prod01 prod02 prod03 prod04 prod05 prod06)
    local BACKUP=(backup01 backup02 backup03 backup04)
    local NAS=(nas01 nas02 nas03)
    local MISC=(gateway fileserver ubuntu debian vps droplet)

    local ALL=(
        "${WEB[@]}" "${MAIL[@]}" "${DB[@]}" "${SRV[@]}"
        "${APP[@]}" "${PROD[@]}" "${BACKUP[@]}" "${NAS[@]}"
        "${MISC[@]}"
    )

    echo "${ALL[$RANDOM % ${#ALL[@]}]}"
}

###############################################################################
# PHASE 1: GATHER ALL CONFIGURATION UP FRONT
###############################################################################

gather_configuration() {
    clear
    echo "============================================================"
    echo "        Honeypot Kit Installer  (v${VERSION})"
    echo "        Configuration - answer a few questions,"
    echo "        then you can walk away."
    echo "============================================================"
    echo ""

    # --- Network interface ---
    echo "Available network interfaces:"
    ip -o link show | awk -F': ' '{print "  " $2}' | grep -v '^  lo$'
    echo ""
    read -p "Enter network interface [eth0]: " NETWORK_IF
    NETWORK_IF=${NETWORK_IF:-eth0}
    if ! ip link show "$NETWORK_IF" > /dev/null 2>&1; then
        log_error "Interface $NETWORK_IF not found. Re-run and pick from the list above."
        exit 1
    fi

    # --- Hostname ---
    echo ""
    SUGGESTED_HOST=$(suggest_hostname)
    echo "Current hostname  : $(hostname)"
    echo "Suggested hostname: $SUGGESTED_HOST"
    echo "For OPSEC, use a generic name (NOT 'honeypot', 'test', or 'trap')."
    read -p "Accept suggested or enter your own [$SUGGESTED_HOST]: " NEW_HOSTNAME
    NEW_HOSTNAME=${NEW_HOSTNAME:-$SUGGESTED_HOST}

    # --- Real SSH port ---
    echo ""
    echo "Real SSH will be moved off port 22 (Cowrie takes that)."
    echo "Port 2222 is suggested. Pick any unused port 1024-65535."
    echo "Tip: a less obvious port (e.g. 4822, 7022) is better OPSEC than 2222."
    while true; do
        read -p "Enter real SSH port [2222]: " SSH_PORT
        SSH_PORT=${SSH_PORT:-2222}

        if ! [[ "$SSH_PORT" =~ ^[0-9]+$ ]]; then
            log_error "Port must be a number."; continue
        fi
        if [ "$SSH_PORT" -lt 1024 ]; then
            log_error "Port must be 1024 or above (below 1024 is reserved)."; continue
        fi
        if [ "$SSH_PORT" -gt 65535 ]; then
            log_error "Port must be 65535 or below."; continue
        fi
        if [[ "$SSH_PORT" =~ ^(8080|8443|3389|3306|5432|6379|27017)$ ]]; then
            log_warn "Port $SSH_PORT is a well-known service port. Consider a less common one."
            read -p "Use it anyway? [y/N]: " USE_ANYWAY
            [[ "$USE_ANYWAY" =~ ^[Yy]$ ]] || continue
        fi
        if ss -tlnp | grep -q ":${SSH_PORT}\b"; then
            log_error "Port $SSH_PORT is already in use. Pick another."; continue
        fi
        break
    done

    # --- Dashboard subnet ---
    echo ""
    echo "The monitoring dashboard (port 8000) is never exposed to the internet."
    echo "Optionally allow it from your internal LAN only."
    read -p "Allow dashboard from subnet [192.168.1.0/24]: " DASHBOARD_SUBNET
    DASHBOARD_SUBNET=${DASHBOARD_SUBNET:-192.168.1.0/24}

    # --- Auto-update ---
    echo ""
    echo "Honeypot Kit can automatically check for and apply weekly updates"
    echo "to its own modules (CLI, monitor daemon, integrations)."
    echo "Cowrie and system packages are never touched by this."
    read -p "Enable automatic weekly module updates? [y/N]: " AUTO_UPDATE
    if [[ "$AUTO_UPDATE" =~ ^[Yy]$ ]]; then
        AUTO_UPDATE_ENABLED=true
    else
        AUTO_UPDATE_ENABLED=false
    fi

    # --- Confirm ---
    echo ""
    echo "------------------------------------------------------------"
    echo " Configuration summary"
    echo "------------------------------------------------------------"
    echo "  Network interface : $NETWORK_IF"
    echo "  Hostname          : $NEW_HOSTNAME"
    echo "  Dashboard subnet  : $DASHBOARD_SUBNET"
    echo "  Cowrie honeypot   : port 22"
    echo "  Real SSH          : port $SSH_PORT"
    echo "  Auto-update       : $AUTO_UPDATE_ENABLED"
    echo "------------------------------------------------------------"
    echo ""
    read -p "Proceed with installation? [y/N]: " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        log_error "Installation cancelled."
        exit 1
    fi

    # Unattended timer starts HERE - last moment of user input
    UNATTENDED_START_EPOCH=$(date +%s)
    UNATTENDED_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

    echo ""
    echo "============================================================"
    echo "  Configuration complete. Starting unattended install."
    echo "  You can safely walk away now."
    echo "============================================================"
    echo ""
}

###############################################################################
# PHASE 2: UNATTENDED INSTALL
###############################################################################

create_directories() {
    log_info "Creating directories..."
    mkdir -p "$HONEYPOT_HOME" "$COWRIE_HOME" \
             "$HONEYPOT_HOME/backend" "$HONEYPOT_HOME/frontend" \
             "$HONEYPOT_HOME/modules" "$HONEYPOT_HOME/scripts" "$LOG_DIR"
}

update_system() {
    log_info "Updating system (this is the slow part)..."
    apt-get update > /dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y > /dev/null 2>&1
}

install_dependencies() {
    log_info "Installing dependencies..."
    apt-get install -y \
        python3 python3-pip python3-venv python3-dev \
        git \
        isc-dhcp-client \
        chrony \
        ufw \
        nmap \
        authbind \
        libffi-dev libssl-dev build-essential \
        net-tools curl wget \
        python3-click \
        python3-rpi.gpio \
        python3-pil \
        > /dev/null 2>&1

    # Adafruit OLED library - not always available via apt on Trixie/Python 3.13
    # Install via pip with --break-system-packages; skip silently if unavailable
    pip3 install --quiet --no-cache-dir --break-system-packages \
        adafruit-circuitpython-ssd1306 adafruit-blinka \
        > /dev/null 2>&1 || \
        log_warn "Adafruit OLED library not available - install manually when connecting OLED display."
}

configure_hostname() {
    log_info "Setting hostname to: $NEW_HOSTNAME"
    hostnamectl set-hostname "$NEW_HOSTNAME" 2>/dev/null || \
        echo "$NEW_HOSTNAME" > /etc/hostname

    if grep -qE '^127\.0\.1\.1' /etc/hosts; then
        sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$NEW_HOSTNAME/" /etc/hosts
    else
        echo -e "127.0.1.1\t$NEW_HOSTNAME" >> /etc/hosts
    fi
}

configure_network() {
    log_info "Ensuring DHCP on $NETWORK_IF..."
    if command -v dhclient > /dev/null 2>&1; then
        dhclient "$NETWORK_IF" > /dev/null 2>&1 || true
    elif command -v dhcpcd > /dev/null 2>&1; then
        dhcpcd "$NETWORK_IF" > /dev/null 2>&1 || true
    else
        systemctl restart systemd-networkd > /dev/null 2>&1 || true
    fi

    sleep 2
    HONEYPOT_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$HONEYPOT_IP" ]; then
        log_warn "Could not auto-detect an IP address; continuing anyway."
        HONEYPOT_IP="(unknown - check with: hostname -I)"
    fi
    log_info "IP address: $HONEYPOT_IP"
    echo "$HONEYPOT_IP" > "$HONEYPOT_HOME/network-info.txt" 2>/dev/null || true
}

configure_ntp() {
    log_info "Configuring time synchronization (chrony)..."
    systemctl enable chrony > /dev/null 2>&1
    systemctl restart chrony > /dev/null 2>&1
    sleep 3
    if timedatectl status 2>/dev/null | grep -qi "synchronized: yes"; then
        log_info "Time synchronized."
    else
        log_warn "Time sync still settling; chrony will catch up shortly."
    fi
}

install_cowrie() {
    log_info "Installing Cowrie SSH honeypot..."

    if ! id "$COWRIE_USER" > /dev/null 2>&1; then
        useradd -r -s /usr/sbin/nologin "$COWRIE_USER" 2>/dev/null || true
    fi

    if [ ! -d "$COWRIE_HOME/.git" ]; then
        rm -rf "$COWRIE_HOME"
        git clone https://github.com/cowrie/cowrie.git "$COWRIE_HOME" > /dev/null 2>&1
    fi

    chown -R "$COWRIE_USER":"$COWRIE_USER" "$COWRIE_HOME"

    sudo -u "$COWRIE_USER" bash -c "
        cd '$COWRIE_HOME' || exit 1
        python3 -m venv venv
        source venv/bin/activate
        pip install --quiet --no-cache-dir --upgrade pip
        pip install --quiet --no-cache-dir -e .
    "

    sudo -u "$COWRIE_USER" bash -c "
        cd '$COWRIE_HOME' || exit 1
        source venv/bin/activate
        if [ ! -f etc/cowrie.cfg ]; then
            cowrie init
        fi
        mkdir -p var/log/cowrie var/lib/cowrie var/run
    "

    # Put Cowrie on port 22
    sudo -u "$COWRIE_USER" sed -i \
        's|tcp:2222:interface=0.0.0.0|tcp:22:interface=0.0.0.0|g' \
        "$COWRIE_HOME/etc/cowrie.cfg"

    log_info "Cowrie installed and configured on port 22."
}

configure_authbind() {
    log_info "Configuring authbind so Cowrie can bind to port 22..."
    touch /etc/authbind/byport/22
    chown "$COWRIE_USER" /etc/authbind/byport/22
    chmod 755 /etc/authbind/byport/22
}

configure_ssh() {
    log_info "Configuring real SSH to listen on port $SSH_PORT..."

    if grep -q "^Port " /etc/ssh/sshd_config; then
        sed -i "s/^Port .*/Port $SSH_PORT/" /etc/ssh/sshd_config
    elif grep -q "^#Port " /etc/ssh/sshd_config; then
        sed -i "s/^#Port .*/Port $SSH_PORT/" /etc/ssh/sshd_config
    else
        echo "Port $SSH_PORT" >> /etc/ssh/sshd_config
    fi

    systemctl enable ssh > /dev/null 2>&1
    systemctl restart ssh > /dev/null 2>&1

    if systemctl is-active --quiet ssh; then
        log_info "SSH enabled and listening on port $SSH_PORT."
    else
        log_warn "SSH may not have started correctly. Check: systemctl status ssh"
    fi
}

fix_permissions() {
    log_info "Verifying ownership and permissions..."
    chown -R "$COWRIE_USER":"$COWRIE_USER" "$HONEYPOT_HOME"
    chmod -R u+rwX "$COWRIE_HOME"
    mkdir -p "$COWRIE_HOME/var/log/cowrie" "$COWRIE_HOME/var/run"
    chmod -R u+rwX "$COWRIE_HOME/var"
    # Log dir writable by cowrie and pi (monitor daemon runs as pi)
    chmod -R 0777 "$LOG_DIR"
    # Pre-create monitor log so permissions are set before daemon starts
    touch "$LOG_DIR/monitor.log"
    chmod 0666 "$LOG_DIR/monitor.log"
}

configure_firewall() {
    log_info "Configuring firewall (UFW)..."
    ufw --force enable > /dev/null 2>&1
    ufw default deny incoming > /dev/null 2>&1
    ufw default allow outgoing > /dev/null 2>&1
    ufw allow 22/tcp   > /dev/null 2>&1
    ufw allow "$SSH_PORT"/tcp > /dev/null 2>&1
    ufw deny to any port 8000 > /dev/null 2>&1
    ufw allow from "$DASHBOARD_SUBNET" to any port 8000 > /dev/null 2>&1
    log_info "Firewall configured."
}

configure_logrotate() {
    log_info "Configuring log rotation..."
    cat > /etc/logrotate.d/honeypot << 'EOF'
/opt/honeypot/cowrie/var/log/cowrie/cowrie.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 cowrie cowrie
    sharedscripts
    postrotate
        systemctl reload cowrie > /dev/null 2>&1 || true
    endscript
}

/opt/honeypot/logs/*.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 0640 cowrie cowrie
}
EOF
}

install_health_check() {
    log_info "Installing health check (runs every 5 minutes)..."
    cat > "$HONEYPOT_HOME/scripts/health-check.sh" << 'HEALTHEOF'
#!/bin/bash
ALERT_FILE="/tmp/honeypot-alert.txt"
> "$ALERT_FILE"

if ! pgrep -u cowrie > /dev/null 2>&1; then
    echo "ALERT: Cowrie honeypot not running" >> "$ALERT_FILE"
    systemctl start cowrie > /dev/null 2>&1
fi

USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
[ "$USAGE" -gt 85 ] && echo "ALERT: Disk usage at ${USAGE}%" >> "$ALERT_FILE"

MEM=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
[ "$MEM" -gt 90 ] && echo "ALERT: Memory usage at ${MEM}%" >> "$ALERT_FILE"

if ! touch /opt/honeypot/logs/.write-test 2>/dev/null; then
    echo "ALERT: Cannot write to logs directory" >> "$ALERT_FILE"
else
    rm -f /opt/honeypot/logs/.write-test
fi

[ -s "$ALERT_FILE" ] && logger -t honeypot-health < "$ALERT_FILE"
HEALTHEOF

    chmod +x "$HONEYPOT_HOME/scripts/health-check.sh"

    if [ ! -f "$HONEYPOT_HOME/scripts/health-check.sh" ]; then
        log_warn "health-check.sh failed to write."
    fi

    cat > /etc/cron.d/honeypot-health << 'CRONEOF'
*/5 * * * * root /opt/honeypot/scripts/health-check.sh > /dev/null 2>&1
CRONEOF
}

install_smoke_test() {
    log_info "Installing smoke test..."

    # Write shebang and SSH_PORT first, then append the rest
    # with a QUOTED heredoc so no backslash escaping is needed
    # and the outer script's variables are not expanded inside it.
    {
        echo "#!/bin/bash"
        echo "SSH_PORT=${SSH_PORT}"
    } > "$HONEYPOT_HOME/scripts/smoke-test.sh"

    cat >> "$HONEYPOT_HOME/scripts/smoke-test.sh" << 'SMOKEEOF'

echo "=== Honeypot Kit Smoke Test ==="
PASS=0; FAIL=0; WARN=0

# 1. Process check
if pgrep -u cowrie > /dev/null 2>&1; then
    echo "  [PASS] Cowrie process running"; ((PASS++))
else
    echo "  [FAIL] No Cowrie process found"; ((FAIL++))
fi

# 2. Cowrie port check
if ss -tlnp | grep -q ':22\b'; then
    echo "  [PASS] Cowrie listening on port 22"; ((PASS++))
elif ss -tlnp | grep -q ':2222\b'; then
    echo "  [WARN] Something on port 2222 - Cowrie may be on wrong port"; ((WARN++))
else
    echo "  [FAIL] Nothing listening on port 22"; ((FAIL++))
fi

# 3. Real SSH check on configured port
if ss -tlnp | grep -q ":${SSH_PORT}\b"; then
    echo "  [PASS] Real SSH listening on port ${SSH_PORT}"; ((PASS++))
else
    echo "  [WARN] Real SSH not found on port ${SSH_PORT}"; ((WARN++))
fi

# 4. Log file exists and was written recently
LOG="/opt/honeypot/cowrie/var/log/cowrie/cowrie.log"
if [ -f "$LOG" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LOG") ))
    if [ "$AGE" -lt 600 ]; then
        echo "  [PASS] Log file active (last write ${AGE}s ago)"; ((PASS++))
    else
        echo "  [WARN] Log file exists but last write was ${AGE}s ago"; ((WARN++))
    fi
else
    echo "  [FAIL] No log file found"; ((FAIL++))
fi

# 5. Disk
DISK=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK" -lt 85 ]; then
    echo "  [PASS] Disk OK (${DISK}%)"; ((PASS++))
else
    echo "  [FAIL] Disk high (${DISK}%)"; ((FAIL++))
fi

# 6. Time sync
if timedatectl status 2>/dev/null | grep -qi "synchronized: yes"; then
    echo "  [PASS] Time synchronized"; ((PASS++))
else
    echo "  [WARN] Time not yet synchronized"; ((WARN++))
fi

# 7. CLI tool present
if command -v honeypot-kit > /dev/null 2>&1; then
    echo "  [PASS] honeypot-kit CLI installed"; ((PASS++))
else
    echo "  [WARN] honeypot-kit CLI not found"; ((WARN++))
fi

# 8. Auto-update timer (warn only if not present - may have been declined)
if systemctl is-enabled --quiet honeypot-update.timer 2>/dev/null; then
    echo "  [PASS] Auto-update timer enabled"; ((PASS++))
else
    echo "  [INFO] Auto-update timer not enabled (declined at install or disabled)"
fi

# 9. I2C interface
if [ -e /dev/i2c-1 ]; then
    echo "  [PASS] I2C enabled (/dev/i2c-1 present)"; ((PASS++))
else
    echo "  [WARN] I2C not detected - OLED will not work; reboot if just installed"; ((WARN++))
fi

echo ""
echo "Results: $PASS passed, $WARN warnings, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
SMOKEEOF

    chmod +x "$HONEYPOT_HOME/scripts/smoke-test.sh"

    if [ ! -f "$HONEYPOT_HOME/scripts/smoke-test.sh" ]; then
        log_warn "smoke-test.sh failed to write."
    else
        log_info "Smoke test installed at $HONEYPOT_HOME/scripts/smoke-test.sh"
    fi
}

###############################################################################
# DEFAULT CONFIG FILE
###############################################################################

install_config() {
    log_info "Writing default configuration file..."
    cat > "$CONF_FILE" << 'CONFEOF'
[oled]
enabled = false
i2c_address = 0x3C
resolution = 128x64

[led]
enabled = false
pin_red = 17
pin_yellow = 27
pin_green = 22
CONFEOF
    log_info "Config written to $CONF_FILE"
}

###############################################################################
# CLI TOOL
###############################################################################

install_cli() {
    log_info "Downloading honeypot-kit CLI from GitHub..."
    if wget -q "$GITHUB_RAW/modules/cli.py" -O "$CLI_SCRIPT"; then
        chmod +x "$CLI_SCRIPT"
        log_info "CLI installed at $CLI_SCRIPT"
        log_info "Usage: honeypot-kit status"
    else
        log_warn "CLI download failed. Check network and try: wget $GITHUB_RAW/modules/cli.py"
    fi
}

install_monitor() {
    log_info "Downloading hardware monitor daemon from GitHub..."
    mkdir -p "$HONEYPOT_HOME/modules"
    if wget -q "$GITHUB_RAW/modules/monitor.py" -O "$HONEYPOT_HOME/modules/monitor.py"; then
        chmod +x "$HONEYPOT_HOME/modules/monitor.py"
        log_info "Monitor daemon installed at $HONEYPOT_HOME/modules/monitor.py"
    else
        log_warn "Monitor download failed. Check network and try: wget $GITHUB_RAW/modules/monitor.py"
    fi
}

create_monitor_service() {
    log_info "Creating honeypot-monitor systemd service..."
    cat > /etc/systemd/system/honeypot-monitor.service << MONEOF
[Unit]
Description=Honeypot Kit Hardware Monitor (OLED + LED)
After=network.target cowrie.service
Wants=cowrie.service

[Service]
Type=simple
User=pi
WorkingDirectory=$HONEYPOT_HOME
ExecStart=/usr/bin/python3 $HONEYPOT_HOME/modules/monitor.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
MONEOF

    systemctl daemon-reload > /dev/null 2>&1
    # Monitor service is NOT enabled by default - only starts when
    # user enables OLED or LED via CLI
    log_info "Monitor service created (disabled by default)."
    log_info "Enable with: honeypot-kit oled enable && honeypot-kit monitor start"
}

install_auto_update() {
    if [ "$AUTO_UPDATE_ENABLED" != "true" ]; then
        log_info "Auto-update disabled - skipping."
        return
    fi

    log_info "Installing auto-update service..."

    # Update script
    cat > /opt/honeypot/scripts/honeypot-update.sh << 'UPDATEEOF'
#!/bin/bash
###############################################################################
# Honeypot Kit - Module Auto-updater
# Updates CLI, monitor daemon, and integration modules from GitHub.
# Never touches Cowrie or system packages.
###############################################################################

GITHUB_RAW="https://raw.githubusercontent.com/ericburnsonline/honeypot-kit/main"
HONEYPOT_HOME="/opt/honeypot"
LOG_FILE="$HONEYPOT_HOME/logs/updates.log"
MODULES_DIR="$HONEYPOT_HOME/modules"
CLI_SCRIPT="/usr/local/bin/honeypot-kit"
UPDATE_CONF="$HONEYPOT_HOME/honeypot-kit.conf"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log_update() { echo "[$TIMESTAMP] $1" >> "$LOG_FILE"; }

# Files to check and update
declare -A UPDATE_FILES=(
    ["$GITHUB_RAW/modules/monitor.py"]="$MODULES_DIR/monitor.py"
    ["$GITHUB_RAW/modules/cli.py"]="$CLI_SCRIPT"
)

CHANGED=0
FAILED=0

log_update "--- Auto-update check started ---"

for URL in "${!UPDATE_FILES[@]}"; do
    DEST="${UPDATE_FILES[$URL]}"
    TMPFILE=$(mktemp)
    FILENAME=$(basename "$DEST")

    if wget -q "$URL" -O "$TMPFILE" 2>/dev/null; then
        # Compare checksums
        NEW_SUM=$(sha256sum "$TMPFILE" | awk '{print $1}')
        if [ -f "$DEST" ]; then
            OLD_SUM=$(sha256sum "$DEST" | awk '{print $1}')
        else
            OLD_SUM=""
        fi

        if [ "$NEW_SUM" != "$OLD_SUM" ]; then
            cp "$TMPFILE" "$DEST"
            chmod +x "$DEST"
            log_update "UPDATED: $FILENAME (checksum changed)"
            CHANGED=$((CHANGED + 1))

            # Restart monitor service if monitor.py changed
            if [[ "$FILENAME" == "monitor.py" ]]; then
                if systemctl is-active --quiet honeypot-monitor; then
                    systemctl restart honeypot-monitor > /dev/null 2>&1
                    log_update "RESTARTED: honeypot-monitor service"
                fi
            fi
        else
            log_update "OK: $FILENAME (no change)"
        fi
    else
        log_update "FAILED: $FILENAME (download error - keeping existing)"
        FAILED=$((FAILED + 1))
    fi

    rm -f "$TMPFILE"
done

log_update "--- Update check complete: $CHANGED updated, $FAILED failed ---"
UPDATEEOF

    chmod +x /opt/honeypot/scripts/honeypot-update.sh

    # systemd service unit (runs the script)
    cat > /etc/systemd/system/honeypot-update.service << 'SVCEOF'
[Unit]
Description=Honeypot Kit Module Updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/honeypot/scripts/honeypot-update.sh
StandardOutput=journal
StandardError=journal
SVCEOF

    # systemd timer (weekly, Sunday at 03:00)
    cat > /etc/systemd/system/honeypot-update.timer << 'TIMEREOF'
[Unit]
Description=Honeypot Kit Weekly Module Update
Requires=honeypot-update.service

[Timer]
OnCalendar=Sun 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
TIMEREOF

    systemctl daemon-reload > /dev/null 2>&1
    systemctl enable honeypot-update.timer > /dev/null 2>&1
    systemctl start  honeypot-update.timer > /dev/null 2>&1

    # Record auto-update preference in config
    if ! grep -q "^\[updates\]" "$CONF_FILE" 2>/dev/null; then
        cat >> "$CONF_FILE" << 'CONFEOF'

[updates]
enabled = true
CONFEOF
    fi

    log_info "Auto-update enabled. Runs weekly Sunday at 03:00."
    log_info "Logs: /opt/honeypot/logs/updates.log"
    log_info "Manual run: honeypot-kit update now"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    cat > /etc/systemd/system/cowrie.service << SERVICEEOF
[Unit]
Description=Cowrie SSH Honeypot
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=forking
User=$COWRIE_USER
WorkingDirectory=$COWRIE_HOME
Environment=PATH=$COWRIE_HOME/venv/bin:/usr/bin:/bin
PIDFile=$COWRIE_HOME/var/run/cowrie.pid
ExecStartPre=/bin/mkdir -p $COWRIE_HOME/var/run
ExecStartPre=/bin/chown $COWRIE_USER:$COWRIE_USER $COWRIE_HOME/var/run
ExecStart=/usr/bin/authbind --deep $COWRIE_HOME/venv/bin/cowrie start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload > /dev/null 2>&1
    systemctl enable cowrie > /dev/null 2>&1
    log_info "Cowrie service created and enabled."
}

configure_i2c() {
    log_info "Enabling I2C interface..."

    # Enable I2C via config.txt - works on Trixie without raspi-config
    # Takes effect after reboot (which the script already prompts for)
    CONFIG="/boot/firmware/config.txt"
    if [ ! -f "$CONFIG" ]; then
        CONFIG="/boot/config.txt"  # fallback for older Pi OS layouts
    fi

    if grep -q "^dtparam=i2c_arm=on" "$CONFIG" 2>/dev/null; then
        log_info "I2C already enabled in $CONFIG."
    else
        echo "dtparam=i2c_arm=on" >> "$CONFIG"
        log_info "I2C enabled in $CONFIG (takes effect after reboot)."
    fi

    # Also load the module now for the current session
    modprobe i2c-dev > /dev/null 2>&1 || true
    modprobe i2c-bcm2835 > /dev/null 2>&1 || true

    # Install i2c-tools so user can run i2cdetect
    apt-get install -y i2c-tools > /dev/null 2>&1
    log_info "i2c-tools installed (run: i2cdetect -y 1)"
}

harden_system() {
    log_info "Applying basic hardening..."
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config 2>/dev/null || true
    systemctl reload ssh > /dev/null 2>&1 || true
    apt-get install -y unattended-upgrades > /dev/null 2>&1
    systemctl enable unattended-upgrades > /dev/null 2>&1
}

###############################################################################
# COMPLETION SUMMARY
###############################################################################

show_summary() {
    FINISH_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    FINISH_EPOCH=$(date +%s)

    UNATTENDED_SECS=$(( FINISH_EPOCH - UNATTENDED_START_EPOCH ))
    TOTAL_SECS=$(( FINISH_EPOCH - SCRIPT_START_EPOCH ))

    echo ""
    log_info "=== Installation Complete ==="
    echo ""
    echo "Timing"
    echo "  Script started        : $SCRIPT_START_TIME"
    echo "  Unattended phase      : $UNATTENDED_START_TIME"
    echo "  Install finished      : $FINISH_TIME"
    echo "  Unattended duration   : $(fmt_secs $UNATTENDED_SECS)"
    echo "  Total elapsed         : $(fmt_secs $TOTAL_SECS)"
    echo ""
    echo "Honeypot"
    echo "  SSH honeypot (Cowrie) : ${HONEYPOT_IP}:22"
    echo "  Real SSH              : ${HONEYPOT_IP}:${SSH_PORT}"
    echo "  Hostname              : $(hostname)"
    echo "  Install location      : $HONEYPOT_HOME"
    echo "  Logs                  : $COWRIE_HOME/var/log/cowrie/cowrie.log"
    echo "  I2C                   : enabled (takes effect after reboot)"
    echo ""
    echo "Hardware Modules (disabled by default)"
    echo "  honeypot-kit status                show current config"
    echo "  honeypot-kit oled enable           enable OLED display"
    echo "  honeypot-kit oled set-address 0x3C set I2C address"
    echo "  honeypot-kit oled test             test OLED hardware"
    echo "  honeypot-kit led enable            enable LED indicators"
    echo "  honeypot-kit led set-pins          assign GPIO pins"
    echo "  honeypot-kit led test              test LED hardware"
    echo "  honeypot-kit monitor start         start hardware daemon"
    echo "  honeypot-kit monitor status        check daemon status"
    echo "  honeypot-kit update status         show update log"
    echo "  honeypot-kit update now            run update check now"
    echo ""
    echo "Verify"
    echo "  sudo bash $HONEYPOT_HOME/scripts/smoke-test.sh"
    echo ""
    echo "Dashboard (when modules are installed) is SSH-tunnel only:"
    echo "  ssh -p $SSH_PORT -L 8000:localhost:8000 pi@${HONEYPOT_IP}"
    echo ""
}

###############################################################################
# REBOOT PROMPT
###############################################################################

prompt_reboot() {
    echo "------------------------------------------------------------"
    echo "  A reboot is required for all changes to take effect."
    echo "  This includes: Cowrie on port 22, SSH on port $SSH_PORT,"
    echo "  hostname change, and firewall rules."
    echo "------------------------------------------------------------"
    echo ""
    read -p "Reboot now? [y/N]: " DO_REBOOT
    if [[ "$DO_REBOOT" =~ ^[Yy]$ ]]; then
        log_info "Rebooting..."
        /sbin/shutdown -r now
    else
        echo ""
        log_warn "Reboot skipped."
        log_warn "IMPORTANT: Changes will NOT be fully active until you reboot."
        log_warn "Run 'sudo reboot' when you are ready."
        echo ""
    fi
}

###############################################################################
# MAIN
###############################################################################

main() {
    check_invocation
    gather_configuration

    create_directories
    update_system
    install_dependencies
    configure_hostname
    configure_network
    configure_ntp
    install_cowrie
    configure_authbind
    configure_ssh
    fix_permissions
    configure_firewall
    configure_logrotate
    install_health_check
    install_smoke_test
    install_config
    install_cli
    install_monitor
    install_auto_update
    create_systemd_service
    create_monitor_service
    configure_i2c
    harden_system

    log_info "Starting Cowrie..."
    systemctl start cowrie > /dev/null 2>&1
    sleep 5

    if pgrep -u cowrie > /dev/null 2>&1; then
        log_info "Cowrie is running."
    else
        log_warn "Cowrie did not start cleanly. Check: journalctl -u cowrie -n 50"
    fi

    show_summary
    prompt_reboot
}

main
