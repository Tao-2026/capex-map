# RD (Real Data) — Mark 1 audit

Generated: `2026-08-02T07:09:52+00:00`

## Scope

This is a data spike, not a production dataset. It tests whether public World Bank project data can be converted into map-ready capital-flow records without changing the dashboard UI.

## Filters

- Status: `Active`
- Approval years: `2021–2026`
- Minimum project amount: `$500,000,000`
- Target sectors: energy, transport, water, and urban development

## Quality checks

- API projects fetched: **1,284**
- Projects with no usable amount: **42**
- Projects below the amount threshold: **1,177**
- Projects not classified into a target sector: **875**
- Selected projects: **38**
- Selected projects missing recipient coordinates: **4**
- Selected multi-country projects: **0**
- Selected projects classified from project-name keywords: **9**
- Selected policy-financing operations (not necessarily physical assets): **8**

## Selected sample

Total represented amount: **$24.8B**

### By sector

- Energy & Extractives: **21**
- Urban Development: **8**
- Water Infrastructure: **5**
- Transport Infrastructure: **4**

### Top recipient countries

- Nigeria: **5**
- Turkiye: **5**
- Pakistan: **3**
- Eastern and Southern Africa: **3**
- Congo, Democratic Republic of: **3**
- Bangladesh: **2**
- Uganda: **2**
- Ethiopia: **2**
- India: **1**
- South Africa: **1**

### Largest projects

- **Second Low-Carbon Energy Programmatic Development Policy Financing** — India, Energy & Extractives, $1.500B ([P181195](https://projects.worldbank.org/en/projects-operations/project-detail/P181195))
- **South Africa Sustainable and Low-Carbon Energy Transition Development Policy Loan** — South Africa, Energy & Extractives, $1.000B ([P179077](https://projects.worldbank.org/en/projects-operations/project-detail/P179077))
- **Second Additional Financing for Dasu Hydropower Stage I Project** — Pakistan, Energy & Extractives, $1.000B ([P181423](https://projects.worldbank.org/en/projects-operations/project-detail/P181423))
- **First Inclusive and Resilient Market Economy Development Policy Operation** — Uzbekistan, Energy & Extractives, $0.800B ([P180470](https://projects.worldbank.org/en/projects-operations/project-detail/P180470))
- **Food Systems Resilience Program for Eastern and Southern Africa** — Eastern and Southern Africa, Water Infrastructure, $0.788B ([P178566](https://projects.worldbank.org/en/projects-operations/project-detail/P178566))
- **Accelerating Transport and Trade Connectivity in Eastern South Asia – Bangladesh Phase 1 Project** — Bangladesh, Urban Development, $0.753B ([P176549](https://projects.worldbank.org/en/projects-operations/project-detail/P176549))
- **Nigeria - AF Power Sector Recovery Performance Based Operation** — Nigeria, Energy & Extractives, $0.750B ([P174622](https://projects.worldbank.org/en/projects-operations/project-detail/P174622))
- **Philippines First Sustainable Recovery DPL** — Philippines, Energy & Extractives, $0.750B ([P178634](https://projects.worldbank.org/en/projects-operations/project-detail/P178634))
- **Peru: Enabling a Green and Resilient Development DPF - DDO II** — Peru, Energy & Extractives, $0.750B ([P179214](https://projects.worldbank.org/en/projects-operations/project-detail/P179214))
- **Nigeria Distributed Access through Renewable Energy Scale-up Project** — Nigeria, Energy & Extractives, $0.750B ([P179687](https://projects.worldbank.org/en/projects-operations/project-detail/P179687))

## Known limitations

- The Projects API frequently leaves its explicit sector fields blank. RD Mark 1 therefore uses transparent whole-word rules on project names when necessary; abstracts do not control classification.
- Project amount fields describe project financing or commitments; they are not equivalent to actual year-by-year cash disbursements.
- The World Bank country endpoint supplies a representative country point, not a project-site location.
- Multi-country projects retain all recipient codes but use one primary coordinate for this first map-ready schema.
- This source covers World Bank projects only; it does not represent all global infrastructure investment.

## Mark 2 decision gate

Use these records in the dashboard only after reviewing the keyword classifications and deciding how the UI should disclose estimated sectors, amounts, and country-level coordinates.
