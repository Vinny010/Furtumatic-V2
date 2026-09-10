# Usage-Based Truck Insurance Platform — Design Discussion

Status: discussion draft, nothing built yet.
Date: 10 September 2026.
Basis: the signed FleetCam / Optimum Strategic Collaboration Agreement (24 June 2026) and the brief to build a
website + app that meters FleetCam telematics and bills heavy commercial vehicle (HCV) insurance on a
pay-as-you-go (PAYG) basis, for South African, Mauritian and EU clients, scaling to ~22,000 trucks within 1–2 years.

Assumption: "our insurance arm" is Optimum Financial Services Group (branded RiskPilot AI on the signature page).
The FUR token repo this document lives in is treated as a separate product; see §9.

---

## 1. What the contract actually locks in (and what it does not)

Read carefully, the agreement constrains the build in ways that matter more than the technology choices.

| Clause | What it says | Design consequence |
|---|---|---|
| 1, 22 | Scope is FleetCam clients in the **South African** transport industry; SA law governs. | Mauritius and EU clients are **outside the written scope**. Serving them needs a written amendment (cl. 23) or a separate agreement. See §7. |
| 2.6, 18 | Usage-based insurance is a "future innovation to jointly explore". | PAYG is contemplated but not yet a defined product. Product terms must be agreed with FleetCam and the insurer before launch. |
| 4.3 | Optimum may not build a similar ecosystem with **any competing HCV telematics provider**. | You cannot plug a different telematics provider in for EU or Mauritius trucks without FleetCam's consent. The ingestion layer should be built with adapters, but commercially FleetCam is the only source. |
| 4.6, 15.1 | The telematics-enabled insurance ecosystem is FleetCam's proprietary business model. FleetCam owns the platform, algorithms, **risk scoring methodologies**, proprietary data and analytics. | Draw a hard line in the architecture: FleetCam-owned = raw telematics, driver behaviour scores, video analytics. Optimum-owned (cl. 15.2) = policy admin, billing, invoicing, ledger, client portal. Who owns the **PAYG rating tables and risk-zone map** is ambiguous and should be settled in the Commercial Services Agreement (cl. 10.2). |
| 5 | FleetCam provides "telematics, risk and operational information **where legally permissible**". | There is **no API specification, data field list, cadence, SLA, or sandbox** in the contract. That is the single biggest gap before any code is written. |
| 8, 9 | Product suite: HCV, Goods in Transit, Environmental Liability, Driver Responsibility Fund, Third Party Liability. Structures: conventional, aggregate excess, burner, 50/50 retained fund, self-funding. | The policy/billing model must not be "one premium per truck". It needs multiple cover lines per vehicle and per-policy structure types from day one, even if only conventional is live at launch. |
| 10.1 | Commission split 60% Optimum / 40% FleetCam after bureau service costs. | The ledger must compute commission per policy per period, deduct bureau costs, and report the split. This is a first-class accounting feature, not a spreadsheet afterthought. |
| 10.3 | All commercial arrangements subject to insurer and regulatory approval. | The rating model is not yours to launch unilaterally. An underwriter/actuary signs it off. Build the rating engine so rate tables are data, versioned and replaceable, not code. |
| 16 | POPIA, FAIS, Insurance Act, FSR Act. | SA-only compliance list. GDPR, Mauritius DPA, IDD etc. are not mentioned. See §7. |
| 17, 20 | 3-year term, 90-day termination. | Design for exit: data export, portability, and clear data ownership on termination. |

**Open contractual items to close before build:** FleetCam API/data specification; POPIA operator/data-sharing agreement with FleetCam; Commercial Services Agreement (cl. 10.2) covering rating-model IP and bureau-cost definition; confirmation of which insurer carries the risk and whether Optimum has premium-collection authority (with Intermediaries Guarantee Facility cover); whether Mauritius/EU are in scope at all.

---

## 2. Billing model recommendation

### Your proposal

Insurance is paid upfront. Month 1: collect a premium, track everything, calculate the true usage cost. Month 2's invoice shows month 1's adjustment. Repeat.

### Recommendation: "base premium + usage adjustment", with a collar

Your proposal is sound and is essentially the standard **deposit-and-adjustment premium** structure used in commercial fleet UBI. Keep it, with four refinements:

1. **Split the premium into a fixed base and a variable usage charge.**
   - Base premium (paid upfront for month M): covers the risk that exists even when the truck is parked (theft, fire, hijack in depot, third-party while stationary) plus a minimum usage floor. This keeps cover continuously paid for, which the insurer and the Policyholder Protection Rules effectively require.
   - Usage charge (metered during month M, invoiced with month M+1's base): km by risk zone, time-of-day, continuous driving, driver behaviour events, etc.
   - Invoice(M+1) = Base(M+1) + UsageAdjustment(M). The adjustment can be a debit or a credit.

2. **Put a collar on the usage charge.** A per-vehicle minimum and maximum for the month. Clients need a bounded worst case for cash-flow planning, the actuary needs a bounded exposure, and SA DebiCheck debit-order mandates require a stated maximum collection amount anyway.

3. **Handle month 1 with an estimated-usage deposit.** If month 1 charges only the base, month 2 is a shock (base + a full month's usage). Instead, month 1 = base + an estimated usage deposit derived from the fleet's historical FleetCam data (which FleetCam already has for existing clients). Month 2 then trues up against the estimate. This also means the insurer is not under-collected in month 1.

4. **Run in shadow mode first.** For the pilot fleet, calculate PAYG charges for 2–3 months while still billing conventionally. Show the client both numbers. This calibrates your rate tables against real data before money moves and gives you the evidence for the insurer sign-off.

### Client-facing behaviour

- A live "meter" per vehicle and per fleet in the portal/app: usage so far this month, projected month-end charge, the collar, and what is driving the number (night km, high-risk-zone km, fatigue events).
- Alerts when a vehicle is trending above its cap or enters a high-risk zone at a high-risk time, so the owner can act before the bill arrives. This is the "reduce cost for truck owners" story made visible.
- Month-end usage statement per vehicle with drill-down to the day, before the invoice is issued, plus a dispute window (e.g. 5 business days) with a defined process. Insurance premium disputes will happen; the data trail must answer them.

### Alternative considered: prepaid kilometre wallet

Client tops up a balance, usage draws it down, auto top-up at a threshold. True "pay as you go" and simpler cash flow, but cover would have to lapse when the balance hits zero, which is a regulatory and reputational problem for an insurance product. Park this as a possible later option for self-funding structures, not the launch model.

### Cancellation and mid-month changes

Final adjustment invoice or refund on cancellation, pro-rated base for vehicles added or removed mid-month, and a frozen usage record after the grace period so late telematics data does not re-open closed months.

---

## 3. The rating model: structure the system needs (numbers are yours to set)

You will set the actual rates. The platform needs the rating model to be expressed as **versioned data**, not code, so the actuary can change it and every historical invoice can be recalculated exactly as it was originally computed.

**Metered inputs, per vehicle per day** (the "usage record"):

| Factor | Source | Notes |
|---|---|---|
| Distance (km) | GPS distance or odometer from FleetCam | Split by risk zone and time band. |
| Risk zone km | Geofenced polygons with a risk weighting | Hijack corridors, urban night zones, border posts, known cargo-theft hotspots. Zone map is versioned; who owns it is a cl. 15 question. |
| Time band | Timestamp | e.g. day / evening / night. Night km on certain corridors is the biggest loss driver for SA HCV. |
| Continuous driving (fatigue) | Trip timestamps, ignition, movement | Minutes driven without a qualifying break; escalating surcharge past a threshold. Thresholds differ by region: EU Regulation 561/2006 is 4.5 h driving then 45 min break; SA has no equivalent statute, RTMS and fleet policy typically use 5 h / 15 min. |
| Driver behaviour events | FleetCam AI camera and telematics | Harsh braking, speeding bands, phone use, distraction, fatigue/yawn events. FleetCam owns the scoring; you consume the score or the events. |
| Cross-border days | Geofence | Different third-party liability exposure outside SA. |
| Parked / idle days | Ignition, movement | Base-only days. |
| Cover lines | Policy | HCV own damage, GIT, third-party, environmental: each line can have its own factor weights. |

**Charge shape** (illustrative, not a proposal for the rates themselves):

```
usage_charge(vehicle, month) =
    clamp(
        Σ_days [ Σ_segments ( km × zone_rate × time_band_multiplier )
                 + fatigue_surcharge(minutes_over_threshold)
                 + Σ_events event_surcharge(type, severity) ]
        − behaviour_discount(driver_score),
        floor, cap )
```

Every term is a row in a rate table with an effective-from date. The engine is deterministic: same inputs + same rate-table version = same output, always. That is what lets you replay, audit, and answer a client or regulator months later.

**Driver incentives** (cl. 2.6, 18): the same events feed a driver score shown to the driver in the app. Rewards can be non-monetary at first; anything monetary paid to drivers, or any token-based reward, needs its own regulatory and tax check (see §9).

---

## 4. System architecture

### Principles

- **Correctness of billing beats scale.** 22,000 trucks is a modest data volume; a wrong invoice is an existential problem. Optimise for auditability, idempotency and replay.
- **Modular monolith first, split later.** One deployable backend with clear internal modules. Do not start with microservices for a few hundred trucks.
- **Region-aware from day one, single region at launch.** See §7.
- **FleetCam is upstream and owns its data; we keep derived records and only the raw data we need.**

### Components

```
FleetCam API ──▶ Ingestion adapters ──▶ Event stream ──▶ Usage processor ──▶ Usage records (per vehicle per day)
                                                                                    │
                                                              Rate tables (versioned) ──▶ Rating engine ──▶ Usage charges
                                                                                                                │
      Policy admin (policies, vehicles, cover lines, structures) ──▶ Billing & invoicing ──▶ Ledger ──▶ Payments (debit order / SEPA / card)
                                                                              │                  │
                                                                     Client portal + apps   Insurer bordereaux, commission split (60/40), reporting
```

1. **Ingestion.** An adapter per upstream feed (FleetCam positions, trips, events, driver assignments, video-analytics events). Supports both push (webhooks) and pull (polling with checkpoints) because we do not yet know what FleetCam offers. Idempotent by upstream event ID. Backfill mode for history.
2. **Event stream.** Kafka/Redpanda (or a managed equivalent). At 22,000 trucks × 1 position / 30 s that is roughly 700 messages/s and ~60 M/day: comfortably inside a single small cluster. If FleetCam can supply trip summaries and events rather than raw pings, ingest those as primary and pull raw positions only on demand; it cuts storage and cost by an order of magnitude.
3. **Usage processor.** Stream job that segments trips by geofence and time band, computes continuous-driving windows, and folds everything into one immutable **usage record per vehicle per day**. Must tolerate late and out-of-order data (trucks lose signal in rural SA and devices backfill hours later): a day can be recomputed until the month is frozen (month end + grace period), after which corrections go in the next period as adjustments.
4. **Rating engine.** Pure, deterministic library. Inputs: usage records + rate-table version + policy terms. Output: usage charge lines with full explanation. Runs nightly for projections and at month close for billing. Replayable for any past period.
5. **Policy administration.** Clients, fleets, vehicles, drivers (pseudonymised), policies, cover lines, structure type (conventional, aggregate excess, burner, retained fund, self-funding), effective dating, endorsements.
6. **Billing, invoicing, ledger.** Double-entry ledger; invoices with base + adjustment lines; tax rules per jurisdiction; collar enforcement; credit notes; dunning. Commission and bureau-cost computation for the 60/40 split. Monthly bordereaux export to the insurer in their format.
7. **Payments.** SA: DebiCheck debit orders via a local provider, plus EFT/card. EU: SEPA Direct Debit and card. Mauritius: card / bank transfer (local debit-order rails are limited). Payment provider behind an interface so rails can be swapped per region.
8. **Portals and apps.**
   - Fleet-owner web portal: live map, per-vehicle meter, projections, alerts, statements, invoices, disputes, driver scores.
   - Driver mobile app: own score, trips, incentive status, fatigue nudges. Single cross-platform codebase (React Native/Expo or Flutter).
   - Broker/admin back office: onboarding, rate-table management with approval workflow, month close, disputes, commission reports.
   - Insurer view: portfolio exposure, bordereaux, loss-ratio inputs.
9. **Cross-cutting.** Identity (SSO for fleets, MFA for admins), audit log on every rate change and every invoice, observability, secrets/key management per region.

### Suggested stack (opinionated; change if your team's skills differ)

- Backend: TypeScript (NestJS) as a modular monolith; the ingestion/stream hot path can move to Go later if needed.
- Data: PostgreSQL for policy/billing/ledger; TimescaleDB (Postgres extension) or ClickHouse for positions/usage time-series; Redis for caching and rate limiting; object storage for exports and evidence.
- Streaming: Redpanda or managed Kafka. At pilot scale a Postgres-backed queue is acceptable, but design the processor against a stream interface from the start.
- Web: Next.js. Mobile: React Native/Expo. Maps/geofencing: PostGIS server-side, MapLibre/Mapbox client-side.
- Infra: Kubernetes or a managed container platform, infrastructure-as-code, one "cell" per region (§7). SA hosting: AWS Cape Town (af-south-1) or Azure South Africa North (Johannesburg).

### Scale path

| Stage | Trucks | What changes |
|---|---|---|
| Pilot | 50–300 | Monolith + Postgres queue is enough. Focus on shadow billing and calibration. |
| Year 1 | 1,000–5,000 | Move to Redpanda/Kafka; time-series store; nightly rating jobs partitioned by fleet. |
| Year 2 | 22,000 | Partition usage tables by month and region; horizontal workers for the usage processor; separate read replicas for portals. No architectural rewrite required if the boundaries above are respected. |

---

## 5. Data model (core entities)

- `Tenant` (fleet owner / client), with `home_region`.
- `Policy` → `CoverLine`s (HCV, GIT, TPL, environmental), `StructureType`, effective dates.
- `Vehicle` ↔ FleetCam device ID mapping, with history (devices get moved between trucks).
- `Driver` (pseudonymous ID; personal details minimised, stored only in home region).
- `TelematicsEvent` (raw, retention-limited), `Trip`.
- `UsageRecord` (vehicle, date, all metered quantities, source data version): immutable once frozen.
- `RateTable` (versioned, effective-from, approved-by).
- `UsageCharge` (vehicle, period, rate-table version, line items with explanations).
- `Invoice`, `InvoiceLine` (base, adjustment, tax), `CreditNote`, `Payment`, `LedgerEntry`.
- `CommissionStatement` (period, gross commission, bureau costs, 60/40 split).
- `AuditEvent`.

---

## 6. Month lifecycle

1. **During month M:** ingest continuously; recompute usage records nightly; publish projections and alerts to the portal.
2. **Month end + grace (e.g. 3 days):** freeze M's usage records; run the rating engine with the rate-table version in force for M; generate usage statements; open the dispute window.
3. **Dispute window closes:** apply agreed corrections as adjustment lines; issue invoice for M+1 = Base(M+1) + Adjustment(M) + tax; submit debit orders within mandate limits.
4. **Insurer close:** bordereaux for M, commission statement, bureau-cost deduction, 60/40 split.
5. **Late data after freeze:** never rewrites M; lands as a line in M+1's adjustment with a reference back.

---

## 7. Compliance and data residency: SA, Mauritius, EU

### The threshold issue

The contract is SA-scoped and SA-law-only. Before any Mauritius or EU work, get a written amendment or a separate agreement with FleetCam confirming scope, and confirm FleetCam actually has devices, data flows and legal permission to share data in those territories. Clause 4.3 stops you using another telematics provider there.

### Two separate compliance tracks per country

**(a) Insurance distribution licensing** (can you sell/administer insurance there at all):
- South Africa: FAIS-licensed FSP, Insurance Act, FSR Act, Policyholder Protection Rules. Premium collection by an intermediary needs insurer authorisation and IGF cover. Variable-premium products need clear premium-basis disclosure to the policyholder.
- Mauritius: Financial Services Commission licensing under the Insurance Act 2005 for intermediaries; realistically a locally licensed partner or entity. Mauritius is also a natural home for captive/cell and reinsurance structures if you pursue the self-funding structures in cl. 9.
- EU: Insurance Distribution Directive (IDD) registration in a member state, plus an EU-authorised insurer for the risk. You cannot broker EU risks from South Africa. Motor third-party liability is compulsory and nationally regulated.

**(b) Data protection** (can you process driver and vehicle data there, and where):
- South Africa (POPIA): telematics, location and cabin video are personal information of drivers. Needs: lawful basis (employment/contract, with driver notification), an operator/data-sharing agreement with FleetCam defining who is responsible party for what, Information Officer registration, a PAIA manual, breach notification, and section 72 conditions for any transfer out of SA (EU and Mauritius both have adequate-level laws, but the transfer still needs a contractual basis).
- Mauritius (Data Protection Act 2017): GDPR-aligned; controllers and processors register with the Data Protection Office; cross-border transfers need adequacy or safeguards.
- EU (GDPR): systematic monitoring of drivers and location data makes this high-risk processing: a Data Protection Impact Assessment is mandatory; Article 22 applies because pricing is automated (provide explanation and a human-review route, which the rating engine's explanation lines give you); Article 27 EU representative if no EU establishment; a DPO is very likely required; cabin video with face analytics may be biometric (Article 9) and should stay inside FleetCam's system rather than be copied. Also relevant: the EU Data Act (applicable since September 2025) on connected-vehicle data access rights, and the EU AI Act, where AI-based monitoring and evaluation of workers is a listed high-risk use; high-risk obligations are scheduled from August 2026 subject to the pending "digital omnibus" changes. Driver scoring for EU drivers needs counsel's view on this before launch.

### Architecture for residency: regional cells

- Every tenant has a **home region**. All personal data (drivers, positions, video references, invoices) lives only in that region's cell. Launch with the SA cell; add an EU cell (Frankfurt/Ireland) when EU clients are real; Mauritius has no hyperscaler region, so it would be served from the SA or EU cell under DPA 2017 transfer safeguards, or from a local Mauritian host if a client demands it.
- A thin **global control plane** holds only non-personal configuration: tenant registry, region routing, rate-table definitions, feature flags, staff identity.
- **Pseudonymise drivers** in the analytics and rating paths; the real identity mapping stays in the home-region policy store with tighter access.
- **Per-region keys**, encryption at rest and in transit, retention policies per region (SA insurance record-keeping expects multi-year retention; GDPR expects minimisation and defined limits: reconcile per data class).
- **Currency and tax per region:** ZAR/MUR/EUR; VAT on SA premiums, VAT-exempt but Insurance Premium Tax in most EU states, Mauritius rules to confirm. Tax is a per-region rule in the invoicing engine, never hard-coded.
- **Audit everything** that touches a rate or an invoice; regulators in all three territories will ask how a premium was derived.
- ISO 27001 certification is worth pursuing early: it is the fastest way to satisfy insurers and EU clients simultaneously.

---

## 8. Phased plan

**Phase 0 — lock the foundations (weeks 1–4, no product code):**
FleetCam API spec and sandbox; POPIA operator agreement; Commercial Services Agreement including rating-IP and bureau costs; insurer and premium-collection confirmation; rating model v1 in a spreadsheet (your costing exercise) expressed as rate tables; POPIA impact assessment; scope decision on Mauritius/EU.

**Phase 1 — pilot in shadow mode (months 2–4):**
SA cell only. Ingestion from FleetCam for a pilot fleet; usage records; rating engine v1; fleet-owner portal with live meter, projections and month-end statements; conventional billing continues; PAYG shown side-by-side. Calibrate rates and the collar against real data.

**Phase 2 — live PAYG billing (months 5–8):**
Base + adjustment invoicing, DebiCheck mandates, ledger, insurer bordereaux, commission split, dispute workflow, driver mobile app with scores and incentives, admin back office with rate-table approval workflow.

**Phase 3 — scale and territories (months 9–18):**
Stream processing hardening for 20k+ vehicles, partitioned storage, EU cell and GDPR programme (DPIA, representative, DPO), Mauritius licensing/partner, IDD route for the EU, ISO 27001.

---

## 9. Notes on the FUR token and this repository

This repository currently holds the Furtumatic (FUR) BEP-20 token metadata and whitepaper. Two cautions:

- Keep the token **out of the regulated premium flow** at launch. In South Africa crypto assets are a declared financial product (FSCA, 2022) requiring a CASP licence for related services, and paying insurance premiums in a token raises premium-collection, FICA and accounting issues you do not need in year one.
- A token-based **driver incentive** is conceivable later, but it is a remuneration/tax/regulatory question in every one of the three territories. Treat it as a Phase 3+ investigation, not a design input now.

The insurance platform should be a separate repository (or a clearly separated `platform/` tree) so its compliance posture, access controls and audit history are not entangled with the token project.

---

## 10. Questions to answer before Phase 1

1. Does FleetCam provide trip/event summaries and driver scores via API, or only raw positions? Push or pull? What identifies a driver (tag, face, manual login)?
2. Which insurer underwrites, and in what structure for launch? Does Optimum collect premium, and under what authorisation?
3. Who owns the risk-zone map and the PAYG rate tables under clause 15?
4. Are Mauritius and the EU in scope of the FleetCam agreement, and does FleetCam operate there?
5. What is the target collar (min/max) per vehicle, and how will the base/usage split be disclosed to policyholders?
6. What is the dispute window and who adjudicates?
7. Retention periods per data class per region, and who is the Information Officer / DPO?

---

## 11. Build timeline: South Africa first, region-ready

### Assumptions

- Team: 1 tech lead/architect, 3 backend engineers (one owning ingestion/geo, one rating/billing, one platform), 1 web front-end, 1 mobile engineer, 1 QA/test automation, 1 product owner/business analyst, part-time DevOps and part-time compliance/legal. Roughly 7–8 people. A team half this size stretches every phase by about 50%.
- FleetCam provides API sandbox access within the first 4 weeks. This is the critical-path dependency; every week of delay here moves go-live by a week.
- The insurer/actuary participates from week 1 and signs off calibrated rates by month 7.
- Two-week sprints. Dates below are relative to project kick-off.

### Phases

| Phase | Weeks | Outcome |
|---|---|---|
| 0. Foundations | 1–4 | Contracts and data agreements in motion, FleetCam API spec and sandbox, rate-table v1 from your costing, POPIA impact assessment started, UX designs for portal and app, infra and CI/CD skeleton in the SA region, Apple/Google developer accounts opened. |
| 1. Core platform and pilot (shadow mode) | 5–16 | Ingestion from FleetCam, vehicle/device mapping, usage processor (zones, time bands, continuous driving), usage records, rating engine v1, admin back office basics, fleet-owner web portal with live meter and month-end statements, mobile app v1 (internal/TestFlight), pilot fleet of 50–200 trucks running in shadow billing. |
| 2. Live billing build and calibration | 17–32 | Shadow data calibrates rates and the collar for 2–3 months. In parallel: policy admin, base + adjustment invoicing, ledger, DebiCheck debit orders, dispute workflow, insurer bordereaux, 60/40 commission statements, rate-table approval workflow, month-close runbook. Mobile app v2 (driver scores, alerts, incentives) submitted to the stores. Penetration test, POPIA readiness review, ISO 27001 gap assessment. |
| Go-live | 33–36 | Insurer signs off calibrated rates. First cohort moves from shadow to live PAYG billing. Month 9 from kick-off. |
| 3. Rollout and hardening | 37–52 | Remaining FleetCam clients onboarded in cohorts, streaming and partitioning work for 5,000+ vehicles, operations dashboards, SLA monitoring, and a second empty regional cell stood up in staging to prove the region model before any EU/Mauritius work. |

Headline: **pilot in shadow mode at month 4, live pay-as-you-go billing in South Africa at month 9, full SA rollout and scale-readiness by month 12.**

Adding a new region afterwards is 4–6 months each, and most of that is licensing and legal work rather than code, provided the region-ready rules below were followed.

### What "region-ready" means in practice during Phase 1

These are cheap on day one and expensive to retrofit, so they are non-negotiable in the first sprints even though only South Africa is live:

- Every tenant carries a `home_region`; every table holding personal data is partitioned or scoped by region; no query joins across regions.
- Infrastructure-as-code parameterised by region, so a second cell is a configuration change plus approvals, not a rebuild.
- Currency, tax, locale, date formats and legal driving-hour thresholds are configuration per region, never constants.
- All timestamps stored in UTC with the vehicle's timezone recorded on the usage record.
- Portal and app built with internationalisation from the first screen, even if only English ships initially.
- Secrets and encryption keys per region; audit log in place before the first invoice is generated.
- Payment provider, identity provider and telematics feed all sit behind interfaces so they can be swapped per region.

### Mobile app: exclusive to FleetCam clients

Exclusivity is enforced at sign-in, not at download:

- **Fleet-owner accounts** are created only through the broker back office, linked to a FleetCam client ID, and verified by matching the client's device list through the FleetCam API. No self-service sign-up.
- **Driver accounts** are invited by their fleet owner via SMS/email link with a one-time code, and are bound to that fleet. A driver who leaves the fleet loses access when the fleet owner removes them.
- If FleetCam has its own login system, add "Sign in with FleetCam" so clients use one identity; confirm this with FleetCam during Phase 0.
- **Distribution:** a normal public listing on the App Store and Google Play with a gated sign-in is the simplest and works on drivers' personal phones. Apple's unlisted-app distribution and Google Play private apps are options if FleetCam wants the app invisible to the public, but they complicate onboarding for drivers. Recommendation: public listing, gated sign-in, branding co-approved with FleetCam given clauses 4.6 and 15.
- **One app, two roles** (fleet owner and driver) on a single React Native/Expo codebase. Fleet owner sees the fleet map, per-vehicle meter, projections, alerts, statements and invoices. Driver sees own trips, score, fatigue nudges and incentive status. Split into two apps later only if the audiences diverge.
- Offline-tolerant for drivers in poor coverage, push notifications for alerts, and no raw video ever cached on the device.

Mobile timeline: v1 internal build by week 16, store submission in Phase 2 around week 26, public availability by week 30. Start Apple and Google developer enrolment in week 1: company verification (D-U-N-S number for Apple) can take several weeks.

### Things that most often move this timeline

1. FleetCam API readiness, field coverage, and whether trips/events are available or only raw positions.
2. Insurer sign-off of the rating model and policy wording for a variable premium.
3. DebiCheck onboarding with the bank or payment provider, which typically takes 4–8 weeks and should start in Phase 1.
4. Quality of the pilot fleet's data. If continuous-driving or driver-identification data is unreliable, calibration takes longer.
5. Apple developer enrolment and app review.
