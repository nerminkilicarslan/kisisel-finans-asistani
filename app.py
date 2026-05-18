import os
import streamlit as st
from datetime import date
from dotenv import load_dotenv
from models import init_db, SessionLocal, Transaction, BudgetPlan, SavingsGoal
from services.firebase_service import (
    is_firebase_enabled,
    get_firestore_transactions,
    sync_transaction,
    sync_budget_plan,
    sync_savings_goal,
    delete_transaction,
    delete_budget_plan,
    delete_savings_goal,
    get_firestore_budget_plans,
    get_firestore_savings_goals,
)
from services.ui_helpers import inject_css, sidebar_stats, status_chip, tip

load_dotenv(override=True)

# Cache Firebase veri çekimi
@st.cache_data(ttl=60)
def get_firestore_transactions_cached():
    return get_firestore_transactions()

@st.cache_data(ttl=60)
def get_firestore_budget_plans_cached():
    return get_firestore_budget_plans()

@st.cache_data(ttl=60)
def get_firestore_savings_goals_cached():
    return get_firestore_savings_goals()

st.set_page_config(
    page_title="Finans Asistanım",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
init_db()

today    = date.today()
fb_ready = is_firebase_enabled()
if fb_ready:
    try:
        tx_count = len(get_firestore_transactions_cached())
    except Exception:
        tx_count = 0
        fb_ready = False
else:
    db = SessionLocal()
    tx_count = db.query(Transaction).count()
    db.close()

ml_ready = os.path.exists("models_ml/categorizer.joblib")
api_key  = os.getenv("GEMINI_API_KEY", "").strip()
ai_ready = bool(api_key) and api_key != "buraya_api_anahtarinizi_yazin"
fb_ready = is_firebase_enabled()

if tx_count > 0:
    from services.analytics import get_monthly_summary
    if fb_ready:
        try:
            txs = get_firestore_transactions_cached()
            summary = get_monthly_summary(txs, today.month, today.year)
        except Exception:
            db = SessionLocal()
            summary = get_monthly_summary(db, today.month, today.year)
            db.close()
    else:
        db = SessionLocal()
        summary = get_monthly_summary(db, today.month, today.year)
        db.close()
    sidebar_stats(summary)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:2.5rem 0 2rem">
    <div style="display:inline-flex;align-items:center;gap:0.6rem;
                background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);
                border-radius:20px;padding:0.3rem 1rem;margin-bottom:1.5rem">
        <span style="width:6px;height:6px;border-radius:50%;background:#818cf8;
                     box-shadow:0 0 8px #818cf8;flex-shrink:0"></span>
        <span style="color:#818cf8;font-size:0.75rem;font-weight:600;
                     letter-spacing:0.06em">KİŞİSEL FİNANS ASISTANI</span>
    </div>
    <h1 style="font-size:2.6rem;margin:0 0 0.6rem;letter-spacing:-0.04em;
               background:linear-gradient(135deg,#e8f0fe 0%,#818cf8 60%,#06b6d4 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;line-height:1.15">
        Paranızın kontrolü<br>sizin elinizde
    </h1>
    <p style="color:#3d5475;font-size:1rem;margin:0;max-width:480px;line-height:1.7">
        Harcamalarınızı kategorilere ayırın, bütçe hedefleri belirleyin
        ve yapay zeka destekli finansal öneriler alın.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Başlamak için (sadece veri yokken) ────────────────────────────────────────
if tx_count == 0:
    sc1, sc2, sc3, _ = st.columns([1, 1, 1, 1])
    with sc1:
        st.markdown(f"""
        <div class="step-card">
            <div class="step-num">1</div>
            <div class="step-title">Demo Veri</div>
            <div class="step-desc">Uygulamayı hemen keşfetmek için örnek işlemler yükleyin.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Demo Verisi Yükle", type="primary", use_container_width=True):
            with st.spinner("Veriler oluşturuluyor…"):
                from seed_data import generate_transactions, generate_budgets, generate_goals
                txs = generate_transactions(months_back=6)
                budgets = generate_budgets(today.year, today.month)
                goals = generate_goals()
                total_items = len(txs) + len(budgets) + len(goals)
                progress = st.progress(0)
                percent_text = st.empty()
                status = st.empty()
                db = SessionLocal()
                completed = 0
                percent_text.markdown("**%0 tamamlandı**")

                for tx in txs:
                    db.add(tx)
                    completed += 1
                    status.markdown(
                        f"İşlem ekleniyor... kalan {total_items-completed} kayıt"
                    )
                    percent = int(completed * 100 / total_items)
                    progress.progress(completed / total_items)
                    percent_text.markdown(f"**%{percent} tamamlandı**")

                for plan in budgets:
                    db.add(plan)
                    completed += 1
                    status.markdown(
                        f"Bütçe kaydı ekleniyor... kalan {total_items-completed} kayıt"
                    )
                    percent = int(completed * 100 / total_items)
                    progress.progress(completed / total_items)
                    percent_text.markdown(f"**%{percent} tamamlandı**")

                for goal in goals:
                    db.add(goal)
                    completed += 1
                    status.markdown(
                        f"Hedef ekleniyor... kalan {total_items-completed} kayıt"
                    )
                    percent = int(completed * 100 / total_items)
                    progress.progress(completed / total_items)
                    percent_text.markdown(f"**%{percent} tamamlandı**")

                db.commit()

                if fb_ready:
                    status.markdown("Firebase'e eşleştiriliyor...")
                    for tx in db.query(Transaction).all():
                        sync_transaction(tx)
                    for plan in db.query(BudgetPlan).all():
                        sync_budget_plan(plan)
                    for goal in db.query(SavingsGoal).all():
                        sync_savings_goal(goal)

                # İşlem tamamlandı — yüzdeyi 100 yap
                progress.progress(100)
                percent_text.markdown("**%100 tamamlandı**")
                db.close()
            st.success("Örnek veriler yüklendi!")
            st.rerun()
    with sc2:
        st.markdown(f"""
        <div class="step-card">
            <div class="step-num">2</div>
            <div class="step-title">Kendi Verileriniz</div>
            <div class="step-desc">Banka ekstrenizi CSV veya Google Drive ile içe aktarın.</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div class="step-card">
            <div class="step-num">3</div>
            <div class="step-title">Analiz Edin</div>
            <div class="step-desc">Dashboard'da grafikleri ve yapay zeka tahminlerini görün.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Demo Verilerini Sil", type="secondary", use_container_width=True):
        with st.spinner("Veriler temizleniyor..."):
            progress = st.progress(0)
            percent_text = st.empty()
            status = st.empty()
            db = SessionLocal()
            status.markdown("İşlemler kaldırılıyor...")
            db.query(Transaction).delete()
            progress.progress(0.25)
            percent_text.markdown("**%25 tamamlandı**")
            db.query(BudgetPlan).delete()
            progress.progress(0.5)
            percent_text.markdown("**%50 tamamlandı**")
            db.query(SavingsGoal).delete()
            progress.progress(0.75)
            percent_text.markdown("**%75 tamamlandı**")
            db.commit()
            db.close()
            if fb_ready:
                status.markdown("Firebase'e eşleştiriliyor...")
                firestore_items = (
                    len(get_firestore_transactions()) +
                    len(get_firestore_budget_plans()) +
                    len(get_firestore_savings_goals())
                )
                completed = 0
                if firestore_items:
                    for tx in get_firestore_transactions():
                        delete_transaction(tx["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                    for plan in get_firestore_budget_plans():
                        delete_budget_plan(plan["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                    for goal in get_firestore_savings_goals():
                        delete_savings_goal(goal["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                else:
                    progress.progress(1.0)
            else:
                progress.progress(1.0)
            percent_text.markdown("**%100 tamamlandı**")
        st.success("Demo verileri silindi.")
        st.rerun()

# ── Bu ay özeti ───────────────────────────────────────────────────────────────
else:
    st.markdown('<p class="section-title">Bu Ay</p>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gelir",        f"{summary['income']:,.0f} ₺")
    m2.metric("Gider",        f"{summary['expense']:,.0f} ₺")
    m3.metric("Net Tasarruf", f"{summary['savings']:,.0f} ₺",
              delta=f"%{summary['savings_rate']:.1f}")
    m4.metric("En Çok",       summary['top_category'])
    st.markdown("<br>", unsafe_allow_html=True)
    # Eğer sistemde veri varsa (örn. demo veriler), kolay erişim için silme butonu göster
    if st.button("🗑️ Demo Verilerini Sil", type="secondary", use_container_width=True):
        with st.spinner("Veriler temizleniyor..."):
            progress = st.progress(0)
            percent_text = st.empty()
            status = st.empty()
            status.markdown("İşlemler kaldırılıyor...")
            db = SessionLocal()
            db.query(Transaction).delete()
            progress.progress(0.25)
            percent_text.markdown("**%25 tamamlandı**")
            db.query(BudgetPlan).delete()
            progress.progress(0.5)
            percent_text.markdown("**%50 tamamlandı**")
            db.query(SavingsGoal).delete()
            progress.progress(0.75)
            percent_text.markdown("**%75 tamamlandı**")
            db.commit()
            db.close()
            if fb_ready:
                status.markdown("Firebase'e eşleştiriliyor...")
                firestore_items = (
                    len(get_firestore_transactions()) +
                    len(get_firestore_budget_plans()) +
                    len(get_firestore_savings_goals())
                )
                completed = 0
                if firestore_items:
                    for tx in get_firestore_transactions():
                        delete_transaction(tx["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                    for plan in get_firestore_budget_plans():
                        delete_budget_plan(plan["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                    for goal in get_firestore_savings_goals():
                        delete_savings_goal(goal["id"])
                        completed += 1
                        progress.progress(0.75 + 0.25 * completed / firestore_items)
                else:
                    progress.progress(1.0)
            else:
                progress.progress(1.0)
            percent_text.markdown("**%100 tamamlandı**")
        st.success("Demo verileri silindi.")
        st.rerun()

# ── Özellik kartları ───────────────────────────────────────────────────────────
st.markdown('<p class="section-title">Neler Yapabilirsiniz?</p>', unsafe_allow_html=True)

features = [
    ("#4f46e5", "#818cf8", "📊", "Finansal Dashboard",
     "Aylık gelir-gider özetinizi, kategori dağılımını ve 6 aylık trend grafiğini görün. "
     "Yapay zeka modeli gelecek ay harcamalarınızı kategori bazlı tahmin eder.",
     ["Özet grafikleri", "Trend analizi", "ML tahmini"]),
    ("#0891b2", "#22d3ee", "💳", "Gelir & Gider Takibi",
     "İşlemlerinizi kaydedin, kategorilere göre filtreleyin. Banka ekstrenizi "
     "CSV veya Google Drive ile içe aktarın; kategoriler otomatik belirlenir.",
     ["İşlem ekleme", "Akıllı kategorileme", "CSV & Drive"]),
    ("#d97706", "#fbbf24", "🎯", "Bütçe & Hedefler",
     "Kategorilere aylık harcama limiti koyun, aşımlarda uyarı alın. "
     "Tatil fonu, acil durum fonu gibi tasarruf hedeflerinizi takip edin.",
     ["Kategori limitleri", "Uyarı sistemi", "Tasarruf hedefleri"]),
    ("#7c3aed", "#a78bfa", "🤖", "AI Finans Danışmanı",
     "Gemini 2.0 Flash ile kendi verilerinize dayalı finansal sorular sorun. "
     "Kişiselleştirilmiş bütçe önerileri ve tasarruf stratejileri alın.",
     ["Kişisel analiz", "Akıllı öneriler", "Serbest sohbet"]),
]

c1, c2, c3, c4 = st.columns(4, gap="small")
for col, (accent, light, icon, title, desc, tags) in zip([c1, c2, c3, c4], features):
    tag_html = " ".join(
        f'<span style="background:rgba(255,255,255,0.04);border:1px solid #0f2035;'
        f'border-radius:5px;padding:0.15rem 0.55rem;font-size:0.7rem;color:#3d5475;'
        f'white-space:nowrap">{t}</span>'
        for t in tags
    )
    col.markdown(f"""
    <div style="background:#0a1522;border:1px solid #0f2035;border-radius:16px;
                padding:1.5rem;display:flex;flex-direction:column;gap:0.8rem;
                position:relative;overflow:hidden;
                transition:border-color 0.2s,transform 0.15s">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;
                    background:linear-gradient(90deg,{accent},{light})"></div>
        <div style="width:40px;height:40px;border-radius:10px;
                    background:rgba(255,255,255,0.04);border:1px solid #0f2035;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.3rem">{icon}</div>
        <div>
            <div style="font-weight:700;color:#c8d8ea;font-size:0.95rem;
                        margin-bottom:0.4rem">{title}</div>
            <div style="color:#3d5475;font-size:0.8rem;line-height:1.6">{desc}</div>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.35rem;padding-top:0.2rem">
            {tag_html}
        </div>
    </div>""", unsafe_allow_html=True)

# ── Durum ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
data_chip = status_chip(f"{tx_count} işlem" if tx_count else "Veri yok",
                        "ok" if tx_count else "warn")
ml_chip   = status_chip("Kategorileme hazır" if ml_ready else "Kategorileme eğitilmedi",
                        "ok" if ml_ready else "warn")
ai_chip   = status_chip("AI Danışman aktif" if ai_ready else "AI bağlı değil",
                        "ok" if ai_ready else "err")
fb_chip   = status_chip("Firebase bağlı" if fb_ready else "Firebase devre dışı",
                        "ok" if fb_ready else "warn")
st.markdown(f'<div class="status-row">{data_chip}{ml_chip}{ai_chip}{fb_chip}</div>',
            unsafe_allow_html=True)
