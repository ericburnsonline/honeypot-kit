# Using Honeypot Kit as a Learning and Portfolio Platform

## For Sales Engineers, Solutions Engineers, and Technical Sellers

Honeypot Kit is more than a security tool. It is a living technical project
with real data, real hardware, and a modular integration framework designed
to be extended. That makes it an unusually good vehicle for learning new
technology quickly and building portfolio evidence that you have shipped
something real with it.

This guide explains how to use Honeypot Kit to accelerate your technical
credibility when exploring new companies, preparing for interviews, or
expanding your skill set.

---

## The Core Idea

When you are evaluating or interviewing with a SaaS company, the strongest
signal you can send is not that you read their documentation - it is that
you built something real with their product.

Honeypot Kit gives you a project with:

- Live data (real SSH attack traffic once deployed)
- A working API integration framework
- A CLI and TUI that users actually interact with
- Hardware that makes demos visually compelling
- An open source GitHub repository that shows your work

The question to ask yourself before any technical conversation:

> "Can I connect [their product] to this honeypot in a way that makes
> sense and shows I understand what their product actually does?"

If yes, that integration is worth building - or at least worth starting.

---

## A Worked Example: Acme Observability

Imagine you are preparing for a Solutions Engineer role at a fictional
company called **Acme Observability**. Acme makes a metrics and alerting
platform that ingests time-series data and lets teams build dashboards and
set alert thresholds.

**Step 1: Ask an AI assistant for integration ideas**

Open a new chat and use a prompt like this one - adapt it to the actual
company you are researching:

```
I'm interviewing for a Solutions Engineer role at Acme Observability.
Their product ingests time-series metrics and provides dashboards and
alerting. I maintain an open source Raspberry Pi SSH honeypot project
at github.com/ericburnsonline/honeypot-kit. For each of their core
product areas, suggest a specific integration with my honeypot that
would demonstrate I understand how their product works, that I can
ship with it quickly, and that would be genuinely interesting to an
interviewer. Include: how organic vs. forced it feels, the specific
use case, effort level, and interview signal value 1-10.
```

**Step 2: Evaluate what the AI suggests**

For Acme Observability, a good AI response might suggest:

- Ship Cowrie attack counts and rates as custom metrics to Acme's ingest API
- Build a dashboard showing attack velocity, source country distribution,
  and session duration over time
- Set an alert threshold: notify when attack rate exceeds 10/minute

That is organic. It maps directly to what their product does. It uses real
data. And it gives you something specific to demo or describe.

**Step 3: Build Stage 1 first**

Before writing any code, write a Stage 1 document: what the integration
would do, what their API entry point is, what the architecture looks like,
and what it would cost. This takes an hour and immediately gives you
something to reference in a conversation:

> "I've been mapping out how your ingest API would work with a honeypot
> project I maintain - I put together an overview of the architecture
> and the data pipeline. Happy to walk through it."

You do not need to have built it yet. You need to have thought about it
seriously enough to have an opinion.

**Step 4: Build Stage 2 if time allows**

A working integration - even a minimal one - changes the conversation
completely. You go from "I've thought about this" to "I built this and
here is what I learned."

A minimal working integration for a metrics platform might be:

- A 50-line Python script that reads the Cowrie JSON log
- Parses attack counts per minute
- Posts them to Acme's metrics API every 60 seconds
- Installed via `honeypot-kit integration install acme`

That is a real integration. It runs on real hardware with real attack data.
It demonstrates you can read an API spec, write working code, and ship
something useful quickly.

**Step 5: Use it in the conversation**

You do not need to say "I built a Honeypot Kit integration for your product."
You can say:

> "I've been working on a security project that generates continuous
> time-series data - SSH attack rates, session patterns, geolocation.
> I connected it to a metrics platform to build dashboards and alerts.
> What I found interesting about that workflow was [specific observation
> about their product or the integration challenge]."

That is specific. It shows hands-on experience. And it opens a technical
conversation that you can navigate because you actually did the work.

---

## The Integration Roadmap

The following integrations are planned for Honeypot Kit. Each represents
a category of SaaS product that Solutions Engineers frequently encounter.
Building or studying any of these gives you transferable credibility in
that product category.

| Integration | Product Category | What You Learn |
|-------------|-----------------|----------------|
| Grafana | Observability / dashboards | Metrics pipelines, Prometheus, Loki, dashboard design |
| Sentry | Developer observability | Application instrumentation, error tracking, traces |
| Temporal | Workflow orchestration | Durable workflows, activity retries, event-driven design |
| Okta | Identity / IAM | OIDC, OAuth2, System Log API, identity-threat correlation |
| OpenAI | AI / LLM platforms | Structured outputs, prompt engineering, eval design |
| Kafka / Redpanda | Event streaming | Topics, producers, consumers, real-time pipelines |
| Alerting (PagerDuty / Slack) | Incident management | Webhook patterns, alert routing, on-call workflows |
| SIEM (Wazuh) | Security operations | Log ingestion, correlation rules, security events |
| Kubernetes / k3s | Container orchestration | Deployments, services, multi-node coordination |

You do not need to build all of these. Pick the one that matches the
company you are targeting.

---

## AI Prompts for Integration Research

Save these prompts and adapt them as needed.

**Prompt: Integration Ideas for a Specific Company**

```
I'm exploring a [role title] opportunity at [Company]. Their core product
is [brief description]. I maintain an open source Raspberry Pi SSH honeypot
at github.com/ericburnsonline/honeypot-kit with the following capabilities:

- Cowrie SSH honeypot capturing real attack traffic (login attempts,
  commands, session behavior) as structured JSON
- Modular integration framework: honeypot-kit integration install <name>
- Hardware monitoring: OLED display, LED status indicators
- CLI and TUI interface
- Existing integrations: OpenAI session analysis (Stage 2), Grafana (Stage 1)

For [Company]'s product, please evaluate:
1. How organic vs. forced would an integration feel?
2. What specific use case would impress an interviewer there?
3. Which of their APIs or products is the entry point?
4. What would Stage 1 (overview doc), Stage 2 (working code), and
   Stage 3 (DIY guide) look like?
5. Effort level: quick win to substantial?
6. Interview signal value (1-10)?

Then recommend whether to build it before or after an interview, and
what I could say about it even if it is only partially built.
```

**Prompt: Build a Stage 2 Integration**

```
I want to build a Stage 2 integration for Honeypot Kit connecting it
to [Company/Product]. Here is the project architecture:

[paste the relevant sections from this guide or the repo README]

The integration should follow this file structure:
- integrations/<name>/install.sh  - setup script
- integrations/<name>/requirements.txt
- integrations/<name>/[main module].py
- A smoke test fragment for scripts/smoke-tests/integrations/<name>.sh

The CLI entry point should be: honeypot-kit integration install <name>
After install it should add a honeypot-kit <name> subcommand group.

Please build the Stage 2 integration starting with the core data flow:
Cowrie JSON → [their ingest API] → [their product].
```

**Prompt: Write a Stage 1 Overview Doc**

```
Write a Stage 1 integration overview document for connecting Honeypot Kit
to [Product]. Follow the format of docs/integrations/openai.md in the repo
at github.com/ericburnsonline/honeypot-kit. Cover: what it does, the
architecture diagram, software required and cost, what data leaves the Pi,
planned CLI commands, and what Stage 2 and Stage 3 would look like.
```

---

## What Makes a Good Integration Story

A strong integration story for an interview has three parts:

**1. You understood their product**
You can explain what problem their product solves, who uses it, and what
the core API or data model looks like. Not from reading a Wikipedia page -
from reading their actual developer documentation.

**2. You made a decision**
You chose a specific use case and can explain why it is the right one for
your data. "I could have used their streaming API but the batch endpoint
made more sense for session data because..."

**3. You hit a real problem**
The best stories include a specific technical obstacle you encountered and
how you solved it. "The tricky part was that Cowrie JSON uses event-based
sessions but their API expects time-series points, so I had to..."

If you have all three, you have a credible technical story regardless of
whether the integration is complete.

---

## Getting Started

1. Deploy Honeypot Kit on a Raspberry Pi (15-20 minutes)
2. Put it on the internet to collect real attack data
3. Pick a company you are interested in
4. Run the integration ideas prompt above
5. Write the Stage 1 doc (1-2 hours)
6. Build a minimal Stage 2 if time allows (4-8 hours)
7. Commit everything to GitHub

The repo, the doc, and the code are your portfolio. The story you can
tell about building it is your interview preparation.

---

## Contributing an Integration

If you build an integration for a product you are familiar with, consider
contributing it back to the repo. See [CONTRIBUTING.md](../CONTRIBUTING.md)
for the integration file structure and submission process.

A contributed integration is itself a portfolio piece: it shows you can
write documentation, follow a contribution process, and build something
other people can use.

---

*Honeypot Kit is an educational project. No affiliation with any of the
companies or products mentioned in this guide.*
