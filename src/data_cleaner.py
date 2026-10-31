"""Data cleaning, deduplication, and anomaly isolation pipeline."""

import re
from pathlib import Path
from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np


def normalize_phone(phone_raw: Any) -> Tuple[str, bool, str]:
    """Clean phone number and determine WhatsApp reachability.
    
    Returns:
        (clean_digits, is_valid_10_digit, phone_type)
    """
    if pd.isna(phone_raw):
        return ("", False, "MISSING")
    
    s = str(phone_raw).strip()
    # Strip spaces, hyphens, pluses, parentheses
    digits = re.sub(r"[\s\+\-\(\)\.]", "", s)
    
    # Strip country code +91 or 91 if length is 12
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
        
    if len(digits) == 10 and digits.isdigit():
        return (digits, True, "VALID_10_DIGIT")
    elif len(digits) == 9 and digits.isdigit():
        return (digits, False, "TRUNCATED_9_DIGIT")
    else:
        return (digits, False, "INVALID_FORMAT")


def clean_orders_dataset(
    filepath_or_df: Any,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Clean orders dataset, removing duplicates and isolating in-transit orders.
    
    Returns:
        (clean_df, in_transit_df, audit_metrics)
    """
    if isinstance(filepath_or_df, (str, Path)):
        df = pd.read_csv(filepath_or_df)
    else:
        df = filepath_or_df.copy()

    raw_row_count = len(df)
    
    # 1. Identify and deduplicate exact duplicate order IDs
    duplicate_mask = df.duplicated(subset=["order_id"], keep="first")
    num_duplicates = int(duplicate_mask.sum())
    duplicate_ids = df.loc[duplicate_mask, "order_id"].tolist()
    
    df_dedup = df[~duplicate_mask].copy()

    # 2. Standardize status labels
    df_dedup["final_status_raw"] = df_dedup["final_status"]
    df_dedup["final_status_clean"] = (
        df_dedup["final_status"].astype(str).str.strip().str.upper()
    )

    # 3. Isolate active IN_TRANSIT orders from historical evaluation
    in_transit_mask = df_dedup["final_status_clean"] == "IN_TRANSIT"
    in_transit_df = df_dedup[in_transit_mask].copy()
    clean_df = df_dedup[~in_transit_mask].copy()

    # Standardize final binary target: is_rto
    clean_df["is_rto"] = clean_df["final_status_clean"].apply(
        lambda x: 1 if "RTO" in x else 0
    )

    # 4. Zero-Rupee order protection (PR seeding / free replacements)
    clean_df["is_replacement_bypass"] = clean_df["order_value"] <= 0

    # 5. Phone normalization
    phone_results = clean_df["phone"].apply(normalize_phone)
    clean_df["phone_clean"] = [res[0] for res in phone_results]
    clean_df["phone_reachable"] = [res[1] for res in phone_results]
    clean_df["phone_issue_type"] = [res[2] for res in phone_results]

    # 6. Parse order datetime if available
    if "order_datetime" in clean_df.columns:
        clean_df["order_datetime"] = pd.to_datetime(clean_df["order_datetime"], errors="coerce")
        clean_df["order_date"] = clean_df["order_datetime"].dt.date

    # 7. Unit price anomaly detection (price glitch / high remorse risk)
    clean_df["num_items"] = clean_df["num_items"].fillna(1).astype(int)
    clean_df["unit_price"] = clean_df["order_value"] / clean_df["num_items"].replace(0, 1)
    clean_df["is_price_inflated"] = clean_df["unit_price"] > 700.0

    # Audit summary
    audit_metrics = {
        "raw_rows": raw_row_count,
        "duplicate_rows_removed": num_duplicates,
        "duplicate_order_ids": duplicate_ids,
        "in_transit_rows_held_out": len(in_transit_df),
        "clean_evaluated_rows": len(clean_df),
        "replacement_bypass_orders": int(clean_df["is_replacement_bypass"].sum()),
        "truncated_9digit_phones": int((clean_df["phone_issue_type"] == "TRUNCATED_9_DIGIT").sum()),
        "price_inflated_orders": int(clean_df["is_price_inflated"].sum()),
        "baseline_rto_rate": float(clean_df["is_rto"].mean()) if len(clean_df) > 0 else 0.0,
    }

    return clean_df, in_transit_df, audit_metrics


def clean_and_enrich_dataset(filepath_or_df: Any) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Helper alias returning clean_df and in_transit_df."""
    clean_df, in_transit_df, _ = clean_orders_dataset(filepath_or_df)
    return clean_df, in_transit_df


DATA_TRAPS_DOCUMENTED = [
    {
        "name": "30 Exact Duplicate Orders (60 rows)",
        "description": "Rows sharing identical order_ids (e.g., KT100191, KT100317, KT100329).",
        "impact": "Failing to deduplicate causes train/test leakage and overweights duplicate return losses."
    },
    {
        "name": "Unclean Status Labels & 1 Active Order",
        "description": "final_status contains 'DELIVERED', 'RTO', 'Rto', 'delivered', 'RTO ' (trailing space), and 'IN_TRANSIT'.",
        "impact": "Naive == 'RTO' checks misclassify 3 returns and evaluate 1 unfulfilled order."
    },
    {
        "name": "3 Zero-Rupee Orders (order_value == ₹0)",
        "description": "Orders KT100710, KT101549, and KT100565 have order_value = 0 (all delivered replacements/PR).",
        "impact": "Naive EV formula calculates negative contribution (-₹25) and wrongfully auto-cancels warranty replacements."
    },
    {
        "name": "The Hinglish Address Intent Paradox",
        "description": "'ph krke aana' notes have a 24.2% RTO (lower than 28.4% avg), while city-only addresses ('Delhi') suffer 54.8% RTO.",
        "impact": "Standard digit/word regex blacklists genuine high-intent buyers while letting vague addresses through."
    },
    {
        "name": "The Serial Returner Cliff (prior_rto >= 2)",
        "description": "Customers with 0 prior RTOs have 27.1% RTO; customers with 2 prior RTOs jump to 76.5% RTO (26 of 34 returned).",
        "impact": "COD loses ₹70-₹140 per parcel on serial returners; requires an automated hard block."
    },
    {
        "name": "Phone Formatting & 9-Digit Truncated Numbers",
        "description": "15 numbers have '+91 ' formatting; 17 numbers are 9-digit truncated (47.1% RTO, reachability r = 0).",
        "impact": "WhatsApp reachability is zero for 9-digit numbers; confirmation and prepaid nudges cannot be delivered."
    }
]

