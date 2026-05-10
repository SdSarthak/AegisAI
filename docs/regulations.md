# Comparative Analysis of AI Regulatory Frameworks

> **Purpose:** This document compares three major regulatory frameworks against the EU AI Act baseline. It is intended to guide multi-regulation support in AegisAI's classification engine.

---

## 1.Overview

AegisAI's classification engine currently targets compliance with the EU AI Act. As the global
regulatory landscape evolves, three additional frameworks are relevant for multi-jurisdictional
deployment:

| Framework | Jurisdiction | Status (as of May 2026) | Approach |
|---|---|---|---|
| EU AI Act | European Union | In force; phased rollout 2025–2027 | Risk-based, prescriptive |
| UK AI (Regulation) Bill | United Kingdom | Private Member's Bill; not yet law | Principles-based (draft) |
| India DPDP Act 2023 | India | Notified Nov 2025; substantive provisions from May 2027 | Consent/data-centric |

---

## 2. EU AI Act (Baseline)

### Status

The EU AI Act (Regulation EU 2024/1689) entered into force in August 2024 and is rolling out
in phases:

- **February 2, 2025** — Prohibted practices enforceable (social scoring, untargeted facial-recognition scraping, emotion inference in hiring/education).
- **August 2, 2025** — GPAI (General-Purpose AI) obligations apply; AI Office becomes operational.
- **August 2, 2026** — High-risk AI obligations (Annex III), transparency rules (Article 50), and enforcement begin.
- **August 2, 2027** — Rules for high-risk AI embedded in regulated products (Annex I) take effect.

> **Note:** The European Commission's Digital Omnibus proposal (late 2025) may delay some
> high-risk obligations to December 2027 if adopted. Monitor status closely.

### Risk Classification - Four Tiers

| Tier | Definition | Examples |
|---|---|---|
| **Unacceptable Risk** | Prohibited outright | Social scoring, subliminal manipulation, real-time biometric ID in public spaces |
| **High Risk** | Regulated with conformity assessments | Hiring tools, credit scoring, biometrics, critical infrastructure, education, law enforcement |
| **Limited Risk** | Transparency obligations only | Chatbots, deepfakes — users must be informed they are interacting with AI |
| **Minimal Risk** | Unregulated | Spam filters, AI video games |

### Key Obligations 
## High-Risk AI

- **Risk management system** — ongoing identification and mitigation of risks throughout the lifecycle.
- **Data governance** — training, validation, and test datasets must meet quality criteria.
- **Technical documentation** — detailed docs for regulators before market placement.
- **Transparency & instructions for use** — deployers must understand how the system works.
- **Human oversight** — technical measures enabling meaningful human intervention.
- **Accuracy, robustness, cybersecurity** — continuous performance standards.
- **Conformity assessment** — mandatory self-assessment or third-party audit before deployment.
- **Post-market monitoring