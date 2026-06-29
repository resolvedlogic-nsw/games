import pandas as pd
import re

# -----------------------------
# Utility: Clean numeric values
# -----------------------------
def clean_val(v):
    if pd.isna(v):
        return 0.0
    s = re.sub(r'[^\d.-]', '', str(v))
    try:
        return float(s)
    except:
        return 0.0


# ----------------------------------------------------
# Build item library from key.csv (same as Streamlit)
# ----------------------------------------------------
def parse_item_library(df):
    mapping = {}

    for _, row in df.iterrows():
        item = str(row.get('Item Name', '')).strip()
        var = str(row.get('Variation Name', 'Regular')).strip()
        cat = str(row.get('Categories', 'Unknown')).strip()

        p_val = str(row.get('Price', 'variable')).lower()
        price = clean_val(p_val) if ('variable' not in p_val and p_val != '') else 'variable'

        info = {"price": price, "min": cat}

        # Build multiple name variants for matching
        base = re.sub(r'^\d+x\s*', '', item).strip()
        names = [
            item,
            f"{item} ({var})",
            base,
            f"{base} ({var})"
        ]

        for n in names:
            if n:
                mapping[n] = info

    return mapping


# ----------------------------------------------------
# Main logic: Split Square transactions into line items
# ----------------------------------------------------
def split_logic(df, library_map):
    # Detect column names dynamically
    desc_col = next((c for c in ['Description', 'Item', 'Items'] if c in df.columns), None)
    gross_col = next((c for c in ['Gross Sales', 'Gross'] if c in df.columns), None)
    fee_col = next((c for c in ['Fees', 'Fee'] if c in df.columns), None)
    date_col = next((c for c in ['Date', 'Transaction Date'] if c in df.columns), None)

    if not all([desc_col, gross_col, fee_col, date_col]):
        raise ValueError("Column detection failed. Required columns not found.")

    all_expanded = []

    # ----------------------------------------------------
    # Expand each transaction into individual line items
    # ----------------------------------------------------
    for _, row in df.iterrows():
        t_gross = clean_val(row[gross_col])
        t_fee = clean_val(row[fee_col])

        parts = [p.strip() for p in str(row[desc_col]).split(',')]
        line_items = []
        known_price_sum = 0.0

        # Parse each item in the description
        for part in parts:
            match = re.match(r'^(?:(\d+)\s*x\s+)?(.+)$', part)
            if match:
                qty = int(match.group(1)) if match.group(1) else 1
                name = match.group(2).strip()

                info = library_map.get(name, {"price": "variable", "min": "Unknown"})

                # Revenue protection logic
                if len(parts) == 1:
                    price = t_gross / qty
                else:
                    price = 0.0 if info['price'] == 'variable' else info['price']

                line_gross = qty * price

                item_data = {
                    "Item": name,
                    "Qty": qty,
                    "Gross": line_gross,
                    "Min": info['min'],
                    "is_v": (info['price'] == 'variable' and len(parts) > 1)
                }

                line_items.append(item_data)

                if not item_data['is_v']:
                    known_price_sum += line_gross

        # ----------------------------------------------------
        # Split remaining gross among variable items
        # ----------------------------------------------------
        vars_list = [i for i in line_items if i['is_v']]

        if vars_list:
            rem = t_gross - known_price_sum
            for i, v in enumerate(vars_list):
                if i == len(vars_list) - 1:
                    v['Gross'] = rem
                else:
                    v['Gross'] = round(rem / len(vars_list), 2)
                    rem -= v['Gross']

        # ----------------------------------------------------
        # Proportional scaling if known prices don't match total
        # ----------------------------------------------------
        elif abs(known_price_sum - t_gross) > 0.001 and t_gross != 0:
            for i in line_items:
                i['Gross'] = (i['Gross'] / known_price_sum) * t_gross

        # ----------------------------------------------------
        # Fee splitting (penny balancing)
        # ----------------------------------------------------
        row_f_sum = 0.0
        for i, item in enumerate(line_items):
            if i == len(line_items) - 1:
                item['Fee'] = round(t_fee - row_f_sum, 2)
            else:
                ratio = item['Gross'] / t_gross if t_gross != 0 else 0
                item['Fee'] = round(t_fee * ratio, 2)
                row_f_sum += item['Fee']

            all_expanded.append({
                "Date": row[date_col],
                "Min": item['Min'],
                "Item": item['Item'],
                "Qty": item['Qty'],
                "Gross": round(item['Gross'], 2),
                "Fees": item['Fee'],
                "ID": row.get('Transaction ID', 'N/A')
            })

    report_df = pd.DataFrame(all_expanded)

    # ----------------------------------------------------
    # Final reconciliation: daily totals must match raw CSV
    # ----------------------------------------------------
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
