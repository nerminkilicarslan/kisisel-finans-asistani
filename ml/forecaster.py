"""
Kullanıcının kendi harcama geçmişinden bir sonraki ayın kategori bazlı
harcamasını tahmin eder.

Model: Ridge Regression
Özellikler:
  - category_enc        : label encoding
  - month               : ay (1-12) → sin/cos ile döngüsel kodlama
  - lag_1               : 1 ay önceki harcama
  - lag_2               : 2 ay önceki harcama
  - lag_3               : 3 ay önceki harcama
  - rolling_3_mean      : son 3 ay ortalaması
  - rolling_3_std       : son 3 ay standart sapması
  - trend               : lag_1 - lag_2 (trend yönü)
"""
from __future__ import annotations

import os
import warnings
import joblib
import numpy as np
import pandas as pd
from datetime import date
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models_ml", "forecaster.joblib")
META_PATH  = os.path.join(os.path.dirname(__file__), "..", "models_ml", "forecaster_meta.joblib")

_model: Pipeline | None = None
_meta: dict | None = None


def _monthly_pivot(transactions: list[dict]) -> pd.DataFrame:
    """İşlemleri ay×kategori pivot tablosuna çevir."""
    if not transactions:
        return pd.DataFrame()
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["period"] = df["date"].dt.to_period("M")
    pivot = (
        df[df["type"] == "gider"]
        .groupby(["period", "category"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    return pivot


def _build_features(pivot: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Kayan pencere özellik matrisi oluşturur.
    En az 4 aylık veri gerekir (3 lag + 1 hedef).
    """
    categories = pivot.columns.tolist()
    X_rows, y_rows = [], []

    for cat in categories:
        series = pivot[cat].values
        for i in range(3, len(series)):
            lag1, lag2, lag3 = series[i-1], series[i-2], series[i-3]
            month_num = pivot.index[i].month
            X_rows.append([
                categories.index(cat),           # category_enc
                np.sin(2 * np.pi * month_num / 12),  # month_sin
                np.cos(2 * np.pi * month_num / 12),  # month_cos
                lag1,
                lag2,
                lag3,
                np.mean([lag1, lag2, lag3]),      # rolling_3_mean
                np.std([lag1, lag2, lag3]) + 1e-9, # rolling_3_std
                lag1 - lag2,                       # trend
            ])
            y_rows.append(series[i])

    if not X_rows:
        return np.array([]), np.array([]), categories
    return np.array(X_rows), np.array(y_rows), categories


def train(transactions: list[dict]) -> dict:
    """
    Kullanıcının işlem geçmişiyle modeli eğit.
    Returns: metrics dict
    """
    global _model, _meta

    pivot = _monthly_pivot(transactions)
    if pivot.shape[0] < 4:
        return {"error": "En az 4 aylık gider verisi gerekli.", "trained": False}

    X, y, categories = _build_features(pivot)
    if len(X) < 6:
        return {"error": "Yeterli veri yok.", "trained": False}

    # Son ayı test seti olarak ayır
    split = max(1, int(len(X) * 0.85))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge",  Ridge(alpha=10.0)),
    ])
    pipeline.fit(X_train, y_train)

    metrics: dict = {"trained": True, "n_samples": len(X), "categories": categories}
    if len(X_test) > 0:
        preds = pipeline.predict(X_test)
        preds = np.maximum(preds, 0)
        metrics["mae"]  = float(mean_absolute_error(y_test, preds))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, preds)))

    _model = pipeline
    _meta  = {"categories": categories, "pivot_index": [str(p) for p in pivot.index]}

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(_model, MODEL_PATH, compress=3)
    joblib.dump(_meta,  META_PATH,  compress=3)
    return metrics


def predict_next_month(transactions: list[dict]) -> dict[str, float]:
    """
    Bir sonraki ay kategori bazlı harcama tahminlerini döndürür.
    Returns: {kategori: tahmini_tutar}
    """
    global _model, _meta

    if _model is None and os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        _meta  = joblib.load(META_PATH)

    pivot = _monthly_pivot(transactions)
    if pivot.shape[0] < 3 or _model is None:
        return {}

    categories = pivot.columns.tolist()
    next_month = (pivot.index[-1] + 1).month
    predictions = {}

    for cat in categories:
        series = pivot[cat].values
        lag1, lag2, lag3 = series[-1], series[-2], series[-3]
        features = np.array([[
            categories.index(cat),
            np.sin(2 * np.pi * next_month / 12),
            np.cos(2 * np.pi * next_month / 12),
            lag1, lag2, lag3,
            np.mean([lag1, lag2, lag3]),
            np.std([lag1, lag2, lag3]) + 1e-9,
            lag1 - lag2,
        ]])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pred = float(_model.predict(features)[0])
        predictions[cat] = round(max(pred, 0), 2)

    return dict(sorted(predictions.items(), key=lambda x: x[1], reverse=True))


def is_ready() -> bool:
    return os.path.exists(MODEL_PATH)
