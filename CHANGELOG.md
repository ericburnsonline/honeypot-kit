# Changelog

All notable changes to Honeypot Kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### In Progress
- Installation script (v2) - active development and testing on Raspberry Pi 4
- Hardware module implementations (OLED, LED, Button)
- Dashboard integration framework
- Testing and validation procedures

### Planned (Phase 2-5)
- Grafana dashboard for attack visualization
- Kafka event streaming integration
- Claude AI analysis of attack patterns
- Kubernetes orchestration support
- Multi-honeypot coordination

---

## [0.1.0] - 2026-07-13

### Added - July 13, 2026
- Code of Conduct establishing community standards and inclusive environment
- Clear expectations for module contributions (substance over marketing)
- Reporting and enforcement procedures for code of conduct violations

### Added - July 3, 2026
- Contributing Guidelines with clear pathways for community contribution
- Six concrete ways to contribute (testing, hardware design, docs, dashboards, modules, SE perspective)
- Development workflow and code style expectations
- Licensing requirements and recognition process

### Added - June 16, 2026
- Public GitHub repository established
- GNU Affero General Public License v3 (AGPL v3) with dual licensing support
- Comprehensive README with project vision, features, hardware requirements
- Threat Model documenting project scope and design boundaries
- Attribution and compliance notices for Cowrie (GPL v2) and dependencies
- .gitignore configured for Python projects

### Project Foundation Status

**Architecture & Design (Documented)**
- Modular architecture supporting 18+ planned modules across 5 phases
- Hardware module trio designed: OLED display, LED indicators, Button control
- GPIO compatibility matrix to prevent hardware conflicts
- Health check framework (5-minute intervals)
- Log rotation strategy (7-day retention)
- OPSEC hardening framework
- Firewall and network isolation design

**Installation Script (In Testing)**
- Version 1 created and deployed to Raspberry Pi 4
- v2 improvements in progress based on testing feedback
- Known issues being resolved

**Ready for Community**
- Licensing and legal foundation solid
- Community guidelines and governance established
- Contributing pathways clear
- Project vision transparent
- Honest about current maturity (vibe coded, untested)

**Not Yet Available**
- Tested, production-ready installation
- Actual module implementations
- Dashboard or visualization tools
- Kubernetes support

---

## Notes

**Version 0.1.0 represents the foundation phase:**
- Project governance and community structure established (June 16 - July 13)
- Architecture and vision documented
- Building blocks established
- Ready for contributors and community feedback
- Installation script in active testing and iteration

**Next milestone (0.2.0):** Working installation script with successful Cowrie deployment on Raspberry Pi 4.

---

## Links

- [GitHub Repository](https://github.com/ericburnsonline/honeypot-kit)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [License](LICENSE)
