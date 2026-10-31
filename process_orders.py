import sys, re, json
sys.path.insert(0, '.')
import pandas as pd
from src.heuristics import classify_address, check_fake_name
from src.data_cleaner import normalize_phone

df = pd.read_csv('orders_sample.csv')

def process_all_orders(df):
    orders = []
    bucket_stats = {
        'SHIP_AS_IS': {'count': 0, 'ov': 0.0, 'ev': 0.0},
        'SHIP_CONFIRM': {'count': 0, 'ov': 0.0, 'ev': 0.0},
        'NUDGE_PREPAID': {'count': 0, 'ov': 0.0, 'ev': 0.0},
        'CANCEL': {'count': 0, 'ov': 0.0, 'ev': 0.0, 'bleed_saved': 0.0},
    }
    
    for idx, row in df.iterrows():
        order_id = str(row.get('order_id', '')).strip()
        customer = str(row.get('customer_name', '')).strip()
        addr = str(row.get('address', '')).strip()
        city = str(row.get('city', '')).strip()
        state = str(row.get('state', '')).strip()
        pincode = str(row.get('pincode', '')).strip()
        ov = float(row.get('order_value', 0) or 0)
        items = str(row.get('items', '')).strip()
        num_items = int(row.get('num_items', 1) or 1)
        prior_orders = int(row.get('customer_prior_orders', 0) or 0)
        prior_rto = int(row.get('customer_prior_rto', 0) or 0)
        courier = str(row.get('courier', '')).strip()
        final_status = str(row.get('final_status', '')).strip()
        dt = str(row.get('order_datetime', '')).strip()
        
        clean_phone, is_valid_phone, phone_type = normalize_phone(row.get('phone', ''))
        phone_fmt = '+91' + clean_phone if len(clean_phone) == 10 else clean_phone
        
        addr_cat, addr_desc, addr_risk = classify_address(addr, city)
        is_fake, name_desc = check_fake_name(customer)
        
        # Risk estimation
        risk = addr_risk
        if state in ['Bihar', 'Uttar Pradesh', 'Madhya Pradesh']:
            risk += 0.05
        elif state in ['Maharashtra', 'Karnataka', 'Tamil Nadu', 'Delhi']:
            risk -= 0.04
            
        if prior_orders >= 2 and prior_rto == 0:
            risk -= 0.08
        elif prior_rto == 1:
            risk += 0.09
            
        if (ov / max(1, num_items)) > 700:
            risk += 0.12
            
        risk = max(0.04, min(0.92, risk))
        
        # Baseline EV
        ev_ship = (1 - risk) * (ov * 0.65 - 80) - risk * 169.40
        
        # Determine action
        if ov <= 0:
            action = 'SHIP_AS_IS'
            risk_pct = 4.0
            ev_val = 0.0
            rationale = 'Free replacement / warranty order (₹0 cart value). Rule-based mathematical bypass.'
            status = 'READY_FOR_DISPATCH'
        elif prior_rto >= 2:
            action = 'CANCEL'
            risk_pct = 78.5
            ev_val = 0.0
            rationale = f'Serial returner cliff ({prior_rto} prior RTOs, 76.5% return rate cliff). Shipping COD guarantees negative unit margin; blocked to save ₹169.40 courier bleed.'
            status = 'BLOCKED'
        elif not is_valid_phone:
            risk = min(0.85, addr_risk + 0.25)
            ev_val = (1 - risk) * (ov * 0.65 - 80) - risk * 169.4
            risk_pct = round(risk * 100, 1)
            if ev_val <= 0:
                action = 'CANCEL'
                ev_val = 0.0
                rationale = f'Invalid phone ({phone_type}) prevents WhatsApp verification; order held/cancelled to avoid negative expected contribution.'
                status = 'BLOCKED'
            else:
                action = 'SHIP_AS_IS'
                rationale = f'Phone uncontactable via WhatsApp; proceeding to ship as-is based on positive expected contribution (+₹{ev_val:.2f}).'
                status = 'READY_FOR_DISPATCH'
        elif addr_cat in ['HINGLISH_HIGH_INTENT_CALL', 'STRUCTURED_URBAN'] and risk < 0.28:
            action = 'SHIP_AS_IS'
            risk_pct = round(risk * 100, 1)
            ev_val = max(0.0, ev_ship)
            rationale = f'Verified high-intent address ({addr_cat}); low baseline risk ({risk:.1%}). Cleared for immediate warehouse dispatch.'
            status = 'READY_FOR_DISPATCH'
        elif ov >= 1200 or risk >= 0.45:
            action = 'NUDGE_PREPAID'
            risk_pct = round(risk * 100, 1)
            discount = round(min(200, max(50, ov * 0.10)))
            payable = ov - discount
            ev_nudge = 0.85 * (0.35 * (payable * 0.65 - 80) + 0.65 * 0.60 * ((1 - risk * 0.65) * (ov * 0.65 - 80) - (risk * 0.65) * 169.40))
            ev_val = max(ev_ship, ev_nudge)
            rationale = f'High basket size (₹{int(ov)}) in elevated variance geography. WhatsApp 10% UPI offer protects ₹{int(payable * 0.65 - 80)} gross margin.'
            status = 'AWAITING_VERIFICATION'
        elif risk >= 0.28:
            action = 'SHIP_CONFIRM'
            risk_pct = round(risk * 100, 1)
            ev_confirm = 0.85 * 0.65 * ((1 - risk * 0.65) * (ov * 0.65 - 80) - (risk * 0.65) * 169.40)
            ev_val = max(ev_ship, ev_confirm)
            rationale = f'Semi-urban address ({addr_cat}) with moderate return variance ({risk:.1%}). WhatsApp confirmation filters remorse.'
            status = 'AWAITING_VERIFICATION'
        else:
            action = 'SHIP_AS_IS'
            risk_pct = round(risk * 100, 1)
            ev_val = ev_ship
            rationale = 'Standard address with established delivery completion rate. Immediate courier handover.'
            status = 'READY_FOR_DISPATCH'
            
        ev_str = f'+₹{ev_val:.2f}' if ev_val > 0 else (f'₹{ev_val:.2f}' if ev_val == 0 else f'-₹{abs(ev_val):.2f}')
        loc = f'{city}, {state}' if city and state else (city or state or 'India')
        
        # update stats
        bucket_stats[action]['count'] += 1
        bucket_stats[action]['ov'] += ov
        bucket_stats[action]['ev'] += max(0.0, ev_val)
        if action == 'CANCEL':
            bucket_stats['CANCEL']['bleed_saved'] += 169.40
            
        orders.append({
            'id': order_id,
            'customer': customer,
            'location': loc,
            'city': city,
            'state': state,
            'pincode': pincode,
            'address': addr,
            'ov': ov,
            'risk': f'{risk_pct:.1f}%',
            'action': action,
            'ev': ev_str,
            'ev_num': round(ev_val, 2),
            'rationale': rationale,
            'phone': phone_fmt,
            'status': status,
            'items': items,
            'num_items': num_items,
            'courier': courier,
            'datetime': dt,
            'final_status': final_status
        })
        
    return orders, bucket_stats

orders, stats = process_all_orders(df)
with open('processed_orders.json', 'w', encoding='utf-8') as f:
    json.dump(orders, f, ensure_ascii=False, indent=2)

with open('processed_stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print('Success! Processed', len(orders), 'orders.')
