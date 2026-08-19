# AI Customer Support Automation System

A client-ready Django customer-support automation portfolio project built around **Harbor & Pine Living**, a fictional U.S. ecommerce home-goods brand.

The system demonstrates how a business can combine a customer-facing support assistant, structured knowledge retrieval, product discovery, mock order lookup, lead capture, human escalation, conversation tracking, and an authenticated staff dashboard in one integrated application.

> **Portfolio Notice:** Harbor & Pine Living is a fictional company. Product, order, customer, FAQ, and knowledge-base data included in this repository are synthetic demonstration data created for portfolio and development purposes.

---

## Project Overview

This project simulates a more complete customer-support operation than a standalone chatbot.

Customers can interact with a support assistant from a realistic ecommerce storefront to:

- ask approved support questions
- search product information
- check mock order information
- request human assistance
- submit sales or bulk-purchase leads
- receive appropriate routing for sensitive or action-oriented requests

Staff can use the authenticated dashboard to review operational activity generated through those customer interactions.

The project focuses on controlled support automation rather than allowing an AI system to freely invent policies, perform unauthorized business actions, or expose sensitive information.

---

## Core Features

### Customer-Facing Support

- Floating support widget integrated into the Harbor & Pine storefront
- Dedicated support page
- Natural multi-turn customer conversations
- FAQ and approved-policy retrieval
- Product-information retrieval
- Product discovery support
- Mock order lookup
- Lead capture
- Human-support escalation
- Unanswered-question logging
- Conversation persistence during the active session
- New visible chat session after page refresh
- Enter-to-send support
- Shift+Enter for multiline messages
- Responsive customer interface
- Smooth widget open, close, and minimize behavior

### Intent and Routing Safety

The support orchestration layer distinguishes between informational questions and requests that require business action.

Examples include:

- explaining delivery-address policy vs. requesting an address change
- explaining damaged-item policy vs. reporting actual damage
- explaining privacy rights vs. requesting personal-data deletion
- explaining bulk pricing vs. requesting a written bulk quote
- explaining human-support response times vs. requesting a person

Sensitive or action-oriented cases are routed to the appropriate workflow instead of being treated as ordinary FAQ questions.

---

## Knowledge Management

The system uses two controlled knowledge sources.

### Approved FAQs

Twenty Harbor & Pine support FAQs are loaded through a Django data migration.

They cover areas such as:

- shipping
- returns
- order changes
- damaged items
- product safety
- payments
- discounts
- product care
- privacy
- human support
- bulk purchasing
- trade enquiries

### PDF Knowledge Base

A synthetic Harbor & Pine knowledge-base PDF is included in the repository:

```text
data/knowledge/07_Harbor_and_Pine_Mock_Knowledge_Base.pdf
```

Uploaded knowledge documents are:

- validated as PDFs
- limited to 10 MB
- SHA-256 checksummed
- versioned
- assigned Draft, Active, or Archived status
- converted into searchable knowledge chunks
- re-indexable through Django Admin or a management command

The runtime uploaded copy is stored under `media/`, which is intentionally excluded from Git.

---

## Product Catalogue

Synthetic catalogue data is stored in:

```text
data/products.csv
```

Products can be loaded into the database with:

```bash
python manage.py import_products
```

The importer validates the expected CSV structure and either creates or updates products based on SKU.

The catalogue contains structured fields such as:

- SKU
- product name
- category
- description
- price
- availability/status
- stock band
- material
- color
- dimensions
- care instructions
- product URL
- last-updated date
- data owner

---

## Mock Order Lookup

Synthetic order data is stored in:

```text
data/orders.csv
```

Import it with:

```bash
python manage.py import_orders
```

The project deliberately uses **mock orders** rather than a real ecommerce platform or customer database.

Order records contain fields such as:

- order ID
- billing ZIP code
- customer name
- customer email
- order date
- status
- carrier
- tracking reference
- ETA
- items
- total value

The order workflow is intended to demonstrate privacy-aware support automation without exposing real customer information.

---

## Lead Capture

Commercial enquiries can be routed to:

```text
/contact/lead/
```

This workflow can capture qualified customer interest rather than allowing useful sales opportunities to disappear inside chatbot conversations.

Examples include:

- bulk-order requests
- quote requests
- trade-program interest
- purchase-related enquiries requiring follow-up

Captured leads are available to staff through the dashboard.

---

## Human Support Escalation

Requests requiring human review can be routed to:

```text
/contact/human-support/
```

Examples include:

- explicit requests for a human
- order cancellation requests
- delivery-address changes
- damaged-product cases
- privacy requests
- safety-sensitive concerns
- situations where the automated assistant should not make the final decision

The customer-support assistant does not claim that these business actions have already been completed.

Human-support requests are recorded for staff review in the dashboard.

---

## Staff Dashboard

Authenticated staff functionality is available through:

```text
/staff/login/
```

The dashboard is available at:

```text
/dashboard/
```

Operational sections include:

```text
/dashboard/conversations/
/dashboard/unanswered-questions/
/dashboard/leads/
/dashboard/human-support-requests/
/dashboard/order-activity/
/dashboard/products/
```

Individual conversations can also be reviewed through their session-specific detail pages.

The dashboard gives the business side of the system visibility into what is happening through the automated customer-support channel.

---

## Main Application Routes

| Route | Purpose |
|---|---|
| `/` | Harbor & Pine storefront |
| `/support/` | Dedicated customer-support page |
| `/order-lookup/` | Mock order lookup |
| `/contact/lead/` | Lead capture |
| `/contact/human-support/` | Human-support request |
| `/staff/login/` | Staff authentication |
| `/staff/logout/` | Staff logout |
| `/dashboard/` | Staff dashboard |
| `/admin/` | Django administration |

---

## Technology Stack

### Backend

- Python 3.14
- Django 6.0.7
- SQLite

### Knowledge Processing

- pypdf 6.14.2
- Django database-backed FAQ retrieval
- PDF text extraction and chunk indexing

### Configuration

- python-dotenv
- environment-variable based settings
- `.env.example` for local configuration

### Frontend

- HTML
- CSS
- JavaScript
- Django templates

### Development and Version Control

- Git
- GitHub
- Django automated testing

---

## AI / Automation Architecture

This portfolio version emphasizes **controlled deterministic support orchestration and retrieval**.

Environment placeholders exist for:

```text
AI_PROVIDER
AI_API_KEY
AI_MODEL
```

but the current portfolio implementation does not depend on a live external LLM API for its verified core support workflows.

This keeps the demonstration reproducible while preserving an integration-ready architecture for future AI-provider connectivity.

---

## Project Structure

```text
ai_customer_support_automation_system/
│
├── accounts/
│   └── Staff authentication and portal routing
│
├── catalog/
│   └── Product models, retrieval, and CSV import
│
├── config/
│   └── Django project configuration
│
├── core/
│   └── Harbor & Pine storefront
│
├── crm_lite/
│   └── Lead capture and human-support workflows
│
├── dashboard/
│   └── Authenticated operational dashboard
│
├── data/
│   ├── knowledge/
│   │   └── Synthetic source knowledge PDF
│   ├── products.csv
│   └── orders.csv
│
├── knowledge/
│   └── FAQs, knowledge documents, indexing, and retrieval
│
├── orders/
│   └── Mock order lookup and activity
│
├── static/
│   └── CSS, JavaScript, images, and frontend assets
│
├── support_chat/
│   └── Conversation handling and support orchestration
│
├── templates/
│   └── Django HTML templates
│
├── .env.example
├── .gitattributes
├── .gitignore
├── manage.py
└── requirements.txt
```

`media/`, the SQLite database, local virtual environments, secrets, caches, and other runtime/development files are intentionally excluded from version control.

---

# Local Setup

## 1. Clone the Repository

```bash
git clone https://github.com/sobangrewal479/ai-customer-support-automation-system.git
cd ai-customer-support-automation-system
```

---

## 2. Create a Virtual Environment

Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Create the Environment File

Copy:

```text
.env.example
```

to:

```text
.env
```

Then replace the example Django secret with a secure local value.

Example configuration:

```text
DJANGO_SECRET_KEY=your-secure-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

AI_PROVIDER=openai
AI_API_KEY=
AI_MODEL=
```

Do not commit `.env`.

---

## 5. Create the Database

Run:

```bash
python manage.py migrate
```

This creates the local SQLite schema and also loads the approved Harbor & Pine FAQ dataset through the project's data migration.

---

## 6. Import the Product Catalogue

```bash
python manage.py import_products
```

The command uses:

```text
data/products.csv
```

by default.

---

## 7. Import Mock Orders

```bash
python manage.py import_orders
```

The command uses:

```text
data/orders.csv
```

by default.

---

## 8. Create an Administrator Account

```bash
python manage.py createsuperuser
```

Follow the terminal prompts.

This account can be used to access:

```text
/admin/
```

and administer the local demonstration environment.

---

# Knowledge Base Setup

Because uploaded runtime media is intentionally excluded from Git, a fresh clone must register the tracked source PDF with Django.

Start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/admin/
```

Sign in with the superuser account.

Go to **Knowledge Documents** and create a new document using:

```text
Title:
Harbor & Pine Living Customer Support Knowledge Base

Version:
1.0

Status:
Active

Effective date:
2026-07-01

Review date:
2026-10-01

Owner:
Support Operations Manager
```

Upload:

```text
data/knowledge/07_Harbor_and_Pine_Mock_Knowledge_Base.pdf
```

Save the document.

Then select the document in Django Admin and run:

```text
Index or re-index selected active PDFs
```

The system will extract the PDF and create searchable knowledge chunks.

A command-line indexing option also exists:

```bash
python manage.py index_knowledge DOCUMENT_ID
```

where `DOCUMENT_ID` is the database ID assigned to the uploaded KnowledgeDocument.

The Django Admin action is generally easier for first-time setup because it does not require manually finding the document ID.

---

# Run the Application

Start Django:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

The Harbor & Pine storefront contains the customer-facing support experience.

---

# Running Tests

Run the complete Django test suite with:

```bash
python manage.py test
```

Run Django's configuration check with:

```bash
python manage.py check
```

The latest verified development checkpoint completed:

```text
283 / 283 automated tests passed
Django system check: 0 issues
```

A focused customer-routing and orchestration suite was also verified before the final full regression run.

---

## Tested Support Scenarios

Manual and automated QA covered representative cases including:

- ordinary FAQs
- support-hours questions
- bulk-pricing information
- bulk quote requests
- trade-program questions
- trade-program leads
- delivery-address information
- delivery-address change requests
- damaged-item information
- active damage reports
- privacy-policy information
- personal-data deletion requests
- human-support requests
- product enquiries
- order-related workflows
- fallback and unanswered questions
- neighboring-intent routing

---

# Security and Privacy Design

The project includes several basic safeguards appropriate to its portfolio scope:

- Django secret key stored outside source control
- environment-controlled `DEBUG`
- environment-controlled allowed hosts
- Django authentication for staff interfaces
- CSRF middleware
- Django password validators
- sensitive runtime files excluded from Git
- real customer data excluded from the public repository
- synthetic portfolio datasets used instead
- no collection of full payment-card credentials through chat
- controlled routing for privacy and sensitive-support requests

This repository should not be interpreted as a production compliance certification.

A real client deployment would require additional infrastructure, security review, operational policies, access controls, backups, monitoring, and client-specific compliance requirements.

---

# What Is Mocked

The following components intentionally use synthetic or simulated data:

- Harbor & Pine Living company
- product catalogue
- customer records
- order records
- tracking information
- knowledge-base content
- FAQs
- support conversations used during testing
- leads and human-support requests created during demonstrations

No real Harbor & Pine business or customer data exists.

---

# Current Integration Boundaries

This portfolio repository does **not** claim live integration with:

- Shopify
- WooCommerce
- Amazon
- payment gateways
- shipping carriers
- CRM platforms
- WhatsApp
- SMS providers
- email providers
- live production customer databases
- live external AI/LLM services

The architecture is intended to provide a foundation for such integrations in a real client implementation.

---

# Potential Client Extensions

A production client version could be extended with:

- Shopify or WooCommerce APIs
- real order-management integration
- CRM synchronization
- email notifications
- SMS or WhatsApp support
- ticketing-system integration
- live LLM provider integration
- role-based staff permissions
- production database infrastructure
- cloud file storage
- monitoring and logging
- deployment pipelines
- production security hardening
- analytics and reporting
- business-specific escalation rules

---

# Project Purpose

This project was built as a **client-ready practice system** for AI and workflow automation freelancing.

Its purpose is to demonstrate the ability to design more than a basic chatbot by combining:

- customer experience
- controlled automation
- structured business data
- retrieval
- operational workflows
- human escalation
- owner/staff visibility
- validation
- testing
- security-conscious design
- integration-ready architecture

---

## Repository

GitHub:

```text
https://github.com/sobangrewal479/ai-customer-support-automation-system
```

---

## Author

**Soban Grewal**

AI Customer Support & Workflow Automation Portfolio Project