# FEC Explorer

Streamlit app for browsing FEC campaign finance data.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## API Key

Get a free key at https://api.data.gov/signup/
- DEMO_KEY: 30 req/hr (default fallback)
- Free key: 1,000 req/hr

Paste your key into the sidebar — it's never stored anywhere.

## Modes

**Top Committees & Candidates** — ranks all political entities by receipts for a given cycle. Supports plaintext name search to filter results.

**Committee Donor Drill-Down** — point at a specific committee ID, pull individual contributions across multiple cycles, aggregate by donor. Search filters across name, employer, and occupation.
