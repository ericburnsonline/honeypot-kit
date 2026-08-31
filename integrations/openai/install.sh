#!/bin/bash
###############################################################################
# Honeypot Kit - OpenAI Integration Setup Script
# Version: 5
# Run automatically by: honeypot-kit integration install openai
###############################################################################

INSTALL_VERSION="5"

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

# Install smoke test fragment
SMOKE_INTG_DIR="/opt/honeypot/scripts/smoke-tests/integrations"
mkdir -p "$SMOKE_INTG_DIR"
cat > "$SMOKE_INTG_DIR/openai.sh" << 'SMOKEEOF'
#!/bin/bash
# OpenAI integration smoke test fragment
# Sourced by smoke-test.sh if /opt/honeypot/integrations/openai/.installed exists

AI_CONF="/opt/honeypot/integrations/openai/config.json"
AI_ANALYZER="/opt/honeypot/integrations/openai/analyzer.py"

if [ -f "$AI_CONF" ]; then
    echo "  [PASS] OpenAI config present"; ((PASS++))
else
    echo "  [FAIL] OpenAI config missing at $AI_CONF"; ((FAIL++))
fi

if [ -f "$AI_ANALYZER" ]; then
    echo "  [PASS] OpenAI analyzer present"; ((PASS++))
else
    echo "  [FAIL] OpenAI analyzer missing at $AI_ANALYZER"; ((FAIL++))
fi

if [ -f "$AI_CONF" ]; then
    ENABLED=$(python3 -c "import json; c=json.load(open('$AI_CONF')); print(c.get('enabled',False))" 2>/dev/null)
    KEY=$(python3 -c "import json; c=json.load(open('$AI_CONF')); print(bool(c.get('api_key','').strip()))" 2>/dev/null)

    if [ "$ENABLED" = "True" ] && [ "$KEY" = "True" ]; then
        echo "  [PASS] OpenAI integration enabled with API key"; ((PASS++))
    elif [ "$KEY" != "True" ]; then
        echo "  [WARN] OpenAI API key not set - run: honeypot-kit ai configure"; ((WARN++))
    else
        echo "  [WARN] OpenAI integration installed but disabled"; ((WARN++))
    fi
fi

# Check openai package importable
if python3 -c "import openai" 2>/dev/null; then
    echo "  [PASS] openai Python package installed"; ((PASS++))
else
    echo "  [FAIL] openai Python package not found - run: sudo pip3 install --break-system-packages --ignore-installed openai"; ((FAIL++))
fi
SMOKEEOF
chmod +x "$SMOKE_INTG_DIR/openai.sh"
echo "  Smoke test fragment installed."
echo ""
echo "Next steps:"
echo "  1. Edit $CONF_FILE and add your OpenAI API key"
echo "  2. Set enabled=true in the config"
echo "  3. Test: honeypot-kit ai test"
echo "  4. Analyze: honeypot-kit ai analyze --latest"
