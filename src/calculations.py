"""Deterministic financial maths. The LLM never does arithmetic."""


def pct(n, d):
    """Percentage rounded to 2 places, None if the divisor is zero."""
    return round(n / d * 100, 2) if d else None


def dti(monthly_debt, gross_monthly_income):
    return pct(monthly_debt, gross_monthly_income)


def ltv(loan_amount, property_value):
    return pct(loan_amount, property_value)


def monthly_payment(principal, annual_rate_pct, years=30):
    """Standard amortised principal and interest payment."""
    r, n = annual_rate_pct / 1200, years * 12
    return principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)


def funds_to_close(price, loan, closing_pct):
    """Down payment plus estimated closing costs (closing % is an assumption)."""
    return (price - loan) + price * closing_pct / 100


def summary(terms, assets, cfg):
    """All headline metrics in one dict."""
    pay = monthly_payment(terms["loan_amount"], cfg["rate"])
    req = funds_to_close(terms["purchase_price"], terms["loan_amount"], cfg["closing_pct"])
    left = assets - req
    return {
        "dti": dti(terms["monthly_debt"], terms["monthly_income"]),
        "ltv": ltv(terms["loan_amount"], terms["property_value"]),
        "payment": round(pay, 2), "assets": assets, "required": round(req, 2),
        "reserves": round(left, 2),
        "reserve_months": round(left / pay, 1) if pay and assets else None,
    }
