#!/bin/bash
###############################################################################
# Honeypot Kit - OpenAI Integration Setup Script
# Run automatically by: honeypot-kit integration install openai
###############################################################################

INTG_DIR="/opt/honeypot/integrations/openai"
CONF_FILE="$INTG_DIR/config.json"

echo "Setting up OpenAI integration..."

# Install Python package
pip3 install --quiet --break-system-packages openai 2>/dev/null || \
    pip3 install --quiet openai 2>/dev/null || \
    echo "WARNING: Could not install openai package. Run manually: pip3 install openai"

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
    chmod 600 "$CONF_FILE"
    echo "Config template created at $CONF_FILE"
    echo "IMPORTANT: Edit $CONF_FILE and add your OpenAI API key."
else
    echo "Config already exists at $CONF_FILE - not overwritten."
fi

# Create sessions directory for analysis output and eval sessions
mkdir -p "$INTG_DIR/sessions"
mkdir -p "$INTG_DIR/evals"
mkdir -p "$INTG_DIR/analysis"

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

echo "OpenAI integration setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit $CONF_FILE and add your OpenAI API key"
echo "  2. Set enabled=true in the config"
echo "  3. Test: honeypot-kit ai test"
echo "  4. Analyze: honeypot-kit ai analyze --latest"
