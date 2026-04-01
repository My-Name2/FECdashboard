import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(
    page_title="FEC Explorer",
    page_icon="🏛️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0f0f0f !important;
    color: #e8e8e8 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {
    background-color: #141414 !important;
    border-right: 1px solid #2a2a2a !important;
}
input, textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-baseweb="base-input"],
[data-baseweb="input"] > div {
    background-color: #1e1e1e !important;
    color: #e8e8e8 !important;
    border-color: #333 !important;
}
[data-baseweb="select"] > div,
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"] {
    background-color: #1e1e1e !important;
    color: #e8e8e8 !important;
    border-color: #333 !important;
}
[role="option"], li[role="option"] {
    background-color: #1e1e1e !important;
    color: #e8e8e8 !important;
}
[role="option"]:hover {
    background-color: #2a2a2a !important;
}
label, p, span,
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p {
    color: #ccc !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
h1, h2, h3, h4 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #e8e8e8 !important;
}
[data-testid="stButton"] button {
    background-color: #c8f542 !important;
    color: #0f0f0f !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    border: none !important;
    letter-spacing: 1px !important;
}
[data-testid="stButton"] button:hover {
    background-color: #aed438 !important;
    color: #0f0f0f !important;
}
[data-testid="metric-container"] {
    background-color: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-left: 3px solid #c8f542 !important;
    padding: 14px !important;
    border-radius: 2px !important;
}
[data-testid="stMetricValue"] {
    color: #c8f542 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.4rem !important;
}
[data-testid="stMetricLabel"] p {
    color: #666 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #2a2a2a !important;
}
[data-testid="stAlert"] {
    background-color: #1a1a1a !important;
    border-color: #333 !important;
    color: #ccc !important;
}
hr { border-color: #2a2a2a !important; }
[data-testid="stCaptionContainer"] p { color: #555 !important; }
[data-baseweb="tag"] {
    background-color: #2a2a2a !important;
    color: #c8f542 !important;
}
[data-testid="stRadio"] label { color: #ccc !important; }
[data-testid="stNumberInput"] button {
    background-color: #2a2a2a !important;
    color: #e8e8e8 !important;
    border-color: #333 !important;
}
</style>
""", unsafe_allow_html=True)

# also write a .streamlit/config.toml so the theme is set at the app level
import os, pathlib
cfg_dir = pathlib.Path(".streamlit")
cfg_dir.mkdir(exist_ok=True)
cfg_path = cfg_dir / "config.toml"
if not cfg_path.exists():
    cfg_path.write_text("""
[theme]
base = "dark"
backgroundColor = "#0f0f0f"
secondaryBackgroundColor = "#141414"
textColor = "#e8e8e8"
primaryColor = "#c8f542"
font = "monospace"
""")

BASE_URL = 'https://api.open.fec.gov/v1'

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## 🏛️ FEC Explorer")
    st.divider()

    api_key = st.text_input(
        "FEC API Key",
        type="password",
        help="Get a free key at api.data.gov/signup — 1,000 req/hr vs 30 for DEMO_KEY",
        placeholder="Paste your key here...",
    )
    if not api_key:
        api_key = "DEMO_KEY"
        st.caption("⚠ DEMO_KEY active (30 req/hr)")
    else:
        st.caption("✓ Custom key active")

    st.divider()
    mode = st.radio(
        "Mode",
        ["Organization Directory", "Individual Donors List", "Top Committees & Candidates", "Committee Donor Drill-Down", "Candidate Lookup"],
    )


# ─────────────────────────────────────────────
# MODE 0: ORGANIZATION DIRECTORY
# ─────────────────────────────────────────────
ORG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ListofOrganizations.xlsx")

@st.cache_data
def load_org_data():
    df = pd.read_excel(ORG_FILE, dtype=str)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=['CMTE_ID']).reset_index(drop=True)
    df['CMTE_ID'] = df['CMTE_ID'].str.strip()
    return df

if mode == "Organization Directory":
    st.markdown("## Organization Directory")
    st.divider()
    st.caption(f"Local committee database — {len(load_org_data()):,} organizations")

    org_df = load_org_data()

    # --- SEARCH + FILTERS ---
    col1, col2 = st.columns([3, 1])
    with col1:
        q = st.text_input("Search", placeholder="Name, connected org, candidate ID, city...")
    with col2:
        zip_filter = st.text_input("Zipcode", placeholder="e.g. 90210")

    col3, col4, col5 = st.columns(3)
    with col3:
        states = ["All"] + sorted(org_df["State"].dropna().unique().tolist())
        state_filter = st.selectbox("State", states)
    with col4:
        types = ["All"] + sorted(org_df["Committee type"].dropna().unique().tolist())
        type_filter = st.selectbox("Committee type", types)
    with col5:
        parties = ["All"] + sorted(org_df["Committee party"].dropna().unique().tolist())
        party_filter = st.selectbox("Party", parties)

    # apply filters
    view = org_df.copy()
    if q:
        q_lower = q.lower()
        mask = (
            view["Committee Name"].str.lower().str.contains(q_lower, na=False) |
            view["CMTE_ID"].str.lower().str.contains(q_lower, na=False) |
            view["Connected organization's name"].str.lower().str.contains(q_lower, na=False) |
            view["Candidate Identification"].str.lower().str.contains(q_lower, na=False) |
            view["City or Town"].str.lower().str.contains(q_lower, na=False)
        )
        view = view[mask]
    if zip_filter.strip():
        view = view[view["Zipcode"].str.startswith(zip_filter.strip(), na=False)]
    if state_filter != "All":
        view = view[view["State"] == state_filter]
    if type_filter != "All":
        view = view[view["Committee type"] == type_filter]
    if party_filter != "All":
        view = view[view["Committee party"] == party_filter]

    st.caption(f"{len(view):,} results")

    # show all columns
    st.dataframe(view.reset_index(drop=True), use_container_width=True, height=500)

    # --- DRILL-THROUGH ---
    st.divider()
    st.markdown("#### Drill into a committee")
    selected_id = st.text_input("Paste a CMTE_ID from the table above to pull its donors", placeholder="e.g. C00478107")
    if selected_id:
        match = org_df[org_df["CMTE_ID"] == selected_id.strip().upper()]
        if not match.empty:
            row = match.iloc[0]
            st.success(f"**{row['Committee Name']}** — switch to *Committee Donor Drill-Down* and paste `{row['CMTE_ID']}` to pull donors.")
        else:
            st.warning("ID not found in local directory.")

# ─────────────────────────────────────────────
# MODE: INDIVIDUAL DONORS LIST
# ─────────────────────────────────────────────
elif mode == "Individual Donors List":
    st.markdown("## Individual Donors List (2023–2026)")
    st.divider()

    import glob

    @st.cache_data
    def load_donor_parts():
        base = os.path.dirname(os.path.abspath(__file__))
        files = sorted(glob.glob(os.path.join(base, "part_*.csv")))
        if not files:
            return None, []
        dfs = []
        for f in files:
            df = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
            df.columns = df.columns.str.strip()
            dfs.append(df)
        combined = pd.concat(dfs, ignore_index=True)
        combined["TRANSACTION_AMOUNT"] = pd.to_numeric(combined["TRANSACTION_AMOUNT"], errors="coerce")
        combined["TRANSACTION_DATE"]   = pd.to_datetime(combined["TRANSACTION_DATE"], format="%m%d%Y", errors="coerce")
        return combined, [os.path.basename(f) for f in files]

    donors, loaded_files = load_donor_parts()

    if donors is None:
        st.warning("No part_*.csv files found in the app directory. Add them to the repo root.")
    else:
        st.caption(f"{len(donors):,} records from {len(loaded_files)} files: {', '.join(loaded_files)}")

        # --- FILTERS ---
        st.markdown("#### Filter")
        col1, col2, col3 = st.columns(3)
        with col1:
            name_q = st.text_input("Donor name", placeholder="e.g. SMITH, JOHN")
        with col2:
            employer_q = st.text_input("Employer", placeholder="e.g. GOOGLE")
        with col3:
            occupation_q = st.text_input("Occupation", placeholder="e.g. ATTORNEY")

        col4, col5, col6, col7 = st.columns(4)
        with col4:
            cmte_q = st.text_input("Committee ID", placeholder="e.g. C00401224")
        with col5:
            zip_q = st.text_input("Zipcode prefix", placeholder="e.g. 9021")
        with col6:
            states_d = ["All"] + sorted(donors["STATE"].dropna().unique().tolist())
            state_d = st.selectbox("State", states_d, key="donor_state")
        with col7:
            min_amt = st.number_input("Min amount ($)", value=0, step=100)

        # apply filters
        view = donors.copy()
        if name_q:
            view = view[view["NAME"].str.contains(name_q, case=False, na=False)]
        if employer_q:
            view = view[view["EMPLOYER"].str.contains(employer_q, case=False, na=False)]
        if occupation_q:
            view = view[view["OCCUPATION"].str.contains(occupation_q, case=False, na=False)]
        if cmte_q:
            view = view[view["CMTE_ID"].str.contains(cmte_q, case=False, na=False)]
        if zip_q.strip():
            view = view[view["ZIPCODE"].str.startswith(zip_q.strip(), na=False)]
        if state_d != "All":
            view = view[view["STATE"] == state_d]
        if min_amt > 0:
            view = view[view["TRANSACTION_AMOUNT"] >= min_amt]

        view = view.sort_values("TRANSACTION_AMOUNT", ascending=False).reset_index(drop=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Records",       f"{len(view):,}")
        c2.metric("Total $",       f"${view['TRANSACTION_AMOUNT'].sum():,.0f}")
        c3.metric("Unique Donors", f"{view['NAME'].nunique():,}")
        c4.metric("Median Gift",   f"${view['TRANSACTION_AMOUNT'].median():,.0f}")

        st.divider()

        DISPLAY_LIMIT = 500000
        if len(view) > DISPLAY_LIMIT:
            st.caption(f"Showing top {DISPLAY_LIMIT:,} of {len(view):,} matching records sorted by amount. Narrow your filters to see more.")
        st.dataframe(view.head(DISPLAY_LIMIT), use_container_width=True, height=600)

# ─────────────────────────────────────────────
# MODE 1
# ─────────────────────────────────────────────
elif mode == "Top Committees & Candidates":
    st.markdown("## Top Committees & Candidates by Receipts")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        cycle = st.selectbox("Election Cycle", [2026, 2024, 2022, 2020], index=1)
    with col2:
        top_n = st.slider("Results to fetch", 50, 500, 200, step=50)
    with col3:
        search_query = st.text_input("Filter by name", placeholder="e.g. Trump, DNC, AIPAC...")

    run = st.button("FETCH DATA", use_container_width=True)

    if run:
        def fetch_pages(endpoint, params, n):
            results, page = [], 1
            bar = st.progress(0, text="Fetching...")
            while len(results) < n:
                r = requests.get(f'{BASE_URL}{endpoint}', params={**params, 'page': page})
                r.raise_for_status()
                batch = r.json().get('results', [])
                if not batch:
                    break
                results.extend(batch)
                bar.progress(min(len(results) / n, 1.0), text=f"{len(results)} records")
                page += 1
                time.sleep(0.2)
            bar.empty()
            return results[:n]

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
            cand_df['entity']              = 'Candidate'
            cand_df['committee_id']        = cand_df.get('candidate_id',  pd.Series(dtype=str))
            cand_df['committee_type_full'] = cand_df.get('office_full',   pd.Series(dtype=str))

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
        view = combined[combined['name'].str.contains(search_query, case=False, na=False)] if search_query else combined

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Rows",      f"{len(view):,}")
        c2.metric("Total Receipts",  f"${view['receipts'].sum():,.0f}")
        c3.metric("Total Disbursed", f"${view['disbursements'].sum():,.0f}")
        c4.metric("Median Receipts", f"${view['receipts'].median():,.0f}")

        if search_query:
            st.caption(f"{len(view):,} results for '{search_query}'")

        st.divider()
        display_cols = ['committee_id', 'entity', 'name', 'committee_type_full',
                        'party_full', 'state', 'receipts', 'disbursements',
                        'cash_on_hand', 'burn_rate', 'coverage_end_date']
        display_cols = [c for c in display_cols if c in view.columns]
        st.dataframe(view[display_cols], use_container_width=True, height=600)

# ─────────────────────────────────────────────
# MODE 3: CANDIDATE LOOKUP
# ─────────────────────────────────────────────
elif mode == "Candidate Lookup":
    st.markdown("## Candidate → Committee Lookup")
    st.divider()
    st.caption("Paste a candidate ID (starts with H, S, or P) to find their linked committee IDs.")

    cand_id_input = st.text_input("Candidate ID", placeholder="e.g. S2HI00106")
    lookup_btn    = st.button("LOOK UP COMMITTEES", use_container_width=True)

    if lookup_btn:
        if not cand_id_input:
            st.warning("Enter a candidate ID first.")
        else:
            try:
                r = requests.get(f'{BASE_URL}/candidate/{cand_id_input.strip()}/committees/', params={
                    'api_key': api_key, 'per_page': 20,
                })
                r.raise_for_status()
                results = r.json().get('results', [])
                if not results:
                    st.warning("No committees found for that candidate ID.")
                else:
                    # also fetch candidate name
                    rc = requests.get(f'{BASE_URL}/candidate/{cand_id_input.strip()}/', params={'api_key': api_key})
                    cand_name = rc.json()['results'][0]['name'] if rc.ok and rc.json().get('results') else cand_id_input

                    st.success(f"**{cand_name}** — {len(results)} committee(s) found")
                    rows = []
                    for c in results:
                        rows.append({
                            'committee_id':   c.get('committee_id'),
                            'name':           c.get('name'),
                            'designation':    c.get('designation_full'),
                            'type':           c.get('committee_type_full'),
                            'party':          c.get('party_full') or '—',
                            'first_filed':    c.get('first_file_date') or '—',
                        })
                    df_comms = pd.DataFrame(rows)
                    st.dataframe(df_comms, use_container_width=True)

                    principal = [r for r in results if r.get('designation') == 'P']
                    if principal:
                        cid = principal[0]['committee_id']
                        st.info(f"Principal campaign committee: **{cid}** — copy this into the Donor Drill-Down tab.")
                    else:
                        st.caption("No principal campaign committee found. Use any C-prefixed ID above in the Donor Drill-Down tab.")

            except requests.HTTPError as e:
                st.error(f"API error: {e}")

# ─────────────────────────────────────────────
# MODE 2
# ─────────────────────────────────────────────
else:
    st.markdown("## Committee Donor Drill-Down")
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        committee_id_raw = st.text_input("Committee or Candidate ID", placeholder="e.g. C00815753 or S2HI00106")
    with col2:
        cycles = st.multiselect("Cycles", [2026, 2024, 2022, 2020], default=[2026, 2024, 2022])
    with col3:
        min_donation = st.number_input("Min donation ($)", value=200, step=100)
    with col4:
        max_records = st.number_input("Max records per cycle", value=1000, step=100)

    search_query = st.text_input("Filter donors", placeholder="Name, employer, or occupation...")
    run2 = st.button("FETCH DONORS", use_container_width=True)

    if run2:
        if not committee_id_raw:
            st.warning("Enter a committee or candidate ID first.")
        else:
            try:
                raw_id = committee_id_raw.strip().upper()

                # Auto-resolve candidate ID -> principal committee ID
                if raw_id.startswith(('H', 'S', 'P')):
                    with st.spinner(f"Resolving candidate {raw_id} to committee..."):
                        r = requests.get(f'{BASE_URL}/candidate/{raw_id}/committees/', params={
                            'api_key': api_key, 'per_page': 20,
                        })
                        r.raise_for_status()
                        comms = r.json().get('results', [])
                        principal = [c for c in comms if c.get('designation') == 'P']
                        chosen = principal[0] if principal else (comms[0] if comms else None)
                        if not chosen:
                            st.error(f"No committees found for candidate {raw_id}.")
                            st.stop()
                        committee_id = chosen['committee_id']
                        st.info(f"Candidate {raw_id} → resolved to committee **{committee_id}** ({chosen['name']})")
                else:
                    committee_id = raw_id

                r = requests.get(f'{BASE_URL}/committees/', params={
                    'api_key': api_key, 'committee_id': committee_id, 'per_page': 1
                })
                r.raise_for_status()
                res = r.json().get('results', [])
                comm_name = res[0]['name'] if res else committee_id
                st.info(f"**{comm_name}** ({committee_id})")

                def pull_cycle(cycle, max_rec):
                    records, last_index, last_date = [], None, None
                    while len(records) < max_rec:
                        params = {
                            'api_key':                     api_key,
                            'committee_id':                committee_id,
                            'two_year_transaction_period': cycle,
                            'min_amount':                  min_donation,
                            'entity_type':                 'IND',
                            'sort':                        '-contribution_receipt_amount',
                            'per_page':                    100,
                            'sort_hide_null':              True,
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
        agg = st.session_state['agg']
        df  = st.session_state['df_raw']

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
        c1.metric("Unique Donors",  f"{len(view):,}")
        c2.metric("Total Raised",   f"${view['total_given'].sum():,.0f}")
        c3.metric("Median Gift",    f"${df['contribution_receipt_amount'].median():,.0f}")
        c4.metric("Repeat Donors",  f"{view['repeat_donor'].sum():,}")
        c5.metric("Multi-Cycle",    f"{view['multi_cycle'].sum():,}")

        if search_query:
            st.caption(f"{len(view):,} donors matching '{search_query}'")

        st.divider()
        display_cols = ['contributor_name', 'total_given', 'num_donations', 'largest_gift',
                        'cycles_active', 'employer', 'occupation', 'state', 'city', 'last_donation']
        display_cols = [c for c in display_cols if c in view.columns]
        st.dataframe(view[display_cols], use_container_width=True, height=600)
