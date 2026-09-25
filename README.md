# Policy Impact Intelligence

An evidence-grounded government analyst workspace that brings policy documents, public feedback, and news coverage into one place for transparent policy analysis.

Built for the **Microsoft + CCI Innovation Challenge for Virginia, September 2026**.

## The Problem

Policy analysis often requires working across long government documents, thousands of public comments, and separate news coverage.

Important information can be difficult to compare, and it can be unclear whether a statement comes from an official policy document, public opinion, journalism, or an AI-generated interpretation.

## The Solution

**Policy Impact Intelligence** brings these sources together and clearly separates them by provenance.

The workspace helps an analyst:

* Understand what a policy actually says
* Compare proposed and final versions
* Analyze public feedback
* Review relevant news coverage
* Identify affected stakeholder groups
* See where sources align or differ
* Track uncertainties and source limitations
* Search across the collected evidence
* Export an analyst briefing
* Explore hypothetical policies without presenting them as real-world evidence

The system is designed to **support analysts, not make policy decisions for them**.

---

## Current Demo

The demo uses the **FTC Non-Compete Clause Rule** as a real policy example.

The application brings together:

* The 2023 proposed rule
* The 2024 final rule
* Public comments from Regulations.gov
* News coverage related to the rule
* AI-generated analysis grounded in those sources

The public feedback analysis uses a **sample of 50 comments from a docket containing 20,697 comments**. The sample is explicitly presented as a sample and is not treated as representative of all commenters.

---

## Key Features

### Policy Overview

A central view of the selected policy showing:

* Current policy status
* Key policy changes
* Stakeholder groups
* Definitions
* Key findings
* Uncertainties and limitations
* Source provenance

### Policy Comparison

Compare the proposed and final versions of a policy.

For the FTC example, the comparison identifies changes including:

* A senior executive exemption
* A notice requirement
* Changes to the employer definition
* Changes to the definition of a non-compete

### Public Feedback

Analyze public comments and organize them into:

* Recurring themes
* Viewpoints
* Affected groups
* Evidence
* Limitations

The application clearly identifies public comments as **Public Opinion**, separate from official policy language.

### News Coverage

Review collected news coverage related to the policy.

News content is presented as **Factual Reporting** and kept separate from official policy documents and public opinion.

### Analyst Briefing

Combines the available policy, public feedback, and news analysis into one briefing containing:

* Executive summary
* Policy context
* Key policy changes
* Public feedback
* News coverage
* Stakeholders
* Areas of alignment
* Areas of difference
* Uncertainties and limitations
* Sources

### Evidence & Provenance

The application distinguishes between:

| Source type                  | Meaning                                        |
| ---------------------------- | ---------------------------------------------- |
| **Official Policy Language** | Information from government policy documents   |
| **Public Opinion**           | Information from public comments               |
| **Factual Reporting**        | Information from collected news coverage       |
| **AI Interpretation**        | Analysis generated from the available evidence |

Where possible, findings include the underlying source, excerpt, and link so an analyst can verify the information.

### Search Evidence

Search across the processed policy, feedback, news, comparison, and briefing data.

Search results show their provenance and source information rather than presenting the search as a chatbot response.

### Export

Export the analyst briefing as:

* PDF
* JSON

The PDF includes source/provenance information and a responsible-use disclaimer.

### Hypothetical Policy Analysis

Analysts can enter a hypothetical policy and receive a structured AI analysis.

Hypothetical results are clearly labeled and are **not presented as real public sentiment or factual reporting**.

The analysis also identifies evidence that would need to be collected before making real-world conclusions.

### Policy Selection & Data Refresh

The application supports selecting the analyzed policy and checking for updated news data.

The refresh system can update the news analysis and analyst briefing when new source data is available.

---

## How It Works

```text
Government Policy Documents
          │
          ▼
   Federal Register
          │
          ├──────────────┐
          ▼              ▼
   Policy Analysis   Policy Comparison
          │
          │
Public Comments ──► Comment Analysis
          │
          │
News Sources ─────► News Analysis
          │
          └──────────────┐
                         ▼
                 Analyst Briefing
                         │
                         ▼
              Next.js + FastAPI UI
```

The application uses preprocessed source data for the main dashboard and Azure AI Foundry for AI-generated analysis.

---

## Data Sources

### Federal Register

Used for official proposed and final policy documents.

### Regulations.gov

Used for public comments associated with the policy docket.

### Google News RSS

Used to collect relevant news articles for the news analysis pipeline.

The application does not treat these sources as interchangeable. Each source type is presented separately so analysts can distinguish official policy language, public opinion, factual reporting, and AI interpretation.

---

## Technology

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* React

### Backend

* Python
* FastAPI

### AI

* Microsoft Azure AI Foundry
* OpenAI GPT-4o

### Data

* Federal Register
* Regulations.gov
* Google News RSS

### Other

* ReportLab for PDF export
* Git / GitHub

---

## Responsible AI

Policy Impact Intelligence is designed to make the boundary between evidence and AI interpretation visible.

The application:

* Labels AI-generated interpretation
* Keeps official policy language separate from public opinion
* Keeps news reporting separate from AI analysis
* Identifies uncertainties and source limitations
* Does not present hypothetical policies as real-world evidence
* Does not treat a limited comment sample as the complete public view
* Provides source information for verification
* Keeps final policy decisions with human analysts

### Current Limitations

The current demo has several limitations:

* Public feedback analysis uses a sample of 50 comments from a 20,697-comment docket.
* The sample may not represent the full population of commenters.
* News analysis uses the articles collected by the implemented news pipeline.
* Some source URLs may redirect through the news aggregation source.
* Policy comparison uses extracted sections of the full documents rather than reproducing every section.
* AI-generated analysis can contain errors and should be checked against the underlying sources.
* The hypothetical analysis does not represent actual public sentiment or real-world reporting.

---

## Project Structure

```text
policy-impact-intelligence/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── (dashboard)/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── scripts/
│   │   ├── fetch_federal_register.py
│   │   ├── fetch_comments.py
│   │   ├── fetch_news.py
│   │   ├── analyze_policy.py
│   │   ├── analyze_comments.py
│   │   ├── analyze_news.py
│   │   ├── analyze_comparison.py
│   │   └── analyze_briefing.py
│   └── requirements.txt
│
├── data/
│   └── processed/
│       ├── policy_summary.json
│       ├── comments_analysis.json
│       ├── news_analysis.json
│       ├── comparison_analysis.json
│       ├── briefing_analysis.json
│       └── data_status.json
│
├── .env.example
└── README.md
```

---

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/amahad0407/policy-impact-intelligence.git
cd policy-impact-intelligence
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Add the required credentials to `.env`.

**Do not commit `.env` or any API keys to GitHub.**

### 3. Install the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Install and start the frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

The FastAPI documentation will be available at:

```text
http://localhost:8000/docs
```

---

## Hackathon

**Microsoft + CCI Innovation Challenge for Virginia**

**Challenge:** Policy and Public Sentiment Analyst

**Project:** Policy Impact Intelligence

The goal is to help government analysts work with policy documents, public feedback, and news coverage while keeping evidence and AI interpretation clearly separated.

---

## Repository

GitHub:

https://github.com/amahad0407/policy-impact-intelligence

````

**One important thing:** I intentionally did **not** include Azure AI Search, Prompt Flow, or Bing News API because those aren't part of your current implementation.

### Now do this

Replace the contents of your local `README.md` with the version above, then run:

```bash
git add README.md
git commit -m "Update project README"
git push
````

After that, **don't change the code anymore** unless we find an actual bug. The next major task should be the **PowerPoint**.
