import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(
    page_title="FEC Explorer",
    page_icon="🏛️",
    layout="wide",
)

# --- STYLING ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
}
.stApp {
    background-color: #0d0d0d;
    color: #e8e8e8;
}
section[data-testid="stSidebar"] {
    background-color: #111 !important;
    border-right: 1px solid #2a2a2a;
}
.metric-box {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #c8f542;
    padding: 14px 18px;
    border-radius: 2px;
    margin-bottom: 8px;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #c8f542;
}
.tag {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 2px;
    margin-right: 4px;
    background: #1e1e1e;
    border: 1px solid #333;
    color: #aaa;
}
.header-bar {
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 12px;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

BASE_URL = 'https://api.open.fec.gov/v1'

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🏛️ FEC Explorer")
    st.markdown("---")

    api_key = st.text_input(
        "FEC API Key",
        type="password",
        help="Get a free key at api.data.gov/signup — 1,000 req/hr vs 30 for DEMO_KEY",
        placeholder="Paste your key here...",
    )
    if not api_key:
        api_key = "DEMO_KEY"
        st.caption("Using DEMO_KEY (30 req/hr). Add your key above for 1,000 req/hr.")
    else:
        st.success("Using your API key", icon="✓")

    st.markdown("---")
    mode = st.radio(
        "Mode",
        ["Top Committees & Candidates", "Committee Donor Drill-Down"],
        label_visibility="collapsed",
    )

# ─────────────────────────────────────────────
# MODE 1: TOP COMMITTEES + CANDIDATES
# ─────────────────────────────────────────────
if mode == "Top Committees & Candidates":
    st.markdown('<div class="header-bar"><h2>Top Committees & Candidates by Receipts</h2></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        cycle = st.selectbox("Election Cycle", [2026, 2024, 2022, 2020], index=1)
    with col2:
        top_n = st.slider("Results to fetch", 50, 500, 200, step=50)
    with col3:
        search_query = st.text_input("🔍 Filter by name", placeholder="e.g. Trump, DNC, AIPAC...")

    run = st.button("Fetch Data", type="primary", use_container_width=True)

    if run:
        def fetch_pages(endpoint, params, top_n):
            results, page = [], 1
            bar = st.progress(0, text=f"Fetching {endpoint}...")
            while len(results) < top_n:
                r = requests.get(f'{BASE_URL}{endpoint}', params={**params, 'page': page})
                r.raise_for_status()
                batch = r.json().get('results', [])
                if not batch:
                    break
                results.extend(batch)
                bar.progress(min(len(results) / top_n, 1.0), text=f"{endpoint}: {len(results)} records")
                page += 1
                time.sleep(0.2)
            bar.empty()
            return results[:top_n]

        with st.spinner("Pulling data..."):
            try:
                comm_results = fetch_pages('/totals/committees/', {
                    'api_key': api_key, 'cycle': cycle,
                    'sort': '-receipts', 'sort_hide_null': True, 'per_page': 100,
                }, top_n)
                comm_df = pd.json_normalize(comm_results)
                comm_df = comm_df.rename(columns={'committee_name': 'name'})
                comm_df['entity'] = 'Committee'

                cand_results = fetch_pages('/candidates/totals/', {
                    'api_key': api_key, 'cycle': cycle,
                    'sort': '-receipts', 'sort_hide_null': True, 'per_page': 100,
                }, top_n)
                cand_df = pd.json_normalize(cand_results)
                cand_df['entity'] = 'Candidate'
                cand_df['committee_id']        = cand_df.get('candidate_id',   pd.Series(dtype=str))
                cand_df['committee_type_full'] = cand_df.get('office_full',    pd.Series(dtype=str))

                COMMON = ['entity', 'committee_id', 'name', 'committee_type_full',
                          'party_full', 'state', 'receipts', 'disbursements', 'coverage_end_date']

                def trim(df):
                    return df[[c for c in COMMON if c in df.columns]].copy()

                combined = pd.concat([trim(comm_df), trim(cand_df)], ignore_index=True)
                combined['receipts']      = pd.to_numeric(combined['receipts'],      errors='coerce')
                combined['disbursements'] = pd.to_numeric(combined['disbursements'], errors='coerce')
                combined['cash_on_hand']  = combined['receipts'] - combined['disbursements']
                combined['burn_rate']     = (combined['disbursements'] / combined['receipts'] * 100).round(1)
                combined = (combined
                    .drop_duplicates(subset='committee_id')
                    .sort_values('receipts', ascending=False)
                    .reset_index(drop=True))
                combined.index += 1

                st.session_state['combined'] = combined

            except requests.HTTPError as e:
                st.error(f"API error: {e}")

    if 'combined' in st.session_state:
        combined = st.session_state['combined']

        # apply search filter
        if search_query:
            mask = combined['name'].str.contains(search_query, case=False, na=False)
            view = combined[mask]
        else:
            view = combined

        # summary metrics
        c1, c2, c3, c4 = st.columns(4)
        metrics = [
            ("Total Rows", f"{len(view):,}"),
            ("Total Receipts", f"${view['receipts'].sum():,.0f}"),
            ("Total Disbursed", f"${view['disbursements'].sum():,.0f}"),
            ("Median Receipts", f"${view['receipts'].median():,.0f}"),
        ]
        for col, (label, val) in zip([c1,c2,c3,c4], metrics):
            with col:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{val}</div>
                </div>""", unsafe_allow_html=True)

        if search_query:
            st.caption(f"Showing {len(view):,} results matching '{search_query}'")

        display_cols = ['committee_id', 'entity', 'name', 'committee_type_full',
                        'party_full', 'state', 'receipts', 'disbursements',
                        'cash_on_hand', 'burn_rate', 'coverage_end_date']
        display_cols = [c for c in display_cols if c in view.columns]
        st.dataframe(view[display_cols], use_container_width=True, height=600)

# ─────────────────────────────────────────────
# MODE 2: COMMITTEE DONOR DRILL-DOWN
# ─────────────────────────────────────────────
else:
    st.markdown('<div class="header-bar"><h2>Committee Donor Drill-Down</h2></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        committee_id = st.text_input("Committee ID", placeholder="e.g. C00815753")
    with col2:
        cycles = st.multiselect("Cycles", [2026, 2024, 2022, 2020], default=[2026, 2024, 2022])
    with col3:
        min_donation = st.number_input("Min donation ($)", value=200, step=100)
    with col4:
        max_records = st.number_input("Max records per cycle", value=1000, step=100)

    search_query = st.text_input("🔍 Filter donors by name, employer, or occupation", placeholder="e.g. Goldman, Retired, Smith...")

    run2 = st.button("Fetch Donors", type="primary", use_container_width=True)

    if run2:
        if not committee_id:
            st.warning("Enter a committee ID first.")
        else:
            try:
                r = requests.get(f'{BASE_URL}/committees/', params={
                    'api_key': api_key, 'committee_id': committee_id, 'per_page': 1
                })
                r.raise_for_status()
                res = r.json().get('results', [])
                comm_name = res[0]['name'] if res else committee_id
                st.info(f"Committee: **{comm_name}** ({committee_id})")

                def pull_cycle(cycle, max_rec):
                    records, last_index, last_date = [], None, None
                    while len(records) < max_rec:
                        params = {
                            'api_key': api_key,
                            'committee_id': committee_id,
                            'two_year_transaction_period': cycle,
                            'min_amount': min_donation,
                            'entity_type': 'IND',
                            'sort': '-contribution_receipt_amount',
                            'per_page': 100,
                            'sort_hide_null': True,
                        }
                        if last_index: params['last_index']                       = last_index
                        if last_date:  params['last_contribution_receipt_amount'] = last_date
                        r = requests.get(f'{BASE_URL}/schedules/schedule_a/', params=params)
                        r.raise_for_status()
                        data  = r.json()
                        batch = data.get('results', [])
                        if not batch:
                            break
                        for rec in batch:
                            rec['_cycle'] = cycle
                        records.extend(batch)
                        pg         = data.get('pagination', {}).get('last_indexes', {})
                        last_index = pg.get('last_index')
                        last_date  = pg.get('last_contribution_receipt_amount')
                        if not last_index:
                            break
                        time.sleep(0.2)
                    return records

                all_records = []
                for cyc in cycles:
                    with st.spinner(f"Pulling cycle {cyc}..."):
                        batch = pull_cycle(cyc, int(max_records))
                        all_records.extend(batch)
                        st.caption(f"Cycle {cyc}: {len(batch)} records")

                FIELDS = [
                    'contributor_name', 'contributor_city', 'contributor_state',
                    'contributor_employer', 'contributor_occupation',
                    'contribution_receipt_amount', 'contribution_receipt_date', '_cycle',
                ]
                raw   = pd.json_normalize(all_records)
                avail = [c for c in FIELDS if c in raw.columns]
                df    = raw[avail].copy()
                df['contribution_receipt_amount'] = pd.to_numeric(df['contribution_receipt_amount'], errors='coerce')
                df['contribution_receipt_date']   = pd.to_datetime(df['contribution_receipt_date'],   errors='coerce')

                agg = df.groupby('contributor_name').agg(
                    total_given    = ('contribution_receipt_amount', 'sum'),
                    num_donations  = ('contribution_receipt_amount', 'count'),
                    largest_gift   = ('contribution_receipt_amount', 'max'),
                    first_donation = ('contribution_receipt_date',   'min'),
                    last_donation  = ('contribution_receipt_date',   'max'),
                    cycles_active  = ('_cycle', lambda x: ', '.join(str(c) for c in sorted(x.unique()))),
                    employer       = ('contributor_employer',   lambda x: ', '.join(x.dropna().unique()[:2])),
                    occupation     = ('contributor_occupation', lambda x: ', '.join(x.dropna().unique()[:2])),
                    state          = ('contributor_state', lambda x: '/'.join(x.dropna().unique())),
                    city           = ('contributor_city',  lambda x: ', '.join(x.dropna().unique()[:2])),
                ).reset_index()

                agg['repeat_donor'] = agg['num_donations'] > 1
                agg['multi_cycle']  = agg['cycles_active'].str.contains(',')
                agg = agg.sort_values('total_given', ascending=False).reset_index(drop=True)
                agg.index += 1

                st.session_state['agg']       = agg
                st.session_state['df_raw']    = df
                st.session_state['comm_name'] = comm_name

            except requests.HTTPError as e:
                st.error(f"API error: {e}")

    if 'agg' in st.session_state:
        agg       = st.session_state['agg']
        df        = st.session_state['df_raw']
        comm_name = st.session_state['comm_name']

        # apply search filter
        if search_query:
            mask = (
                agg['contributor_name'].str.contains(search_query, case=False, na=False) |
                agg['employer'].str.contains(search_query, case=False, na=False) |
                agg['occupation'].str.contains(search_query, case=False, na=False)
            )
            view = agg[mask]
        else:
            view = agg

        c1, c2, c3, c4, c5 = st.columns(5)
        metrics = [
            ("Unique Donors", f"{len(view):,}"),
            ("Total Raised", f"${view['total_given'].sum():,.0f}"),
            ("Median Gift", f"${df['contribution_receipt_amount'].median():,.0f}"),
            ("Repeat Donors", f"{view['repeat_donor'].sum():,}"),
            ("Multi-Cycle", f"{view['multi_cycle'].sum():,}"),
        ]
        for col, (label, val) in zip([c1,c2,c3,c4,c5], metrics):
            with col:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{val}</div>
                </div>""", unsafe_allow_html=True)

        if search_query:
            st.caption(f"Showing {len(view):,} donors matching '{search_query}'")

        display_cols = ['contributor_name', 'total_given', 'num_donations', 'largest_gift',
                        'cycles_active', 'employer', 'occupation', 'state', 'city', 'last_donation']
        display_cols = [c for c in display_cols if c in view.columns]
        st.dataframe(view[display_cols], use_container_width=True, height=600)
