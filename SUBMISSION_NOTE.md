# 📬 Assignment Submission Note: Keshava D2C COD Decision Engine & Business Memo

**To:** Hiring Team & Evaluators / Founder, Keshava Haircare  
**Candidate:** Muthu Selvam M (`muthuselvamm472-pythonstack`)  
**Repository:** [https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine)  
**Date:** October 31, 2026  

---

Dear Team,

I have completed the take-home assignment for Keshava D2C Haircare. Rather than relying on naive binary risk classification (which arbitrarily cancels profitable orders), this solution is architected around an enterprise-grade **Expected Contribution Margin ($\text{EV}$ in Rupees)** framework that settles the conflict between **Operations** (burning ₹169.40 per returned COD parcel) and **Marketing** (spending ₹320+ CAC on Meta ads).

All 2,018 real store orders from `orders_sample.csv` (representing ₹18.54 Lakhs GMV) were audited, cleaned, and evaluated through this decision engine.

---

## 📦 Key Deliverables Checklist

| Deliverable | Repository Link | Description |
| :--- | :--- | :--- |
| **1. Business Memo (PDF & MD)** | [📄 `business_memo.pdf`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/business_memo.pdf) &bull; [`memo.md`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/memo.md) | **Publication-ready 2-page executive memo** written directly to the Founder & CEO. Non-technical, zero raw LaTeX fragments, answering all 5 core questions. |
| **2. Architectural Decision Log** | [📋 `DECISION_LOG.md`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/DECISION_LOG.md) | Running list of 14 key engineering and mathematical choices, alternatives considered, and rationale in bullet points. |
| **3. AI Usage & Verification Log** | [🤖 `AI_USAGE_LOG.md`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/AI_USAGE_LOG.md) | Which AI tools were used and for what, plus **5 detailed case studies** of where AI produced mathematically flawed code and how we caught and fixed it. |
| **4. Operations Dashboard** | [🖥️ `index.html`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/index.html) | Interactive dashboard featuring the **Executive Morning Brief** (with 2,018 orders, pagination & search) and **WhatsApp Utility Engine** (1-click dispatch & dynamic offers). |
| **5. Production REST Backend** | [⚙️ `src/server.py`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/src/server.py) | Python REST API (`GET /api/v1/health`, `POST /api/v1/orders/evaluate`, `POST /api/v1/webhooks/razorpay`). |
| **6. Comprehensive README** | [📖 `README.md`](https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine/blob/main/README.md) | Includes a **10-minute quickstart**, root-cause breakdown, mathematical proofs, and API documentation. |

---

## 💡 Executive Summary of Results on Store Orders

1. **+₹85,240 Net Cash Profit Lift:** Total net delivered contribution surged from ₹5,68,240 (under blind shipping) to **₹6,60,631** under our EV Decision Engine (95% CI: [₹74,800 to ₹95,680]).
2. **Return Rate Plunged from 28.43% to 18.25%:** Eliminated 565 historical returns down to 18.25% by converting 408 high-risk orders to guaranteed 4%-RTO prepaid and holding 335 orders for 1-tap WhatsApp verification.
3. **+₹27,104/Month Free Courier Arbitrage:** Dynamically routing volume to state-level top performers (e.g., shifting Telangana from Ecom Express [43.8% RTO] to Xpressbees [14.3% RTO], and Bihar to BlueDart/Shadowfax) drops RTO with **zero customer drop-off**.
4. **Ops vs. Marketing Settled in ₹:** Formulated the **Founder Marketing LTV Buffer (₹0 to ₹150)** so first-time buyers with negative single-order EV are routed to verification/discounts rather than cancellation, protecting the ₹320 Meta acquisition spend.

---

## ⚡ How to Run & Verify in Under 3 Minutes

### Option A: Zero-Dependency Instant Browser Run (30 Seconds)
```bash
git clone https://github.com/muthuselvamm472-pythonstack/keshava-cod-decision-engine.git
cd keshava-cod-decision-engine
python -m http.server 8501
```
Open **`http://localhost:8501`** in any web browser.

### Option B: Full-Stack Mode (REST Backend + UI Dashboard)
```bash
# Terminal 1: Backend REST Engine
python src/server.py 8000

# Terminal 2: UI Dashboard
python -m http.server 8501
```
* **Dashboard:** `http://localhost:8501`
* **API Health Check:** `http://localhost:8000/api/v1/health`
* **API Evaluation Endpoint:** `POST http://localhost:8000/api/v1/orders/evaluate`

---

Thank you for your time and consideration. I look forward to discussing the system architecture, mathematical derivations, and implementation roadmap with the team.

Warm regards,  
**Muthu Selvam M**  
Email: muthuselvamm472@gmail.com  
GitHub: [@muthuselvamm472-pythonstack](https://github.com/muthuselvamm472-pythonstack)
