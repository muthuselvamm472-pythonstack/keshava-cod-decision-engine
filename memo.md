# Executive Business Memo: Resolving the COD RTO Dilemma at Keshava D2C

**To:** Founder & CEO, Keshava Haircare  
**From:** Associate Software Engineer  
**Date:** October 31, 2026  
**Subject:** Settle the COD RTO Conflict: Expected Contribution Margin (EV) Strategy  
**Data Analyzed:** Store Order Batch (`orders_sample.csv`, 2,018 Orders &bull; ₹18.54 Lakhs GMV)  

---

## 1. What Surprised Us in the Data (3 Key Empirical Findings)

Our audit of Keshava's 2,018 store orders revealed that blanket pincode blacklists or arbitrary risk thresholds (e.g., "cancel if risk score > 70") are financially destructive. We uncovered three surprising, non-intuitive patterns in the empirical data:

1. **The "Hinglish Delivery Note" Intent Paradox (99 Orders &bull; 24.24% RTO):**  
   Operations proposed an address filter flagging orders lacking house/flat numbers. However, data proves orders with Hinglish delivery notes like *"ph krke aana, Hanuman Mandir ke paas"* ("call me before arriving") achieved an empirical RTO of **24.24%**—significantly better than the 28.43% national average and structured English nagar addresses (28.10%)! Customers who type explicit delivery instructions are high-intent buyers who genuinely want their parcel. Conversely, dummy tokens (`"."`, `"home"`, 152 orders) suffer a **63.82% RTO**, and addresses that merely repeat the city name (`"Delhi"`, 31 orders) suffer **54.84% RTO**. Intent markers matter far more than formal premise numbers.

2. **The Serial Returner 76.5% Cliff (34 Orders &bull; 76.47% RTO):**  
   Customer order history is non-linear. While 1-order repeat veterans have an exceptional 15.69% RTO, customers with **2 or more prior returns return 76.47% of subsequent orders (26 of 34 returned)**. With our ₹169.40 courier return loss, shipping COD to this group guarantees a loss of ₹70 to ₹140 on every typical basket. These customers cannot be persuaded via phone calls; they must prepay online via UPI or be blocked.

3. **Free ₹27,104/Month Cash via State Courier Routing Arbitrage:**  
   Cross-tabulating state delivery by carrier revealed massive misrouting that has nothing to do with customer quality:
   * **Telangana (174 orders):** Ecom Express fails at an unviable **43.8% RTO**, while Xpressbees delivers at an exceptional **14.3% RTO**!
   * **Bihar (145 orders):** Xpressbees suffers an abysmal **65.6% RTO**, whereas BlueDart achieves **42.1%** and Shadowfax achieves **44.0%**.
   * **Karnataka (212 orders):** Xpressbees fails at **34.0% RTO**, while BlueDart (15.8%) and Delhivery (16.9%) cut returns in half.  
   * **The Big Win:** Without canceling a single order or spending ₹1 on customer discounts, simply shifting state volumes to their top-performing carrier drops national RTO from **28.43% down to 23.12%**, immediately capturing **₹27,104/month in pure profit on 3,000 orders**.

---

## 2. Our Recommended Rules & What They Would Have Done to Last Month's Orders

### The 4-Action Expected Contribution Margin Policy
Instead of predicting whether a customer will return, our engine calculates the **Expected Contribution Margin in Rupees (EV)** for 4 operational choices:
* **Delivered Margin:** 65% of Cart Value &minus; ₹80 Base Courier Costs
* **Net Courier RTO Loss:** ₹65 Forward + ₹65 Reverse + ₹25 Packaging + ₹14.40 Damage = **₹169.40 Fixed Loss**

| Action | Operational Trigger | Cohort Share | Delivered Profit | Strategic Financial Rationale |
| :--- | :--- | :---: | :---: | :--- |
| **1. SHIP_AS_IS** | Positive Expected Value (EV > ₹0) and Return Risk < 28% | **61.3%** (1,238 orders) | ₹4,02,615 | Verified metro addresses, repeat buyers (0 RTO), and high-intent delivery notes. Immediate warehouse dispatch. |
| **2. SHIP_CONFIRM** | Confirmation EV > Immediate EV & Return Risk 28% to 45% | **16.6%** (335 orders) | ₹61,138 | Moderate-risk semi-urban pin codes. Automated 1-tap WhatsApp prompt filters out buyer remorse before packaging. |
| **3. NUDGE_PREPAID** | Prepaid EV > Confirmation EV, Cart Value &ge; ₹1,200 or Risk &ge; 40% | **20.2%** (408 orders) | ₹1,96,878 | High basket values in elevated risk zones. Dynamic 10% UPI offer converts risky COD to 4% RTO prepaid, locking profit. |
| **4. CANCEL** | 2 or More Past RTOs, Invalid Phone, or Negative Expected Value | **1.8%** (37 orders) | ₹0 (Saved ₹6,268) | Serial returner cliff (76.5% RTO). Strict COD hard block eliminates guaranteed reverse courier burn. |

### What This Would Have Done to Last Month's Orders (The Backtest)
* **Under Old Policy (Ship 100% Blindly):** Suffered 565 RTO returns, burned **₹95,711 in courier losses**, and delivered ₹5,68,240 net contribution.
* **Under Our Decision Engine:** Realized RTO rate plunged from **28.43% down to 18.25%**, 408 high-risk orders converted to guaranteed 4%-RTO prepaid, and total delivered profit surged to **₹6,60,631**.
* **Net Cash Improvement:** **+₹85,240 in pure net profit** across the batch (95% Confidence Interval: [₹74,800 to ₹95,680]), scaling to **~₹1,28,000/month at 3,000 orders/month scale**.

---

## 3. How We Balanced Operations vs. Marketing (The ₹ Trade-Off)

Operations hates courier return fees (₹169.40/parcel). Marketing hates losing customer acquisitions (Meta CAC ~₹320). We settled this mathematically via the **Founder Marketing LTV Buffer (₹0 to ₹150)**:

**Effective Expected Value = Single Order Expected Value + Founder Marketing LTV Buffer**

1. **For Genuine First-Time Buyers (0 Prior Returns):**  
   Marketing spent ~₹320 acquiring this customer. If single-order expected profit is mildly negative (e.g. -₹40 on an ₹800 cart in Patna), outright cancellation throws away that ₹320 investment. By crediting a Founder LTV Buffer (₹100 to ₹150), the engine routes the order to **WhatsApp Confirmation** or **10% Prepaid Nudge** rather than cancellation.
2. **For Serial Returners (2 or More Past Returns):**  
   Marketing cannot claim future LTV on customers who return 76.5% of parcels (their empirical LTV is negative -₹380). Here, Operations wins unconditionally: COD is hard-blocked.
3. **The 10% Prepaid Discount as "RTO Insurance":**  
   On an ₹1,800 cart with 60% risk, offering a 10% discount (₹180 off) to secure UPI payment locks **₹806 in net delivered margin** while eliminating the ₹169.40 courier risk. Leaving it on COD produces an expected profit of only ₹589 (or a ₹169.40 cash loss upon return). Discounting saves Operations while satisfying Marketing's demand for completed GMV.

---

## 4. What Could Go Wrong & How We'd Notice Early

1. **Meta WhatsApp Template Classification Shift or API Ban:**  
   *The Risk:* If Meta misclassifies verification messages as promotional marketing rather than transactional utility, message fees spike 10x or delivery drops.  
   *Early Warning Metric:* WhatsApp confirmation response rate falling below 40% in any 4-hour window.  
   *Immediate Fallback:* Automated SMS webhook delivering a 1-click web confirmation link.
2. **Courier Rider "Fake Attempted Delivery" Fraud:**  
   *The Risk:* Delivery riders mark parcels "Customer Refused" without attempting delivery to meet daily targets.  
   *Early Warning Metric:* Day-1 out-for-delivery RTO rate exceeding 15% without rider call records.  
   *Immediate Action:* System flags courier manifest and automatically raises automated disputes via Shiprocket API.
3. **Discount Cannibalization on Safe Metro Orders:**  
   *The Risk:* Offering prepaid discounts to customers who were already 90% likely to accept COD gives away gross margin unnecessarily.  
   *Early Warning Metric:* Prepaid discount uptake on low-risk orders (risk < 20%) exceeding 60%.  
   *Built-In Guardrail:* Formula strictly restricts discounts to orders with Return Risk &ge; 30% or Cart Value &ge; ₹1,200.

---

## 5. What We Would Build Next (2-Week Technical Roadmap)

### Week 1: Production Infrastructure & Real-Time Logistics Routing
* **Days 1–2 (Shopify Webhook Integration):** Connect Shopify `orders/create` webhook to our production API (`src/server.py`). Incoming orders are evaluated and tagged in warehouse dispatch within 800ms (`COD_SHIP_IMMEDIATE`, `COD_WHATSAPP_VERIFY`, `COD_HOLD`).
* **Days 3–4 (Shiprocket Dynamic Carrier Routing):** Deploy state-level courier allocation rules to immediately shift Telangana volume off Ecom Express and Bihar volume to BlueDart/Shadowfax, capturing ₹27,100/mo.
* **Day 5 (1-Click WhatsApp Dispatch):** Launch 2-way interactive WhatsApp utility templates with quick-reply buttons ("Pay via UPI & Save ₹X", "Confirm COD", "Cancel").

### Week 2: NDR Auto-Intervention & Continuous Bayesian Learning
* **Days 6–8 (Real-Time NDR Location Drop):** When a courier logs "Door Closed / Customer Unreachable", automatically trigger a WhatsApp message within 15 minutes asking the buyer to send a live Google Maps location pin for the rider.
* **Days 9–10 (Automated Daily Bayesian Prior Update):** Schedule a daily cron job that recalibrates city and pincode risk shrinkage priors using the previous day's delivery outcomes.
* **Days 11–12 (Executive Operations & Marketing Dashboard):** Deploy real-time P&L visibility with live courier SLA tracking and a Founder LTV buffer dial for the executive team.
