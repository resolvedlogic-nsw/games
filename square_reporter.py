import streamlit as st
import pandas as pd
import re
import io
import os

st.set_page_config(page_title="Church Finance Reporter", layout="wide")

AUTO_KEY_PATH = r"E:\church\finances\key.csv"

st.title("⛪ Square Ministry Reporter (v8)")
st.markdown("Precision Mode: **Revenue Protection Logic** + **Daily Balancing**.")

# --- SIDEBAR: UPLOADS ---
with st.sidebar:
    st.header("Upload Files")
    raw_file = st.file_uploader("1. Square Transactions (RAW DATA CSV)", type="csv")
    
    if os.path.exists(AUTO_KEY_PATH):
        st.success(f"✅ Key loaded from E: drive")
        auto_load_key = pd.read_csv(AUTO_KEY_PATH)
    else:
        st.warning("⚠️ key.csv not found on E: drive.")
        key_file = st.file_uploader("2. Manually Upload key.csv", type="csv")
        auto_load_key = pd.read_csv(key_file) if key_file else None

def clean_val(v):
    if pd.isna(v): return 0.0
    s = re.sub(r'[^\d.-]', '', str(v))
    try: return float(s)
    except: return 0.0

def parse_item_library(df):
    mapping = {}
    for _, row in df.iterrows():
        item = str(row.get('Item Name', '')).strip()
        var = str(row.get('Variation Name', 'Regular')).strip()
        cat = str(row.get('Categories', 'Unknown')).strip()
        p_val = str(row.get('Price', 'variable')).lower()
        price = clean_val(p_val) if 'variable' not in p_val and p_val != '' else 'variable'
        
        info = {"price": price, "min": cat}
        names = [item, f"{item} ({var})", re.sub(r'^\d+x\s*', '', item).strip(), f"{re.sub(r'^\d+x\s*', '', item).strip()} ({var})"]
        for n in names:
            if n: mapping[n] = info
    return mapping

def split_logic(df, library_map):
    # Detect Columns
    desc_col = next((c for c in ['Description', 'Item', 'Items'] if c in df.columns), None)
    gross_col = next((c for c in ['Gross Sales', 'Gross'] if c in df.columns), None)
    fee_col = next((c for c in ['Fees', 'Fee'] if c in df.columns), None)
    date_col = next((c for c in ['Date', 'Transaction Date'] if c in df.columns), None)
    
    if not all([desc_col, gross_col, fee_col, date_col]):
        st.error("Column detection failed.")
        return pd.DataFrame()

    all_expanded = []
    
    for _, row in df.iterrows():
        t_gross = clean_val(row[gross_col])
        t_fee = clean_val(row[fee_col])
        parts = [p.strip() for p in str(row[desc_col]).split(',')]
        
        line_items = []
        known_price_sum = 0.0
        
        for part in parts:
            match = re.match(r'^(?:(\d+)\s+x\s+)?(.+)$', part)
            if match:
                qty = int(match.group(1)) if match.group(1) else 1
                name = match.group(2).strip()
                info = library_map.get(name, {"price": "variable", "min": "Unknown"})
                
                # REVENUE PROTECTION: 
                # If it's the ONLY item in the row, we trust the Square Gross Sales over the library price
                if len(parts) == 1:
                    price = t_gross / qty
                else:
                    price = 0.0 if info['price'] == 'variable' else info['price']
                
                line_gross = qty * price
                line_items.append({"Item": name, "Qty": qty, "Gross": line_gross, "Min": info['min'], "is_v": (info['price'] == 'variable' and len(parts) > 1)})
                if not line_items[-1]['is_v']: known_price_sum += line_gross

        # Split remaining gross for multi-item bundles with variable items
        vars_list = [i for i in line_items if i['is_v']]
        if vars_list:
            rem = t_gross - known_price_sum
            for i, v in enumerate(vars_list):
                v['Gross'] = rem if i == len(vars_list)-1 else round(rem/len(vars_list), 2)
                rem -= v['Gross']
        # If no variable items but sums don't match (e.g. price change), scale items proportionally to match Square total
        elif abs(known_price_sum - t_gross) > 0.001 and t_gross != 0:
            for i in line_items:
                i['Gross'] = (i['Gross'] / known_price_sum) * t_gross

        # Fee Splitting & Penny Balancing per row
        row_f_sum = 0.0
        for i, item in enumerate(line_items):
            if i == len(line_items) - 1:
                item['Fee'] = round(t_fee - row_f_sum, 2)
            else:
                ratio = item['Gross'] / t_gross if t_gross != 0 else 0
                item['Fee'] = round(t_fee * ratio, 2)
                row_f_sum += item['Fee']
            
            all_expanded.append({
                "Date": row[date_col], "Min": item['Min'], "Item": item['Item'],
                "Qty": item['Qty'], "Gross": round(item['Gross'], 2), "Fees": item['Fee'],
                "ID": row.get('Transaction ID', 'N/A')
            })

    report_df = pd.DataFrame(all_expanded)
    
    # FINAL RECONCILIATION: Check Daily Totals against Raw CSV to force a perfect match
    final_rows = []
    for date, group in report_df.groupby("Date"):
        target_f = round(df[df[date_col] == date][fee_col].apply(clean_val).sum(), 2)
        target_g = round(df[df[date_col] == date][gross_col].apply(clean_val).sum(), 2)
        
        diff_f = round(target_f - group['Fees'].sum(), 2)
        diff_g = round(target_g - group['Gross'].sum(), 2)
        
        recs = group.to_dict('records')
        if recs:
            recs[-1]['Fees'] = round(recs[-1]['Fees'] + diff_f, 2)
            recs[-1]['Gross'] = round(recs[-1]['Gross'] + diff_g, 2)
        
        for r in recs:
            r['Net'] = round(r['Gross'] + r['Fees'], 2)
            final_rows.append(r)

    return pd.DataFrame(final_rows)

# --- UI EXECUTION ---
if raw_file and auto_load_key is not None:
    try:
        raw_df = pd.read_csv(raw_file)
        library = parse_item_library(auto_load_key)
        final_report = split_logic(raw_df, library)
        
        st.subheader("Balanced Ministry Summary")
        st.table(final_report.groupby("Min")[["Gross", "Fees", "Net"]].sum())
        
        st.subheader("Daily Total Check")
        daily_check = final_report.groupby("Date")[["Gross", "Fees", "Net"]].sum()
        st.write(daily_check)
        
        st.download_button("📥 Download Final Split Report", final_report.to_csv(index=False), "Square_Final_Reconciled.csv", "text/csv")
    except Exception as e:
        st.error(f"Error: {e}")