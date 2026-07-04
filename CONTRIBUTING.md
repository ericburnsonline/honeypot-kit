# Contributing to Honeypot Kit

Thank you for your interest in contributing to Honeypot Kit! We welcome all contributions: code, documentation, hardware designs, testing, and ideas.

## Project Status

**Current State:** Foundation phase. Core honeypot framework and architecture are designed and documented. The installation script is in active development and testing on Raspberry Pi hardware.

**What's Ready:**
- Core architecture and design docs
- Module roadmap and specifications
- OLED, LED, Button hardware module designs
- OPSEC framework and threat model

**What's In Progress:**
- Installation script (v2 in testing)
- Actual module implementations
- Dashboard integration

## Ways to Contribute Right Now

### 1. Test the Installation Script

We're actively testing `install-honeypot.sh` on Raspberry Pi 4 hardware. If you have a Pi:

- Run the script on a fresh OS install
- Document what works, what breaks
- Report issues with hardware, Python versions, OS variants
- Suggest fixes

See `docs/TESTING_GUIDE.md` for detailed testing procedures.

### 2. Hardware Module Design

Each module (OLED display, LED indicators, Button control, etc.) needs:

- **GPIO mapping validation**: Test actual pin conflicts
- **Fritzing diagrams**: Visual wiring guides for makers
- **Assembly documentation**: Step-by-step hardware setup
- **Alternative implementations**: Different display types, LED configurations

Pick a module from `docs/NEXT_FEATURES.md` and design your version.

### 3. Documentation

- Expand OPSEC guide with specific examples
- Add troubleshooting sections for common issues
- Create beginner's guide to Raspberry Pi + SSH
- Expand threat model with real-world scenarios
- Add performance benchmarks

### 4. Dashboard & Visualization

The Phase 2 roadmap includes Grafana integration. Contributions welcome:

- Dashboard mockups (Grafana templates)
- Query designs for attack visualization
- Alert rules and thresholds
- Real-time display concepts

### 5. Module Development

Look at `docs/NEXT_FEATURES.md` for planned modules across 18 different areas:

- Visualization (Grafana, Kibana, Splunk connectors)
- Analysis (Kafka, Temporal, Claude AI)
- Advanced (Kubernetes, multi-honeypot, machine learning)

Pick one and start building. We'll help integrate it.

### 6. SE/Network Perspective

Your angle as a Solutions Engineer is valuable:

- How would you pitch this to security teams?
- What features would make this actually useful in a SOC?
- What metrics matter for incident response?
- How does this fit into threat intelligence workflows?

Document your ideas in GitHub Issues.

## Development Setup

### Clone the Repository

```bash
git clone https://github.com/ericburnsonline/honeypot-kit.git
cd honeypot-kit
```

### Suggested Workflow

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-module-name
   ```

2. **Make your changes** in a feature directory:
   ```bash
   mkdir modules/your-module/
   ```

3. **Document as you go:**
   - Add a README.md in your module directory
   - Include GPIO/hardware requirements
   - Add example code and usage

4. **Test on actual hardware** if possible

5. **Submit a pull request** with:
   - Clear description of what you added
   - Testing notes (what hardware, what OS version)
   - Any dependencies or assumptions

## Licensing Requirements

**Important:** All contributions must be compatible with AGPL v3.

- Your code will be licensed under AGPL v3
- You retain copyright, but agree to the license terms
- If you use other open source code, ensure it's AGPL-compatible

See `LICENSE` file for full terms.

## Code Style & Standards

### Python

- Follow PEP 8 style guide
- Add docstrings to functions
- Include type hints where practical
- Test on Python 3.9+ (Raspberry Pi standard)

### Documentation

- Use Markdown for all docs
- Include examples and code snippets
- Link to related docs
- Keep it beginner-friendly (new to RPi/honeypots)

### Hardware

- Include Fritzing diagrams (.fzz files)
- Document pin numbers clearly
- List parts with supplier links (no affiliate links in repo)
- Include assembly time estimates

## Reporting Issues

Found a bug? Have a suggestion?

**Create a GitHub Issue with:**
1. Clear title (e.g., "Script fails on Raspberry Pi OS Lite")
2. Steps to reproduce
3. What you expected
4. What actually happened
5. Hardware/software details (Pi model, OS version, Python version)

## Questions?

- Check existing issues and discussions
- Review the docs in `docs/` directory
- Create an issue to ask (we respond quickly)

## Recognition

Contributors are recognized in:
- `CHANGELOG.md` (for each release)
- Project README (for significant contributions)
- Commit history (always preserved)

## What We're Looking For

**High Priority:**
- Installation script testing and fixes
- Hardware module Fritzing diagrams
- Raspberry Pi OS compatibility testing
- Documentation improvements

**Nice to Have:**
- Module implementations
- Dashboard designs
- Example deployments
- Educational content

**Always Welcome:**
- Bug reports (even if you can't fix them)
- Ideas and suggestions
- Use case examples
- Questions (they often improve docs)

## Code of Conduct

Be respectful. Honeypot Kit is an educational project for learning. We welcome all skill levels, backgrounds, and perspectives.

---

**Thanks for contributing to Honeypot Kit!** 

Let's build something useful for the SE and security learning community.
