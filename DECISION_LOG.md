# Architectural Decision Log: COD Risk & Expected-Rupee ($\text{EV}$) Decision Engine

A running record of the foundational architectural, mathematical, and operational choices made in building the Keshava D2C COD Decision Engine, contrasting our choices against traditional heuristic and machine learning approaches.

---

## 1. Expected Rupee Value ($\text{EV}$) vs. Arbitrary Score Cutoffs (e.g., Score > 70)
* **Choice:** Evaluated every incoming COD order across 4 discrete actions in **Expected Contribution Rupees ($\text{EV}$)**:
  $$\text{Winning Action} = \arg\max \left( \text{EV}_{\text{ship}}, \text{EV}_{\text{confirm}}, \text{EV}_{\text{nudge}}, \text{EV}_{\text{cancel}} \right)$$
* **Alternatives Considered:** Standard risk score cutoff (e.g. cancel if score > 70); binary classification model (XGBoost predicting return 0 or 1).
* **Why We Picked It:**
  * Score cutoffs treat a ₹399 single scrunchie and a ₹2,499 premium hair combo identically if both originate from a 45% return-risk pincode.
  * For an ₹1,800 order with $p = 50\%$, delivered margin is ₹1,091 and net RTO bleed is ₹169.40. $\text{EV} = 0.50(1091) - 0.50(169.40) = \mathbf{+₹460.80}$. Rejecting it destroys profitable revenue!
  * For a ₹350 order with $p = 45\%$, delivered margin is ₹192, and $\text{EV} = \mathbf{+₹29.37}$ (razor-thin margin).
  * Expected value aligns Operations (protecting ₹169.40 courier loss) and Marketing (maximizing revenue) in a single financial currency.

---

## 2. Hierarchical Empirical Bayes (Beta-Binomial Shrinkage) vs. Raw Win Rates vs. Flat Global Average
* **Choice:** Implemented Beta-Binomial shrinkage pulling city-level RTO rates toward parent state priors ($m = 10$):
  $$\hat{p}_{\text{city}} = \frac{k_{\text{city}} + m \cdot \hat{p}_{\text{state}}}{n_{\text{city}} + m}$$
* **Alternatives Considered:** Raw empirical city RTO ($k/n$); flat national average (28.43%).
* **Why We Picked It:**
  * Small towns with $n = 2$ or $3$ orders suffer extreme variance (e.g. Madhubani with 3 orders and 3 RTOs $\implies 100\%$ raw rate; Darbhanga with 2 orders and 0 RTOs $\implies 0\%$).
  * Raw win rates permanently blacklist low-volume pincodes based on bad luck.
  * Flat national average ignores that Bihar has a 53.8% state RTO while Karnataka has 16.5%.
  * Empirical Bayes smooths Madhubani to a realistic **64.5%** and Darbhanga to **38.2%**, preserving genuine demand while respecting regional logistics realities.

---

## 3. Law of Total Probability in WhatsApp Reachability vs. Additive Funnels
* **Choice:** Formulated WhatsApp verification around a single reachable cohort ($r_{\text{reach}} = 65\%$):
  $$P(\text{Prepaid}) = r_{\text{reach}} \cdot \alpha, \quad P(\text{Fallback Confirm}) = r_{\text{reach}} \cdot (1 - \alpha), \quad P(\text{Unreachable}) = 1 - r_{\text{reach}}$$
* **Alternatives Considered:** Independent additive funnel ($45\% \text{ prepaid} + 55\% \times 65\% \text{ confirmation} = 80.75\%$).
* **Why We Picked It:**
  * In common AI drafts, funnels silently assumed 80.75% of high-risk customers actively respond.
  * In the real world, customers who don't answer calls or read WhatsApp cannot be reached by a secondary prompt.
  * Strictly respecting probability conservation prevents phantom revenue projections and accurately models unreachable order cancellations.

---

## 4. Relative Risk Reduction ($\gamma = 0.65$) vs. Flat 10% Post-Confirmation RTO
* **Choice:** Modeled WhatsApp confirmation as reducing behavioral risk relative to base risk:
  $$p_{\text{confirmed}} = p_{\text{base}} \times (1 - \gamma)$$
* **Alternatives Considered:** Setting post-confirmation RTO to a static 10% across all orders.
* **Why We Picked It:**
  * A customer return has two distinct drivers: **Behavioral Remorse** (customer changes mind) and **Logistics Failure** (unpaved roads, rider fake attempts, unreachable locations).
  * WhatsApp confirmation cures remorse, but it does *not* fix courier infrastructure.
  * A confirmed order in rural Bihar ($p = 60\%$) drops to $21.0\%$ RTO; a confirmed order in Bengaluru ($p = 20\%$) drops to $7.0\%$ RTO.

---

## 5. Dynamic Risk-Proportional Discounting (5%–12%) vs. Flat 10% Coupon
* **Choice:** Calibrated prepaid discount formula:
  $$d(p) = \text{round}\left(\min\left(₹200, \max\left(₹50, 0.10 \cdot \text{OV}\right)\right)\right)$$
* **Alternatives Considered:** Flat 10% coupon code across all checkout traffic; fixed ₹100 discount.
* **Why We Picked It:**
  * Blanket coupons give away margin to safe metro customers who would have accepted COD anyway.
  * Risk-proportional discounts act as **RTO Insurance**: On an ₹1,800 order with 60% risk, giving a ₹180 discount locks ₹806 in net delivered margin, saving ₹169.40 in courier return fees.

---

## 6. Serial Returner Hard COD Block (`customer_prior_rto >= 2`) vs. Soft Warning
* **Choice:** Hard COD block on any buyer with $\ge 2$ prior RTOs. They must prepay via UPI or the parcel is canceled pre-dispatch.
* **Alternatives Considered:** Adding a ₹50 COD convenience fee; sending a WhatsApp confirmation prompt.
* **Why We Picked It:**
  * Data revealed a steep non-linear cliff: buyers with $\ge 2$ prior RTOs return **76.47% of parcels (26 of 34 returned)**.
  * At 76.5% return rate, shipping COD produces a guaranteed net loss on any cart under ₹1,050.
  * Serial returners reply "Yes" on WhatsApp and still refuse at doorstep. COD must be blocked unconditionally.

---

## 7. Address Intent NLP vs. Naive Length/Digit Regex (The Hinglish Intent Paradox)
* **Choice:** Built 15 empirical token classifiers in `src/heuristics.py` to identify intent markers (`"ph krke aana"`, `"ke peeche wala ghar"`).
* **Alternatives Considered:** Standard regex checking `len(address) >= 20 and has_digits`; heavy BERT / LLM text classifier.
* **Why We Picked It:**
  * Standard regexes catastrophically rejected `"ph krke aana, Big Bazaar ke paas"` because it had no digits. Yet data proved this cohort has a **24.24% RTO rate—better than the 28.43% national average**!
  * LLM classifiers add 1,500ms API latency to order ingestion and incur per-token SaaS fees.
  * Intent-aware regex executes in **< 0.2ms**, costs ₹0, and prevents false rejections of high-intent buyers.

---

## 8. State-Level Courier Routing Arbitrage vs. Pincode Blacklisting
* **Choice:** Dynamically allocated state order volume to lowest-RTO carriers via Shiprocket routing matrix.
* **Alternatives Considered:** Blacklisting all shipments to Bihar and Eastern UP; round-robin courier split.
* **Why We Picked It:**
  * Blacklisting Bihar forfeits 145 orders and ₹1.2L in revenue.
  * In Bihar, Xpressbees fails at 65.6% RTO, but BlueDart delivers at 42.1% RTO.
  * In Telangana, Ecom Express fails at 43.8% RTO, but Xpressbees delivers at 14.3% RTO.
  * Re-routing state volume drops national returns from **28.43% to 23.12%**, capturing **₹27,104/month with zero cancellations**.

---

## 9. Founder Marketing LTV Buffer ($\Delta_{\text{CAC}}$) vs. Pure Operations Mode
* **Choice:** Added a tunable ₹0–₹300 buffer for first-time buyers (`prior_orders == 0`) without extending it to serial returners.
* **Alternatives Considered:** Rigid Operations mode (cancel any order where $\text{EV} < 0$); unrestricted marketing mode (ship all orders).
* **Why We Picked It:**
  * Marketing spends ₹320 CAC to acquire a customer. Canceling over a -₹30 single-order bleed destroys a ₹320 acquisition investment.
  * The buffer routes borderline first-time buyers to WhatsApp confirmation or 10% UPI offer rather than immediate cancellation.

---

## 10. Zero-Rupee Warranty / Replacement Rule Bypass vs. Raw EV Calculation
* **Choice:** Added hardcoded mathematical bypass for zero-rupee orders (`order_value == 0`).
* **Alternatives Considered:** Allowing standard EV math to evaluate ₹0 orders.
* **Why We Picked It:**
  * Standard math on ₹0 orders yields delivered margin $D = 0.65(0) - 80 = -₹80 \implies \text{EV} < 0 \implies \text{CANCEL}$.
  * Auto-canceling warranty replacements or influencer PR seedings triggers severe customer support crises and brand reputation damage.

---

## 11. Client-Side Paginated Table (25/50/100/All) vs. Unpaginated DOM Freeze
* **Choice:** Rendered the 2,018-order store batch using responsive client-side pagination with in-memory filtering.
* **Alternatives Considered:** Dumping all 2,018 `<tr>` rows directly into DOM; server-side database pagination with API roundtrips.
* **Why We Picked It:**
  * Injecting 2,018 rows into innerHTML freezes the browser for 3–5 seconds and causes choppy scrolling.
  * Client-side pagination slices the array in < 2ms, maintains selection state across pages, and works 100% offline.

---

## 12. 1-Click WhatsApp Direct Deep Link (`wa.me`) vs. Manual Copy-Paste
* **Choice:** Added an emerald `📲 1-Click Msg` button on every customer card and table row that opens `https://wa.me/...` directly with pre-filled message text.
* **Alternatives Considered:** Displaying text on screen for warehouse operators to copy-paste manually into WhatsApp.
* **Why We Picked It:**
  * Manual copy-pasting takes 45–60 seconds per customer and leads to typing errors and mismatched phone numbers.
  * 1-click deep linking takes 1 second, streamlining warehouse dispatch operations.

---

## 13. Unique Number Search Engine (Order ID + Mobile Phone) vs. Generic Single-Column Search
* **Choice:** Unified search input matching unique Order ID (`#KT...`) and 10-digit phone digits with instant auto-selection of the matching card.
* **Alternatives Considered:** Separate search inputs for Order ID, Customer Name, and Phone.
* **Why We Picked It:**
  * Warehouse operators scan barcode labels (Order ID) while customer support reps receive incoming calls/messages (Phone number).
  * A unified unique number search handles both workflows instantly.

---

## 14. Dual Production Architecture (Port 8501 Web UI + Port 8000 REST/Webhook Backend)
* **Choice:** Deployed lightweight standalone UI on Port 8501 paired with a thread-safe Python REST API on Port 8000.
* **Alternatives Considered:** Pure frontend mock without backend; monolithic Flask/Django application.
* **Why We Picked It:**
  * The standalone dashboard operates independently with zero dependencies.
  * The REST API provides real-time JSON order evaluation and cryptographic HMAC-SHA256 webhook listeners for Shopify and Razorpay with idempotency locking.
