# SolarKenya Pro ☀️
### Solar operations, projects, inventory, service and document management

SolarKenya Pro is a Python/Streamlit MVP for a Kenyan solar installation, distribution and maintenance business. It combines an operations dashboard with customer records, project/site tracking, inventory and reorder alerts, service tickets, reporting, company settings, and an A4 PDF document centre.

> **Scope and production notice:** This is a locally runnable MVP, not a certified ERP, accounting system, inverter monitoring platform, or KRA/eTIMS-certified invoicing application. The current build does not yet implement login/authentication or enforce user roles in the application. The role matrix below is a recommended deployment policy, not an implemented security control. Do not expose the app publicly or use it to store sensitive customer information until the security items in this README are completed.

## Features

- **Dashboard:** document totals, document value, open document count, customers served and recent records.
- **Customers:** create and view customer/organisation records including contact details, address and optional KRA PIN.
- **Projects & sites:** create projects, assign a customer, record location, system size, budget, dates, status and notes.
- **Inventory:** register stock items by unique SKU, category, quantity, reorder threshold, cost, warehouse and supplier; flag items at/below reorder level.
- **Maintenance:** create service tickets with site, issue, priority, assignee, due date, status and notes.
- **Documents & billing:** create and save quotations, tax invoices, proforma invoices, receipts, delivery notes, work orders, installation checklists, commissioning certificates, warranty certificates, service reports, customer handover packs and purchase orders.
- **PDFs:** generate A4 PDF documents with customer details, line items, subtotals, configurable VAT, totals, dates, status and terms. Download the PDF and print it from a PDF viewer.
- **Reports:** document totals grouped by type and status.
- **Company settings:** configure company identity and payment instructions for generated documents (current session only in this MVP).
- **Persistence:** SQLite stores customers, projects, inventory, service tickets and documents on the local machine.

## Requirements

- Python 3.10 or newer (Python 3.11/3.12 recommended)
- pip
- A modern browser

## Quick start

### Windows (PowerShell)

1. Download and extract this repository ZIP.
2. Open PowerShell in the extracted `solarkenya_pro` folder.
3. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Launch the app:

   ```powershell
   streamlit run app.py
   ```

6. Open the local address Streamlit prints, usually `http://localhost:8501`.

If PowerShell blocks environment activation, use `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `\.venv\Scripts\python.exe -m streamlit run app.py` instead.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Typical workflows

### Add a customer
Open **Customers → Add customer**, complete the required organisation name and save.

### Create a project
Open **Projects & Sites → Create project / site**, select a customer if available, add location, system size, budget, dates and status, then save.

### Track stock
Open **Inventory → Add / receive stock**. Each SKU must be unique. Items at or below their reorder threshold appear in the reorder alert table. This version records stock quantities but does not yet provide a full stock-movement ledger, project reservations or serial-number-level traceability.

### Log a maintenance issue
Open **Maintenance & service tickets → Create service ticket**, enter the issue and priority, assign a technician if known, set the due date and save.

### Generate, download and print documents
1. Open **Documents & Billing**.
2. Select a document type, enter customer and date information, choose currency and VAT rate, and add line items.
3. Select **Generate and save document**.
4. Download the generated PDF using the download control.
5. Open the PDF and use your PDF viewer's **Print** command. Documents are formatted for A4 paper.
6. Previously generated documents appear in the document register and can be downloaded again while their PDF files remain in `generated_documents/`.

Configure the company profile before generating customer-facing documents. Confirm the correct tax treatment and VAT rate for each transaction; the app's default rate is a configurable starting value, not tax advice.

## Data locations and backup

- SQLite database: `data/solarkenya.db`
- Generated PDF documents: `generated_documents/`
- Optional database override: set the `SOLARKENYA_DB` environment variable to a writable database file path before launching.

Stop the app before making a consistent manual backup. Copy both the database and `generated_documents/` to a protected backup location. Test restoration periodically. The database and PDFs may contain customer/business information; restrict filesystem access.

## User rights and recommended access policy

**Important:** application login and role-based access enforcement are not implemented in this MVP. The following is the recommended permission model to implement before multi-user or internet deployment:

| Role | Recommended permissions |
|---|---|
| Administrator | Manage users/roles, company settings, all records, backups and audit history |
| Operations Manager | View all operational records; manage projects, inventory, maintenance and operational reports |
| Sales | Manage leads/customers and draft quotations; view only approved commercial records needed for sales |
| Finance | Manage invoices, receipts, payment status and financial reports; no unrestricted user administration |
| Technician | View assigned work orders; update service status and submit commissioning/service evidence |
| Inventory Officer | Manage item catalogue, stock receipts/issues/transfers and reorder reporting |
| Read-only Auditor | View permitted records and reports without create/edit/delete rights |
| Customer (future portal) | View only their own sites, documents and service tickets |

For a production implementation, enforce permissions server-side for every operation, use individual accounts, secure password hashing, session expiry, audit events, least-privilege defaults and tenant isolation if multiple businesses share one deployment. Hiding a menu item alone is not access control.

## Tests and quality checks

Install test dependencies and run:

```bash
pip install pytest
pytest -q
python -m py_compile app.py document_engine.py
```

Tests cover VAT arithmetic, zero VAT and PDF generation. A successful automated test run does not replace manual end-to-end testing in a browser or a security review.

## Suggested GitHub repository structure

```text
solarkenya_pro/
├── app.py                    # Streamlit user interface and workflows
├── document_engine.py        # Document arithmetic and PDF generation
├── requirements.txt          # Runtime dependencies
├── README.md                 # Setup, usage, scope and security guidance
├── .gitignore                # Excludes local data, PDFs and virtual environments
├── tests/
│   └── test_documents.py     # Automated document tests
├── data/                     # Created locally; SQLite database (not committed)
└── generated_documents/      # Created locally; PDFs (not committed)
```

## Current limitations / roadmap

1. Authentication, enforced role permissions, password reset and audit log.
2. Persistent company settings and configurable document templates/logo.
3. Full inventory transaction ledger, serial-number and warranty tracking, stock reservation and supplier purchase workflow.
4. Project milestone management, site surveys, commissioning evidence and digital asset passports.
5. Maintenance scheduling, technician assignment, SLA timers and repeat-fault analysis.
6. Payment reconciliation and accounting integrations; live M-Pesa integration requires authorised credentials and testing.
7. Vendor-authorised inverter/battery telemetry integrations, validated energy KPIs and anomaly alerts.
8. Database migrations, automated backups, error monitoring, security hardening and deployment pipeline.
9. KRA/eTIMS integration and validation against current tax requirements.

## Tax and regulatory note

A PDF labelled “Tax Invoice” is not automatically a legally compliant tax invoice. Validate the applicable KRA/eTIMS requirements, business registration details, tax treatment and any required integration with KRA or a qualified Kenyan tax adviser before issuing official tax documents. The software does not submit invoices to KRA, process payments, or verify tax status.

## Security and deployment checklist

- Do not commit `data/`, customer exports, generated PDFs, secrets, API keys or `.env` files.
- Do not expose the development server directly to the public internet.
- Add authentication and server-side role enforcement before multi-user deployment.
- Deploy behind HTTPS with a supported hosting configuration and restricted network access.
- Apply least-privilege filesystem/database permissions and protect backups.
- Define retention, privacy notices, lawful processing and incident response in line with applicable Kenyan data-protection obligations.
- Validate user input, add CSRF/session protections appropriate to the chosen deployment, and review dependency updates.
- Configure monitoring, database migrations, recovery tests and a documented incident process.

## License

No license is granted by default. Add a `LICENSE` file before distributing this repository publicly; choose a license appropriate to your intended use.
