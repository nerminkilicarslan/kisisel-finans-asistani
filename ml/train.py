"""
Tüm ML modellerini eğiten pipeline.
Kullanım: python ml/train.py

Adımlar:
  1. Kategorileme: sentetik 9 000 örneklik Türkçe veri seti → TF-IDF + LR
  2. Tahmin:       veritabanındaki gerçek kullanıcı verisi   → Ridge Regression
  3. Anomali:      veritabanındaki gerçek kullanıcı verisi   → IsolationForest
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

from ml.dataset    import build_dataset
from ml.categorizer import train as train_categorizer, save as save_categorizer
from ml.forecaster  import train as train_forecaster
from ml.anomaly     import train as train_anomaly
from models         import SessionLocal, Transaction, init_db


def _load_db_transactions() -> list[dict]:
    init_db()
    db = SessionLocal()
    txs = db.query(Transaction).all()
    db.close()
    return [{
        "id":          t.id,
        "date":        t.date,
        "amount":      t.amount,
        "category":    t.category,
        "description": t.description,
        "type":        t.type,
    } for t in txs]


def train_all(verbose: bool = True) -> dict:
    results = {}

    # ── 1. KATEGORİLEYİCİ ─────────────────────────────────────────────────────
    if verbose:
        print("\n" + "=" * 60)
        print("1/3  KATEGORİLEYİCİ  (TF-IDF + Logistic Regression)")
        print("=" * 60)

    t0 = time.time()
    df = build_dataset(n_per_category=900)   # 9 000 örnek

    X_train, X_test, y_train, y_test = train_test_split(
        df["description"].tolist(),
        df["category"].tolist(),
        test_size=0.15,
        random_state=42,
        stratify=df["category"],
    )

    pipeline, cv_metrics = train_categorizer(X_train, y_train)

    # Test seti değerlendirmesi
    y_pred = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)
    report   = classification_report(y_test, y_pred, zero_division=0)

    save_categorizer(pipeline)
    elapsed = time.time() - t0

    results["categorizer"] = {
        "cv_accuracy":   round(cv_metrics["cv_mean"] * 100, 2),
        "cv_std":        round(cv_metrics["cv_std"] * 100, 2),
        "test_accuracy": round(test_acc * 100, 2),
        "n_train":       len(X_train),
        "n_test":        len(X_test),
        "elapsed_s":     round(elapsed, 1),
    }

    if verbose:
        print(f"  Eğitim seti    : {len(X_train):,} örnek")
        print(f"  Test seti      : {len(X_test):,} örnek")
        print(f"  5-katlı CV     : %{cv_metrics['cv_mean']*100:.2f} ± %{cv_metrics['cv_std']*100:.2f}")
        print(f"  Test doğruluğu : %{test_acc*100:.2f}")
        print(f"  Süre           : {elapsed:.1f}s")
        print("\nSınıf bazında rapor:")
        print(report)

    # ── 2. HARCAMA TAHMİN MODELİ ──────────────────────────────────────────────
    if verbose:
        print("=" * 60)
        print("2/3  HARCAMA TAHMİN MODELİ  (Ridge Regression)")
        print("=" * 60)

    t0 = time.time()
    transactions = _load_db_transactions()
    metrics_f    = train_forecaster(transactions)
    elapsed = time.time() - t0

    results["forecaster"] = {**metrics_f, "elapsed_s": round(elapsed, 1)}

    if verbose:
        if metrics_f.get("trained"):
            print(f"  İşlem sayısı   : {metrics_f['n_samples']}")
            if "mae" in metrics_f:
                print(f"  MAE            : {metrics_f['mae']:,.0f} ₺")
                print(f"  RMSE           : {metrics_f['rmse']:,.0f} ₺")
        else:
            print(f"  ⚠️  {metrics_f.get('error')}")
        print(f"  Süre           : {elapsed:.1f}s")

    # ── 3. ANOMALİ DEDEKTÖRÜ ──────────────────────────────────────────────────
    if verbose:
        print("=" * 60)
        print("3/3  ANOMALİ DEDEKTÖRÜ  (IsolationForest)")
        print("=" * 60)

    t0 = time.time()
    metrics_a = train_anomaly(transactions)
    elapsed = time.time() - t0

    results["anomaly"] = {**metrics_a, "elapsed_s": round(elapsed, 1)}

    if verbose:
        if metrics_a.get("trained"):
            print(f"  Gider işlemi   : {metrics_a['n_samples']}")
        else:
            print(f"  ⚠️  {metrics_a.get('error')}")
        print(f"  Süre           : {elapsed:.1f}s")

    if verbose:
        print("\n" + "=" * 60)
        print("✅  Tüm modeller eğitildi → models_ml/ dizinine kaydedildi")
        print("=" * 60)

    return results


if __name__ == "__main__":
    train_all(verbose=True)
