"""
Banka ekstresi CSV içe aktarıcı.

Kategorileme önceliği:
  1. CSV'de 'kategori' sütunu varsa → onu kullan
  2. ML modeli (TF-IDF+LR) eğitilmişse → ML tahmini
  3. Fallback: kural tabanlı keyword eşleştirmesi
"""
import pandas as pd
from datetime import date
from models import Transaction, SessionLocal
from services.firebase_service import sync_transaction

# ── Kural tabanlı fallback ────────────────────────────────────────────────────
_FALLBACK_RULES = {
    "Market":  ["migros", "a101", "bim", "şok", "carrefour", "market", "gıda"],
    "Fatura":  ["elektrik", "doğalgaz", "internet", "telefon", "ttnet", "turkcell", "fatura", "abonelik"],
    "Yemek":   ["restoran", "cafe", "yemek", "döner", "pizza", "burger", "kahve", "starbucks", "getir", "yemeksepeti"],
    "Ulaşım":  ["akbil", "metro", "otobüs", "taxi", "uber", "akaryakıt", "benzin", "shell", "bp", "opet"],
    "Eğlence": ["sinema", "netflix", "spotify", "oyun", "bilet", "konser", "digiturk"],
    "Sağlık":  ["eczane", "hastane", "klinik", "doktor", "ilaç"],
    "Giyim":   ["lcw", "zara", "h&m", "koton", "mango", "giyim", "ayakkabı", "defacto"],
    "Eğitim":  ["okul", "kurs", "udemy", "kitap", "kırtasiye", "coursera", "üniversite"],
    "Kira":    ["kira", "aidat", "site yönetimi"],
}


def _keyword_categorize(description: str) -> str:
    desc = description.lower()
    for cat, keywords in _FALLBACK_RULES.items():
        if any(k in desc for k in keywords):
            return cat
    return "Diğer"


def _ml_categorize_batch(descriptions: list[str]) -> list[str]:
    """ML modeli mevcutsa toplu kategorileme; yoksa keyword fallback."""
    try:
        from ml.categorizer import predict_batch, is_ready
        if is_ready():
            return predict_batch(descriptions)
    except ImportError:
        pass
    return [_keyword_categorize(d) for d in descriptions]


def parse_date(val) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return pd.to_datetime(str(val), format=fmt).date()
        except Exception:
            pass
    return None


def import_csv(filepath: str) -> dict:
    """
    Banka ekstresi CSV formatı (otomatik sütun tespiti).
    Beklenen sütunlar: tarih, tutar, açıklama  (isim varyasyonlarını kabul eder)
    """
    df = pd.read_csv(filepath, encoding="utf-8-sig", sep=None, engine="python")
    df.columns = [c.strip().lower() for c in df.columns]

    col_map = _detect_columns(df.columns.tolist())
    if not col_map:
        return {"success": False, "error": "Sütun isimleri tanınamadı. Lütfen örnek şablona bakın."}

    df = df.rename(columns=col_map)
    df = df.dropna(subset=["tarih", "tutar"])

    # Tarih ve tutar parse
    valid_rows = []
    for _, row in df.iterrows():
        tx_date = parse_date(row["tarih"])
        if tx_date is None:
            continue
        try:
            amount = float(str(row["tutar"]).replace(",", ".").replace(" ", ""))
        except ValueError:
            continue
        desc = str(row.get("aciklama", "")).strip()
        manual_cat = str(row.get("kategori", "")).strip()
        valid_rows.append((tx_date, amount, desc, manual_cat))

    if not valid_rows:
        return {"success": False, "error": "Geçerli satır bulunamadı."}

    # Kategori belirleme: CSV'de tanımlı yoksa ML/keyword
    need_ml = [r[2] for r in valid_rows if not r[3]]
    ml_cats = _ml_categorize_batch(need_ml) if need_ml else []
    ml_iter = iter(ml_cats)

    db = SessionLocal()
    imported = 0
    created_transactions = []
    try:
        for (tx_date, amount, desc, manual_cat) in valid_rows:
            category = manual_cat if manual_cat else next(ml_iter)
            tx_type  = "gider" if amount < 0 else "gelir"
            tx = Transaction(
                date=tx_date,
                amount=abs(amount),
                category=category,
                description=desc,
                type=tx_type,
                source="csv",
            )
            db.add(tx)
            created_transactions.append(tx)
            imported += 1
        db.commit()
        for tx in created_transactions:
            try:
                sync_transaction(tx)
            except Exception:
                pass
    finally:
        db.close()

    skipped = len(df) - imported
    return {"success": True, "imported": imported, "skipped": skipped,
            "ml_categorized": len(ml_cats)}


def _detect_columns(cols: list[str]) -> dict | None:
    date_candidates   = ["tarih", "date", "işlem tarihi", "tarih/saat", "islem tarihi"]
    amount_candidates = ["tutar", "amount", "miktar", "işlem tutarı", "borç", "alacak", "islem tutari"]
    desc_candidates   = ["açıklama", "aciklama", "description", "işlem açıklaması", "detay", "islem aciklamasi"]
    cat_candidates    = ["kategori", "category", "tur", "tür"]

    result = {}
    for c in cols:
        if c in date_candidates:
            result[c] = "tarih"
        elif c in amount_candidates:
            result[c] = "tutar"
        elif c in desc_candidates:
            result[c] = "aciklama"
        elif c in cat_candidates:
            result[c] = "kategori"

    if "tarih" in result.values() and "tutar" in result.values():
        return result
    return None
