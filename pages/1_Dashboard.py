import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from models import SessionLocal, Transaction
from services.analytics import (
    get_monthly_summary, get_category_breakdown,
    get_last_6_months_trend, get_last_n_months_trend, check_budget_alerts,
    get_budget_alerts_from_plans,
)
from services.firebase_service import (
    is_firebase_enabled, get_firestore_transactions,
    get_firestore_budget_plans,
)
from services.ui_helpers import inject_css, page_header, section_title, sidebar_stats, tip, empty_state

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_css()

# Cache Firebase veri çekimi
@st.cache_data(ttl=60)
def get_firestore_transactions_cached():
    return get_firestore_transactions()

@st.cache_data(ttl=60)
def get_firestore_budget_plans_cached():
    return get_firestore_budget_plans()

# ── Tarih seçici (kompakt) ─────────────────────────────────────────────────────
today = date.today()
_ay = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
       "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

fb_ready = is_firebase_enabled()

c_title, c_m, c_y, _ = st.columns([5, 1.5, 1, 4])
c_title.markdown("<h1 style='margin:0;font-size:1.75rem'>📊 Dashboard</h1>",
                 unsafe_allow_html=True)
month = c_m.selectbox("ay", range(1, 13), index=today.month - 1,
                       format_func=lambda m: _ay[m-1], label_visibility="collapsed")
year  = c_y.selectbox("yıl", [today.year - 1, today.year], index=1,
                       label_visibility="collapsed")

if fb_ready:
    try:
        txs = get_firestore_transactions_cached()
        summary = get_monthly_summary(txs, month, year)
        breakdown = get_category_breakdown(txs, month, year)
        # Trend için kullanıcı seçilebilir periyot ekle (1,2,3,6,12 ay)
        period_label_to_months = {
            "Son Ay": 1,
            "Son 2 Ay": 2,
            "Son 3 Ay": 3,
            "Son 6 Ay": 6,
            "Son 1 Yıl": 12,
        }
        sel_period = st.selectbox("Periyot", list(period_label_to_months.keys()), index=3,
                                  help="Grafikte gösterilecek son N aylık periyot")
        sel_months = period_label_to_months.get(sel_period, 6)
        trend = get_last_n_months_trend(txs, sel_months)
        all_txs = txs
        plans = get_firestore_budget_plans_cached()
        alerts = get_budget_alerts_from_plans(plans, breakdown)
    except Exception as e:
        st.error(f"Firebase veri yükleme hatası: {str(e)}")
        fb_ready = False
        db = SessionLocal()
        summary = get_monthly_summary(db, month, year)
        breakdown = get_category_breakdown(db, month, year)
        trend = get_last_6_months_trend(db)
        all_txs = db.query(Transaction).all()
        alerts = check_budget_alerts(db, month, year)
        db.close()
else:
    sel_period = "Son 6 Ay"
    db = SessionLocal()
    summary = get_monthly_summary(db, month, year)
    breakdown = get_category_breakdown(db, month, year)
    trend = get_last_6_months_trend(db)
    all_txs = db.query(Transaction).all()
    alerts = check_budget_alerts(db, month, year)
    db.close()

sidebar_stats(summary)

# ── Veri yoksa yönlendirme ────────────────────────────────────────────────────
if summary["income"] == 0 and summary["expense"] == 0:
    empty_state("📊", "Bu ay için veri bulunamadı",
                "Farklı bir ay/yıl seçin ya da Harcamalar sayfasından işlem ekleyin.")
    tip("İlk kez kullanıyorsanız terminalde <strong>python seed_data.py</strong> "
        "çalıştırarak demo verisi yükleyebilirsiniz.")
    st.stop()

# ── Üst metrikler ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Gelir",       f"{summary['income']:,.0f} ₺")
m2.metric("Gider",       f"{summary['expense']:,.0f} ₺")
m3.metric("Net Tasarruf",f"{summary['savings']:,.0f} ₺",
          delta=f"%{summary['savings_rate']:.1f}")
m4.metric("En Çok Harcanan", summary['top_category'])

# ── Bütçe uyarıları ────────────────────────────────────────────────────────────
if alerts:
    st.markdown("<br>", unsafe_allow_html=True)
    for a in alerts:
        is_critical = a["status"] == "kritik"
        bg    = "rgba(239,68,68,0.05)"
        left  = "#ef4444" if is_critical else "#f59e0b"
        icon  = "🔴" if is_critical else "🟡"
        st.markdown(f"""
        <div style="background:{bg};border-left:3px solid {left};
                    border-radius:0 8px 8px 0;padding:0.6rem 1rem;margin-bottom:0.35rem;
                    display:flex;justify-content:space-between;align-items:center">
            <span style="color:#e2e8f0;font-size:0.875rem">
                {icon} <strong>{a['category']}</strong> bütçe uyarısı
            </span>
            <span style="color:#94a3b8;font-size:0.82rem">
                {a['spent']:,.0f} ₺ / {a['limit']:,.0f} ₺
                &nbsp;·&nbsp;
                <span style="color:{left};font-weight:600">%{a['pct']:.0f}</span>
            </span>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── Grafikler ──────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#3d5475",
    font_size=11,
    margin=dict(t=10, b=10, l=0, r=0),
    xaxis=dict(gridcolor="#0a1522", zeroline=False, showline=False),
    yaxis=dict(gridcolor="#0a1522", zeroline=False, showline=False),
)

with col_left:
    section_title("Kategori Dağılımı")
    if not breakdown.empty:
        # Yatay bar — pasta yerine daha okunabilir
        df_bar = breakdown.sort_values("amount")
        fig = go.Figure(go.Bar(
            x=df_bar["amount"], y=df_bar["category"],
            orientation="h",
            marker=dict(
                color=df_bar["amount"],
                colorscale=[[0, "#111e35"], [0.5, "#4f46e5"], [1, "#818cf8"]],
                showscale=False,
                cornerradius=5,
            ),
            text=df_bar["amount"].map(lambda v: f"{v:,.0f} ₺"),
            textposition="outside",
            textfont=dict(color="#3d5475", size=11),
        ))
        layout = CHART_LAYOUT.copy()
        layout["height"] = 300
        st.plotly_chart(fig.update_layout(**layout), use_container_width=True)
    else:
        st.info("Bu ay için harcama verisi yok.")

with col_right:
    section_title(f"{sel_period} Gelir / Gider")
    if not trend.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=trend["ay"], y=trend["gelir"], name="Gelir",
            fill="tozeroy",
            fillcolor="rgba(74,222,128,0.06)",
            line=dict(color="#4ade80", width=2.5),
            mode="lines+markers",
            marker=dict(size=6, color="#4ade80",
                        line=dict(color="#060c15", width=2)),
        ))
        fig2.add_trace(go.Scatter(
            x=trend["ay"], y=trend["gider"], name="Gider",
            fill="tozeroy",
            fillcolor="rgba(248,113,113,0.06)",
            line=dict(color="#f87171", width=2.5),
            mode="lines+markers",
            marker=dict(size=6, color="#f87171",
                        line=dict(color="#060c15", width=2)),
        ))
        fig2.update_layout(
            **CHART_LAYOUT,
            height=300,
            hovermode="x unified",
            legend=dict(orientation="h", y=1.08, font_color="#64748b", font_size=11),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Yeterli trend verisi yok.")

# ── Harcama Tahmini ────────────────────────────────────────────────────────────
st.divider()
section_title("Gelecek Ay Tahmini", badge="ML")

try:
    from ml.forecaster import predict_next_month, is_ready as forecaster_ready
    if not forecaster_ready():
        tip("Harcama tahmin modeli henüz eğitilmedi. "
            "Terminalde <strong>python ml/train.py</strong> çalıştırın; "
            "model eğitildikten sonra bu bölüm otomatik aktif olur.")
    else:
        tx_dicts = []
        for t in all_txs:
            # destek: SQLAlchemy nesnesi veya Firestore'dan gelen dict
            if isinstance(t, dict):
                tx_date = t.get("date")
                tx_amount = t.get("amount")
                tx_cat = t.get("category")
                tx_type = t.get("type")
            else:
                tx_date = getattr(t, "date", None)
                tx_amount = getattr(t, "amount", None)
                tx_cat = getattr(t, "category", None)
                tx_type = getattr(t, "type", None)

            tx_dicts.append({
                "date": tx_date,
                "amount": tx_amount,
                "category": tx_cat,
                "type": tx_type,
            })
        forecasts = predict_next_month(tx_dicts)
        if forecasts:
            next_m = today.month % 12 + 1
            next_y = today.year if next_m > 1 else today.year + 1
            ay_adi = _ay[next_m - 1]
            total  = sum(forecasts.values())

            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:baseline;
                        padding:0 0 0.8rem;border-bottom:1px solid #111c2d;margin-bottom:0.8rem">
                <span style="color:#475569;font-size:0.875rem">{ay_adi} {next_y} — tahmini toplam gider</span>
                <span style="color:#818cf8;font-size:1.5rem;font-weight:700;
                             letter-spacing:-0.02em">{total:,.0f} ₺</span>
            </div>""", unsafe_allow_html=True)

            fc_df = pd.DataFrame([
                {"Kategori": k, "Tahmin": v}
                for k, v in sorted(forecasts.items(), key=lambda x: x[1], reverse=True)
            ])
            fig3 = go.Figure(go.Bar(
                x=fc_df["Kategori"], y=fc_df["Tahmin"],
                marker=dict(
                    color=fc_df["Tahmin"],
                    colorscale=[[0, "#111e35"], [0.5, "#4f46e5"], [1, "#818cf8"]],
                    showscale=False,
                    cornerradius=6,
                ),
                text=fc_df["Tahmin"].map(lambda v: f"{v:,.0f}"),
                textposition="outside",
                textfont=dict(color="#3d5475", size=10),
            ))
            layout_update = CHART_LAYOUT.copy()
            layout_update.update(dict(
                height=260, showlegend=False,
                yaxis=dict(gridcolor="#111c2d", zeroline=False,
                          showline=False, showticklabels=False)
            ))
            fig3.update_layout(**layout_update)
            st.plotly_chart(fig3, use_container_width=True)

            if not breakdown.empty:
                with st.expander("Bu ay ile karşılaştır"):
                    curr_map = dict(zip(breakdown["category"], breakdown["amount"]))
                    rows = []
                    for cat, pred in forecasts.items():
                        curr = curr_map.get(cat, 0)
                        diff = pred - curr
                        rows.append({
                            "Kategori":  cat,
                            "Bu Ay":     f"{curr:,.0f} ₺",
                            "Tahmin":    f"{pred:,.0f} ₺",
                            "Fark":      f"{'+'if diff>=0 else ''}{diff:,.0f} ₺",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True,
                                 hide_index=True)
        else:
            st.info("Tahmin için en az 3 aylık veri gerekli.")
except Exception as e:
    st.info(f"Tahmin modeli yüklenemedi: {e}")

# ── Son işlemler ───────────────────────────────────────────────────────────────
st.divider()
section_title("Son 15 İşlem")
txs = summary.get("transactions", [])
if txs:
    df = pd.DataFrame(txs).sort_values("date", ascending=False).head(15)
    df["Tür"] = df["type"].map({"gelir": "✅ Gelir", "gider": "❌ Gider"})
    df["Tutar"] = df["amount"].map(lambda x: f"{x:,.2f} ₺")
    df = df.rename(columns={"date": "Tarih", "category": "Kategori",
                             "description": "Açıklama"})
    st.dataframe(
        df[["Tarih","Tür","Kategori","Tutar","Açıklama"]].style.apply(
            lambda row: (["background-color:rgba(74,222,128,0.05)"]*5
                         if "Gelir" in str(row["Tür"])
                         else ["background-color:rgba(248,113,113,0.05)"]*5),
            axis=1,
        ),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("Bu ay için işlem bulunamadı.")
