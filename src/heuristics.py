"""Heuristic address classification, fraud signal extraction, and Empirical Bayes shrinkage."""

import re
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


# Common fake/junk name tokens
SUSPICIOUS_NAMES = {
    "asdf", "test", "test order", "qwerty", "na", "abc", "xyz", "xyz xyz", "aaa", "bbb", "ccc", "none"
}

# 15 Address Patterns Regex / Token Rules
JUNK_EXACT_VALUES = {".", "home", "xyz", "call me", "near station", "test", "none"}


def classify_address(address_raw: Any, city_raw: Any) -> Tuple[str, str, float]:
    """Classify address into one of 6 structural archetype categories.
    
    Returns:
        (category_code, description, base_address_risk)
    """
    if pd.isna(address_raw):
        return ("JUNK_EMPTY", "Missing Address", 0.70)
        
    addr = str(address_raw).strip()
    addr_lower = addr.lower()
    city_clean = str(city_raw).strip().lower() if not pd.isna(city_raw) else ""

    # 1. Junk: Single symbol / dummy word
    if addr_lower in JUNK_EXACT_VALUES or len(addr) <= 4 or addr in [".", ",", "-", "/"]:
        return ("JUNK_SYMBOL", "Junk dummy token (e.g. '.', 'home', 'xyz', 'call me')", 0.638)

    # 2. Junk: City Name repeated only
    if city_clean and addr_lower == city_clean:
        return ("JUNK_CITY_REPEAT", f"Address merely repeats city name '{addr}'", 0.548)

    # 3. Hinglish: High-Intent Delivery Instructions
    if "ph krke aana" in addr_lower or "phone karke aana" in addr_lower or "call karke aana" in addr_lower:
        return ("HINGLISH_HIGH_INTENT_CALL", "High-intent buyer delivery note ('ph krke aana')", 0.242)
    if "ke peeche wala ghar" in addr_lower or "ke piche wala ghar" in addr_lower:
        return ("HINGLISH_HIGH_INTENT_BEHIND", "Informal landmark locator ('ke peeche wala ghar')", 0.273)

    # 4. Hinglish: Vague Landmark / Gali
    if ("chowk se left" in addr_lower or "chowk se right" in addr_lower or 
        "ke saamne" in addr_lower or "ke samne" in addr_lower or 
        "ke paas" in addr_lower or "ghar ka naam" in addr_lower or "niwas" in addr_lower or
        "gali no" in addr_lower or "gali number" in addr_lower):
        return ("HINGLISH_VAGUE_LANDMARK", "Colloquial Hinglish gali/landmark address", 0.346)

    # 5. Structured English: Nagar format (e.g. 784/17, MG Nagar, Opp. Hanuman Mandir)
    if re.search(r"\d+/\d+", addr) or "nagar" in addr_lower:
        return ("STRUCTURED_NAGAR", "Semi-structured postal nagar address", 0.281)

    # 6. Structured English: Urban Society / Apartment / Sector
    if (re.search(r"\bflat\b", addr_lower) or 
        re.search(r"\bhouse no\b", addr_lower) or 
        re.search(r"\bsector\b", addr_lower) or 
        re.search(r"\bsociety\b", addr_lower) or 
        re.search(r"\bapartments?\b", addr_lower)):
        return ("STRUCTURED_URBAN", "Verified structured urban apartment / society / sector", 0.213)

    # Fallback: check length & digits
    has_digits = bool(re.search(r"\d", addr))
    word_count = len(addr.split())
    if word_count >= 5 and has_digits:
        return ("STRUCTURED_GENERIC", "Detailed multi-word address with premise numbers", 0.250)
    else:
        return ("VAGUE_UNSTRUCTURED", "Short unstructured address without standard markers", 0.420)


def check_fake_name(name_raw: Any) -> Tuple[bool, str]:
    """Detect test/dummy customer names."""
    if pd.isna(name_raw):
        return (True, "Missing Name")
    clean = str(name_raw).strip().lower()
    if clean in SUSPICIOUS_NAMES or len(clean) < 3 or clean.isdigit():
        return (True, f"Dummy/test name detected ('{name_raw}')")
    return (False, "Authentic name")


class EmpiricalBayesPriorEstimator:
    """Calculates smoothed Beta-Binomial Empirical Bayes priors for cities and states."""

    def __init__(self, m_weight: float = 10.0):
        self.m_weight = m_weight
        self.global_rto_rate = 0.2843
        self.state_stats: Dict[str, Dict[str, float]] = {}
        self.city_stats: Dict[str, Dict[str, float]] = {}

    def fit(self, df: pd.DataFrame) -> "EmpiricalBayesPriorEstimator":
        """Fit empirical stats on clean historical orders."""
        if len(df) == 0:
            return self
            
        self.global_rto_rate = float(df["is_rto"].mean())

        # State priors
        state_grouped = df.groupby("state")["is_rto"].agg(["sum", "count"]).reset_index()
        for _, row in state_grouped.iterrows():
            st = str(row["state"]).strip()
            k = float(row["sum"])
            n = float(row["count"])
            # State shrunk slightly to global mean
            p_shrunk = (k + 5.0 * self.global_rto_rate) / (n + 5.0)
            self.state_stats[st] = {"k": k, "n": n, "p_raw": k / n if n > 0 else self.global_rto_rate, "p_shrunk": p_shrunk}

        # City priors shrunk to state prior
        city_grouped = df.groupby(["city", "state"])["is_rto"].agg(["sum", "count"]).reset_index()
        for _, row in city_grouped.iterrows():
            ct = str(row["city"]).strip().lower()
            st = str(row["state"]).strip()
            k = float(row["sum"])
            n = float(row["count"])
            state_p = self.state_stats.get(st, {}).get("p_shrunk", self.global_rto_rate)
            # Two-level Beta-Binomial shrinkage:
            # p_city = (k_city + m * p_state) / (n_city + m)
            p_shrunk = (k + self.m_weight * state_p) / (n + self.m_weight)
            self.city_stats[ct] = {
                "city": str(row["city"]).strip(),
                "state": st,
                "k": k,
                "n": n,
                "p_raw": k / n if n > 0 else state_p,
                "p_shrunk": p_shrunk,
            }
        return self

    def get_shrunk_city_risk(self, city: str, state: str) -> float:
        """Get smoothed RTO probability for a city."""
        ct_clean = str(city).strip().lower() if city else ""
        if ct_clean in self.city_stats:
            return self.city_stats[ct_clean]["p_shrunk"]
        
        # Fallback to state prior
        st_clean = str(state).strip() if state else ""
        if st_clean in self.state_stats:
            return self.state_stats[st_clean]["p_shrunk"]
            
        return self.global_rto_rate

    def predict_city_risk(self, city: str, state: str) -> float:
        """Alias for get_shrunk_city_risk."""
        return self.get_shrunk_city_risk(city, state)


EmpiricalBayesCalculator = EmpiricalBayesPriorEstimator



def estimate_order_rto_risk(
    order: Dict[str, Any],
    eb_estimator: Optional[EmpiricalBayesPriorEstimator] = None,
    serial_rto_cap: int = 2,
    unit_price_threshold: float = 700.0,
) -> Tuple[float, Dict[str, Any]]:
    """Compute calibrated RTO probability p and feature diagnostic signals.
    
    Returns:
        (p_rto, signal_breakdown)
    """
    # 1. Address signal
    address = order.get("address") or order.get("shipping_address") or ""
    city = order.get("city", "")
    state = order.get("state", "")
    addr_cat, addr_desc, addr_risk = classify_address(address, city)

    # 2. Fake name signal
    name = order.get("customer_name", "")
    is_fake_name, name_desc = check_fake_name(name)

    # 3. Customer prior history (Loyalty non-linear U-shape & Serial returner cliff)
    prior_orders = int(order.get("customer_prior_orders", 0) or 0)
    prior_rto = int(order.get("customer_prior_rto", 0) or 0)

    # Base risk starts from address category baseline
    risk = addr_risk

    # 4. Geographic Empirical Bayes adjustment
    geo_risk = eb_estimator.get_shrunk_city_risk(city, state) if eb_estimator else 0.2843
    # Blend address archetype with regional logistics reality (60% address, 40% geo prior)
    risk = 0.55 * risk + 0.45 * geo_risk

    # 5. Customer History Adjustment
    if prior_rto >= serial_rto_cap:
        # Serial returner cliff (76.5% RTO observed empirically)
        risk = max(risk, 0.765)
    elif prior_rto == 1:
        risk += 0.08
    else:
        # Prior RTO == 0
        if prior_orders == 1:
            # Safest cohort (15.7% empirical RTO)
            risk *= 0.65
        elif prior_orders == 2:
            risk *= 0.75
        elif prior_orders >= 3:
            risk *= 0.88

    # 6. Price Inflation / Ticket Size Regret Signal
    order_val = float(order.get("order_value", 0) or 0)
    num_items = max(1, int(order.get("num_items", 1) or 1))
    unit_price = order_val / num_items

    is_price_inflated = unit_price > unit_price_threshold
    if is_price_inflated:
        risk = min(0.92, risk + 0.16)

    # Cart-stuffing penalty for 4+ items
    if num_items >= 4 and order_val > 1500:
        risk = min(0.92, risk + 0.08)

    # 7. Fake Name Penalty
    if is_fake_name:
        risk = min(0.95, risk + 0.25)

    # 8. Bounds check
    final_p = float(np.clip(risk, 0.04, 0.94))

    signals = {
        "address_category": addr_cat,
        "address_description": addr_desc,
        "address_base_risk": addr_risk,
        "is_fake_name": is_fake_name,
        "name_description": name_desc,
        "geo_shrunk_risk": geo_risk,
        "prior_orders": prior_orders,
        "prior_rto": prior_rto,
        "is_serial_returner": prior_rto >= serial_rto_cap,
        "unit_price": unit_price,
        "is_price_inflated": is_price_inflated,
        "final_rto_risk": final_p,
    }

    return final_p, signals


class AddressIntentResult:
    def __init__(self, cat_code: str, desc: str, risk: float):
        self.category = type("CategoryEnum", (), {"value": cat_code})()
        self.description = desc
        self.base_risk = risk
        self.risk_multiplier = round(risk / 0.2843, 2)


def classify_address_intent(address: Any, city: Any) -> AddressIntentResult:
    cat, desc, risk = classify_address(address, city)
    return AddressIntentResult(cat, desc, risk)


detect_fake_name = check_fake_name
calculate_bayesian_rto_risk = estimate_order_rto_risk

