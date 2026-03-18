import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

@st.cache_data 
def run_lbo_model(
    T = 5, Entry = 7.0, Exit = 8.0, LTM_EBITDA = 400.0, LTM_REVENUE = 1000.0,
    margin = 40.0, growth = 5.0, Tax = 30.0, CAPEX = 3.0, DA = 3.0, WK_Inv = 1.0,
    Cash = 50.0, Int_Cash = 1.0, Int_Debt = 8.0, Debt_pct = 60.0, Fixed_assets_share = 70.0, Dividend_sweep = 0.0
):
    # Calculations
    Purchase_EV = Entry * LTM_EBITDA
    Debt = (Debt_pct / 100) * Purchase_EV
    Equity = Purchase_EV - Debt
    sweep = Dividend_sweep / 100

    IS = np.zeros((9, T + 1))
    CF = np.zeros((9, T + 1))
    BS = np.zeros((9, T + 1))
    
    DB = np.zeros((1, T + 1))
    CH = np.zeros((1, T + 1))
    Sponsor = np.zeros((1, T + 1))
    
    Ratios = np.zeros((5, T + 1))
    Outcome = np.zeros((9, 1))

    for i in range(T + 1):
        if i == 0:
            IS[0, i] = LTM_REVENUE
            IS[1, i] = - (LTM_REVENUE - LTM_EBITDA)
            IS[2, i] = LTM_EBITDA
            
            CH[0, i] = Cash
            DB[0, i] = Debt
            
            BS[0, i] = CH[0, i]
            BS[1, i] = (Equity + Debt - Cash) * (1 - Fixed_assets_share / 100)
            BS[2, i] = (Equity + Debt - Cash) * Fixed_assets_share / 100
            BS[3, i] = BS[0, i] + BS[1, i] + BS[2, i]
            BS[4, i] = DB[0, i]
            BS[5, i] = Equity
            BS[6, i] = 0            
            BS[7, i] = BS[5, i] + BS[6, i]
            BS[8, i] = BS[4, i] + BS[7, i]

            Ratios[0, i] = (DB[0, i] - CH[0, i]) / IS[2, i]
            Sponsor[0, i] = - Equity
            
        else: 
            # Income Statement
            IS[0, i] = IS[0, i - 1] * (1 + growth / 100)
            IS[1, i] = - (1 - margin / 100) * IS[0, i]
            IS[2, i] = (margin / 100) * IS[0, i]
            IS[3, i] = - (DA / 100) * IS[0, i]
            IS[4, i] = IS[2, i] + IS[3, i]
            IS[5, i] = - DB[0, i - 1] * (Int_Debt / 100) + CH[0, i - 1] * (Int_Cash / 100)
            IS[6, i] = IS[4, i] + IS[5, i]
            IS[7, i] = - (Tax / 100) * IS[6, i]
            IS[8, i] = IS[6, i] + IS[7, i]

            # Cash Flow
            CF[0, i] = IS[8, i]
            CF[1, i] = - IS[3, i]
            CF[2, i] = - (WK_Inv / 100) * IS[0, i]
            CF[3, i] = CF[0, i] + CF[1, i] + CF[2, i]
            CF[4, i] = - (CAPEX / 100) * IS[0, i]
            CF[5, i] = CF[3, i] + CF[4, i]
            CF[6, i] = - np.minimum(CF[5, i], DB[0, i - 1])
            CF[7, i] = - (CF[5, i] + CF[6, i]) * sweep
            CF[8, i] = CF[5, i] + CF[6, i] + CF[7, i]

            # Balances
            DB[0, i] = DB[0, i - 1] + CF[6, i]
            CH[0, i] = CH[0, i - 1] + CF[8, i]

            # Balance Sheet
            BS[0, i] = CH[0, i]
            BS[1, i] = BS[1, i - 1] - CF[2, i]
            BS[2, i] = BS[2, i - 1] - CF[4, i] - CF[1, i]
            BS[3, i] = BS[0, i] + BS[1, i] + BS[2, i]
            BS[4, i] = DB[0, i]

            BS[5, i] = BS[5, i - 1]
            BS[6, i] = BS[6, i - 1] + IS[8, i] + CF[7, i]
            BS[7, i] = BS[5, i] + BS[6, i]
            BS[8, i] = BS[4, i] + BS[7, i]

            # Ratios
            Ratios[0, i] = (DB[0, i] - CH[0, i]) / IS[2, i]
            Ratios[1, i] = - IS[2, i] / IS[5, i] if IS[5, i] != 0 else 0
            Ratios[2, i] = (1 - Tax / 100) * IS[4, i] / np.mean([BS[1, i] + BS[2, i], BS[1, i - 1] + BS[2, i - 1]])
            Ratios[3, i] = IS[8, i] / np.mean([BS[5, i], BS[5, i - 1]])
            Ratios[4, i] = IS[8, i] / IS[0, i]

            if i == T:
                Sponsor[0, i] = - CF[7, i] + Exit * IS[2, T] - DB[0, T] + CH[0, T] 
            else:
                Sponsor[0, i] = - CF[7, i]
                    
    # IRR Calculation
    
        # 1. Ensure the Sponsor array is 1-dimensional for the IRR function
    # If Sponsor is (1, T+1), we use .flatten() or [0] to make it a simple list
    cash_flow_stream = Sponsor.flatten()
    true_irr = npf.irr(cash_flow_stream)
        
    # Outcomes
    Outcome[0, 0] = Exit * IS[2, T] # EV Exit
    Outcome[1, 0] = Outcome[0, 0] - DB[0, T] + CH[0, T] # Equity Exit
    Outcome[2, 0] = (Outcome[1, 0] - np.sum(CF[7, 1:])) / Equity # MOIC
    Outcome[3, 0] = true_irr if true_irr is not None else 0.0 # IRR
    
    Outcome[4, 0] = (IS[2, T] - IS[2, 0]) * Entry # EBITDA Growth
    Outcome[5, 0] = (Exit - Entry) * IS[2, T] # Multiple Expansion
    Outcome[6, 0] = - np.sum(CF[7, 1:]) # Dividend Payment
    Outcome[8, 0] = Outcome[1, 0] - Equity # Total Equity Return
    Outcome[7, 0] = Outcome[8, 0] - Outcome[6, 0] - Outcome[5, 0] - Outcome[4, 0] # Paydown Debt

    column_headers = [f"Year {i}" for i in range(T + 1)]
    
    df_IS = pd.DataFrame(IS, index = ["Revenue", "Less Costs and Expenses", "EBITDA", "Less D&A", "EBIT", "Less Net Interest Expense", "Pretax Income", "Less Tax", "Net Income"], columns = column_headers)
    df_CF = pd.DataFrame(CF, index = ["Net Income", "Plus D&A", "Less Working Capital Investment", "Cash from Operations", "Less CAPEX", "Free Cash Flow", "Less Debt Repayment", "Less Dividends Paid", "Change in Cash"], columns = column_headers)
    df_BS = pd.DataFrame(BS, index = ["Cash", "Net Oper Work Capital Stock", "Net Fixed Assets", "Total Assets", "Total Debt", "Additional Paid-in-Capital", "Retained Earnings", "Total Equity", "Liabilities + Equity"], columns = column_headers)
    df_Ratios = pd.DataFrame(Ratios, index = ["Net Debt / EBITDA", "Interest Coverage", "ROIC", "ROE", "Net Margin"], columns = column_headers)
    df_Outcome = pd.DataFrame(Outcome, index = ["EV_Exit", "Equity_Exit", "MOIC", "IRR", "Attr: EBITDA Growth", "Attr: Multiple Expansion", "Attr: Dividend Payment", "Attr: Paydown Debt", "Total Equity Return"], columns=['Value'])
    df_Sponsor = pd.DataFrame(Sponsor, index = ["Sponsor Cash Flow"], columns = column_headers)
    
    return {"IS": df_IS, "CF": df_CF, "BS": df_BS, "Ratios": df_Ratios, "Outcome": df_Outcome, "Sponsor_CF": df_Sponsor}