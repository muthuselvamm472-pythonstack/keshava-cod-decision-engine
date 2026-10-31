"""Expected Value (EV) decision engine computing exact contribution margin in ₹."""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from src.config import AppConfig
from src.heuristics import estimate_order_rto_risk, EmpiricalBayesPriorEstimator


class DecisionAction:
    SHIP_AS_IS = "SHIP_AS_IS"
    SHIP_CONFIRM = "SHIP_CONFIRM"
    NUDGE_PREPAID = "NUDGE_PREPAID"
    CANCEL = "CANCEL"


class DecisionResult:
    """Encapsulates the decision engine output for an order."""

    def __init__(
        self,
        order_id: str,
        winning_action: str,
        winning_action_label: str,
        plain_english_reason: str,
        ev_ship: float,
        ev_confirm: float,
        ev_nudge: float,
        ev_cancel: float,
        winning_ev: float,
        baseline_risk: float,
        confirmed_risk: float,
        prepaid_discount: float,
        profit_if_delivered: float,
        rto_loss: float,
        break_even_risk: float,
        diagnostics: Dict[str, Any],
        order_raw: Optional[Dict[str, Any]] = None,
    ):
        self.order_id = order_id
        self.winning_action = winning_action
        self.winning_action_label = winning_action_label
        self.plain_english_reason = plain_english_reason
        self.ev_ship = round(ev_ship, 2)
        self.ev_confirm = round(ev_confirm, 2)
        self.ev_nudge = round(ev_nudge, 2)
        self.ev_cancel = round(ev_cancel, 2)
        self.winning_ev = round(winning_ev, 2)
        self.baseline_risk = round(baseline_risk, 4)
        self.confirmed_risk = round(confirmed_risk, 4)
        self.prepaid_discount = round(prepaid_discount, 2)
        self.profit_if_delivered = round(profit_if_delivered, 2)
        self.rto_loss = round(rto_loss, 2)
        self.break_even_risk = round(break_even_risk, 4)
        self.diagnostics = diagnostics
        self.order_raw = order_raw or {}

    @property
    def recommended_action(self) -> str:
        return self.winning_action

    @property
    def recommended_ev(self) -> float:
        return self.winning_ev

    @property
    def rto_risk(self) -> float:
        return self.baseline_risk

    @property
    def reason(self) -> str:
        return self.plain_english_reason

    @property
    def ev_ship_as_is(self) -> float:
        return self.ev_ship

    @property
    def ev_ship_confirm(self) -> float:
        return self.ev_confirm

    @property
    def ev_nudge_prepaid(self) -> float:
        return self.ev_nudge

    @property
    def ev_delta_vs_ship(self) -> float:
        return round(self.winning_ev - self.ev_ship, 2)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "order_id": self.order_id,
            "action": self.winning_action,
            "winning_action": self.winning_action,
            "winning_action_label": self.winning_action_label,
            "recommended_action": self.winning_action,
            "reason": self.plain_english_reason,
            "plain_english_reason": self.plain_english_reason,
            "recommended_ev": self.winning_ev,
            "winning_ev": self.winning_ev,
            "ev_delta_vs_ship": self.ev_delta_vs_ship,
            "rto_risk": self.baseline_risk,
            "baseline_risk": self.baseline_risk,
            "confirmed_risk": self.confirmed_risk,
            "ev_ship": self.ev_ship,
            "ev_confirm": self.ev_confirm,
            "ev_nudge": self.ev_nudge,
            "ev_cancel": self.ev_cancel,
            "prepaid_discount": self.prepaid_discount,
            "profit_if_delivered": self.profit_if_delivered,
            "rto_loss": self.rto_loss,
            "break_even_risk": self.break_even_risk,
        }
        # Populate raw order fields
        for k in ["customer_name", "city", "state", "pincode", "order_value", "customer_prior_orders", "customer_prior_rto", "phone", "shipping_address"]:
            if k in self.order_raw:
                d[k] = self.order_raw[k]
        d.update(self.diagnostics)
        return d


EvaluationResult = DecisionResult


def calculate_dynamic_prepaid_discount(
    p_risk: float,
    d_profit: float,
    l_loss: float,
    config: AppConfig,
) -> float:
    """Calculate risk-proportional prepaid discount in ₹.
    
    Gross Savings = (p - 0.04) * (D + L)
    Discount = 35% of gross savings, capped at max_prepaid_discount, rounded to step.
    """
    if p_risk <= 0.20:
        return 0.0  # Safe orders ship as-is, no discount waste

    gross_savings = (p_risk - config.financials.prepaid_rto_rate) * (d_profit + l_loss)
    if gross_savings <= 0:
        return 0.0

    target_discount = gross_savings * config.operational_funnel.prepaid_discount_share
    capped = min(config.operational_funnel.max_prepaid_discount, target_discount)
    
    step = config.operational_funnel.prepaid_discount_step
    rounded = round(capped / step) * step
    return float(np.clip(rounded, 0.0, config.operational_funnel.max_prepaid_discount))


def evaluate_order(
    order: Dict[str, Any],
    config: AppConfig,
    eb_estimator: Optional[EmpiricalBayesPriorEstimator] = None,
) -> DecisionResult:
    """Evaluate a single COD order and output the optimal Expected-Profit action."""
    order_id = str(order.get("order_id", "NEW_ORDER"))
    order_value = float(order.get("order_value", 0.0) or 0.0)
    prior_orders = int(order.get("customer_prior_orders", 0) or 0)
    prior_rto = int(order.get("customer_prior_rto", 0) or 0)
    phone_reachable = bool(order.get("phone_reachable", True))

    # Base financial parameters
    d_base = config.profit_if_delivered(order_value)
    l_loss = config.rto_loss()
    p_star = config.break_even_risk(order_value)

    # Add founder Marketing CAC buffer for genuine first-time customers
    ltv_buffer = config.marketing_compromise.first_time_customer_ltv_buffer if prior_orders == 0 else 0.0
    d_adj = d_base + ltv_buffer

    # Check Zero-Rupee Replacement Bypass
    if order_value <= 0 or order.get("is_replacement_bypass", False):
        return DecisionResult(
            order_id=order_id,
            winning_action="SHIP_AS_IS",
            winning_action_label="Ship as-is",
            plain_english_reason="Replacement / Warranty / PR Seeding order (₹0 value) bypassed from financial rejection rules to protect customer goodwill.",
            ev_ship=0.0,
            ev_confirm=0.0,
            ev_nudge=0.0,
            ev_cancel=0.0,
            winning_ev=0.0,
            baseline_risk=0.04,
            confirmed_risk=0.02,
            prepaid_discount=0.0,
            profit_if_delivered=0.0,
            rto_loss=l_loss,
            break_even_risk=0.0,
            diagnostics={"bypass": True, "category": "REPLACEMENT_BYPASS"},
        )

    # Estimate calibrated RTO risk p
    p_risk, diagnostics = estimate_order_rto_risk(
        order,
        eb_estimator=eb_estimator,
        serial_rto_cap=config.marketing_compromise.serial_rto_hard_cap,
        unit_price_threshold=config.marketing_compromise.high_ticket_unit_price_threshold,
    )

    # 1. Action: Ship as-is
    ev_ship = (1.0 - p_risk) * d_adj - p_risk * l_loss

    # 2. Action: Ship after confirmation (relative risk reduction gamma)
    gamma = config.operational_funnel.confirmation_risk_reduction
    p_confirmed = p_risk * (1.0 - gamma)
    ev_delivery_confirmed = (1.0 - p_confirmed) * d_adj - p_confirmed * l_loss
    
    r_reach = config.operational_funnel.whatsapp_reachability if phone_reachable else 0.0
    k_confirm = config.operational_funnel.cod_confirm_take_rate

    # If customer replies NO or timeouts, order cancelled pre-dispatch (EV = 0)
    ev_confirm = r_reach * k_confirm * max(0.0, ev_delivery_confirmed)

    # 3. Action: Nudge to prepaid
    prepaid_discount = calculate_dynamic_prepaid_discount(p_risk, d_adj, l_loss, config)
    d_prepaid = max(0.0, d_adj - prepaid_discount)
    p_prepaid = config.financials.prepaid_rto_rate
    ev_paid = (1.0 - p_prepaid) * d_prepaid - p_prepaid * l_loss

    alpha = config.operational_funnel.prepaid_take_rate
    # Conditional Funnel Math: Both draw from the same reachable pool r_reach
    # Alpha of reachable accept prepaid; remaining (1 - alpha) fallback to COD confirmation
    ev_nudge = r_reach * (
        alpha * ev_paid + (1.0 - alpha) * k_confirm * max(0.0, ev_delivery_confirmed)
    )

    # 4. Action: Hold / cancel
    ev_cancel = 0.0

    # Policy Enforcement: Serial Returner Hard Cap
    is_serial_rto = prior_rto >= config.marketing_compromise.serial_rto_hard_cap
    if is_serial_rto:
        # Strict COD Block: only prepaid or cancel allowed
        ev_ship = -999.0
        ev_confirm = -999.0

    # Policy Enforcement: Unreachable Phone
    if not phone_reachable:
        ev_confirm = -999.0
        ev_nudge = -999.0

    # Determine Winning Action (Argmax)
    actions = [
        (DecisionAction.SHIP_AS_IS, "Ship as-is", ev_ship),
        (DecisionAction.SHIP_CONFIRM, "Ship after confirmation", ev_confirm),
        (DecisionAction.NUDGE_PREPAID, "Nudge to prepaid", ev_nudge),
        (DecisionAction.CANCEL, "Hold / cancel", ev_cancel),
    ]
    actions.sort(key=lambda x: x[2], reverse=True)
    best_action, best_label, best_ev = actions[0]

    # Generate Plain-English Financial Rationale
    if is_serial_rto:
        if best_action == DecisionAction.NUDGE_PREPAID and ev_nudge > 10.0:
            reason = f"Customer has {prior_rto} prior RTOs (76.5% return rate cliff); COD blocked to protect contribution margin, offering ₹{int(prepaid_discount)} prepaid discount to convert safely."
        else:
            best_action = DecisionAction.CANCEL
            best_label = "Hold / cancel"
            best_ev = 0.0
            reason = f"Customer has {prior_rto} prior RTOs (76.5% return rate cliff); COD held/cancelled to avoid burning ₹{int(l_loss)} in reverse shipping and damaged inventory."
    elif not phone_reachable:
        if ev_ship > 0:
            reason = f"Phone number has invalid length preventing WhatsApp contact; proceeding to ship as-is based on positive expected contribution of ₹{int(ev_ship)}."
        else:
            best_action = DecisionAction.CANCEL
            best_label = "Hold / cancel"
            best_ev = 0.0
            reason = f"Invalid/truncated 9-digit phone prevents WhatsApp verification; order held/cancelled to avoid negative expected contribution of ₹{int(ev_ship)}."
    elif best_action == DecisionAction.SHIP_AS_IS:
        reason = f"Expected contribution of shipping immediately (₹{int(ev_ship)}) exceeds WhatsApp verification delays, backed by verified address quality and low baseline risk ({p_risk:.1%})."
    elif best_action == DecisionAction.NUDGE_PREPAID:
        reason = f"High order value (₹{int(order_value)}) and elevated risk ({p_risk:.1%}) yield ₹{int(ev_nudge)} net expected value under ₹{int(prepaid_discount)} prepaid discount with WhatsApp COD fallback."
    elif best_action == DecisionAction.SHIP_CONFIRM:
        reason = f"Address signals reflect moderate risk ({p_risk:.1%}); WhatsApp confirmation filters out buyer remorse, lifting expected contribution from ₹{int(ev_ship)} to ₹{int(ev_confirm)}."
    else:
        reason = f"High RTO probability ({p_risk:.1%}) exceeds break-even threshold ({p_star:.1%}); order held to eliminate ₹{int(l_loss)} reverse logistics bleed."

    return DecisionResult(
        order_id=order_id,
        winning_action=best_action,
        winning_action_label=best_label,
        plain_english_reason=reason,
        ev_ship=ev_ship if ev_ship != -999.0 else -l_loss,
        ev_confirm=ev_confirm if ev_confirm != -999.0 else 0.0,
        ev_nudge=ev_nudge if ev_nudge != -999.0 else 0.0,
        ev_cancel=0.0,
        winning_ev=best_ev,
        baseline_risk=p_risk,
        confirmed_risk=p_confirmed,
        prepaid_discount=prepaid_discount,
        profit_if_delivered=d_adj,
        rto_loss=l_loss,
        break_even_risk=p_star,
        diagnostics=diagnostics,
        order_raw=order,
    )


def evaluate_cohort(
    cohort_df_or_records: Any,
    config: AppConfig,
    eb_estimator: Optional[EmpiricalBayesPriorEstimator] = None,
) -> List[DecisionResult]:
    """Evaluate an entire batch or DataFrame of orders."""
    import pandas as pd
    if isinstance(cohort_df_or_records, pd.DataFrame):
        records = cohort_df_or_records.to_dict("records")
    else:
        records = cohort_df_or_records

    results = []
    for row in records:
        res = evaluate_order(row, config, eb_estimator=eb_estimator)
        results.append(res)
    return results

