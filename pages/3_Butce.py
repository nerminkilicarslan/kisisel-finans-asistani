import streamlit as st
from datetime import date
from models import SessionLocal, BudgetPlan, SavingsGoal, init_db
from services.analytics import (
    get_category_breakdown, CATEGORIES_GIDER, get_monthly_summary,
    get_budget_alerts_from_plans,
)
from services.firebase_service import (
    sync_budget_plan, sync_savings_goal,
    is_firebase_enabled, get_firestore_budget_plans,
    get_firestore_savings_goals, get_firestore_transactions,
)
from services.ui_helpers import inject_css, page_header, section_title, sidebar_stats, tip, empty_state

st.set_page_config(page_title="Bütçe & Hedefler", page_icon="🎯", layout="wide")
inject_css()
page_header("🎯", "Bütçe & Tasarruf Hedefleri")
init_db()

today = date.today()
_ay   = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
         "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

fb_ready = is_firebase_enabled()
if fb_ready:
    summary = get_monthly_summary(get_firestore_transactions(), today.month, today.year)
else:
    db = SessionLocal()
    summary = get_monthly_summary(db, today.month, today.year)
    db.close()
sidebar_stats(summary)

tip("Kategorilere <strong>aylık harcama limiti</strong> tanımlayın; "
    "Dashboard'da otomatik uyarılar göreceksiniz. "
    "<strong>Tasarruf Hedefleri</strong> sekmesinden tatil fonu, acil durum fonu gibi "
    "uzun vadeli hedefler oluşturabilirsiniz.")

tab_budget, tab_goals = st.tabs(["📊 Bütçe Planı", "🏆 Tasarruf Hedefleri"])

# ── TAB 1: Bütçe ───────────────────────────────────────────────────────────────
with tab_budget:
    c1, c2, _ = st.columns([2, 1, 5])
    month = c1.selectbox("ay", range(1, 13), index=today.month - 1,
                          format_func=lambda m: _ay[m-1], label_visibility="collapsed")
    year  = c2.selectbox("yıl", [today.year - 1, today.year], index=1,
                          label_visibility="collapsed")

    if fb_ready:
        plans = [p for p in get_firestore_budget_plans() if p["month"] == month and p["year"] == year]
        breakdown = get_category_breakdown(get_firestore_transactions(), month, year)
    else:
        db = SessionLocal()
        plans = db.query(BudgetPlan).filter(
            BudgetPlan.month == month, BudgetPlan.year == year
        ).all()
        breakdown = get_category_breakdown(db, month, year)
        db.close()

    spent_map = dict(zip(breakdown["category"], breakdown["amount"])) if not breakdown.empty else {}

    if plans:
        total_limit = sum((p["limit_amount"] if fb_ready else p.limit_amount) for p in plans)
        total_spent = sum(spent_map.get((p["category"] if fb_ready else p.category), 0) for p in plans)
        total_pct = total_spent / total_limit if total_limit else 0

        sm1, sm2, sm3 = st.columns(3)
        sm1.metric("Toplam Limit",   f"{total_limit:,.0f} ₺")
        sm2.metric("Harcanan",       f"{total_spent:,.0f} ₺")
        sm3.metric("Kalan",          f"{max(total_limit-total_spent,0):,.0f} ₺",
                   delta=f"%{(1-total_pct)*100:.0f} kullanılmadı")

        st.markdown("<br>", unsafe_allow_html=True)

        for plan in plans:
            category = plan["category"] if fb_ready else plan.category
            limit_amount = plan["limit_amount"] if fb_ready else plan.limit_amount
            actual = spent_map.get(category, 0)
            pct = min(actual / limit_amount, 1.0) if limit_amount else 0
            bar_c = "#ef4444" if pct >= 1 else "#f59e0b" if pct >= 0.8 else "#4ade80"

            st.markdown(f"""
            <div style="margin-bottom:1.1rem">
                <div style="display:flex;justify-content:space-between;
                            align-items:baseline;margin-bottom:0.35rem">
                    <span style="color:#e2e8f0;font-size:0.875rem;font-weight:500">
                        {category}
                    </span>
                    <span style="color:#64748b;font-size:0.8rem">
                        <span style="color:{bar_c};font-weight:600">{actual:,.0f} ₺</span>
                        &nbsp;/&nbsp;{limit_amount:,.0f} ₺
                    </span>
                </div>
                <div style="background:#111c2d;border-radius:6px;height:6px;overflow:hidden">
                    <div style="background:{bar_c};width:{pct*100:.1f}%;
                                height:100%;border-radius:6px;transition:width 0.4s"></div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        empty_state("🎯", "Bu ay için bütçe tanımlanmamış",
                    "Aşağıdaki formdan kategori seçin ve aylık harcama limiti belirleyin. "
                    "Örneğin Market için 3.000 ₺ limit koyarsanız, "
                    "bu tutara yaklaştığınızda Dashboard'da uyarı görürsünüz.")

    st.divider()
    section_title("Yeni Bütçe Kalemi")
    with st.form("budget_form", clear_on_submit=True):
        bc1, bc2, bc3 = st.columns(3)
        b_cat   = bc1.selectbox("Kategori", CATEGORIES_GIDER)
        b_limit = bc2.number_input("Limit (₺)", min_value=1.0, format="%.0f")
        b_month = bc3.selectbox("Ay", range(1, 13), index=today.month - 1,
                                 format_func=lambda m: _ay[m-1])
        if st.form_submit_button("Kaydet", use_container_width=True):
                if fb_ready:
                    plan = {
                        "id": f"{year}-{b_month}-{b_cat}",
                        "year": year,
                        "month": b_month,
                        "category": b_cat,
                        "limit_amount": b_limit,
                    }
                    try:
                        sync_budget_plan(plan)
                    except Exception:
                        pass
                else:
                    db = SessionLocal()
                    ex = db.query(BudgetPlan).filter(
                        BudgetPlan.year == year, BudgetPlan.month == b_month,
                        BudgetPlan.category == b_cat
                    ).first()
                    if ex:
                        ex.limit_amount = b_limit
                        plan = ex
                    else:
                        plan = BudgetPlan(year=year, month=b_month,
                                          category=b_cat, limit_amount=b_limit)
                        db.add(plan)
                    db.commit()
                    try:
                        sync_budget_plan(plan)
                    except Exception:
                        pass
                    db.close()
                st.success(f"**{b_cat}** bütçesi: **{b_limit:,.0f} ₺**")
                st.rerun()

# ── TAB 2: Tasarruf Hedefleri ──────────────────────────────────────────────────
with tab_goals:
    if fb_ready:
        goals = get_firestore_savings_goals()
    else:
        db = SessionLocal()
        goals = db.query(SavingsGoal).all()
        db.close()

    if fb_ready:
        active = [g for g in goals if not g.get("is_completed", False)]
        completed = [g for g in goals if g.get("is_completed", False)]
    else:
        active = [g for g in goals if not g.is_completed]
        completed = [g for g in goals if g.is_completed]

    if active:
        section_title("Aktif Hedefler", badge=str(len(active)))
        for g in active:
            current_amount = g["current_amount"] if fb_ready else g.current_amount
            target_amount = g["target_amount"] if fb_ready else g.target_amount
            pct = min(current_amount / target_amount, 1.0) if target_amount else 0
            remaining = max(target_amount - current_amount, 0)
            target_date = g.get("target_date") if fb_ready else g.target_date
            days_left = (target_date - today).days if target_date else None

            st.markdown(f"""
            <div style="background:#0a1522;border:1px solid #0f2035;border-radius:14px;
                        padding:1.2rem 1.4rem;margin-bottom:0.75rem">
                <div style="display:flex;justify-content:space-between;
                            align-items:baseline;margin-bottom:0.7rem">
                    <span style="color:#e2e8f0;font-weight:600;font-size:0.95rem">{g['name'] if fb_ready else g.name}</span>
                    <span style="color:#818cf8;font-size:0.82rem;font-weight:600">
                        %{pct*100:.0f} tamamlandı
                    </span>
                </div>
                <div style="background:#111c2d;border-radius:6px;height:6px;
                            overflow:hidden;margin-bottom:0.8rem">
                    <div style="background:#4f46e5;width:{pct*100:.1f}%;
                                height:100%;border-radius:6px"></div>
                </div>
                <div style="display:flex;gap:2rem">
                    <div>
                        <div style="color:#475569;font-size:0.7rem;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.06em">Hedef</div>
                        <div style="color:#94a3b8;font-weight:600;font-size:0.875rem">
                            {target_amount:,.0f} ₺
                        </div>
                    </div>
                    <div>
                        <div style="color:#475569;font-size:0.7rem;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.06em">Biriken</div>
                        <div style="color:#4ade80;font-weight:600;font-size:0.875rem">
                            {current_amount:,.0f} ₺
                        </div>
                    </div>
                    <div>
                        <div style="color:#475569;font-size:0.7rem;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.06em">Kalan</div>
                        <div style="color:#f87171;font-weight:600;font-size:0.875rem">
                            {remaining:,.0f} ₺
                        </div>
                    </div>
                    {f'''<div>
                        <div style="color:#475569;font-size:0.7rem;font-weight:700;
                                    text-transform:uppercase;letter-spacing:0.06em">Süre</div>
                        <div style="color:#fbbf24;font-weight:600;font-size:0.875rem">
                            {days_left} gün
                        </div>
                    </div>''' if days_left is not None else ''}
                </div>
            </div>""", unsafe_allow_html=True)

            uc1, uc2 = st.columns([4, 1])
            new_amt = uc1.number_input(
                "güncelle", value=float(current_amount), min_value=0.0, format="%.0f",
                key=f"g_{g['id'] if fb_ready else g.id}", label_visibility="collapsed",
            )
            if uc2.button("Güncelle", key=f"u_{g['id']}" if fb_ready else f"u_{g.id}", use_container_width=True):
                if fb_ready:
                    updated_goal = dict(g)
                    updated_goal["current_amount"] = new_amt
                    if new_amt >= updated_goal["target_amount"]:
                        updated_goal["is_completed"] = True
                        st.balloons()
                    try:
                        sync_savings_goal(updated_goal)
                    except Exception:
                        pass
                else:
                    db = SessionLocal()
                    goal = db.query(SavingsGoal).filter(SavingsGoal.id == g.id).first()
                    goal.current_amount = new_amt
                    if new_amt >= goal.target_amount:
                        goal.is_completed = True
                        st.balloons()
                    db.commit()
                    try:
                        sync_savings_goal(goal)
                    except Exception:
                        pass
                    db.close()
                st.rerun()

    if completed:
        st.divider()
        section_title("Tamamlananlar", badge=f"✅ {len(completed)}")
        for g in completed:
            name = g["name"] if fb_ready else g.name
            target_amount = g["target_amount"] if fb_ready else g.target_amount
            st.markdown(f"""
            <div style="background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.15);
                        border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.4rem;
                        display:flex;justify-content:space-between;align-items:center">
                <span style="color:#4ade80;font-weight:500;font-size:0.875rem">
                    ✅ {name}
                </span>
                <span style="color:#475569;font-size:0.82rem">{target_amount:,.0f} ₺</span>
            </div>""", unsafe_allow_html=True)

    if not goals:
        empty_state("🏆", "Henüz tasarruf hedefi yok",
                    "Aşağıdan hedef adı, tutar ve tarih girerek başlayın. "
                    "Örnek: 'Tatil Fonu — 15.000 ₺ — Ağustos 2026'")

    st.divider()
    section_title("Yeni Hedef")
    with st.form("goal_form", clear_on_submit=True):
        g_name = st.text_input("Hedef adı", placeholder="örn: Tatil Fonu, Acil Durum Fonu")
        gc1, gc2 = st.columns(2)
        g_target  = gc1.number_input("Hedef (₺)", min_value=1.0, format="%.0f")
        g_current = gc2.number_input("Mevcut (₺)", min_value=0.0, format="%.0f")
        g_date    = st.date_input("Hedef tarihi (isteğe bağlı)", value=None)
        if st.form_submit_button("Hedef Oluştur", use_container_width=True):
            db = SessionLocal()
            goal = SavingsGoal(name=g_name, target_amount=g_target,
                               current_amount=g_current, target_date=g_date)
            db.add(goal)
            db.commit()
            try:
                sync_savings_goal(goal)
            except Exception:
                pass
            db.close()
            st.success(f"**{g_name}** hedefi oluşturuldu!")
            st.rerun()
