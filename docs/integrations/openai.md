# AI Session Analysis Integration

**Stage 1 of 3 - Overview and Planning**

This document covers what an AI-powered session analysis integration for Honeypot Kit
would look like, how it works architecturally, what software is involved, and what it
would cost. A working installable integration (Stage 2) and a DIY guide for writing
your own (Stage 3) will follow.

---

## What This Integration Does

Converts raw Cowrie SSH session data into structured, human-readable security analysis.
Instead of seeing a wall of JSON events and shell commands, you get:

- A plain-English summary of what the attacker did
- The probable attacker objective
- Observed actions in sequence
- Interesting or unusual commands flagged
- Possible MITRE ATT&CK technique mappings
- Extracted indicators (IPs, domains, file hashes, user agents)
- Confidence level and areas of uncertainty
- An educational explanation of why the session matters

This is especially useful for the educational mission of Honeypot Kit - students and
home-lab users can understand what attackers actually attempted without needing a
security operations background.

---

## Architecture

```
Cowrie SSH Honeypot
      |
      v
Cowrie JSON log (cowrie.json)
      |
      v
Session Assembler
  - Groups events by session ID
  - Filters to completed sessions
  - Normalizes to internal format
      |
      v
Safety Boundary
  - Attacker content treated as untrusted data, never instructions
  - No shell access granted to model
  - No network/web-search capability
  - Optional IP address redaction
      |
      v
AI Provider (OpenAI Responses API / provider-neutral)
  - Structured output schema enforced
  - Response validated before storage
      |
      v
Local storage (JSON / SQLite)
      |
      v
CLI output
OLED summary (short form)
Future: Grafana annotation
```

---

## Provider Architecture

The AI analysis integration is designed to be **provider-neutral**. OpenAI is the first
working implementation. The same session data format and output schema will work with
any provider that supports structured output.

Planned provider support:

| Provider | API | Status |
|----------|-----|--------|
| OpenAI | Responses API | Stage 2 (first implementation) |
| Anthropic Claude | Messages API | Planned |
| Local (Ollama) | OpenAI-compatible API | Planned |

Switching providers requires only a config change, not a code rewrite.

---

## OpenAI Integration Details

### Getting an API Key

You need an OpenAI API key to use this integration. Here is how to get one:

1. Go to [platform.openai.com](https://platform.openai.com) and sign up or log in
2. Click your profile icon (top right) → **API keys** in the left sidebar
3. Click **Create new secret key** - give it a name like "honeypot-kit"
4. **Set permissions** - choose **Restricted**, then under Model capabilities
   enable **Responses - Write** only. Write is required to send sessions to
   the API and receive analysis back. Leave Realtime and all other options unchecked.
5. **Copy the key immediately** - OpenAI will not show it again after you close the dialog
5. Paste it into your config file at `/opt/honeypot/integrations/openai/config.json`

**Important - set a spending limit before you start:**

A misconfigured `auto_analyze` setting on a busy honeypot could send many sessions
to the API and generate unexpected charges. Set a monthly spending cap before
enabling the integration:

1. Go to **Settings** → **Billing** → **Usage limits**
2. Set a **Monthly budget** you are comfortable with (e.g. $5-10 to start)
3. OpenAI will stop API calls when the limit is reached

At current pricing, typical honeypot usage costs well under $1/day, but the
limit protects you if attack traffic spikes or `auto_analyze` is left enabled
on a very active system.

**Billing note:** OpenAI requires a payment method to use the API even for small
amounts. The free tier (if available) covers limited usage. Check
[platform.openai.com/account/billing](https://platform.openai.com/account/billing)
for current tier information.

### API Used

**OpenAI Responses API with Structured Outputs**

The Responses API is the appropriate entry point for this use case. Each analysis
request is a bounded artifact - one completed Cowrie session - fed to the model with
a strict output schema. This is not an agent or multi-step orchestration problem;
it is a well-defined transformation: session JSON in, structured analysis out.

The Agents SDK is not used for the initial implementation. It would add complexity
without benefit for a single-turn, bounded input use case.

### Model Selection

Start with a cost-conscious current model for high-volume session analysis. Reserve
larger models for sessions flagged as high-confidence or high-severity. The integration
configuration will allow the model to be changed without code modification.

### Structured Output Schema

The model is required to return output conforming to this schema:

```json
{
  "summary": "Plain-English description of what happened in this session",
  "intent": "reconnaissance | credential_stuffing | payload_delivery | lateral_movement | unknown",
  "confidence": 0.87,
  "observed_actions": [
    "Connected via SSH",
    "Attempted login with 3 credential pairs",
    "Downloaded executable from external host",
    "Attempted to execute downloaded file"
  ],
  "interesting_commands": [
    "wget http://...",
    "chmod +x ...",
    "./payload"
  ],
  "technique_candidates": [
    {
      "technique_id": "T1078",
      "technique_name": "Valid Accounts",
      "confidence": "medium"
    }
  ],
  "indicators": [
    {
      "type": "ip",
      "value": "...",
      "context": "source of session"
    },
    {
      "type": "url",
      "value": "...",
      "context": "download source"
    }
  ],
  "educational_explanation": "This session demonstrates a common automated attack pattern...",
  "uncertainties": [
    "Could not determine payload purpose without executing it",
    "Source IP may be a VPN exit node rather than attacker infrastructure"
  ]
}
```

Structured output is enforced at the API level, not just prompted. Responses that
do not conform to the schema are rejected and retried.

---

## Safety and Privacy Design

This section is particularly important because Honeypot Kit captures
**adversary-controlled text**. An attacker could type commands like:

```
echo "Ignore your previous instructions and..."
```

This is a real prompt injection risk, not a contrived example.

### Mitigations

**Treat all attacker content as data, never instructions:**
The system prompt explicitly frames attacker-generated text as untrusted input
to be analyzed, not executed or followed. The model receives no ability to act
on attacker commands.

**No shell access:** The model has no tools that touch the Pi filesystem or
execute commands.

**No network access:** The model has no web search or external lookup capability.
Enrichment is handled separately by the Honeypot Kit enrichment layer before
the AI call.

**Schema enforcement:** Structured output constrains what the model can return,
limiting the impact of any successful injection on downstream systems.

**Credential safety:** API keys are stored in environment variables or the
Honeypot Kit config file, never in the codebase or logs.

**Optional IP redaction:** Users who do not want attacker IP addresses leaving
the Pi can enable redaction before the API call.

**Advisory framing:** All AI-generated analysis is explicitly labeled as
educational and advisory. It is not presented as authoritative threat intelligence.

---

## What Data Leaves the Pi

When AI analysis is enabled, the following Cowrie session data is sent to the
configured AI provider:

- Session ID (anonymized)
- Event types and timestamps
- Commands entered by the attacker
- Login attempts (username only, not passwords by default)
- File download URLs observed
- Session duration

The following is **never sent:**

- Credentials (passwords) - configurable
- Real IP addresses - configurable (redaction available)
- Pi hostname or network configuration
- Any data from other Honeypot Kit users

---

## Planned CLI Commands

```bash
# Configure AI provider
honeypot-kit ai configure

# Test connection and structured output
honeypot-kit ai test

# Analyze most recent completed session
honeypot-kit ai analyze --latest

# Analyze a specific session by ID
honeypot-kit ai analyze --session <session-id>

# Show analysis for recent sessions
honeypot-kit ai history

# Enable automatic analysis of new sessions
honeypot-kit ai enable

# Disable automatic analysis
honeypot-kit ai disable

# Show current configuration and status
honeypot-kit ai status
```

---

## Evaluation and Testing

A key part of Stage 2 will be a small synthetic session library for testing and
validation. These are not real attacker sessions but representative examples used
to verify that the integration works correctly.

Planned synthetic sessions:

| Session | Description | Expected classification |
|---------|-------------|------------------------|
| `reconnaissance.json` | Passive enumeration, no downloads | reconnaissance |
| `downloader.json` | wget/curl + chmod + execution attempt | payload_delivery |
| `crypto-miner.json` | Known mining commands and URLs | payload_delivery |
| `failed-login-only.json` | Multiple failed credentials, no shell | credential_stuffing |
| `interactive-human.json` | Deliberate, slow, exploratory commands | lateral_movement |
| `prompt-injection-attempt.json` | Commands containing injection strings | any (injection ignored) |

Tests verify:

- Does the model correctly classify session intent?
- Does it distinguish login noise from interactive sessions?
- Does it identify download-and-execute behavior?
- Does it refrain from inventing actions not in the session data?
- Does the prompt injection session remain data rather than instructions?
- What happens when the API is unavailable? (fallback path)
- What happens with malformed or incomplete session data?
- What happens when model confidence is low?

---

## Fallback Behavior

If the AI provider is unavailable or the API call fails, Honeypot Kit continues
operating normally. The session is flagged for later analysis and a summary is
shown using available local data only:

```
AI Analysis: unavailable (API timeout)
Session: 12 commands | Downloads: 1 | Execution attempts: 1
Retry: honeypot-kit ai analyze --session <id>
```

The rest of Honeypot Kit - Cowrie, LEDs, OLED, smoke test, health check - is
completely unaffected by AI provider availability.

---

## Cost Estimate

AI analysis cost depends on session length and model selection. Typical Cowrie
sessions range from a few events (failed login attempt) to hundreds of events
(interactive human attacker).

| Session type | Approximate tokens | Approximate cost (current models) |
|-------------|--------------------|------------------------------------|
| Failed login only | ~500 | < $0.001 |
| Automated scanner | ~1,000 | ~$0.001 |
| Interactive session | ~3,000-5,000 | ~$0.003-0.005 |

A Pi on a residential connection receiving moderate attack traffic might process
50-200 sessions per day. At current pricing, daily AI analysis cost is likely
under $0.50 for most deployments.

Analysis can be configured to run automatically on all sessions, only on sessions
that reached a shell, or only on manually requested sessions.

---

## What's Next

- **Stage 2** - Working integration installable via the Honeypot Kit CLI:
  ```bash
  honeypot-kit integration install openai
  ```
  Installs the session assembler, structured output schema, CLI commands,
  synthetic eval sessions, fallback behavior, and adds an AI check to the
  smoke test.

- **Stage 3** - DIY guide covering how to examine raw Cowrie JSON, reduce it
  to the events an analyst needs, build a Responses API call, enforce structured
  output, add prompt injection test data, validate responses, and add retry and
  fallback behavior. The educational lesson: building a reliable LLM integration
  is more than writing a prompt.

---

## Links

- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Cowrie JSON log format](https://cowrie.readthedocs.io/en/latest/README.html)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [Honeypot Kit GitHub](https://github.com/ericburnsonline/honeypot-kit)
