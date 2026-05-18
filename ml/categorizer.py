"""
İşlem açıklama metni → harcama kategorisi sınıflandırıcısı.

Pipeline:
  TF-IDF (karakter 2-4gram + kelime 1-2gram)  →  LogisticRegression (L2)

Çıktı:
  predict(text)          → str  (kategori)
  predict_proba(text)    → dict (kategori → olasılık)
  is_ready()             → bool (model yüklü mü?)
"""
from __future__ import annotations

import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import FunctionTransformer
from sklearn.model_selection import StratifiedKFold, cross_val_score

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models_ml", "categorizer.joblib")


def _normalize_single(text: str) -> str:
    """Pickle edilebilir top-level normalize fonksiyonu."""
    t = str(text).upper()
    for src, dst in [("İ","I"),("Ğ","G"),("Ü","U"),("Ş","S"),("Ö","O"),("Ç","C")]:
        t = t.replace(src, dst)
    return t


def _build_pipeline() -> Pipeline:
    word_tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=12_000,
        sublinear_tf=True,
        min_df=2,
        preprocessor=_normalize_single,
    )
    char_tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=18_000,
        sublinear_tf=True,
        min_df=2,
        preprocessor=_normalize_single,
    )
    features = FeatureUnion([("word", word_tfidf), ("char", char_tfidf)])
    clf = LogisticRegression(
        C=4.0,
        max_iter=1000,
        solver="lbfgs",
        class_weight="balanced",
        random_state=42,
    )
    return Pipeline([("features", features), ("clf", clf)])


def train(X_train: list[str], y_train: list[str]) -> tuple[Pipeline, dict]:
    """
    Modeli eğit ve cross-validation metriklerini döndür.
    Returns: (fitted_pipeline, metrics_dict)
    """
    pipeline = _build_pipeline()

    # 5-katlı çapraz doğrulama
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=-1)

    pipeline.fit(X_train, y_train)

    metrics = {
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "cv_scores": cv_scores.tolist(),
        "n_train": len(X_train),
        "classes": list(pipeline.classes_),
    }
    return pipeline, metrics


def save(pipeline: Pipeline, path: str = MODEL_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(pipeline, path, compress=3)


def load(path: str = MODEL_PATH) -> Pipeline | None:
    if not os.path.exists(path):
        return None
    return joblib.load(path)


# ── Singleton yükleme ─────────────────────────────────────────────────────────

_pipeline: Pipeline | None = None


def is_ready() -> bool:
    return _pipeline is not None or os.path.exists(MODEL_PATH)


def _ensure_loaded() -> Pipeline | None:
    global _pipeline
    if _pipeline is None:
        _pipeline = load()
    return _pipeline


def predict(text: str) -> str:
    """Tek açıklama → kategori. Model yoksa 'Diğer' döner."""
    p = _ensure_loaded()
    if p is None:
        return "Diğer"
    return str(p.predict([text])[0])


def predict_proba(text: str) -> dict[str, float]:
    """Tek açıklama → {kategori: olasılık} sözlüğü."""
    p = _ensure_loaded()
    if p is None:
        return {}
    probs = p.predict_proba([text])[0]
    return dict(sorted(
        zip(p.classes_, probs.tolist()),
        key=lambda x: x[1], reverse=True
    ))


def predict_batch(texts: list[str]) -> list[str]:
    p = _ensure_loaded()
    if p is None:
        return ["Diğer"] * len(texts)
    return list(p.predict(texts))
