"""
Extensible fingerprint library (rule-driven) for platform and PSP detection.
Each fingerprint has: id/name, category ("platform" | "psp"), matchers, weight, output.
"""
from typing import List, Dict, Any

# Fingerprint: category, matchers (all optional), weight, output (platform= or psp_add=)
# Matchers: html_contains, script_src_contains, cookie_names, global_vars, request_url_contains
FINGERPRINTS: List[Dict[str, Any]] = [
    # --- Platform: Shopify (strong) ---
    {
        "id": "shopify_platform",
        "name": "Shopify",
        "category": "platform",
        "weight": 1.0,
        "output_platform": "Shopify",
        "matchers": {
            "html_contains": ["cdn.shopify.com", "Shopify", "myshopify.com"],
            "script_src_contains": ["cdn.shopify.com", "shopify.com"],
            "request_url_contains": ["/cart.js", "/cart/add.js", "shopify.com"],
        },
        "global_vars": ["Shopify"],
    },
    # --- PSP: Stripe ---
    {
        "id": "stripe_psp",
        "name": "Stripe",
        "category": "psp",
        "weight": 1.0,
        "output_psp_add": "Stripe",
        "matchers": {
            "script_src_contains": ["js.stripe.com/v3", "stripe.com"],
            "request_url_contains": ["api.stripe.com", "checkout.stripe.com", "hooks.stripe.com", "js.stripe.com"],
        },
        "global_vars": ["Stripe"],
    },
    # --- PSP: Adyen ---
    {
        "id": "adyen_psp",
        "name": "Adyen",
        "category": "psp",
        "weight": 1.0,
        "output_psp_add": "Adyen",
        "matchers": {
            "script_src_contains": ["adyen.js", "components.adyen.com", "adyen.com"],
            "request_url_contains": ["checkoutshopper-live.adyen.com", "adyen.com", "checkoutshopper-test.adyen.com"],
        },
        "global_vars": ["AdyenCheckout"],
    },
    # --- PSP: Braintree / PayPal ---
    {
        "id": "paypal_braintree_psp",
        "name": "PayPal/Braintree",
        "category": "psp",
        "weight": 0.8,
        "output_psp_add": "PayPal",
        "matchers": {
            "script_src_contains": ["paypal.com/sdk/js", "paypalobjects.com", "braintree-api.com"],
            "request_url_contains": ["paypal.com", "braintree-api.com", "braintreegateway.com"],
        },
    },
]

# Minimum score (sum of weights) to add a platform/PSP to the profile
PLATFORM_THRESHOLD = 0.5
PSP_THRESHOLD = 0.5
