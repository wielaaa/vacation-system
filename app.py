import streamlit as st
import pandas as pd
from datetime import date
import sqlite3

# إعداد الصفحة
st.set_page_config(
    page_title="نظام إدارة الإجازات - مطار طابا الدولي",
    page_icon="✈️",
    layout="wide"
)

# العنوان الرئيسي
st.title("✈️ نظام إدارة الإجازات - مطار طابا الدولي")
st.markdown("---")

# إنشاء قاعدة البيانات في الذاكرة
if 'employees' not in st.session_state:
    st.session_state.employees = []
if 'vacations' not in st.session_state:
    st.session_state.vacations = []

# القائمة الجانبية
menu = st.sidebar.selectbox(
    "القائمة الرئيسية",
    ["الرئيسية", "إدارة الموظفين", "طلب إجازة", "التقارير"]
)

if menu == "الرئيسية":
    st.header("🏠 لوحة التحكم")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("إجمالي الموظفين", len(st.session_state.employees))
    
    with col2:
        st.metric("طلبات الإجازة", len(st.session_state.vacations))
    
    with col3:
        st.metric("النظام", "🟢 نشط")
    
    st.info("مرحباً بك في نظام إدارة إجازات موظفي مطار طابا الدولي")

elif menu == "إدارة الموظفين":
    st.header("👥 إدارة الموظفين")
    
    with st.form("add_employee"):
        st.subheader("إضافة موظف جديد")
        
        col1, col2 = st.columns(2)
        
        with col1:
            emp_id = st.text_input("رقم الموظف")
            name = st.text_input("اسم الموظف")
        
        with col2:
            department = st.selectbox(
                "القسم",
                ["الشؤون المالية", "الشؤون الإدارية", "الأمن", "التشغيل", "الصيانة"]
            )
            position = st.text_input("الوظيفة")
        
        if st.form_submit_button("إضافة الموظف"):
            if emp_id and name:
                st.session_state.employees.append({
                    'id': emp_id,
                    'name': name,
                    'department': department,
                    'position': position
                })
                st.success(f"تم إضافة الموظف {name} بنجاح!")
            else:
                st.error("الرجاء ملء جميع الحقول المطلوبة")
    
    # عرض الموظفين
    if st.session_state.employees:
        st.subheader("قائمة الموظفين")
        employees_df = pd.DataFrame(st.session_state.employees)
        st.dataframe(employees_df)
    else:
        st.info("لا يوجد موظفين مسجلين حتى الآن")

elif menu == "طلب إجازة":
    st.header("📝 طلب إجازة")
    
    if not st.session_state.employees:
        st.warning("الرجاء إضافة موظفين أولاً من صفحة إدارة الموظفين")
    else:
        with st.form("vacation_request"):
            col1, col2 = st.columns(2)
            
            with col1:
                employee = st.selectbox(
                    "اختر الموظف",
                    options=[emp['name'] for emp in st.session_state.employees]
                )
                vacation_type = st.selectbox(
                    "نوع الإجازة",
                    ["سنوية", "عارضة", "مرضية", "ظرف طارئ"]
                )
                start_date = st.date_input("تاريخ البدء")
            
            with col2:
                end_date = st.date_input("تاريخ الانتهاء")
                reason = st.text_area("سبب الإجازة")
            
            if st.form_submit_button("تقديم طلب الإجازة"):
                if start_date <= end_date:
                    st.session_state.vacations.append({
                        'employee': employee,
                        'type': vacation_type,
                        'start_date': start_date,
                        'end_date': end_date,
                        'reason': reason,
                        'status': 'معلقة'
                    })
                    st.success("تم تقديم طلب الإجازة بنجاح!")
                else:
                    st.error("تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء")

elif menu == "التقارير":
    st.header("📊 التقارير")
    
    tab1, tab2 = st.tabs(["تقارير الموظفين", "تقارير الإجازات"])
    
    with tab1:
        if st.session_state.employees:
            st.subheader("تقرير الموظفين")
            employees_df = pd.DataFrame(st.session_state.employees)
            st.dataframe(employees_df)
            
            # إحصائيات
            dept_counts = employees_df['department'].value_counts()
            st.bar_chart(dept_counts)
        else:
            st.info("لا توجد بيانات للموظفين")
    
    with tab2:
        if st.session_state.vacations:
            st.subheader("تقرير طلبات الإجازة")
            vacations_df = pd.DataFrame(st.session_state.vacations)
            st.dataframe(vacations_df)
        else:
            st.info("لا توجد طلبات إجازة")

# تذييل الصفحة
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "نظام إدارة الإجازات - مطار طابا الدولي ✈️<br>"
    "تم التطوير خصيصاً لإدارة الشؤون المالية والإدارية"
    "</div>",
    unsafe_allow_html=True
)