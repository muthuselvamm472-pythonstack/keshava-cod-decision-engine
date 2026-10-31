"""WhatsApp Confirmation & Prepaid Nudge State Machine with Multi-Language Support."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple


TEMPLATES = {
    "English": {
        "confirm_outbound": (
            "Hi {customer_name}! Thank you for placing your Cash on Delivery order with *Keshava Haircare*.\n\n"
            "Order ID: *{order_id}*\n"
            "Items: {items}\n"
            "Amount to Pay at Door: *₹{order_value}*\n\n"
            "To help our rider deliver safely to *{city}*, please confirm if you will be available to receive this parcel."
        ),
        "prepaid_outbound": (
            "Hi {customer_name}! Special instant savings on your *Keshava Haircare* order *{order_id}*.\n\n"
            "Pay online right now and get an *instant ₹{discount} discount* on your cart! You only pay *₹{discounted_value}* (Save ₹{discount}).\n\n"
            "Prepaid orders get priority dispatch within 6 hours.\n"
            "Pay securely: {payment_link}\n\n"
            "Prefer COD? Reply *YES* to dispatch as regular Cash on Delivery."
        ),
        "reply_yes": "Thank you, {customer_name}! Your COD order has been confirmed and queued for priority dispatch.",
        "reply_no": "We understand! Your order *{order_id}* has been cancelled. No charges will be incurred. We hope to serve you again soon!",
        "reply_paid": "Payment received! ₹{discount} discount applied. Your order *{order_id}* has been converted to Prepaid and will be dispatched today.",
        "reply_random": "We received your message: \"{text}\". Our delivery team typically arrives within 2-4 working days. Please tap below to confirm your delivery:",
        "reminder_4h": "Gentle reminder: Your ₹{discount} discount link for order *{order_id}* expires shortly: {payment_link}",
        "timeout_24h": "Order *{order_id}* has been placed on hold as we did not receive confirmation within 24 hours. Tap to verify or contact support.",
    },
    "Hinglish": {
        "confirm_outbound": (
            "Namaste {customer_name} ji! *Keshava Haircare* se aapka COD order place karne ke liye dhanyavaad.\n\n"
            "Order ID: *{order_id}*\n"
            "Items: {items}\n"
            "COD Amount: *₹{order_value}*\n\n"
            "Rider delivery ke samay parcel receive karne ke liye kya aap available rahenge? Please confirm karein."
        ),
        "prepaid_outbound": (
            "Namaste {customer_name} ji! Aapke *Keshava Haircare* order *{order_id}* par ek exclusive offer hai.\n\n"
            "Agar aap abhi online pay karte hain, toh aapko milega *flat ₹{discount} OFF*! Aapko sirf *₹{discounted_value}* pay karna hoga.\n\n"
            "Prepaid orders fast courier se 6 ghante mein dispatch hote hain.\n"
            "Payment link: {payment_link}\n\n"
            "Agar COD hi chahiye toh bas *YES* reply karein."
        ),
        "reply_yes": "Shukriya {customer_name} ji! Aapka COD order confirm ho gaya hai aur packaging ke liye bhej diya gaya hai.",
        "reply_no": "Ji theek hai! Aapka order *{order_id}* cancel kar diya gaya hai. Koi charges nahi lagenge. Future mein dobara welcome hai!",
        "reply_paid": "Payment mil gaya! ₹{discount} discount deduct ho gaya hai. Aapka order ab Prepaid mark ho chuka hai aur priority se deliver hoga.",
        "reply_random": "Aapka message mila: \"{text}\". Normal delivery time 2 se 4 din ka hai. Order confirm karne ke liye neeche button dabayein:",
        "reminder_4h": "Reminder: Order *{order_id}* ka ₹{discount} discount offer expire ho raha hai. Abhi pay karein: {payment_link}",
        "timeout_24h": "Order *{order_id}* hold par daal diya gaya hai kyunki 24 ghante mein confirmation nahi mila.",
    },
    "Hindi": {
        "confirm_outbound": (
            "नमस्ते {customer_name} जी! *केशव हेयरकेयर* से आपका कैश ऑन डिलीवरी ऑर्डर प्राप्त हुआ।\n\n"
            "ऑर्डर संख्या: *{order_id}*\n"
            "सामान: {items}\n"
            "भुगतान राशि: *₹{order_value}*\n\n"
            "कृपया पुष्टि करें कि क्या आप डिलीवरी के समय पार्सल प्राप्त करने के लिए उपलब्ध रहेंगे?"
        ),
        "prepaid_outbound": (
            "नमस्ते {customer_name} जी! आपके ऑर्डर *{order_id}* पर विशेष छूट उपलब्ध है।\n\n"
            "अभी ऑनलाइन भुगतान करने पर *सीधे ₹{discount} की छूट* पाएं! आपको केवल *₹{discounted_value}* देना होगा।\n\n"
            "प्रीपेड ऑर्डर 6 घंटे में प्राथमिकता से भेजे जाते हैं।\n"
            "भुगतान लिंक: {payment_link}\n\n"
            "कैश ऑन डिलीवरी के लिए *हाँ (YES)* लिखकर भेजें।"
        ),
        "reply_yes": "धन्यवाद {customer_name} जी! आपका ऑर्डर स्वीकृत हो गया है और प्रेषण के लिए तैयार है।",
        "reply_no": "आपका ऑर्डर *{order_id}* रद्द कर दिया गया है। कोई शुल्क नहीं लिया जाएगा।",
        "reply_paid": "भुगतान सफल! ₹{discount} की छूट लागू हो गई है। ऑर्डर प्रीपेड श्रेणी में भेज दिया गया है।",
        "reply_random": "आपका संदेश प्राप्त हुआ: \"{text}\"। डिलीवरी 2-4 दिनों में होगी। कृपया नीचे दिए विकल्प से पुष्टि करें:",
        "reminder_4h": "स्मरण पत्र: आपके ऑर्डर *{order_id}* पर ₹{discount} की छूट का लिंक समाप्त होने वाला है: {payment_link}",
        "timeout_24h": "24 घंटे में कोई उत्तर न मिलने के कारण ऑर्डर *{order_id}* रोक दिया गया है।",
    },
}


class WhatsAppSession:
    """Manages chat state, messages, and state machine transitions for an order."""

    def __init__(
        self,
        order: Dict[str, Any],
        action_type: str,
        discount: float = 50.0,
        language: str = "English",
    ):
        self.order = order
        self.order_id = str(order.get("order_id", "KT100000"))
        self.customer_name = str(order.get("customer_name", "Customer"))
        self.city = str(order.get("city", "India"))
        self.items = str(order.get("items", "Haircare Products"))
        self.order_value = float(order.get("order_value", 649.0))
        self.discount = float(discount)
        self.discounted_value = max(0.0, self.order_value - self.discount)
        self.language = language
        self.action_type = action_type  # 'CONFIRM_COD' or 'NUDGE_PREPAID'
        
        self.state = "OUTBOUND_SENT"
        self.chat_history: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        
        # Send initial outbound message
        self._send_initial_message()

    def _send_initial_message(self) -> None:
        lang_dict = TEMPLATES.get(self.language, TEMPLATES["English"])
        payment_link = f"https://pay.keshava.in/checkout?id={self.order_id}&disc={int(self.discount)}"
        
        if self.action_type == "NUDGE_PREPAID" and self.discount > 0:
            text = lang_dict["prepaid_outbound"].format(
                customer_name=self.customer_name,
                order_id=self.order_id,
                items=self.items,
                discount=int(self.discount),
                discounted_value=int(self.discounted_value),
                payment_link=payment_link,
            )
        else:
            text = lang_dict["confirm_outbound"].format(
                customer_name=self.customer_name,
                order_id=self.order_id,
                items=self.items,
                order_value=int(self.order_value),
                city=self.city,
            )

        self.chat_history.append({
            "sender": "bot",
            "text": text,
            "timestamp": self.created_at.strftime("%I:%M %p"),
            "type": "outbound",
        })

    def handle_customer_action(self, action_event: str, custom_text: Optional[str] = None) -> None:
        """State machine handler for interactive simulator buttons."""
        now_str = datetime.now().strftime("%I:%M %p")
        lang_dict = TEMPLATES.get(self.language, TEMPLATES["English"])
        payment_link = f"https://pay.keshava.in/checkout?id={self.order_id}&disc={int(self.discount)}"

        if action_event == "REPLY_YES":
            self.state = "CONFIRMED_COD_DISPATCH"
            self.chat_history.append({
                "sender": "user",
                "text": "YES, please deliver COD",
                "timestamp": now_str,
                "type": "inbound",
            })
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["reply_yes"].format(customer_name=self.customer_name),
                "timestamp": now_str,
                "type": "system",
            })

        elif action_event == "REPLY_PAID":
            self.state = "PREPAID_CONVERTED"
            self.chat_history.append({
                "sender": "user",
                "text": f"Paid online ₹{int(self.discounted_value)} via UPI/Card",
                "timestamp": now_str,
                "type": "inbound",
            })
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["reply_paid"].format(
                    customer_name=self.customer_name,
                    order_id=self.order_id,
                    discount=int(self.discount),
                ),
                "timestamp": now_str,
                "type": "system",
            })

        elif action_event == "REPLY_NO":
            self.state = "CANCELLED_BY_CUSTOMER"
            self.chat_history.append({
                "sender": "user",
                "text": "NO, cancel this order",
                "timestamp": now_str,
                "type": "inbound",
            })
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["reply_no"].format(order_id=self.order_id),
                "timestamp": now_str,
                "type": "system",
            })

        elif action_event == "RANDOM_TEXT":
            msg_text = custom_text or "kab tak aayega parcel?"
            self.chat_history.append({
                "sender": "user",
                "text": msg_text,
                "timestamp": now_str,
                "type": "inbound",
            })
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["reply_random"].format(text=msg_text),
                "timestamp": now_str,
                "type": "bot",
            })

        elif action_event == "TIMEOUT_4H":
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["reminder_4h"].format(
                    order_id=self.order_id,
                    discount=int(self.discount),
                    payment_link=payment_link,
                ),
                "timestamp": (datetime.now() + timedelta(hours=4)).strftime("%I:%M %p"),
                "type": "reminder",
            })

        elif action_event == "TIMEOUT_24H":
            self.state = "AUTO_HELD_TIMEOUT"
            self.chat_history.append({
                "sender": "bot",
                "text": lang_dict["timeout_24h"].format(order_id=self.order_id),
                "timestamp": (datetime.now() + timedelta(hours=24)).strftime("%I:%M %p"),
                "type": "hold",
            })


class WhatsAppStatus:
    SENT = "SENT"
    CONFIRMED = "CONFIRMED"
    PREPAID = "PREPAID"
    CANCELLED_BY_CUSTOMER = "CANCELLED_BY_CUSTOMER"
    UNRESPONSIVE_TIMEOUT = "UNRESPONSIVE_TIMEOUT"


WhatsAppStateMachine = WhatsAppSession


WHATSAPP_TEMPLATES = {
    "english": {
        "outbound_template": (
            "Hi {customer_name}! Special instant savings on your *Keshava Haircare* order *{order_id}*.\n\n"
            "Pay online right now and get an *instant ₹{discount_rupees} discount* on your cart! You only pay *₹{prepaid_value}*.\n\n"
            "Delivery Address: {delivery_address}\n\n"
            "Prepaid orders get priority dispatch within 6 hours.\n"
            "Pay securely: https://pay.keshava.in/{order_id}\n\n"
            "Prefer COD? Reply *YES* to dispatch as regular Cash on Delivery."
        )
    },
    "hinglish": {
        "outbound_template": (
            "Namaste {customer_name} ji! Aapke *Keshava Haircare* order *{order_id}* par ek exclusive offer hai.\n\n"
            "Agar aap abhi online pay karte hain, toh aapko milega *flat ₹{discount_rupees} OFF*! Aapko sirf *₹{prepaid_value}* pay karna hoga.\n\n"
            "Delivery Address: {delivery_address}\n\n"
            "Prepaid orders fast courier se 6 ghante mein priority dispatch hote hain.\n"
            "Payment link: https://pay.keshava.in/{order_id}\n\n"
            "Agar COD hi chahiye toh bas *YES* reply karein."
        )
    },
    "hindi": {
        "outbound_template": (
            "नमस्ते {customer_name} जी! आपके *केशव हेयरकेयर* ऑर्डर *{order_id}* पर विशेष छूट उपलब्ध है।\n\n"
            "अभी ऑनलाइन भुगतान करने पर *सीधे ₹{discount_rupees} की छूट* पाएं! आपको केवल *₹{prepaid_value}* देना होगा।\n\n"
            "डिलीवरी का पता: {delivery_address}\n\n"
            "प्रीपेड ऑर्डर 6 घंटे में प्राथमिकता से भेजे जाते हैं।\n"
            "भुगतान लिंक: https://pay.keshava.in/{order_id}\n\n"
            "कैश ऑन डिलीवरी के लिए *हाँ (YES)* लिखकर भेजें।"
        )
    }
}


def generate_prepaid_profit_curve(
    order_value: float,
    base_risk: float,
    config: Any = None,
) -> List[Dict[str, Any]]:
    """Generate expected profit curve across discount percentages from 0% to 20%."""
    d_base = 0.62 * order_value - 25.0
    l_loss = 169.40
    points = []
    import numpy as np
    for disc_pct in np.linspace(0.0, 0.20, 21):
        disc_inr = order_value * disc_pct
        d_prep = max(0.0, d_base - disc_inr)
        # As discount increases from 0% to 12%, take rate increases from 12% to 48%
        conversion = 0.12 + 0.36 * min(1.0, disc_pct / 0.10)
        ev_prep = 0.96 * d_prep - 0.04 * l_loss
        ev_cod = (1.0 - base_risk * 0.35) * d_base - (base_risk * 0.35) * l_loss
        blended_ev = 0.65 * (conversion * ev_prep + (1.0 - conversion) * 0.70 * max(0.0, ev_cod))
        points.append({
            "discount_pct": f"{disc_pct*100:.0f}%",
            "expected_profit": round(blended_ev, 2),
            "discount_inr": round(disc_inr, 2),
            "take_rate": round(conversion, 2)
        })
    return points

