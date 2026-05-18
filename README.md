# 💰 Kişisel Finans Asistanı

Türkçe arayüzlü, yapay zeka destekli kişisel finans takip uygulaması.  
Streamlit + SQLite + Gemini 2.0 Flash + scikit-learn ile geliştirilmiştir.

---

## Özellikler

- **📊 Dashboard** — Aylık gelir/gider özeti, kategori dağılımı, 6 aylık trend grafiği
- **🔮 ML Harcama Tahmini** — Ridge Regression ile gelecek ay kategori bazlı tahmin
- **💳 Harcama Yönetimi** — İşlem ekleme, listeleme, silme, CSV banka ekstresi içe aktarma
- **🚨 Anomali Tespiti** — IsolationForest + Z-score ile olağandışı harcama tespiti
- **🤖 ML Kategori Önerisi** — TF-IDF + Logistic Regression, %99.9 doğrulukla otomatik kategori tahmini
- **🎯 Bütçe Planı** — Kategori bazlı limit tanımlama, görsel ilerleme takibi
- **🏆 Tasarruf Hedefleri** — Hedef oluşturma ve ilerleme takibi
- **🤖 AI Danışman** — Gemini 2.0 Flash ile kişisel finans analizi ve öneriler

---

## Kurulum

### Gereksinimler

- Python 3.10+
- [Gemini API Key](https://aistudio.google.com) (AI Danışman için; anahtarı kendiniz alıp .env dosyanıza eklemelisiniz)
- Firebase Service Account JSON (isteğe bağlı, verilerin bulut tabanlı saklanması için)

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/nerminkilicarslan/finans-asistani.git
cd finans-asistani

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# 3. API anahtarını ayarla
cp .env.example .env
# .env dosyasını açıp GEMINI_API_KEY= satırına kendi Gemini API anahtarınızı yazın
# Gemini API anahtarını henüz almadıysanız https://aistudio.google.com adresinden edinin
# Eğer Firebase kullanacaksanız FIREBASE_SERVICE_ACCOUNT_PATH= satırına servis hesabı JSON dosya yolunu girin

# 4. Demo verisi yükle (isteğe bağlı)
python seed_data.py

# 5. ML modellerini eğit
python ml/train.py

# 6. Uygulamayı başlat
streamlit run app.py
```

Uygulama `http://localhost:8501` adresinde açılır.

---

## Proje Yapısı

```
finans-asistani/
├── app.py                    # Ana giriş noktası
├── models.py                 # SQLAlchemy ORM modelleri
├── seed_data.py              # Demo veri üretici
├── requirements.txt
│
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_💳_Harcamalar.py
│   ├── 3_🎯_Butce.py
│   └── 4_🤖_AI_Danışman.py
│
├── services/
│   ├── analytics.py          # Özet, trend, bütçe uyarıları
│   ├── csv_importer.py       # Banka ekstresi CSV içe aktarıcı
│   ├── gemini_service.py     # Gemini API entegrasyonu
│   └── ui_helpers.py         # CSS ve ortak UI bileşenleri
│
├── ml/
│   ├── dataset.py            # 9 000 örneklik Türkçe sentetik veri seti
│   ├── categorizer.py        # TF-IDF + Logistic Regression
│   ├── forecaster.py         # Ridge Regression harcama tahmini
│   ├── anomaly.py            # IsolationForest anomali dedektörü
│   └── train.py              # Tüm modelleri eğiten pipeline
│
└── .streamlit/
    └── config.toml           # Koyu indigo tema
```

---

## ML Modelleri

| Model | Algoritma | Amaç | Performans |
|-------|-----------|------|------------|
| Kategorileme | TF-IDF + Logistic Regression | İşlem açıklaması → kategori | %99.9 CV doğruluğu |
| Harcama Tahmini | Ridge Regression | Gelecek ay gider tahmini | ~142 ₺ MAE |
| Anomali Tespiti | IsolationForest + Z-score | Olağandışı harcama tespiti | %7 kontaminasyon |

Modeller `python ml/train.py` ile eğitilir ve `models_ml/` dizinine kaydedilir.

### Kategoriler

`Market · Fatura · Yemek · Ulaşım · Eğlence · Sağlık · Giyim · Eğitim · Kira · Diğer`

---

## CSV İçe Aktarma

Banka ekstrenizi aşağıdaki formatta CSV olarak içe aktarabilirsiniz:

```csv
tarih,tutar,aciklama
15/04/2025,-250.00,MIGROS MARKET ALINMASI
01/04/2025,22000.00,MAAS ODEME
```

- Negatif tutarlar → **gider**, pozitif tutarlar → **gelir**
- Kategori sütunu yoksa ML modeli otomatik atar
- Kabul edilen tarih formatları: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD.MM.YYYY`

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Streamlit |
| Veritabanı | SQLite + SQLAlchemy |
| ML | scikit-learn, joblib |
| AI | Google Gemini 2.0 Flash |
| Grafikler | Plotly |
| Veri | Pandas, NumPy |

---

## Ekran Görüntüleri

> Uygulamayı başlatıp `http://localhost:8501` adresini ziyaret edin.

---

## Lisans

MIT
