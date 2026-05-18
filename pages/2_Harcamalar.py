import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from models import SessionLocal, Transaction, init_db
from services.analytics import CATEGORIES_GIDER, CATEGORIES_GELIR, get_monthly_summary
from services.csv_importer import import_csv
from services.firebase_service import (
    delete_transaction, sync_transaction, is_firebase_enabled,
    get_firestore_transactions, upload_csv_file, is_firebase_storage_enabled,
)
from services.ui_helpers import inject_css, page_header, section_title, sidebar_stats, tip, empty_state
import tempfile, os

st.set_page_config(page_title="Harcamalar", page_icon="💳", layout="wide")
inject_css()
page_header("💳", "Gelir & Gider Yönetimi")
init_db()

today = date.today()
fb_ready = is_firebase_enabled()
if fb_ready:
    txs = get_firestore_transactions()
    summary = get_monthly_summary(txs, today.month, today.year)
else:
    db = SessionLocal()
    summary = get_monthly_summary(db, today.month, today.year)
    db.close()
sidebar_stats(summary)

tip("Bu sayfadan <strong>manuel işlem ekleyebilir</strong>, geçmiş işlemleri <strong>arayıp filtreleyebilir</strong>, "
    "banka ekstrenizi <strong>CSV olarak içe aktarabilir</strong> ve "
    "<strong>olağandışı harcamaları</strong> tespit edebilirsiniz.")

tab_add, tab_list, tab_anomaly, tab_import = st.tabs([
    "➕ Yeni İşlem", "📋 İşlemler", "🚨 Anomali", "📂 CSV İçe Aktar"
])

# ── TAB 1: Yeni İşlem ──────────────────────────────────────────────────────────
with tab_add:
    col_form, col_ml = st.columns([3, 2], gap="large")

    with col_form:
        with st.form("tx_form", clear_on_submit=True):
            r1c1, r1c2 = st.columns(2)
            tx_type = r1c1.radio("Tür", ["gider", "gelir"], horizontal=True)
            amount  = r1c1.number_input("Tutar (₺)", min_value=0.01, format="%.2f")
            cats     = CATEGORIES_GIDER if tx_type == "gider" else CATEGORIES_GELIR
            category = r1c2.selectbox("Kategori", cats)
            tx_date  = r1c2.date_input("Tarih", value=today)
            description = st.text_input("Açıklama", placeholder="örn: Migros market alışverişi")
            submitted = st.form_submit_button("Kaydet", use_container_width=True)

        if submitted:
            db = SessionLocal()
            tx = Transaction(date=tx_date, amount=amount, category=category,
                               description=description, type=tx_type, source="manual")
            db.add(tx)
            db.commit()
            try:
                sync_transaction(tx)
            except Exception:
                pass
            db.close()
            st.success(f"**{amount:,.2f} ₺** kaydedildi — {category}")
            st.rerun()

    with col_ml:
        section_title("ML Kategori Önerisi")
        preview_desc = st.text_input(
            "ml_input", placeholder="Açıklama yazın → anlık tahmin",
            key="ml_preview", label_visibility="collapsed",
        )
        if preview_desc:
            try:
                from ml.categorizer import predict_proba, is_ready
                if is_ready():
                    probs = predict_proba(preview_desc)
                    top3  = list(probs.items())[:3]
                    for i, (cat, prob) in enumerate(top3):
                        is_top = i == 0
                        bg   = "rgba(99,102,241,0.12)" if is_top else "rgba(255,255,255,0.03)"
                        col_c = "#818cf8" if is_top else "#475569"
                        st.markdown(f"""
                        <div style="background:{bg};border:1px solid {'#2d3a6e' if is_top else '#111c2d'};
                                    border-radius:8px;padding:0.55rem 0.8rem;margin-bottom:0.35rem;
                                    display:flex;justify-content:space-between;align-items:center">
                            <span style="color:{col_c};font-weight:{'700' if is_top else '400'};
                                         font-size:0.875rem">{cat}</span>
                            <span style="color:{col_c};font-size:0.82rem;font-weight:600">
                                %{prob*100:.1f}
                            </span>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.info("`python ml/train.py` ile modeli eğitin.")
            except Exception:
                pass
        else:
            st.markdown("""
            <div style="color:#1e2d3d;border:1px dashed #1e2d3d;border-radius:10px;
                        padding:2rem;text-align:center;font-size:0.82rem">
                İşlem açıklaması yazın
            </div>""", unsafe_allow_html=True)

# ── TAB 2: İşlemler ───────────────────────────────────────────────────────────
with tab_list:
    if fb_ready:
        txs = sorted(get_firestore_transactions(), key=lambda t: t["date"], reverse=True)[:500]
    else:
        db = SessionLocal()
        txs = db.query(Transaction).order_by(Transaction.date.desc()).limit(500).all()
        db.close()

    if not txs:
        empty_state("📋", "Henüz işlem yok",
                    "Yeni İşlem sekmesinden manuel ekleyin ya da CSV İçe Aktar sekmesinden "
                    "banka ekstrenizi yükleyin.")
    else:
        df = pd.DataFrame([{
                "ID": t["id"] if isinstance(t, dict) else t.id,
                "Tarih": t["date"] if isinstance(t, dict) else t.date,
                "Tür": t["type"] if isinstance(t, dict) else t.type,
                "Kategori": t["category"] if isinstance(t, dict) else t.category,
                "Tutar": t["amount"] if isinstance(t, dict) else t.amount,
                "Açıklama": (t["description"] if isinstance(t, dict) else t.description) or "",
            } for t in txs])

        # Özet istatistikler
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Toplam",         len(df))
        s2.metric("Toplam Gelir",   f"{df[df['Tür']=='gelir']['Tutar'].sum():,.0f} ₺")
        s3.metric("Toplam Gider",   f"{df[df['Tür']=='gider']['Tutar'].sum():,.0f} ₺")
        s4.metric("Ort. İşlem",     f"{df['Tutar'].mean():,.0f} ₺")

        st.markdown("<br>", unsafe_allow_html=True)

        # Filtreler
        f1, f2, f3 = st.columns([3, 1.5, 1.5])
        search_q = f1.text_input("ara", placeholder="🔍 Açıklama veya kategori ara…",
                                  label_visibility="collapsed", key="tx_search")
        f_type   = f2.multiselect("Tür", ["gelir","gider"],
                                   default=["gelir","gider"],
                                   label_visibility="collapsed")
        f_cat    = f3.multiselect("Kategori", sorted(df["Kategori"].unique()),
                                   default=list(df["Kategori"].unique()),
                                   label_visibility="collapsed")

        mask = df["Tür"].isin(f_type) & df["Kategori"].isin(f_cat)
        if search_q:
            mask &= (
                df["Açıklama"].str.contains(search_q, case=False, na=False) |
                df["Kategori"].str.contains(search_q, case=False, na=False)
            )
        df_f = df[mask].copy()
        df_f["Tür"]   = df_f["Tür"].map({"gelir": "✅ Gelir", "gider": "❌ Gider"})
        df_f["Tutar"] = df_f["Tutar"].map(lambda x: f"{x:,.2f} ₺")

        st.dataframe(
            df_f.drop(columns=["ID"]).style.apply(
                lambda row: (
                    ["background-color:rgba(74,222,128,0.04)"]*5
                    if "Gelir" in str(row["Tür"])
                    else ["background-color:rgba(248,113,113,0.04)"]*5
                ),
                axis=1,
            ),
            use_container_width=True, hide_index=True,
        )
        st.caption(f"{len(df_f)} işlem gösteriliyor")

        st.divider()
        del_c1, del_c2 = st.columns([3, 1])
        del_id = del_c1.number_input("Silinecek ID", min_value=1, step=1,
                                      label_visibility="collapsed",
                                      placeholder="Silinecek işlem ID'si…")
        if del_c2.button("🗑️ Sil", type="secondary", use_container_width=True):
            if fb_ready:
                # Firestore delete relies on local DB id mapping if available.
                # For now, delete from local DB for consistency and remove from Firebase if present.
                db = SessionLocal()
                tx = db.query(Transaction).filter(Transaction.id == del_id).first()
                if tx:
                    tx_id = tx.id
                    db.delete(tx)
                    db.commit()
                    try:
                        delete_transaction(tx_id)
                    except Exception:
                        pass
                    st.success(f"ID {del_id} silindi.")
                    st.rerun()
                else:
                    st.error("İşlem bulunamadı.")
                db.close()
            else:
                db = SessionLocal()
                tx = db.query(Transaction).filter(Transaction.id == del_id).first()
                if tx:
                    tx_id = tx.id
                    db.delete(tx)
                    db.commit()
                    try:
                        delete_transaction(tx_id)
                    except Exception:
                        pass
                    st.success(f"ID {del_id} silindi.")
                    st.rerun()
                else:
                    st.error("İşlem bulunamadı.")
                db.close()

# ── TAB 3: Anomali ────────────────────────────────────────────────────────────
with tab_anomaly:
    st.markdown("""
    <p style="color:#475569;font-size:0.85rem;margin-bottom:1rem">
        IsolationForest + Z-score ile olağandışı harcamalar tespit edilir.
        Birleşik skor: <strong style="color:#94a3b8">%60 IsolationForest + %40 Z-score</strong>
    </p>""", unsafe_allow_html=True)

    try:
        from ml.anomaly import score_transactions, is_ready as anomaly_ready
        if not anomaly_ready():
            tip("Anomali modeli henüz eğitilmedi. "
                "Terminalde <strong>python ml/train.py</strong> çalıştırın. "
                "Model, sizin harcama örüntünüzü öğrenerek alışılmadık tutarları otomatik işaretler.")
        else:
            db = SessionLocal()
            txs_all = db.query(Transaction).order_by(Transaction.date.desc()).limit(500).all()
            db.close()

            scored = score_transactions([{
                "id": t.id, "date": t.date, "amount": t.amount,
                "category": t.category, "description": t.description, "type": t.type,
            } for t in txs_all])

            high = sum(1 for t in scored if t["anomaly_level"] == "yüksek")
            mid  = sum(1 for t in scored if t["anomaly_level"] == "orta")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("🔴 Yüksek", high)
            mc2.metric("🟡 Orta",   mid)
            mc3.metric("✅ Normal",  len(scored) - high - mid)
            st.divider()

            level_opts = {"Tümü": None, "Yüksek": "yüksek", "Orta": "orta"}
            sel = st.segmented_control("Filtre", list(level_opts.keys()),
                                        default="Tümü") \
                  if hasattr(st, "segmented_control") \
                  else st.radio("Filtre", list(level_opts.keys()), horizontal=True)

            filtered = sorted(
                [t for t in scored
                 if (level_opts[sel] is None or t["anomaly_level"] == level_opts[sel])
                 and t.get("type") == "gider"],
                key=lambda x: x["anomaly_score"], reverse=True,
            )

            if filtered:
                rows = []
                for t in filtered[:50]:
                    lv = t["anomaly_level"]
                    icon = "🔴" if lv == "yüksek" else "🟡"
                    rows.append({
                        "":         icon,
                        "Tarih":    t["date"],
                        "Kategori": t["category"],
                        "Tutar":    f"{t['amount']:,.2f} ₺",
                        "Skor":     f"{t['anomaly_score']:.2f}",
                        "Açıklama": t.get("description",""),
                        "Neden":    t.get("anomaly_reason",""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.success("Bu filtrede anomali bulunamadı.")
    except Exception as e:
        st.error(f"Anomali modülü hatası: {e}")

# ── TAB 4: CSV ────────────────────────────────────────────────────────────────
with tab_import:
    # Format bilgisi
    with st.expander("CSV formatı nasıl olmalı?", expanded=False):
        st.markdown("""
        En az `tarih` ve `tutar` sütunu içeren CSV dosyası yeterlidir:
        ```
        tarih,tutar,aciklama
        15/04/2025,-250.00,MIGROS MARKET ALINMASI
        01/04/2025,22000.00,MAAS ODEME
        ```
        - Negatif tutarlar **gider**, pozitifler **gelir** olarak işlenir
        - Kategori sütunu yoksa yapay zeka otomatik atar
        - Kabul edilen sütun adları: `tarih / date`, `tutar / amount / borç`, `açıklama / aciklama / description`
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    src_tab1, src_tab2 = st.tabs(["💻 Bilgisayardan Yükle", "☁️ Google Drive'dan Yükle"])

    def _process_and_import(tmp_path: str) -> None:
        with st.spinner("Dosya işleniyor…"):
            result = import_csv(tmp_path)
        os.unlink(tmp_path)
        if result["success"]:
            ml_note = (f" · {result.get('ml_categorized', 0)} işlem otomatik kategorilendi"
                       if result.get("ml_categorized") else "")
            st.success(f"✅ **{result['imported']}** işlem içe aktarıldı{ml_note} "
                       f"· {result['skipped']} satır atlandı")
            st.rerun()
        else:
            st.error(f"❌ {result['error']}")

    with src_tab1:
        uploaded = st.file_uploader("CSV dosyası seçin", type=["csv"],
                                     label_visibility="collapsed")
        if uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            if fb_ready and is_firebase_storage_enabled():
                destination = f"csv_uploads/{date.today().isoformat()}_{Path(tmp_path).name}"
                upload_csv_file(tmp_path, destination=destination)
            _process_and_import(tmp_path)

    with src_tab2:
        st.markdown("""
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:0.8rem">
            Google Drive'daki CSV dosyasını herkesle paylaşılabilir yapıp
            bağlantısını buraya yapıştırın.
        </p>
        """, unsafe_allow_html=True)

        drive_url = st.text_input(
            "drive_url", label_visibility="collapsed",
            placeholder="https://drive.google.com/file/d/…/view?usp=sharing",
        )

        if st.button("Drive'dan İçe Aktar", type="primary",
                     disabled=not bool(drive_url)):
            import re, requests as req

            # Dosya ID'sini URL'den çıkar
            match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", drive_url) or \
                    re.search(r"id=([a-zA-Z0-9_-]+)", drive_url)

            if not match:
                st.error("Geçerli bir Google Drive bağlantısı değil. "
                         "Paylaşma bağlantısını kopyaladığınızdan emin olun.")
            else:
                file_id = match.group(1)
                download_url = (f"https://drive.google.com/uc"
                                f"?export=download&id={file_id}&confirm=t")
                try:
                    with st.spinner("Drive'dan indiriliyor…"):
                        resp = req.get(download_url, timeout=30)
                    if resp.status_code != 200:
                        st.error("Dosya indirilemedi. Dosyanın 'Bağlantıya sahip herkes' "
                                 "ile paylaşıldığından emin olun.")
                    elif b"<!DOCTYPE" in resp.content[:100]:
                        st.error("Drive erişim hatası. Dosyayı 'Bağlantıya sahip herkes — "
                                 "Görüntüleyici' olarak paylaşın ve tekrar deneyin.")
                    else:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            tmp.write(resp.content)
                            tmp_path = tmp.name
                        if fb_ready and is_firebase_storage_enabled():
                            destination = f"csv_uploads/{date.today().isoformat()}_{Path(tmp_path).name}"
                            upload_csv_file(tmp_path, destination=destination)
                        _process_and_import(tmp_path)
                except Exception as e:
                    st.error(f"Bağlantı hatası: {e}")

        st.markdown("""
        <div style="background:#0d1826;border:1px solid #1a2840;border-radius:10px;
                    padding:0.9rem 1rem;margin-top:1rem;font-size:0.8rem;color:#475569">
            <strong style="color:#64748b">Nasıl paylaşılır?</strong><br>
            Drive'da dosyaya sağ tıklayın →
            <em>Paylaş</em> → <em>Bağlantıya sahip herkes</em> →
            <em>Görüntüleyici</em> → Bağlantıyı kopyalayın
        </div>
        """, unsafe_allow_html=True)
