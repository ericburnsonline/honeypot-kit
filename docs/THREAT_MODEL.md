# Threat Model & Design Goals

## What This Honeypot IS FOR

**Target attacker:** Automated botnets, script kiddies, port scanners

**Attack types caught well:**
- Brute force SSH login attempts
- Common credentials (admin/admin, root/root)  
- Exploit code (automated CVE scanners)
- Command injection attempts
- Credential harvesting
- Botnet activity patterns

**Design goal:** Capture and analyze attacker behavior, techniques, and motivations

## What This Honeypot IS NOT FOR

**Out of scope:**
- ✗ Defending against nation-state APTs
- ✗ Detecting sophisticated privilege escalation
- ✗ Forensic evidence for prosecution
- ✗ Real-time attack blocking/mitigation
- ✗ Protecting sensitive data

**Won't catch:**
- Attackers who know it's a honeypot
- Sophisticated evasion techniques
- Zero-day exploits (unless targeting SSH)
- Lateral movement (isolated system)
- Firmware-level attacks

## Assumptions

1. **Network:** Standard home/lab network (not military/government)
2. **Attacker:** Automated or semi-automated (not Advanced Persistent Threat)
3. **Skill level:** Medium or below
4. **Motivation:** Data/botnet recruitment, not targeted breach
5. **Timeline:** Minutes to hours, not persistent multi-month campaign

## Design Principles

- **Invisibility:** Blend in, don't advertise as honeypot
- **Simplicity:** Single Pi, minimal dependencies, easy to deploy
- **Learning:** Educational first, understand attacks
- **Monitoring:** Capture and analyze behavior
- **Resilience:** Keep running even under sustained attack

## Suitable Scenarios

✓ Learning how attackers work  
✓ Network monitoring and alerting  
✓ Threat intelligence collection  
✓ Security team training  
✓ Home network protection  
✓ Lab environment analysis

## Not Suitable For

✗ Stopping real attacks (not a firewall)  
✗ Protecting sensitive systems  
✗ Legal/prosecutorial evidence  
✗ Mission-critical monitoring  
✗ Enterprise security (too simple)

## Attack Coverage

### Excellent Coverage
- SSH brute force attempts
- Credential guessing
- Automated scanning/exploitation
- Botnet activity
- Command execution
- Simple privilege escalation attempts

### Limited Coverage
- Sophisticated social engineering
- DNS tunneling exfiltration
- Encrypted command channels
- Multi-stage exploits
- Firmware attacks

### No Coverage
- Network-level attacks (DDoS, routing attacks)
- Physical attacks
- Supply chain compromises
- Social engineering
- Insider threats

## Detection & Evasion Resistance

### Strong Against
- Automated scanning
- Dictionary attacks
- Known CVE exploits
- Simple evasion checks

### Weak Against
- Manual inspection by security professionals
- Timing analysis
- Behavioral analysis
- Sophisticated fingerprinting

## Limitations

1. **Single system:** No distributed deployment
2. **No lateral movement:** Isolated from other systems  
3. **Limited OS fidelity:** Simple Cowrie SSH only
4. **No persistence:** Attacks can't establish persistence
5. **No network access:** Can't exfiltrate data to attacker C2

## Recommended Use Cases

**Good:**
- Personal network monitoring
- Security awareness training
- Threat intelligence gathering
- Attack pattern analysis
- Learning honeypot concepts

**Bad:**
- Production security
- Compliance/audit purposes
- Stopping real attacks
- Prosecuting attackers

## Success Metrics

How do you know if it's working?

✓ Logs showing SSH attempts  
✓ Multiple failed login attempts  
✓ Attacker commands visible  
✓ Interesting patterns emerging  
✓ Learning insights from attacks

## Failure Modes

What doesn't work:

✗ High-skill attackers detect it immediately  
✗ Sophisticated malware ignores it  
✗ Zero-day exploits not caught  
✗ Can't stop attacks (not a firewall)  
✗ Won't catch APT activity
