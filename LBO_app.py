import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
from LBO_engine import run_lbo_model

st.set_page_config(page_title="LBO Calculator", layout="wide")

# --- CONSOLIDATED PROFESSIONAL CSS ---
st.markdown("""
    <style>
    /* 1. THE STICKY HEADER ENGINE */
    /* This targets the specific Streamlit wrapper to allow the 'sticky' property to work */
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-header) {
        position: -webkit-sticky;
        position: sticky;
        top: 2.875rem; /* Sits exactly below the Streamlit top bar */
        z-index: 999;
        background-color: #0e1117; /* Matches main background to prevent transparency */
    }

    .sticky-header {
        border-bottom: 2px solid #29b5e8;
        padding: 10px 0px;
        width: 100%;
    }
    
    .sticky-header h1 {
        font-size: 2.2rem !important;
        margin: 0 !important;
        padding-left: 10px;
        color: white;
    }

    /* 2. TAB STYLING: High Contrast & Large Font */
    button[data-baseweb="tab"] {
        margin: 0 10px;
        height: 50px;
    }
    
    button[data-baseweb="tab"] p {
        font-size: 19px !important;
        font-weight: 600 !important;
    }

    /* Active Tab Highlight */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(41, 181, 232, 0.1) !important;
        border-radius: 8px 8px 0px 0px;
        border-bottom: 3px solid #29b5e8 !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #29b5e8 !important;
    }

    /* 3. MAIN AREA KPI CARDS */
    [data-testid="stMain"] [data-testid="stMetric"] {
        background-color: #1e2129;
        padding: 20px 25px;
        border-radius: 12px;
        border-left: 6px solid #29b5e8;
        box-shadow: 4px 4px 15px rgba(0,0,0,0.4);
        margin-bottom: 15px;
    }

    [data-testid="stMain"] [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }

    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        font-size: 13px !important; /* Slightly smaller to prevent wrapping */
        font-weight: 600 !important;
        color: #9ea1a6 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 4. SIDEBAR CLEANUP (Keep inputs simple) */
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    
    /* 5. OVERALL LAYOUT ADJUSTMENTS */
    .block-container {
        padding-top: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDER STICKY HEADER ---
st.markdown('<div class="sticky-header"><h1>🏦 Leverage Buyout Dashboard</h1></div>', unsafe_allow_html=True)

# Add a tiny vertical spacer
st.write("##")

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Model Inputs")
    
    # --- 1. TRANSACTION DETAILS ---
    with st.expander("🖊️ Transaction Details", expanded=True):
        rev_ui = st.number_input("LTM Revenue $M", min_value=0.1, value=1000.0, step=10.0)
        ebitda_ui = st.number_input("LTM EBITDA $M", min_value=0.0, value=400.0, step=10.0)
        
        # Validation Logic
        ltm_revenue = rev_ui
        ltm_ebitda = min(ebitda_ui, rev_ui)
        if ebitda_ui > rev_ui:
            st.warning(f"⚠️ EBITDA capped at Revenue (${rev_ui:,.0f})")
        
        st.caption(f"Implied Margin: {(ltm_ebitda/ltm_revenue)*100:.1f}%")
        
        # Two columns for Multiples
        col1, col2 = st.columns(2)
        entry_mult = col1.number_input("Entry EV/EBITDA", 3.0, 15.0, 7.0, 0.1)
        exit_mult = col2.number_input("Exit EV/EBITDA.", 3.0, 15.0, 8.0, 0.1)
        
        horizon = st.slider("Time Horizon (Years)", 2, 10, 5)

    # --- 2. CAPITAL STRUCTURE ---
    with st.expander("💵 Capital Structure", expanded=True):
        debt_pct = st.slider("Debt Financing (%)", 0.0, 90.0, 60.0, 5.0)
        
        col3, col4 = st.columns(2)
        int_debt = col3.number_input("Int. Debt %", 5.0, 20.0, 8.0, 0.1)
        int_cash = col4.number_input("Int. Cash %", 0.0, 5.0, 1.0, 0.1)
        col5, col6 = st.columns(2)
        cash_req = col5.number_input("Min Cash", value=50.0, step=1.0)
        fa_share = col6.number_input("Fixed A % IC", 10.0, 90.0, 70.0, 5.0)
        dvd_sweep = st.slider("Dividend Sweep (%) after Debt Repayment", 0.0, 100.0, 25.0, 5.0)
    
    # --- 3. OPERATING ASSUMPTIONS ---
    with st.expander("🏭 Operating Assumptions", expanded=True):
        col7, col8 = st.columns(2)
        growth = col7.number_input("Rev Growth %", -5.0, 20.0, 5.0, 1.0)
        margin = col8.number_input("EBITDA Margin %", 10.0, 60.0, 40.0, 1.0)
        
        tax_rate = st.slider("Tax Rate (%)", 0.0, 40.0, 30.0, 1.0)
        
        col9, col10 = st.columns(2)
        CAPEX = col9.number_input("CAPEX % Rev", 0.0, 10.0, 3.0, 0.1)
        DA = col10.number_input("D&A % Rev", 0.0, 10.0, 3.0, 0.1)
        
        WK_Inv = st.number_input("Working Capital Investment % of Rev", -5.0, 5.0, 1.0, 0.1)

    # --- RESET BUTTON ---
    st.markdown("---")
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.components.v1.html("<script>parent.window.location.reload()</script>", height=0)
        
    
# --- RUN ENGINE ---
results = run_lbo_model(
    T = horizon, Entry = entry_mult, Exit = exit_mult, LTM_EBITDA = ltm_ebitda, LTM_REVENUE = ltm_revenue,
    growth = growth, margin = margin, Tax = tax_rate, CAPEX = CAPEX, DA = DA, WK_Inv = WK_Inv,
    Cash = cash_req, Int_Cash = int_cash, Int_Debt = int_debt, Debt_pct = debt_pct, Fixed_assets_share = fa_share, Dividend_sweep = dvd_sweep
)

# --- DISPLAY ---
moic = results["Outcome"].loc["MOIC", "Value"]
irr = results["Outcome"].loc["IRR", "Value"]
entry_eq = ltm_ebitda * entry_mult * (1 - debt_pct/100)
exit_eq = results['Outcome'].loc['Equity_Exit', 'Value']
total_dividends = -results["CF"].loc["Less Dividends Paid"].sum()
total_proceeds = exit_eq + total_dividends

# --- HEADER KPI SECTION ---
header_container = st.container()
with header_container:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("MOIC", f"{moic:.2f}x")
    col2.metric("IRR", f"{irr:.2%}")
    col3.metric("Entry Equity", f"${entry_eq:,.0f}M") # Using the manual calc we set up
    col4.metric("Exit Equity + Dividends", f"${total_proceeds:,.0f}M")
    st.divider() # Creates a clean break before the tabs



# --- TAB DEFINITION WITH ICONS ---
# Using Emojis directly in the labels is the most reliable way in Streamlit
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📋 Financials", 
    "📊 Charts", 
    "🎯 Attribution", 
    "🕹️ Sensitivity", 
    "🎭 Scenarios", 
    "👮 Covenants", 
    "🔍 Reverse LBO"
])

# --- TAB 1: FINANCIAL STATEMENTS ---
with tab1:
    st.header("📋 Financials")
    
    st.subheader("Income Statement")
    st.dataframe(results["IS"].style.format("{:,.1f}"), use_container_width=True)
    
    st.subheader("Cash Flow Statement")
    st.dataframe(results["CF"].style.format("{:,.1f}"), use_container_width=True)    
    
    st.subheader("Balance Sheet")
    st.dataframe(results["BS"].style.format("{:,.1f}"), use_container_width=True)
    
# --- TAB 2: INTERACTIVE CHARTS (TRENDS) ---
with tab2:
    st.header("📊 Financial Charts")
    st.info("Select a line item from each statement to visualize its progression over the holding period.")
    
    col_is, col_cf, col_bs = st.columns(3)
    
    with col_is:
        st.subheader("Income Statement")
        is_item = st.selectbox("Select IS Line Item:", options=results["IS"].index, index=2)
        # FIX: Strip "Year " and convert to int so the X-axis sorts numerically (0, 1, 2... 10)
        is_chart_data = results["IS"].loc[[is_item]].T
        is_chart_data.index = is_chart_data.index.str.replace('Year ', '').astype(int)
        st.bar_chart(is_chart_data, color="#29b5e8")
        
    with col_cf:
        st.subheader("Cash Flow")
        cf_item = st.selectbox("Select CF Line Item:", options=results["CF"].index, index=5)
        # FIX: Same numeric conversion here
        cf_chart_data = results["CF"].loc[[cf_item]].T
        cf_chart_data.index = cf_chart_data.index.str.replace('Year ', '').astype(int)
        st.bar_chart(cf_chart_data, color="#15a0a3")
        
    with col_bs:
        st.subheader("Balance Sheet")
        bs_item = st.selectbox("Select BS Line Item:", options=results["BS"].index, index=4)
        # FIX: Same numeric conversion here
        bs_chart_data = results["BS"].loc[[bs_item]].T
        bs_chart_data.index = bs_chart_data.index.str.replace('Year ', '').astype(int)
        st.bar_chart(bs_chart_data, color="#ffd166")
        
import plotly.graph_objects as go

# --- TAB 3: RETURN ATTRIBUTION ---
with tab3:
    st.header("🎯 Performance Analysis")
    
    # 1. Prepare Data for Waterfall
    try:
        # Calculate Entry Equity manually to ensure it matches Sidebar logic
        # Formula: (EBITDA * Entry Multiple) * (1 - Debt %)
        entry_eq = ltm_ebitda * entry_mult * (1 - debt_pct/100)
        
        # Pull the rest from your engine's Outcome table
        exit_eq = results["Outcome"].loc["Equity_Exit", "Value"]
        attr_ebitda = results["Outcome"].loc["Attr: EBITDA Growth", "Value"]
        attr_mult = results["Outcome"].loc["Attr: Multiple Expansion", "Value"]
        attr_dvd = results["Outcome"].loc["Attr: Dividend Payment", "Value"]
        attr_debt = results["Outcome"].loc["Attr: Paydown Debt", "Value"]

        # 2. Create the Waterfall Chart
        fig = go.Figure(go.Waterfall(
            name="Value Creation", 
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "relative", "total"],
            x=["Entry Equity", "EBITDA Growth", "Multiple Expansion", "Dividends", "Debt Paydown", "Exit Equity"],
            textposition="outside",
            text=[f"${entry_eq:,.0f}", f"+${attr_ebitda:,.0f}", f"+${attr_mult:,.0f}", f"+${attr_dvd:,.0f}", f"+${attr_debt:,.0f}", f"${exit_eq:,.0f}"],
            y=[entry_eq, attr_ebitda, attr_mult, attr_dvd, attr_debt, 0], 
            connector={"line":{"color":"#636363"}},
            decreasing={"marker":{"color":"#f04c64"}}, # Red
            increasing={"marker":{"color":"#29b5e8"}}, # Blue
            totals={"marker":{"color":"#15a0a3"}}      # Teal
        ))

        fig.update_layout(
            title="Equity Value Creation Bridge ($)",
            showlegend=False,
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white"),
            margin=dict(t=50, b=50, l=50, r=50)
        )

        # 3. Display with Columns
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            st.subheader("Value Creation Waterfall")
            st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("Deal Summary")
            # Using your engine's results dictionary
            st.table(results["Outcome"].style.format("{:,.2f}"))

    except Exception as e:
        st.error(f"Waterfall Error: {e}. Check if 'Equity_Exit' and 'Attr:' rows exist in your engine output.")

# --- SPONSOR CASH FLOW SECTION (Properly Indented) ---
    st.divider()
    st.subheader("💰 Sponsor Cash Flow Profile")
    st.info("Visualizing the 'Money Out vs. Money In' profile of the investment.")

    # 1. Prepare Data using integers for the X-axis
    # We use a simple list of integers: [0, 1, 2, ..., horizon]
    x_axis = list(range(horizon + 1))
    spon_cf = results["Sponsor_CF"].values.flatten()
    
    # 2. Create the Bar Chart
    fig_spon = go.Figure()
    
    fig_spon.add_trace(go.Bar(
        x=x_axis,
        y=spon_cf,
        marker_color=['#ff4b4b' if val < 0 else '#29b5e8' for val in spon_cf],
        # Only show text for Year 0 and the Final Year
        text=[f"${val:,.0f}M" if val != 0 else "" for val in spon_cf],
        textposition='auto',
    ))

    # 3. Styling with Integer-Only Axis
    fig_spon.update_layout(
        height=400,
        xaxis_title="Year",
        yaxis_title="Equity Value ($M)",
        # Ensure the x-axis only shows integers and every year is marked
        xaxis=dict(
            tickmode='linear',
            tick0=0,
            dtick=1
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"),
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20)
    )
    
    # Add a zero line for visual grounding
    fig_spon.add_hline(y=0, line_color="white", line_width=1)
    
    st.plotly_chart(fig_spon, use_container_width=True)
    
        
# --- TAB 4: SENSITIVITY ANALYSIS ---
with tab4:
    st.header("🕹️ Dynamic Sensitivity Analysis")
    
    # 1. Metric Selection
    metric_choice = st.radio(
        "Select Return Metric:",
        options=["IRR", "MOIC"],
        horizontal=True,
        help="IRR (Internal Rate of Return) vs. MOIC (Multiple of Invested Capital)"
    )

    # 2. Variable Selection Logic
    sens_options = ["Revenue Growth %", "Exit Multiple", "EBITDA Margin %"]
    selection = st.multiselect(
        "Select exactly 2 variables to sensitize:",
        options=sens_options,
        default=["Revenue Growth %", "Exit Multiple"],
        max_selections=2
    )

    # --- THE FIX: Vertical spacing to push content below the multiselect warning ---
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    
    if len(selection) < 2:
        st.warning("Please select exactly 2 variables to generate the matrix.")
    else:
        # 3. Define the ranges centered around current sidebar values
        ranges = {
            "Revenue Growth %": [growth + i for i in [-2.0, -1.0, 0, 1.0, 2.0]],
            "Exit Multiple": [exit_mult + i for i in [-1.0, -0.5, 0, 0.5, 1.0]],
            "EBITDA Margin %": [margin + i for i in [-5.0, -2.5, 0, 2.5, 5.0]]
        }

        var_x = selection[0]  # Horizontal Axis
        var_y = selection[1]  # Vertical Axis
        
        # 4. Calculation Loop
        sens_results = []
        for val_y in ranges[var_y]:
            row = []
            for val_x in ranges[var_x]:
                # Map variables to their temporary values for the engine
                gr_param = val_x if var_x == "Revenue Growth %" else (val_y if var_y == "Revenue Growth %" else growth)
                ex_param = val_x if var_x == "Exit Multiple" else (val_y if var_y == "Exit Multiple" else exit_mult)
                ma_param = val_x if var_x == "EBITDA Margin %" else (val_y if var_y == "EBITDA Margin %" else margin)

                # Run the model engine (Make sure @st.cache_data is in engine.py for speed!)
                s_res = run_lbo_model(
                    T=int(horizon), Entry=entry_mult, Exit=ex_param, 
                    LTM_EBITDA=ltm_ebitda, LTM_REVENUE=ltm_revenue,
                    growth=gr_param, margin=ma_param, Tax=tax_rate, CAPEX=CAPEX, DA=DA, WK_Inv=WK_Inv,
                    Cash=cash_req, Int_Cash=int_cash, Int_Debt=int_debt, Debt_pct=debt_pct, Fixed_assets_share=fa_share, Dividend_sweep=dvd_sweep
                )
                
                # Pick the metric to display based on radio selection
                if metric_choice == "IRR":
                    row.append(s_res["Outcome"].loc["IRR", "Value"])
                else:
                    row.append(s_res["Outcome"].loc["MOIC", "Value"])
            sens_results.append(row)

        # 5. Create DataFrame
        df_sens = pd.DataFrame(
            sens_results, 
            index=[f"{val:.1f}" for val in ranges[var_y]],
            columns=[f"{val:.1f}" for val in ranges[var_x]]
        )
        
        # 6. Apply the "Corner Label" (The Blue Encircled Area)
        # This combines both variables into the top-left cell of the table
        df_sens.index.name = f"{var_y} / {var_x}" 

        # 7. Display Axis Labels and Matrix
        st.subheader(f" {metric_choice} Analysis")
        
        # Markdown clarification for absolute certainty
        st.markdown(f"""
        **Vertical Axis (Rows):** {var_y}  
        **Horizontal Axis (Columns):** {var_x}
        """)
        
        # Formatting: % for IRR, x for MOIC
        fmt = "{:.1%}" if metric_choice == "IRR" else "{:.2f}x"
        
        # Display the Heatmap with conditional formatting
        st.dataframe(
            df_sens.style.background_gradient(cmap="RdYlGn", axis=None).format(fmt),
            use_container_width=True
        )

        st.caption(f"Note: The center of the grid represents your current sidebar settings.")

# --- TAB 5: SCENARIO MANAGER ---
with tab5:
    st.header("🎭 Strategic Scenario Manager")
    st.info("Compare how the deal performs under different economic conditions without manually adjusting every slider.")
    
    # 1. Define Scenario Presets
    # These represent fixed "states of the world" to compare against your sidebar
    scenarios = {
        "Base Case": {"growth": growth, "margin": margin, "exit": exit_mult},
        "Recession (Downside)": {"growth": -2.0, "margin": margin - 5.0, "exit": entry_mult - 1.0},
        "Aggressive (Upside)": {"growth": growth + 3.0, "margin": margin + 2.5, "exit": exit_mult + 1.0}
    }
    
    selected_scen = st.selectbox("Select a Deal Scenario to Compare against Base:", options=list(scenarios.keys()))
    
    # 2. Run the "Shadow" model for the selected scenario
    s_data = scenarios[selected_scen]
    scen_results = run_lbo_model(
        T=horizon, Entry=entry_mult, Exit=s_data["exit"], 
        LTM_EBITDA=ltm_ebitda, LTM_REVENUE=ltm_revenue,
        growth=s_data["growth"], margin=s_data["margin"], 
        Tax=tax_rate, CAPEX=CAPEX, DA=DA, WK_Inv=WK_Inv,
        Cash=cash_req, Int_Cash=int_cash, Int_Debt=int_debt, 
        Debt_pct=debt_pct, Fixed_assets_share=fa_share, Dividend_sweep=dvd_sweep
    )
    
    # 3. CALCULATE DELTAS
    current_irr = results["Outcome"].loc["IRR", "Value"]
    scen_irr = scen_results["Outcome"].loc["IRR", "Value"]
    
    current_moic = results["Outcome"].loc["MOIC", "Value"]
    scen_moic = scen_results["Outcome"].loc["MOIC", "Value"]
    
    # 4. DISPLAY METRICS WITH DELTAS
    st.subheader(f"Results for {selected_scen}")
    c1, c2 = st.columns(2)
    
    # IRR Metric (Percentage delta)
    c1.metric(
        label="Projected IRR", 
        value=f"{scen_irr:.1%}", 
        delta=f"{scen_irr - current_irr:.1%}",
        help="Green indicates the scenario outperforms your current sidebar settings."
    )
    
    # MOIC Metric (Multiple delta)
    c2.metric(
        label="Projected MOIC", 
        value=f"{scen_moic:.2f}x", 
        delta=f"{scen_moic - current_moic:.2f}x",
        help="Shows the change in total cash returned per dollar invested."
    )
    
    st.divider()
    
    # 5. ASSUMPTION COMPARISON TABLE
    st.subheader("Assumptions Used")
    comparison_df = pd.DataFrame({
        "Assumption": ["Rev Growth %", "EBITDA Margin %", "Exit Multiple"],
        "Current (Sidebar)": [f"{growth}%", f"{margin}%", f"{exit_mult}x"],
        f"Selected ({selected_scen})": [f"{s_data['growth']}%", f"{s_data['margin']}%", f"{s_data['exit']}x"]
    })
    st.table(comparison_df)


# --- TAB 6: DEBT & COVENANTS ---
with tab6:
    st.header("👮 Debt Profile & Covenant Tracking")
    
    # 1. Prepare Data
    # Convert "Year X" to integer X for numerical axis sorting
    df_r = results["Ratios"].copy()
    df_r.columns = [int(str(col).replace("Year ", "")) for col in df_r.columns]
    
    # 2. Visualizing Covenants with Plotly for Markers and Integer Axis
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("Net Debt / EBITDA")
        # Chart 1: Leverage (Full range 0 to T)
        fig_lev = go.Figure()
        fig_lev.add_trace(go.Scatter(
            x=df_r.columns, 
            y=df_r.loc["Net Debt / EBITDA"],
            mode='lines+markers',
            marker=dict(size=8, color='#29b5e8'),
            line=dict(width=3, color='#29b5e8'),
            name="Leverage"
        ))
        fig_lev.update_layout(
            height=350, margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(tickmode='linear', dtick=1), # Forces integer ticks
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white")
        )
        st.plotly_chart(fig_lev, use_container_width=True)
        peak_lev = df_r.loc["Net Debt / EBITDA"].max()
        st.write(f"Peak Leverage: **{peak_lev:.2f}x**")

    with col_r:
        st.subheader("Interest Coverage")
        # Chart 2: Interest Coverage (Filter to start from Year 1)
        # We slice the columns to exclude 0
        df_r_filtered = df_r.iloc[:, 1:] 
        
        fig_cov = go.Figure()
        fig_cov.add_trace(go.Scatter(
            x=df_r_filtered.columns, 
            y=df_r_filtered.loc["Interest Coverage"],
            mode='lines+markers',
            marker=dict(size=8, color='#15a0a3'),
            line=dict(width=3, color='#15a0a3'),
            name="Coverage"
        ))
        fig_cov.update_layout(
            height=350, margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(tickmode='linear', dtick=1), # Forces integer ticks
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white")
        )
        st.plotly_chart(fig_cov, use_container_width=True)
        min_cov = df_r_filtered.loc["Interest Coverage"].min()
        st.write(f"Min Coverage (Y1+): **{min_cov:.2f}x**")

    # 3. Debt Balance (Revolver)
    st.divider()
    st.subheader("📋 Debt Balance Schedule")
    debt_schedule = results["BS"].loc[["Total Debt"]]
    st.dataframe(debt_schedule.style.format("${:,.0f}"), use_container_width=True)

    # 4. Covenant "Health Check" Alerts
    st.divider()
    st.subheader("✅ Covenant Status")
    c1, c2 = st.columns(2)
    
    # --- Leverage Check (Net Debt / EBITDA) ---
    if peak_lev > 5.0:
        c1.error(f"🚨 **Danger: High Leverage**\nPeak is {peak_lev:.2f}x (Threshold > 5.0x)")
    elif 4.0 <= peak_lev <= 5.0:
        c1.warning(f"⚠️ **Warning: Elevated Leverage**\nPeak is {peak_lev:.2f}x (Watchlist Range: 4.0x - 5.0x)")
    else:
        c1.success(f"✅ **Leverage Safe**\nPeak {peak_lev:.2f}x is within comfortable limits")
        
    # --- Interest Coverage Check ---
    if min_cov < 1.5:
        c2.error(f"🚨 **Danger: Low Coverage**\nMinimum is {min_cov:.2f}x (Threshold < 1.5x)")
    elif 1.5 <= min_cov <= 2.5:
        c2.warning(f"⚠️ **Warning: Tight Coverage**\nMinimum is {min_cov:.2f}x (Watchlist Range: 1.5x - 2.5x)")
    else:
        c2.success(f"✅ **Coverage Safe**\nMinimum {min_cov:.2f}x provides ample cushion")


# --- TAB 7: reverse LBO ---
with tab7:
    st.header("🔍 Reverse LBO: Price Discovery")
    
    # 1. Only one input: The IRR you want to achieve
    target_irr = st.number_input("Target IRR (%)", value=22.0, step=0.5) / 100
    
    # 2. Calculation Loop
    test_multiples = np.linspace(4.0, 15.0, 30)
    reverse_results = []

    for m in test_multiples:
        res = run_lbo_model(
            T = horizon, Entry = m, Exit = exit_mult, 
            LTM_EBITDA = ltm_ebitda, LTM_REVENUE = ltm_revenue,
            growth = growth, margin = margin, Tax = tax_rate, CAPEX = CAPEX, DA = DA, WK_Inv = WK_Inv,
            Cash = cash_req, Int_Cash = int_cash, Int_Debt = int_debt, Debt_pct = debt_pct, Fixed_assets_share = fa_share, Dividend_sweep=dvd_sweep
        )
        reverse_results.append({
            "Entry": m,
            "IRR": res["Outcome"].loc["IRR", "Value"],
            "MOIC": res["Outcome"].loc["MOIC", "Value"]
        })

    df_rev = pd.DataFrame(reverse_results)

    # 3. Find the Entry Multiple where IRR matches Target
    # We find the multiple closest to our target IRR
    idx = (df_rev['IRR'] - target_irr).abs().idxmin()
    solved_m = df_rev.loc[idx, "Entry"]
    resulting_moic = df_rev.loc[idx, "MOIC"]

    # 4. Display Clean Results
    st.subheader(f"To achieve a {target_irr:.1%} IRR:")
    
    res_c1, res_c2, res_c3 = st.columns(3)
    
    res_c1.metric("Max Entry Multiple", f"{solved_m:.1f}x", 
                 delta=f"{solved_m - entry_mult:.1f}x", delta_color="normal")
    
    res_c2.metric("Resulting MOIC", f"{resulting_moic:.2f}x")
    
    max_ev = solved_m * ltm_ebitda
    res_c3.metric("Max Enterprise Value", f"${max_ev:,.0f}M")

    # 5. Visualizing the Price/Return Tradeoff
    fig_rev = go.Figure()
    fig_rev.add_trace(go.Scatter(x=df_rev["Entry"], y=df_rev["IRR"], name="IRR", line=dict(color='#29b5e8')))
    fig_rev.add_hline(y=target_irr, line_dash="dash", line_color="red", annotation_text="Target IRR")
    
    fig_rev.update_layout(
        title="IRR Decay vs. Purchase Price",
        xaxis_title="Entry Multiple (EBITDA x)",
        yaxis_tickformat='.0%',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white")
    )
    st.plotly_chart(fig_rev, use_container_width=True)
    
st.divider()
st.header("💾 Export Results")

# 1. Map your exact Sidebar names to a dictionary
# Using the variable names from your sidebar code (rev_ui, dvd_sweep, etc.)
inputs_data = {
    "LTM Revenue ($M)": rev_ui,
    "LTM EBITDA ($M)": ltm_ebitda,
    "Entry EV/EBITDA": entry_mult,
    "Exit EV/EBITDA": exit_mult,
    "Time Horizon (Years)": horizon,
    
    "Debt Financing (%)": debt_pct,
    "Interest on Debt (%)": int_debt,
    "Interest on Cash (%)": int_cash,    
    "Min Cash Requirement": cash_req,
    "Fixed Assets (%) of Invested Capital": fa_share,
    "Dividend Sweep (%)": dvd_sweep,
    
    "Revenue Growth (%)": growth,
    "EBITDA Margin (%)": margin,
    "Tax Rate (%)": tax_rate,
    "CAPEX (% Rev)": CAPEX,
    "Depreciation & Amortization": DA,
    "Working Capital (% Rev)": WK_Inv
}
df_inputs = pd.DataFrame.from_dict(inputs_data, orient='index', columns=['Assumption Value'])

# 2. Create the Excel Buffer
buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # --- A. Assumptions Sheet (with formatting) ---
    df_inputs.to_excel(writer, sheet_name='Assumptions')
    
    workbook  = writer.book
    worksheet = writer.sheets['Assumptions']
    
    # Add some Wall Street flair
    header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#29b5e8', 'border': 1})
    num_fmt    = workbook.add_format({'num_format': '#,##0.0', 'border': 1})
    
    # Apply formatting to columns
    worksheet.set_column('A:A', 30) # Widen labels
    worksheet.set_column('B:B', 20, num_fmt)
    
    # --- B. Financial Statements (Your existing logic) ---
    results["IS"].to_excel(writer, sheet_name='Income Statement')
    results["CF"].to_excel(writer, sheet_name='Cash Flow')
    results["BS"].to_excel(writer, sheet_name='Balance Sheet')
    results["Outcome"].to_excel(writer, sheet_name='Returns and Ratios')
    results["Sponsor_CF"].to_excel(writer, sheet_name='Sponsor Cash Flow')
    
    # Sensitivity Check
    if 'df_sens' in locals():
        df_sens.to_excel(writer, sheet_name='Sensitivity Analysis')

# 3. The Download Button
st.download_button(
    label="📥 Download Full LBO Package",
    data=buffer.getvalue(),
    file_name="LBO_Model_Output.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Exports all assumptions and three-statement financial results to Excel."
)

# Uses and Sources?
# Uses and Funds?, fees?