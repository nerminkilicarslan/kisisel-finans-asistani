import pandas as pd
import numpy as np
from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Transaction, BudgetPlan


CATEGORIES_GIDER = [
    "Market", "Fatura", "Yemek", "Ulaşım", "Eğlence",
    "Sağlık", "Giyim", "Eğitim", "Kira", "Diğer"
]

CATEGORIES_GELIR = ["Maaş", "Freelance", "Kira Geliri", "Yatırım", "Diğer Gelir"]


def get_monthly_summary(db_or_transactions, month: int, year: int) -> dict:
    if isinstance(db_or_transactions, Session):
        txs = db_or_transactions.query(Transaction).filter(
            Transaction.date >= date(year, month, 1),
            Transaction.date < date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1),
        ).all()
    else:
        start = date(year, month, 1)
        end = date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1)
        txs = [tx for tx in db_or_transactions
               if tx.get("date") is not None and start <= tx.get("date") < end]

    df = _to_df(txs)
    if df.empty:
        return {
            "income": 0,
            "expense": 0,
            "savings": 0,
            "savings_rate": 0,
            "top_category": "-",
            "transactions": [],
        }

    income = df[df["type"] == "gelir"]["amount"].sum()
    expense = df[df["type"] == "gider"]["amount"].sum()
    top_cat = (
        df[df["type"] == "gider"].groupby("category")["amount"]
        .sum()
        .idxmax()
        if not df[df["type"] == "gider"].empty else "-"
    )
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "savings": round(income - expense, 2),
        "savings_rate": round((income - expense) / income * 100, 1) if income > 0 else 0,
        "top_category": top_cat,
        "transactions": df.to_dict("records"),
    }


def get_category_breakdown(db_or_transactions, month: int, year: int) -> pd.DataFrame:
    if isinstance(db_or_transactions, Session):
        txs = db_or_transactions.query(Transaction).filter(
            Transaction.type == "gider",
            Transaction.date >= date(year, month, 1),
            Transaction.date < date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1),
        ).all()
    else:
        start = date(year, month, 1)
        end = date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1)
        txs = [tx for tx in db_or_transactions
               if tx.get("type") == "gider"
               and tx.get("date") is not None
               and start <= tx.get("date") < end]
    df = _to_df(txs)
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "pct"])
    breakdown = df.groupby("category")["amount"].sum().reset_index()
    breakdown["pct"] = (breakdown["amount"] / breakdown["amount"].sum() * 100).round(1)
    return breakdown.sort_values("amount", ascending=False)


def get_last_6_months_trend(db_or_transactions) -> pd.DataFrame:
    return get_last_n_months_trend(db_or_transactions, 6)


def get_last_n_months_trend(db_or_transactions, months: int = 6) -> pd.DataFrame:
    """Return a DataFrame with the last `months` months trend (income/expense).

    `months` must be >= 1. The returned DataFrame has rows ordered from oldest to newest.
    """
    if months < 1:
        months = 1
    today = date.today()
    rows = []
    # iterate from months-1 down to 0 to get oldest -> newest
    for i in range(months - 1, -1, -1):
        # compute month and year for offset i
        # month index (1-12)
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((today.month - i - 1) // 12)
        end = date(y, m % 12 + 1, 1) if m < 12 else date(y + 1, 1, 1)
        if isinstance(db_or_transactions, Session):
            txs = db_or_transactions.query(Transaction).filter(
                Transaction.date >= date(y, m, 1),
                Transaction.date < end,
            ).all()
        else:
            txs = [tx for tx in db_or_transactions
                   if tx.get("date") is not None
                   and date(y, m, 1) <= tx.get("date") < end]
        df = _to_df(txs)
        income = df[df["type"] == "gelir"]["amount"].sum() if not df.empty else 0
        expense = df[df["type"] == "gider"]["amount"].sum() if not df.empty else 0
        rows.append({"ay": f"{y}-{m:02d}", "gelir": income, "gider": expense})
    return pd.DataFrame(rows)


def check_budget_alerts(db: Session, month: int, year: int) -> list[dict]:
    plans = db.query(BudgetPlan).filter(
        BudgetPlan.month == month, BudgetPlan.year == year
    ).all()
    if not plans:
        return []

    breakdown = get_category_breakdown(db, month, year)
    if breakdown.empty:
        return []

    spent = dict(zip(breakdown["category"], breakdown["amount"]))
    alerts = []
    for plan in plans:
        actual = spent.get(plan.category, 0)
        pct = actual / plan.limit_amount * 100 if plan.limit_amount > 0 else 0
        if pct >= 80:
            alerts.append({
                "category": plan.category,
                "limit": plan.limit_amount,
                "spent": actual,
                "pct": round(pct, 1),
                "status": "kritik" if pct >= 100 else "uyarı",
            })
    return alerts


def get_budget_alerts_from_plans(plans: list[dict], breakdown: pd.DataFrame) -> list[dict]:
    if not plans or breakdown.empty:
        return []
    spent = dict(zip(breakdown["category"], breakdown["amount"]))
    alerts = []
    for plan in plans:
        actual = spent.get(plan.get("category", ""), 0)
        limit = float(plan.get("limit_amount", 0) or 0)
        pct = actual / limit * 100 if limit else 0
        if pct >= 80:
            alerts.append({
                "category": plan.get("category", ""),
                "limit": limit,
                "spent": actual,
                "pct": round(pct, 1),
                "status": "kritik" if pct >= 100 else "uyarı",
            })
    return alerts


def _to_df(transactions) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame()
    rows = []
    for t in transactions:
        if isinstance(t, dict):
            rows.append({
                "id": t.get("id"),
                "date": t.get("date"),
                "amount": float(t.get("amount", 0) or 0),
                "category": t.get("category", ""),
                "description": t.get("description", ""),
                "type": t.get("type", ""),
            })
        else:
            rows.append({
                "id": t.id,
                "date": t.date,
                "amount": t.amount,
                "category": t.category,
                "description": t.description,
                "type": t.type,
            })
    return pd.DataFrame(rows)
