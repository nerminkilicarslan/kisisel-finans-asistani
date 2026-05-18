"""
Demo verisi oluşturur. Sadece bir kez çalıştırılır.
Kullanım: python seed_data.py
"""
import random
from datetime import date, timedelta
from models import init_db, SessionLocal, Transaction, BudgetPlan, SavingsGoal

random.seed(42)

EXPENSE_TEMPLATES = [
    ("Market",   900,  300,  ["Migros alışveriş", "A101 market", "BİM", "Carrefour"]),
    ("Fatura",   650,  100,  ["Elektrik faturası", "Su faturası", "Doğalgaz", "İnternet"]),
    ("Yemek",    600,  200,  ["Yemeksepeti", "Getir", "Restoran", "Kahve"]),
    ("Ulaşım",   350,   80,  ["Akbil yükleme", "Taxi", "Akaryakıt"]),
    ("Eğlence",  250,  100,  ["Netflix", "Spotify", "Sinema", "Kitap"]),
    ("Sağlık",   200,  150,  ["Eczane", "Doktor randevusu", "Diş hekimi"]),
    ("Giyim",    400,  250,  ["LCW alışveriş", "Zara", "Ayakkabı"]),
    ("Eğitim",   150,   80,  ["Udemy kurs", "Kitap", "Kırtasiye"]),
    ("Kira",    8500,    0,  ["Kira ödemesi"]),
]

INCOME_TEMPLATES = [
    ("Maaş",         22000, 0,   ["Maaş - Kasım", "Maaş - Ekim"]),
    ("Freelance",     3500, 1500, ["Freelance proje", "Danışmanlık"]),
    ("Kira Geliri",   2800, 0,   ["Kira geliri"]),
    ("Yatırım",        600, 400, ["Faiz geliri", "Temettü"]),
]


def generate_transactions(months_back: int = 6):
    today = date.today()
    transactions = []

    for i in range(months_back, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year - ((today.month - i - 1) // 12)
        days_in_month = 28 if month == 2 else 30 if month in [4, 6, 9, 11] else 31

        # Giderler
        for cat, base, variance, descs in EXPENSE_TEMPLATES:
            n_tx = 1 if cat in ("Kira", "Fatura") else random.randint(2, 6)
            for _ in range(n_tx):
                amount = max(10, base / n_tx + random.uniform(-variance / n_tx, variance / n_tx))
                tx_date = date(year, month, random.randint(1, days_in_month))
                transactions.append(Transaction(
                    date=tx_date,
                    amount=round(amount, 2),
                    category=cat,
                    description=random.choice(descs),
                    type="gider",
                    source="mock",
                ))

        # Gelirler
        for cat, base, variance, descs in INCOME_TEMPLATES:
            amount = base + random.uniform(-variance, variance)
            tx_date = date(year, month, random.randint(1, 5))
            transactions.append(Transaction(
                date=tx_date,
                amount=round(amount, 2),
                category=cat,
                description=random.choice(descs),
                type="gelir",
                source="mock",
            ))

    return transactions


def generate_budgets(year: int, month: int):
    return [
        BudgetPlan(year=year, month=month, category="Market",   limit_amount=1200),
        BudgetPlan(year=year, month=month, category="Yemek",    limit_amount=700),
        BudgetPlan(year=year, month=month, category="Eğlence",  limit_amount=300),
        BudgetPlan(year=year, month=month, category="Ulaşım",   limit_amount=400),
        BudgetPlan(year=year, month=month, category="Giyim",    limit_amount=500),
    ]


def generate_goals():
    today = date.today()
    return [
        SavingsGoal(
            name="Tatil Fonu",
            target_amount=15000,
            current_amount=4200,
            target_date=date(today.year, 8, 1),
        ),
        SavingsGoal(
            name="Acil Durum Fonu",
            target_amount=50000,
            current_amount=18500,
            target_date=None,
        ),
        SavingsGoal(
            name="Laptop",
            target_amount=25000,
            current_amount=25000,
            target_date=date(today.year, 3, 1),
            is_completed=True,
        ),
    ]


if __name__ == "__main__":
    init_db()
    db = SessionLocal()

    existing = db.query(Transaction).count()
    if existing > 0:
        print(f"Veritabanında zaten {existing} işlem var. Seed atlandı.")
        db.close()
        exit(0)

    today = date.today()

    txs = generate_transactions(months_back=6)
    db.add_all(txs)

    budgets = generate_budgets(today.year, today.month)
    db.add_all(budgets)

    goals = generate_goals()
    db.add_all(goals)

    db.commit()
    db.close()

    print(f"✅ {len(txs)} işlem, {len(budgets)} bütçe kalemi, {len(goals)} tasarruf hedefi oluşturuldu.")
