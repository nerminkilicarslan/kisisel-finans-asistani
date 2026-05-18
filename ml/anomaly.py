"""
Kullanıcının harcama geçmişinde anormal işlemleri tespit eder.

Yaklaşım (iki katmanlı):
  1. İstatistiksel: Kategori bazında z-score > 2.5 → şüpheli
  2. IsolationForest: Genel harcama örüntüsünden sapma

Her işleme 0-1 arası anomali skoru atanır.
score >= 0.6  → yüksek anomali
score >= 0.4  → orta anomali
score < 0.4   → normal
"""
from __future__ import annotations

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models_ml", "anomaly.joblib")
META_PATH  = os.path.join(os.path.dirname(__file__), "..", "models_ml", "anomaly_meta.joblib")

_model: Pipeline | None = None
_meta:  dict   | None = None


def _build_features(df: pd.DataFrame, le: LabelEncoder | None = None) -> tuple[np.ndarray, LabelEncoder]:
    """İşlem DataFrame'inden özellik matrisi çıkar."""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["day_of_week"] = d["date"].dt.dayofweek
    d["day_of_month"] = d["date"].dt.day
    d["month"] = d["date"].dt.month

    if le is None:
        le = LabelEncoder()
        d["cat_enc"] = le.fit_transform(d["category"].astype(str))
    else:
        known = set(le.classes_)
        d["cat_enc"] = d["category"].apply(
            lambda c: le.transform([c])[0] if c in known else -1
        )

    X = d[["amount", "cat_enc", "day_of_week", "day_of_month", "month"]].values.astype(float)
    return X, le


def train(transactions: list[dict]) -> dict:
    """IsolationForest'i kullanıcı verisiyle eğit."""
    global _model, _meta

    gider = [t for t in transactions if t.get("type") == "gider"]
    if len(gider) < 20:
        return {"error": "Anormallik tespiti için en az 20 gider işlemi gerekli.", "trained": False}

    df = pd.DataFrame(gider)

    # Kategori istatistikleri (z-score için)
    cat_stats: dict[str, dict] = {}
    for cat, group in df.groupby("category"):
        cat_stats[str(cat)] = {
            "mean": float(group["amount"].mean()),
            "std":  float(group["amount"].std() + 1e-9),
        }

    X, le = _build_features(df)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("iso",    IsolationForest(
            n_estimators=200,
            contamination=0.07,   # Veri setinin ~%7'si anomali varsayımı
            max_features=1.0,
            random_state=42,
        )),
    ])
    pipeline.fit(X)

    _model = pipeline
    _meta  = {"le": le, "cat_stats": cat_stats}

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(_model, MODEL_PATH, compress=3)
    joblib.dump(_meta,  META_PATH,  compress=3)
    return {"trained": True, "n_samples": len(gider)}


def score_transactions(transactions: list[dict]) -> list[dict]:
    """
    Her işleme anomali skoru ekleyerek döndür.
    Ek alanlar:
      anomaly_score  : float 0-1 (yüksek = daha anormal)
      anomaly_level  : "yüksek" | "orta" | "normal"
      anomaly_reason : str açıklama
    """
    global _model, _meta

    if _model is None and os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        _meta  = joblib.load(META_PATH)

    result = []
    for tx in transactions:
        tx = dict(tx)
        tx["anomaly_score"] = 0.0
        tx["anomaly_level"] = "normal"
        tx["anomaly_reason"] = ""
        result.append(tx)

    if _model is None or not result:
        return result

    df = pd.DataFrame(result)
    if "date" not in df.columns or "amount" not in df.columns:
        return result

    le: LabelEncoder = _meta["le"]
    cat_stats: dict  = _meta["cat_stats"]

    X, _ = _build_features(df, le=le)

    # IsolationForest skoru: decision_function → normalize et
    raw_scores = _model.decision_function(X)    # + normal, - anormal
    iso_scores = 1 - (raw_scores - raw_scores.min()) / (np.ptp(raw_scores) + 1e-9)

    for i, tx in enumerate(result):
        if tx.get("type") != "gider":
            continue

        iso_s = float(iso_scores[i])

        # Z-score katmanlı kontrol
        cat  = str(tx.get("category", ""))
        amt  = float(tx.get("amount", 0))
        z_s  = 0.0
        reason = ""

        if cat in cat_stats:
            mu, sigma = cat_stats[cat]["mean"], cat_stats[cat]["std"]
            z = abs(amt - mu) / sigma
            z_s = min(z / 4.0, 1.0)   # z=4 → skor=1
            if z > 2.5:
                direction = "yüksek" if amt > mu else "düşük"
                reason = (f"{cat} kategorisinde ortalama {mu:,.0f} ₺ iken "
                          f"{amt:,.0f} ₺ ({direction}) — z={z:.1f}")

        # Kombine skor: %60 iso + %40 z-score
        combined = 0.6 * iso_s + 0.4 * z_s

        if combined >= 0.6:
            level = "yüksek"
        elif combined >= 0.4:
            level = "orta"
        else:
            level = "normal"
            reason = ""

        result[i]["anomaly_score"] = round(combined, 3)
        result[i]["anomaly_level"] = level
        result[i]["anomaly_reason"] = reason

    return result


def is_ready() -> bool:
    return os.path.exists(MODEL_PATH)
