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
    ["الرئيسية", "إدارة الموظفين", "طلب إجازة", "مراجعة الطلبات", "التقارير"]
)

if menu == "الرئيسية":
    st.header("🏠 لوحة التحكم")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي الموظفين", len(st.session_state.employees))
    
    with col2:
        st.metric("طلبات الإجازة", len(st.session_state.vacations))
    
    with col3:
        pending = len([v for v in st.session_state.vacations if v['status'] == 'معلقة'])
        st.metric("طلبات معلقة", pending)
    
    with col4:
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

elif menu == "مراجعة الطلبات":
    st.header("📋 مراجعة طلبات الإجازة")
    st.info("هذه الصفحة مخصصة لمدير الشؤون الإدارية لمراجعة طلبات الإجازة")
    
    # عرض الطلبات المعلقة فقط
    pending_vacations = [v for v in st.session_state.vacations if v['status'] == 'معلقة']
    
    if not pending_vacations:
        st.success("🎉 لا توجد طلبات إجازة معلقة للمراجعة")
    else:
        st.subheader(f"طلبات معلقة تحتاج المراجعة ({len(pending_vacations)})")
        
        for i, vacation in enumerate(pending_vacations):
            with st.container():
                st.markdown("---")
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**👤 الموظف:** {vacation['employee']}")
                    st.write(f"**📋 نوع الإجازة:** {vacation['type']}")
                    st.write(f"**📅 الفترة:** من {vacation['start_date']} إلى {vacation['end_date']}")
                    st.write(f"**📝 السبب:** {vacation['reason']}")
                
                with col2:
                    if st.button("✅ موافقة", key=f"approve_{i}", use_container_width=True):
                        # البحث عن الطلب في القائمة الرئيسية وتحديثه
                        for j, v in enumerate(st.session_state.vacations):
                            if (v['employee'] == vacation['employee'] and 
                                v['start_date'] == vacation['start_date']):
                                st.session_state.vacations[j]['status'] = 'مقبولة'
                                break
                        st.success("✅ تمت الموافقة على طلب الإجازة!")
                        st.rerun()
                
                with col3:
                    if st.button("❌ رفض", key=f"reject_{i}", use_container_width=True):
                        # البحث عن الطلب في القائمة الرئيسية وتحديثه
                        for j, v in enumerate(st.session_state.vacations):
                            if (v['employee'] == vacation['employee'] and 
                                v['start_date'] == vacation['start_date']):
                                st.session_state.vacations[j]['status'] = 'مرفوضة'
                                break
                        st.error("❌ تم رفض طلب الإجازة!")
                        st.rerun()
        
        st.markdown("---")

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
            
            # إضافة تلوين للحالات
            def color_status(status):
                if status == 'مقبولة':
                    return '🟢 مقبولة'
                elif status == 'مرفوضة':
                    return '🔴 مرفوضة'
                else:
                    return '🟡 معلقة'
            
            vacations_df['الحالة'] = vacations_df['status'].apply(color_status)
            st.dataframe(vacations_df[['employee', 'type', 'start_date', 'end_date', 'الحالة']])
            
            # إحصائيات الحالات
            status_counts = vacations_df['status'].value_counts()
            st.write("**إحصائيات الحالات:**")
            st.write(status_counts)
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
