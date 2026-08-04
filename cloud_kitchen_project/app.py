import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# فراخوانی ماژول‌های پروژه
from core.lp_solver import solve_cloud_kitchen_lp
from core.ga_solver import CloudKitchenVRPSA
from core.chatbot import generate_ai_analysis_response

# تنظیمات اصلی صفحه
st.set_page_config(
    page_title="داشبورد بهینه‌سازی آشپزخانه ابری",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 سیستم تصمیم‌گیری و بهینه‌سازی آشپزخانه ابری و کترینگ زنجیره‌ای")
st.caption("دانشگاه صنعتی شریف | پروژه درس برنامه‌نویسی پیشرفته")

# ----------------------------------------------------
# سایدبار: شبیه‌سازی عدم قطعیت (خواسته کلیدی استاد)
# ----------------------------------------------------
st.sidebar.header("⚠️ تنظیمات سناریو و عدم قطعیت")
st.sidebar.write("در دنیای واقعی زنجیره تامین همواره قطعی نیست.")
crisis_mode = st.sidebar.checkbox("فعال‌سازی شوک تقاضا و بحران تامین")

if crisis_mode:
    st.sidebar.warning("وضعیت بحران فعال است! تامین مواد اولیه ۴۰٪ کاهش و کف تقاضا ۳۰٪ افزایش یافته است.")
    supply_factor = 0.6  # تامین مواد اولیه به مشکل خورده است
    demand_factor = 1.3  # شوک تقاضا ایجاد شده است
else:
    st.sidebar.success("وضعیت زنجیره تامین پایدار و نرمال است.")
    supply_factor = 1.0
    demand_factor = 1.0

# ساخت تب‌های اصلی برنامه
tab_lp, tab_ga, tab_chat = st.tabs([
    "📊 ۱. بهینه‌سازی تولید و ضایعات (LP)", 
    "🛵 ۲. مسیریابی پیک‌ها و کیفیت غذا (GA)", 
    "🤖 ۳. چت‌بات تحلیلی (AI Assistant)"
])

# ----------------------------------------------------
# تب اول: برنامه‌ریزی خطی (LP)
# ----------------------------------------------------
with tab_lp:
    st.header("ماژول بهینه‌سازی تامین، منو و کمینه‌سازی ضایعات")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ پارامترهای ورودی انبار و تولید")
        max_time = st.number_input("حداکثر زمان کاری آشپزخانه (دقیقه):", value=1800, step=100)
        
        st.write("**موجودی اولیه انبار (کیلوگرم):**")
        rice_stock = st.slider("موجودی برنج:", 50, 400, 150)
        meat_stock = st.slider("موجودی گوشت:", 20, 200, 60)
        oil_stock = st.slider("موجودی روغن:", 10, 100, 30)
        
        # اعمال ضریب بحران روی موجودی انبار
        ingredients_supply = {
            "Rice": rice_stock * supply_factor, 
            "Meat": meat_stock * supply_factor, 
            "Oil": oil_stock * supply_factor
        }
        
        ingredient_costs = {"Rice": 80, "Meat": 450, "Oil": 90} # قیمت به هزار تومان
        
        # اعمال ضریب بحران روی تقاضا
        menu_items = [
            {"name": "چلوکباب", "price": 250, "prep_time": 15, "recipe": {"Rice": 0.35, "Meat": 0.2, "Oil": 0.05}, "min_demand": int(30 * demand_factor), "max_demand": 200},
            {"name": "زرشک‌پلو", "price": 180, "prep_time": 10, "recipe": {"Rice": 0.3, "Meat": 0.15, "Oil": 0.04}, "min_demand": int(20 * demand_factor), "max_demand": 150},
            {"name": "جوجه‌کباب", "price": 200, "prep_time": 12, "recipe": {"Rice": 0.35, "Meat": 0.18, "Oil": 0.03}, "min_demand": int(25 * demand_factor), "max_demand": 180},
        ]
        
        btn_run_lp = st.button("🚀 اجرای بهینه‌سازی تولید (LP)", key="lp_btn")

    with col2:
        if btn_run_lp or 'lp_results' in st.session_state:
            if btn_run_lp:
                st.session_state['lp_results'] = solve_cloud_kitchen_lp(
                    ingredients_supply, menu_items, max_time, ingredient_costs
                )
            
            results = st.session_state['lp_results']
            
            st.success(f"وضعیت مدل: {results['status']}")
            st.metric("سود خالص کل (هزار تومان):", f"{results['total_profit']:,}")
            
            # نمودار برنامه تولید
            df_plan = pd.DataFrame(list(results['production_plan'].items()), columns=['غذا', 'تعداد تولید'])
            fig_plan = px.bar(df_plan, x='غذا', y='تعداد تولید', title="برنامه بهینه تولید روزانه", color='غذا')
            st.plotly_chart(fig_plan, use_container_width=True)
            
            # نمایش باقی‌مانده انبار (ضایعات/مصرف‌نشده)
            st.subheader("📦 وضعیت باقی‌مانده مواد اولیه در انبار (کنترل ضایعات)")
            st.json(results['leftover_ingredients'])

# ----------------------------------------------------
# تب دوم: الگوریتم ژنتیک (GA)
# ----------------------------------------------------
with tab_ga:
    st.header("ماژول مسیریابی پیک‌های موتوری جهت حفظ گرمای غذا")
    
    col_ga1, col_ga2 = st.columns([1, 2])
    
    with col_ga1:
        num_orders = st.slider("تعداد سفارش‌های فعال:", 5, 15, 8)
        num_vehicles = st.slider("تعداد موتورهای سیستم ارسال:", 1, 4, 2)
        generations = st.slider("تعداد نسل‌های الگوریتم ژنتیک:", 20, 150, 50)
        
        btn_run_ga = st.button("🧬 اجرای مسیریابی بهینه (GA)", key="ga_btn")

    with col_ga2:
        if btn_run_ga or 'ga_results' in st.session_state:
            if btn_run_ga:
                np.random.seed(42)
                dist_matrix = np.random.randint(2, 15, size=(num_orders+1, num_orders+1))
                np.fill_diagonal(dist_matrix, 0)
                time_windows = {i: 35 for i in range(1, num_orders+1)} # ۳۵ دقیقه زمان مجاز تحویل
                
                solver = CloudKitchenVRPSA(num_orders, num_vehicles, dist_matrix, time_windows, generations=generations)
                st.session_state['ga_results'] = solver.solve()
            
            ga_res = st.session_state['ga_results']
            
            st.metric("کمترین هزینه مسافت و تاخیر کل:", f"{ga_res['min_total_cost']:.2f}")
            
            # نمودار همگرایی GA
            fig_conv = go.Figure()
            fig_conv.add_trace(go.Scatter(y=ga_res['convergence_curve'], mode='lines+markers', name='هزینه کل'))
            fig_conv.update_layout(title="نمودار همگرایی الگوریتم ژنتیک (کاهش هزینه‌ها)", xaxis_title="نسل", yaxis_title="هزینه")
            st.plotly_chart(fig_conv, use_container_width=True)
            
            st.subheader("🛵 مسیر تخصیص‌یافته به پیک‌ها:")
            for idx, route in enumerate(ga_res['best_routes']):
                st.info(f"پیک شماره {idx+1}: آشپزخانه ⬅️ " + " ⬅️ ".join(map(str, route)) + " ⬅️ بازگشت به آشپزخانه")

# ----------------------------------------------------
# تب سوم: چت‌بات تحلیلی (Chatbot)
# ----------------------------------------------------
with tab_chat:
    st.header("🤖 دستیار هوشمند تحلیلی و مدیریتی")
    st.write("پاسخگویی زنده به سوالات مدیریتی بر اساس خروجی مدل‌های LP و GA")
    
    api_key = st.text_input("کلید API هوش مصنوعی (اختیاری):", type="password")
    
    # راهنمای کاربر در صورت عدم اجرای الگوریتم‌ها
    if 'lp_results' not in st.session_state or 'ga_results' not in st.session_state:
        st.warning("💡 **توصیه:** برای دریافت بهترین تحلیل‌ها، ابتدا دکمه‌های اجرای مدل را در **تب ۱ (LP)** و **تب ۲ (GA)** بزنید.")

    # مقداردهی آرشیو پیام‌ها
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # نمایش تاریخچه گفتگو
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # گرفتن سوال جدید کاربر
    if prompt := st.chat_input("سوال تحلیلی خود را بنویسید (مثلاً: علت محدودیت در تولید جوجه‌کباب چیست؟)"):
        # ثبت و نمایش سوال کاربر
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # استخراج خروجی‌های ذخیره‌شده
        lp_res = st.session_state.get('lp_results', {})
        ga_res = st.session_state.get('ga_results', {})

        # تولید پاسخ از چت‌بات و نمایش آن
        with st.chat_message("assistant"):
            with st.spinner("در حال تحلیل داده‌های مدل..."):
                ans = generate_ai_analysis_response(prompt, lp_res, ga_res, api_key)
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
