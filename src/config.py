"""Configuration schema and loader with Pydantic validation."""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field, computed_field


class FinancialsConfig(BaseModel):
    gross_margin: float = Field(0.62, ge=0.0, le=1.0, description="Gross contribution margin fraction")
    forward_shipping: float = Field(65.0, ge=0.0, description="Forward shipping charge in ₹")
    return_shipping: float = Field(65.0, ge=0.0, description="Return shipping charge in ₹")
    packaging_cost: float = Field(25.0, ge=0.0, description="Packaging & handling cost in ₹")
    damage_rate: float = Field(0.08, ge=0.0, le=1.0, description="Damage rate of returned merchandise")
    damaged_product_cost: float = Field(180.0, ge=0.0, description="Cost of unsellable damaged unit in ₹")
    prepaid_rto_rate: float = Field(0.04, ge=0.0, le=1.0, description="Baseline RTO rate on prepaid orders")

    @computed_field
    @property
    def rto_loss(self) -> float:
        """Net rupee loss incurred on every RTO order (L).
        L = Forward Shipping + Return Shipping + Packaging + (Damage Rate * Product Cost)
        """
        return (
            self.forward_shipping
            + self.return_shipping
            + self.packaging_cost
            + (self.damage_rate * self.damaged_product_cost)
        )


class OperationalFunnelConfig(BaseModel):
    whatsapp_reachability: float = Field(0.65, ge=0.0, le=1.0, description="Baseline WhatsApp reachability")
    confirmation_risk_reduction: float = Field(0.65, ge=0.0, le=1.0, description="Relative RTO reduction gamma")
    prepaid_discount_share: float = Field(0.35, ge=0.0, le=1.0, description="Share of gross RTO savings offered")
    max_prepaid_discount: float = Field(100.0, ge=0.0, description="Maximum prepaid discount cap in ₹")
    prepaid_discount_step: float = Field(25.0, ge=1.0, description="Prepaid discount step rounding in ₹")
    prepaid_take_rate: float = Field(0.45, ge=0.0, le=1.0, description="Prepaid acceptance rate among reachable")
    cod_confirm_take_rate: float = Field(0.70, ge=0.0, le=1.0, description="COD confirmation rate on fallback")


class MarketingCompromiseConfig(BaseModel):
    first_time_customer_ltv_buffer: float = Field(150.0, ge=0.0, le=500.0, description="Founder LTV buffer in ₹")
    serial_rto_hard_cap: int = Field(2, ge=1, le=5, description="Prior RTO count for mandatory COD block")
    high_ticket_unit_price_threshold: float = Field(700.0, ge=100.0, description="Per-unit price anomaly threshold")
    bayesian_shrinkage_weight: float = Field(10.0, ge=1.0, description="Empirical Bayes pseudo-weight m")


class AppConfig(BaseModel):
    financials: FinancialsConfig = Field(default_factory=FinancialsConfig)
    operational_funnel: OperationalFunnelConfig = Field(default_factory=OperationalFunnelConfig)
    marketing_compromise: MarketingCompromiseConfig = Field(default_factory=MarketingCompromiseConfig)

    def profit_if_delivered(self, order_value: float) -> float:
        """Calculate net delivery contribution margin D(OV) in ₹.
        D = (gross_margin * order_value) - packaging_cost
        """
        if order_value <= 0:
            return 0.0
        return (self.financials.gross_margin * order_value) - self.financials.packaging_cost

    def rto_loss(self) -> float:
        """Return net RTO loss L in ₹."""
        return self.financials.rto_loss

    def break_even_risk(self, order_value: float) -> float:
        """Calculate break-even RTO probability: p* = D / (D + L)."""
        d = self.profit_if_delivered(order_value)
        l = self.rto_loss()
        if d + l <= 0:
            return 0.0
        return d / (d + l)

    @property
    def costs(self):
        class CostAdapter:
            def __init__(self, fin: FinancialsConfig):
                self._fin = fin
            @property
            def forward_shipping(self) -> float:
                return self._fin.forward_shipping
            @forward_shipping.setter
            def forward_shipping(self, val: float):
                self._fin.forward_shipping = val
            @property
            def reverse_shipping(self) -> float:
                return self._fin.reverse_shipping
            @reverse_shipping.setter
            def reverse_shipping(self, val: float):
                self._fin.reverse_shipping = val
            @property
            def packaging_cost(self) -> float:
                return self._fin.packaging_cost
            @packaging_cost.setter
            def packaging_cost(self, val: float):
                self._fin.packaging_cost = val
            @property
            def damaged_return_rate(self) -> float:
                return self._fin.damage_rate
            @damaged_return_rate.setter
            def damaged_return_rate(self, val: float):
                self._fin.damage_rate = val
            @property
            def damaged_product_replacement_cost(self) -> float:
                return self._fin.damaged_product_cost
            @damaged_product_replacement_cost.setter
            def damaged_product_replacement_cost(self, val: float):
                self._fin.damaged_product_cost = val
            @property
            def net_rto_loss(self) -> float:
                return self._fin.rto_loss
        return CostAdapter(self.financials)

    @property
    def marketing(self):
        class MarketingAdapter:
            def __init__(self, mkt: MarketingCompromiseConfig):
                self._mkt = mkt
            @property
            def founder_ltv_buffer(self) -> float:
                return self._mkt.first_time_customer_ltv_buffer
            @founder_ltv_buffer.setter
            def founder_ltv_buffer(self, val: float):
                self._mkt.first_time_customer_ltv_buffer = val
        return MarketingAdapter(self.marketing_compromise)

    @property
    def whatsapp(self):
        class WhatsAppAdapter:
            def __init__(self, fun: OperationalFunnelConfig):
                self._fun = fun
            @property
            def reachability_rate(self) -> float:
                return self._fun.whatsapp_reachability
            @reachability_rate.setter
            def reachability_rate(self, val: float):
                self._fun.whatsapp_reachability = val
            @property
            def prepaid_acceptance_rate(self) -> float:
                return self._fun.prepaid_take_rate
            @prepaid_acceptance_rate.setter
            def prepaid_acceptance_rate(self, val: float):
                self._fun.prepaid_take_rate = val
        return WhatsAppAdapter(self.operational_funnel)


DecisionEngineConfig = AppConfig


def get_default_config() -> AppConfig:
    """Return default configuration."""
    return AppConfig()



DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load and validate configuration from YAML file."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        # Fallback to default instantiated model
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return AppConfig.model_validate(data)


def save_config(config: AppConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration model back to YAML file."""
    path = config_path or DEFAULT_CONFIG_PATH
    # Export dict excluding computed fields
    data = {
        "financials": {
            "gross_margin": config.financials.gross_margin,
            "forward_shipping": config.financials.forward_shipping,
            "return_shipping": config.financials.return_shipping,
            "packaging_cost": config.financials.packaging_cost,
            "damage_rate": config.financials.damage_rate,
            "damaged_product_cost": config.financials.damaged_product_cost,
            "prepaid_rto_rate": config.financials.prepaid_rto_rate,
        },
        "operational_funnel": {
            "whatsapp_reachability": config.operational_funnel.whatsapp_reachability,
            "confirmation_risk_reduction": config.operational_funnel.confirmation_risk_reduction,
            "prepaid_discount_share": config.operational_funnel.prepaid_discount_share,
            "max_prepaid_discount": config.operational_funnel.max_prepaid_discount,
            "prepaid_discount_step": config.operational_funnel.prepaid_discount_step,
            "prepaid_take_rate": config.operational_funnel.prepaid_take_rate,
            "cod_confirm_take_rate": config.operational_funnel.cod_confirm_take_rate,
        },
        "marketing_compromise": {
            "first_time_customer_ltv_buffer": config.marketing_compromise.first_time_customer_ltv_buffer,
            "serial_rto_hard_cap": config.marketing_compromise.serial_rto_hard_cap,
            "high_ticket_unit_price_threshold": config.marketing_compromise.high_ticket_unit_price_threshold,
            "bayesian_shrinkage_weight": config.marketing_compromise.bayesian_shrinkage_weight,
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
