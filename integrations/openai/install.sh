#!/bin/bash
###############################################################################
# Honeypot Kit - OpenAI Integration Setup Script
# Version: 4
# Run automatically by: honeypot-kit integration install openai
###############################################################################

INSTALL_VERSION="4"

INTG_DIR="/opt/honeypot/integrations/openai"
CONF_FILE="$INTG_DIR/config.json"

echo "Setting up OpenAI integration..."

# Install Python package
# Install openai Python package
# On Debian Trixie, --break-system-packages is required
# --ignore-installed prevents conflicts with apt-managed packages like typing_extensions
echo "  Installing openai Python package..."
if pip3 install --quiet --break-system-packages --ignore-installed openai 2>&1; then
    echo "  openai package installed."
else
    echo "  WARNING: pip install failed."
    echo "  If AI analysis fails, run: sudo pip3 install --break-system-packages --ignore-installed openai"
fi

# Create config template if not already present
# Never overwrite an existing config (would wipe the API key)
if [ ! -f "$CONF_FILE" ]; then
    cat > "$CONF_FILE" << 'CONFEOF'
{
  "api_key": "",
  "model": "gpt-4o-mini",
  "enabled": false,
  "auto_analyze": false,
  "redact_ips": false,
  "redact_passwords": true,
  "max_session_events": 100,
  "notes": "Set api_key and set enabled=true to activate. Never commit this file."
}
CONFEOF
    # Set ownership so the installing user can read the config without sudo
    REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo pi)}"
    chmod 640 "$CONF_FILE"
    chown "root:${REAL_USER}" "$CONF_FILE" 2>/dev/null || chmod 644 "$CONF_FILE"
    echo "Config template created at $CONF_FILE"
    echo "IMPORTANT: Edit $CONF_FILE and add your OpenAI API key."
else
    echo "Config already exists at $CONF_FILE - not overwritten."
fi

# Create directories for analysis output and eval sessions
# analysis/ must be writable by pi user (runs without sudo)
mkdir -p "$INTG_DIR/sessions"
mkdir -p "$INTG_DIR/evals"
mkdir -p "$INTG_DIR/analysis"
chmod 777 "$INTG_DIR/analysis"

# Write eval session templates
cat > "$INTG_DIR/evals/README.md" << 'EVALEOF'
# OpenAI Integration - Eval Sessions

Synthetic Cowrie sessions for testing the AI analyzer.
These are representative examples, not real attack data.

Sessions:
- reconnaissance.json    - passive enumeration, no downloads
- downloader.json        - wget + chmod + execution attempt
- failed-login-only.json - credential stuffing, no shell
- prompt-injection.json  - commands containing injection strings

Run evals: honeypot-kit ai eval
EVALEOF

echo "OpenAI integration setup complete (install.sh v${INSTALL_VERSION})."
echo ""
echo "Next steps:"
echo "  1. Edit $CONF_FILE and add your OpenAI API key"
echo "  2. Set enabled=true in the config"
echo "  3. Test: honeypot-kit ai test"
echo "  4. Analyze: honeypot-kit ai analyze --latest"
