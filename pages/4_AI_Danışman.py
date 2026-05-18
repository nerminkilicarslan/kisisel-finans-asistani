import os
import streamlit as st
from datetime import date
from dotenv import load_dotenv
from models import SessionLocal
from services.analytics import get_monthly_summary, get_category_breakdown
from services.firebase_service import is_firebase_enabled, get_firestore_transactions
from services.firebase_service import is_firebase_enabled
from services.gemini_service import ask_assistant
from services.ui_helpers import inject_css, page_header, section_title, sidebar_stats, tip, status_chip

load_dotenv(override=True)

st.set_page_config(page_title="AI Danışman", page_icon="🤖", layout="wide")
inject_css()
page_header("🤖", "AI Finans Danışmanı",
            "Gemini 2.0 Flash — kişisel verilerinize dayalı analiz")

today = date.today()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_question" not in st.session_state:
    st.session_state.last_question = None

# Cache veri çekimini 1 saat boyunca tutmak
@st.cache_data(ttl=3600)
def get_firestore_transactions_cached():
    return get_firestore_transactions()

@st.cache_data(ttl=3600)
def get_monthly_summary_cached(month, year):
    if is_firebase_enabled():
        transactions = get_firestore_transactions_cached()
        return get_monthly_summary(transactions, month, year)
    else:
        db = SessionLocal()
        summary = get_monthly_summary(db, month, year)
        db.close()
        return summary

@st.cache_data(ttl=3600)
def get_category_breakdown_cached(month, year):
    if is_firebase_enabled():
        transactions = get_firestore_transactions_cached()
        return get_category_breakdown(transactions, month, year)
    else:
        db = SessionLocal()
        breakdown = get_category_breakdown(db, month, year)
        db.close()
        return breakdown

fb_ready = is_firebase_enabled()
summary = get_monthly_summary_cached(today.month, today.year)
breakdown = get_category_breakdown_cached(today.month, today.year)

cat_summary = "\n".join(
    f"  • {r['category']}: {r['amount']:,.0f} ₺ (%{r['pct']:.0f})"
    for _, r in breakdown.iterrows()
) if not breakdown.empty else ""

context = {
    "income": summary["income"], "expense": summary["expense"],
    "savings": summary["savings"], "savings_rate": summary["savings_rate"],
    "top_category": summary["top_category"], "category_summary": cat_summary,
}

sidebar_stats(summary)

# ── API durum göstergesi ──────────────────────────────────────────────────────
api_key  = os.getenv("GEMINI_API_KEY", "").strip()
ai_ready = bool(api_key) and api_key != "buraya_api_anahtarinizi_yazin"
fb_ready = is_firebase_enabled()

if ai_ready:
    st.markdown(
        f'<div style="margin-bottom:1rem">{status_chip("Gemini 2.0 Flash — Bağlı", "ok")}</div>',
        unsafe_allow_html=True,
    )
else:
    tip("AI Danışman şu anda bağlı değil. "
        "Proje klasöründeki <strong>.env</strong> dosyasına "
        "<strong>GEMINI_API_KEY=…</strong> satırını ekleyip uygulamayı yeniden başlatın. "
        "API anahtarını <a href='https://aistudio.google.com' target='_blank' "
        "style='color:#818cf8'>aistudio.google.com</a> adresinden ücretsiz alabilirsiniz.")
    st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    f'<div>{status_chip("Firebase bağlı" if fb_ready else "Firebase devre dışı", "ok" if fb_ready else "warn")}</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Sohbeti Temizle", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.rerun()

# ── Hızlı soru kartları ────────────────────────────────────────────────────────
quick_qs = [
    ("💸", "Bu ay nerede fazla harcama yapıyorum?"),
    ("📈", "Tasarruf oranımı nasıl artırabilirim?"),
    ("🛡️", "Acil durum fonu ne kadar olmalı?"),
    ("🔍", "Bütçemi optimize etmem için 3 öneri"),
    ("🧾", "Gelecek ay harcama tahminim nedir?"),
    ("🎯", "Tasarruf hedefi oluşturmak için öneriler"),
    ("🔎", "En çok harcama yaptığım 3 kategori hangileri?"),
    ("💡", "Gereksiz abonelikleri nasıl tespit ederim?"),
    ("📊", "3 aylık harcama trendimi özetle"),
    ("💬", "Bana 3 hızlı bütçe kuralı söyle"),
]

section_title("Hızlı Sorular")
# 10 öneri için 5 sütunlu ızgara (otomatik satır sarma)
cols = st.columns(5, gap="small")
for i, (icon, q) in enumerate(quick_qs):
    col = cols[i % 5]
    with col:
        label = q[:28] + "…" if len(q) > 28 else q
        if st.button(f"{icon}  {label}", use_container_width=True, help=q, key=f"btn_{i}"):
            # Aynı soruya tekrar tıklanırsa tekrar yapma
            if st.session_state.last_question != q:
                st.session_state.last_question = q
                st.session_state.messages.append({"role": "user", "content": q})
                reply = ask_assistant(q, context)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.rerun()

st.divider()

# ── Sohbet ─────────────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div style="background:#0a1522;border:1px dashed #0f2035;border-radius:14px;
                padding:3rem 2rem;text-align:center;margin:1rem 0">
        <div style="font-size:2rem;margin-bottom:0.6rem">💬</div>
        <div style="color:#94a3b8;font-size:0.9rem">Finansal sorunuzu yazın</div>
        <div style="color:#475569;font-size:0.8rem;margin-top:0.3rem">
            Yukarıdan hızlı soru seçebilir veya aşağıya yazabilirsiniz
        </div>
    </div>""", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Sorunuzu yazın…"):
    # Tekrarlanan çağrıları engellemek için kontrol et
    if st.session_state.last_question != prompt:
        st.session_state.last_question = prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner(""):
                reply = ask_assistant(prompt, context)
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
