# AI Regulatory Frameworks: Comparative Analysis

This document compares three major regulatory frameworks against the EU AI Act. It is intended to guide multi regulation support in AegisAI's classification engine.

---

## 1. Overview

AegisAI's classification engine currently targets compliance with the EU AI Act. As the global
regulatory landscape evolves, three additional frameworks are relevant for multi-jurisdictional
deployment:

| Framework | Jurisdiction | Status (as of May 2026) | Approach |
|---|---|---|---|
| EU AI Act | European Union | In force; phased rollout 2025–2027 | Risk-based, prescriptive |
| UK AI (Regulation) Bill | United Kingdom | Private Member's Bill; not yet law | Principles-based (draft) |
| India DPDP Act 2023 | India | Notified Nov 2025; substantive provisions from May 2027 | Consent/data-centric |

---

## 2. EU AI Act 

### Status

The EU AI Act (Regulation EU 2024/1689) entered into force in August 2024 and is rolling out
in phases:

- **February 2, 2025** — Prohibited practices enforceable (social scoring, untargeted facial-recognition scraping, emotion inference in hiring/education).
- **August 2, 2025** — GPAI (General-Purpose AI) obligations apply; AI Office becomes operational.
- **August 2, 2026** — High risk AI obligations (Annex III), transparency rules (Article 50), and enforcement begin.
- **August 2, 2027** — Rules for high-risk AI embedded in regulated products (Annex I) take effect.

> **Note:** The European Commission's Digital Omnibus proposal (late 2025) may delay some
> high risk obligations to December 2027 if adopted. Monitor status closely.

### Risk Classification (Four Tiers)

| Tier | Definition | Examples |
|---|---|---|
| **Unacceptable Risk** | Prohibited outright | Social scoring, subliminal manipulation, real-time biometric ID in public spaces |
| **High Risk** | Regulated with conformity assessments | Hiring tools, credit scoring, biometrics, critical infrastructure, education, law enforcement |
| **Limited Risk** | Transparency obligations only | Chatbots, deepfakes — users must be informed they are interacting with AI |
| **Minimal Risk** | Unregulated | Spam filters, AI video games |

### Key Obligations 
## High Risk AI

- **Risk management system** — ongoing identification and mitigation of risks throughout the lifecycle.
- **Data governance** — training, validation, and test datasets must meet quality criteria.
- **Technical documentation** — detailed docs for regulators before market placement.
- **Transparency & instructions for use** — deployers must understand how the system works.
- **Human oversight** — technical measures enabling meaningful human intervention.
- **Accuracy, robustness, cybersecurity** — continuous performance standards.
- **Conformity assessment** — mandatory self-assessment or third-party audit before deployment.
- **Post-market monitoring** — ongoing performance data collection.
- **Incident reporting** — serious incidents must be reported to national authorities.

### GPAI  Specific Obligations 
From august 2025

- Technical documentation and training data summaries
- Copyright compliance disclosures.
- Adversarial testing and incident reporting for systemic-risk models (trained above 10²⁵ FLOPs).
- Open source GPAI models largely exempt unless they pose systemic risk.

### Enforcement

- EU AI Office + national competent authorities.
- Fines up to **€35M or 7% of global annual turnover** for prohibited practices.

---

## 3. UK AI Bill Draft

### Status

The UK has **no dedicated AI Act in force** as of May 2026:

- **Current approach:** Non statutory, principles based. Sector regulators (ICO, FCA, Ofcom, CMA) apply existing law to AI within their domains. No new AI regulator exists.
- **Artificial Intelligence (Regulation) Bill [HL]** — Reintroduced March 4, 2025 by Lord Holmes of Richmond as a Private Member's Bill. Lacks government backing; passage into law is uncertain.
- **Government stance:** Pro innovation. A more comprehensive government backed Bill has been signalled for 2026 but no firm timeline exists.
- **Data (Use and Access) Act 2025** — Passed mid 2025. Introduces statutory provisions on AI training datasets, algorithmic accountability, and automated decision-making; the UK's first statutory step toward AI-relevant obligations.
- **ICO:** Developing a statutory code of practice on AI and automated decision-making (targeting 2026), moving from voluntary guidance to mandatory compliance.

### Five Core AI Principles (NonStatutory , UK White Paper 2023)

Currently applied by sector regulators; proposed to be codified as legal duties by the Bill:

1. **Safety and security** — AI systems must be robust and secure.
2. **Transparency** — Stakeholders must be able to understand AI decisions.
3. **Fairness** — AI must not create unlawful discrimination or bias.
4. **Accountability** — Clear lines of responsibility for AI outcomes.
5. **Contestability and redress** — Individuals must be able to challenge AI decisions.

### Key Provisions of the Draft Bill 
##(If Enacted)

- **AI Authority** — Central body to coordinate regulators, issue binding codes of practice, and accredit AI auditors (analogous to the EU AI Office).
- **AI Responsible Officer** — Businesses developing or deploying AI must designate an officer responsible for ethical, transparent, and unbiased AI use (analogous to a DPO).
- **Codified principles** — The five White Paper principles become legally binding duties.
- **Impact assessments** — Required for AI systems posing risk to individuals.
- **AI sandboxes** — Controlled testing environments with regulatory supervision.
- **Public engagement** — Mandatory consultation on AI risks; informed consent for training datasets.
- **Transparency obligations** — User labelling and notification requirements.

### Current Obligations (Without the Bill)

Organisations operating in the UK must already comply with:

- **UK GDPR / Data Protection Act 2018** — Governs personal data used to train or operate AI.
- **Equality Act 2010** — Prohibits discriminatory AI outcomes.
- **Consumer protection and product safety laws** — Apply to AI-enabled products.
- **Sector-specific guidance** — FCA (financial services), Ofcom (media), CMA (competition).

### UK vs EU: Key Differences

| Dimension | EU AI Act | UK (Current) |
|---|---|---|
| Legal basis | Comprehensive cross-sectoral regulation | Sector-specific, principles-based |
| Risk classification | Formal four-tier system | No statutory classification |
| Enforcement body | EU AI Office + national authorities | ICO, FCA, Ofcom, CMA |
| Binding AI rules | Yes (in force) | Not yet (draft Bill only) |

---

## 4. India Digital Personal Data Protection Act (DPDP)

### Status

- **DPDP Act 2023** — Published in Official Gazette on August 11, 2023.
- **DPDP Rules 2025** — Notified late 2025; operationalised the Act for industry.
- **Implementation phases:**
  - **Phase I (immediate):** Data Protection Board of India (DPBI) established.
  - **Phase II (within 6 months of notification):** Significant Data Fiduciary (SDF) obligations begin.
  - **Phase III (May 13, 2027):** All substantive compliance obligations become effective.
- **Scope:** Applies to digital personal data processed in India, and to entities outside India processing data of Indian data principals. Does **not** cover non personal or non digital data.
- **No standalone AI Act:** India regulates AI indirectly through the DPDP Act, sector rules, consumer protection law, and the IT Act. A February 2026 deepfakes framework was introduced as a targeted intervention but is separate from the DPDP Act.

### Core Concepts

| Term | Definition |
|---|---|
| **Data Principal** | Individual whose personal data is processed (≈ GDPR "data subject") |
| **Data Fiduciary** | Entity that determines purpose and means of processing (≈ GDPR "data controller") |
| **Significant Data Fiduciary (SDF)** | High-volume or high-sensitivity fiduciaries designated by government; face enhanced obligations |
| **Consent Manager** | Registered intermediary through which individuals give, manage, review, and withdraw consent |

### Key Obligations for Data Fiduciaries

- **Lawful basis:** Primary lawful basis is **consent** — must be free, specific, informed, unconditional, and unambiguous. Bundled consent is not acceptable.
- **Purpose limitation:** Data may only be used for the stated collection purpose. No secondary use provisions , strict by design.
- **Consent withdrawal:** Must be as easy as giving consent. Upon withdrawal, data must be deleted unless a legal retention obligation applies.
- **Privacy notice:** Plain language; available in all 22 scheduled languages of India.
- **Data security:** Appropriate technical and organisational measures required.
- **Data deletion:** Data no longer needed or for which consent is withdrawn must be erased.
- **Breach notification:** Notify Data Protection Board and affected individuals. Failure carries penalties up to **INR 200 crore (~USD 24M)**.
- **DPO requirement:** SDFs must appoint a Data Protection Officer based in India.
- **Children's data:** Verifiable parental consent required. Penalties up to INR 200 crore.
- **DPIA:** SDFs must conduct yearly Data Protection Impact Assessments and independent audits.
- **Cross-border transfers:** Government may restrict transfers to certain countries; permitted countries list pending finalisation.

### Enforcement

- **Data Protection Board of India (DPBI)** — single national enforcement body.
- **Penalties:** Up to **INR 250 crore (~USD 30M)** for the most serious violations.

### AI-Specific Relevance

The DPDP Act does not define AI risk tiers or AI-specific obligations directly. Its relevance to AI is indirect but material:

- Any AI system processing personal data of Indian users must comply with consent, purpose limitation, and data security obligations.
- No explicit right to contest automated decisions (less developed than GDPR Article 22).
- Deepfake/AI-generated content is addressed by a separate 2026 framework outside DPDP.
- SDFs using AI for profiling or large-scale data processing face enhanced obligations (DPIA, audit, DPO).

---

## 5. Side-by-Side Comparison

| Dimension | EU AI Act | UK AI Bill (Draft) | India DPDP Act |
|---|---|---|---|
| **Legal status** | In force (phased 2025–2027) | Private Member's Bill; not law | In force (phased to May 2027) |
| **Regulatory model** | Risk-based, prescriptive | Principles-based (non-statutory) | Consent and data-centric |
| **AI risk classification** | Four-tier system | None in current law | None |
| **Prohibited AI uses** | Yes (social scoring, emotion inference, etc.) | Not defined in current law | None AI-specific |
| **High-risk AI obligations** | Conformity assessment, documentation, human oversight, incident reporting | Proposed only | None AI-specific |
| **Transparency / labelling** | Mandatory (Aug 2026 for limited-risk + GPAI) | Proposed in draft Bill | Data processing notices required; deepfake labelling via separate 2026 framework |
| **Human oversight** | Mandatory for high-risk AI | Proposed as a principle | Not required |
| **Enforcement body** | EU AI Office + national authorities | Sector regulators + proposed AI Authority | Data Protection Board of India |
| **Fines** | Up to €35M / 7% global turnover | Not yet defined | Up to INR 250 crore (~USD 30M) |
| **Data governance** | Training data quality criteria for high-risk AI | UK GDPR applies | Consent, purpose limitation, deletion |
| **GPAI / foundation model rules** | Yes (from Aug 2025) | Not addressed | Not addressed |
| **Automated decision-making rights** | Yes (right to human review for high-risk AI) | Proposed via contestability principle | Not explicitly defined |
| **Incident reporting** | Mandatory (high-risk AI) | Proposed | Breach notification required |
| **Cross-border data** | Data localisation not required; adequacy decisions apply | UK adequacy regime post-Brexit | Pending government whitelist |

---

## 6. Overlaps and Gaps Relevant to AegisAI

### Areas of Overlap (Shared Obligations Across Frameworks)

| Theme | EU AI Act | UK AI Bill | India DPDP |
|---|---|---|---|
| **Transparency** | Article 50; GPAI docs | Proposed principle | Privacy notice requirement |
| **Accountability** | Provider/deployer distinction | Proposed AI Responsible Officer | Data Fiduciary obligations |
| **Data quality / security** | High risk data governance | UK GDPR | Data security obligation |
| **Human oversight / redress** | Mandatory for high risk | Contestability principle (proposed) | Weak (no explicit ADM rights) |
| **Children's data** | Extra safeguards required | Equality Act / ICO guidance | Verifiable parental consent required |

### Gaps AegisAI Must Account For

1. **No risk classification in UK or India.** AegisAI's EU AI Act classification engine (Unacceptable / High / Limited / Minimal) cannot be directly mapped to UK or Indian law. These jurisdictions will require a separate, principles-based assessment module rather than tier assignment.

2. **India DPDP has no AI specific obligations.** Compliance for Indian deployments is currently a data protection question, not an AI regulation question. AegisAI should trigger DPDP consent and data governance checks whenever an AI system processes personal data of Indian users — independent of risk tier.

3. **UK regulatory status is uncertain.** The absence of a binding UK AI law means AegisAI cannot currently generate a "UK AI Act compliant" verdict. The engine should instead output a principles based gap analysis against the five UK AI White Paper principles, and flag readiness for potential future legislation.

4. **Automated decision making (ADM) rights differ significantly.** EU high-risk AI rules and GDPR Article 22 give strong ADM rights. India DPDP has no equivalent. UK GDPR mirrors EU GDPR for now. AegisAI classification output should include a per-jurisdiction ADM rights flag.

5. **Cross border data transfer rules are unsettled in India.** AegisAI systems operating cross-border with Indian data must flag the pending DPDP whitelist as a blocking risk until resolved.

6. **GPAI obligations exist only in the EU.** Foundation model / GPAI classification is currently an EU-only concern. UK and India do not yet regulate foundation models specifically.

---

## 7. Implementation Notes for AegisAI Classification Engine

Based on the above analysis, the following changes are recommended for multi-regulation support:

- **Add a `jurisdiction` field** to classification requests — valid values: `EU`, `UK`, `IN`, `MULTI`. Output format should vary by jurisdiction.
- **EU output:** Risk tier (Unacceptable / High / Limited / Minimal) + applicable obligations checklist.
- **UK output:** Principles-based gap analysis against the five White Paper principles + "draft Bill readiness" flag. No tier assignment.
- **India output:** DPDP data processing checklist (consent, purpose, security, deletion, DPO if SDF) + ADM rights gap flag. No AI risk tier.
- **Add a `gpai_flag`** — currently triggers EU GPAI obligations only; monitor UK and India for future rules.
- **Add a `children_data_flag`** — triggers enhanced obligations in all three jurisdictions (EU AI Act + GDPR, UK GDPR + ICO guidance, India DPDP verifiable parental consent).
- **Add an `adm_rights_matrix`** to output — shows per-jurisdiction automated decision-making rights status.
- **Surface regulatory status warnings** — UK Bill and India DPDP Phase III are not yet fully in force; output should timestamp the regulatory status used for classification.

---

## 8. References

- EU AI Act — Regulation (EU) 2024/1689: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- EU AI Act Single Information Platform: https://ai-act-service-desk.ec.europa.eu
- UK Artificial Intelligence (Regulation) Bill [HL] 2025: https://bills.parliament.uk/bills/3942
- UK AI White Paper (2023): https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach
- Data (Use and Access) Act 2025 (UK): https://www.legislation.gov.uk
- India DPDP Act 2023: https://www.meity.gov.in/data-protection-framework
- India DPDP Rules 2025: https://www.meity.gov.in
- DLA Piper Data Protection Laws of the World — India: https://www.dlapiperdataprotection.com/?t=law&c=IN

---

*Last updated: May 2026. Regulatory status should be re-verified before each major release.*
