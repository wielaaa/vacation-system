import streamlit as st
import pandas as pd
from datetime import date
import sqlite3
import os

# إعداد الصفحة
st.set_page_config(
    page_title="نظام إدارة الإجازات - مطار طابا الدولي",
    page_icon="✈️",
    layout="wide"
)

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect('vacation_system.db')
    c = conn.cursor()
    
    # جدول الموظفين
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE,
            name TEXT NOT NULL,
            department TEXT,
            position TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول طلبات الإجازة
    c.execute('''
        CREATE TABLE IF NOT EXISTS vacations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            employee_name TEXT,
            vacation_type TEXT,
            start_date DATE,
            end_date DATE,
            reason TEXT,
            status TEXT DEFAULT 'معلقة',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# استدعاء إنشاء قاعدة البيانات
init_db()

# العنوان الرئيسي
st.title("✈️ نظام إدارة الإجازات - مطار طابا الدولي")
st.markdown("---")

# القائمة الجانبية
menu = st.sidebar.selectbox(
    "القائمة الرئيسية",
    ["الرئيسية", "إدارة الموظفين", "طلب إجازة", "مراجعة الطلبات", "التقارير"]
)

if menu == "الرئيسية":
    st.header("🏠 لوحة التحكم")
    
    conn = sqlite3.connect('vacation_system.db')
    
    # إحصائيات
    employees_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    vacations_count = conn.execute("SELECT COUNT(*) FROM vacations").fetchone()[0]
    pending_count = conn.execute("SELECT COUNT(*) FROM vacations WHERE status = 'معلقة'").fetchone()[0]
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي الموظفين", employees_count)
    
    with col2:
        st.metric("طلبات الإجازة", vacations_count)
    
    with col3:
        st.metric("طلبات معلقة", pending_count)
    
    with col4:
        st.metric("النظام", "🟢 نشط")
    
    st.info("مرحباً بك في نظام إدارة إجازات موظفي مطار طابا الدولي")

elif menu == "إدارة الموظفين":
    st.header("👥 إدارة الموظفين")
    
    conn = sqlite3.connect('vacation_system.db')
    
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
                try:
                    conn.execute(
                        "INSERT INTO employees (employee_id, name, department, position) VALUES (?, ?, ?, ?)",
                        (emp_id, name, department, position)
                    )
                    conn.commit()
                    st.success(f"تم إضافة الموظف {name} بنجاح!")
                except sqlite3.IntegrityError:
                    st.error("رقم الموظف موجود مسبقاً!")
            else:
                st.error("الرجاء ملء جميع الحقول المطلوبة")
    
    # عرض الموظفين
    st.subheader("قائمة الموظفين")
    employees_df = pd.read_sql("SELECT * FROM employees ORDER BY name", conn)
    
    if not employees_df.empty:
        st.dataframe(employees_df[['employee_id', 'name', 'department', 'position']])
    else:
        st.info("لا يوجد موظفين مسجلين حتى الآن")
    
    conn.close()

elif menu == "طلب إجازة":
    st.header("📝 طلب إجازة")
    
    conn = sqlite3.connect('vacation_system.db')
    
    employees_df = pd.read_sql("SELECT * FROM employees", conn)
    
    if employees_df.empty:
        st.warning("الرجاء إضافة موظفين أولاً من صفحة إدارة الموظفين")
    else:
        with st.form("vacation_request"):
            col1, col2 = st.columns(2)
            
            with col1:
                employee_id = st.selectbox(
                    "اختر الموظف",
                    options=employees_df['employee_id'].tolist(),
                    format_func=lambda x: f"{employees_df[employees_df['employee_id']==x]['name'].iloc[0]} ({x})"
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
                    employee_name = employees_df[employees_df['employee_id']==employee_id]['name'].iloc[0]
                    
                    conn.execute(
                        "INSERT INTO vacations (employee_id, employee_name, vacation_type, start_date, end_date, reason) VALUES (?, ?, ?, ?, ?, ?)",
                        (employee_id, employee_name, vacation_type, start_date, end_date, reason)
                    )
                    conn.commit()
                    st.success("تم تقديم طلب الإجازة بنجاح!")
                else:
                    st.error("تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء")
    
    conn.close()

elif menu == "مراجعة الطلبات":
    st.header("📋 مراجعة طلبات الإجازة")
    st.info("هذه الصفحة مخصصة لمدير الشؤون الإدارية لمراجعة طلبات الإجازة")
    
    conn = sqlite3.connect('vacation_system.db')
    
    # عرض الطلبات المعلقة فقط
    pending_vacations = pd.read_sql(
        "SELECT * FROM vacations WHERE status = 'معلقة' ORDER BY created_date",
        conn
    )
    
    if pending_vacations.empty:
        st.success("🎉 لا توجد طلبات إجازة معلقة للمراجعة")
    else:
        st.subheader(f"طلبات معلقة تحتاج المراجعة ({len(pending_vacations)})")
        
        for _, vacation in pending_vacations.iterrows():
            with st.container():
                st.markdown("---")
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**👤 الموظف:** {vacation['employee_name']} ({vacation['employee_id']})")
                    st.write(f"**📋 نوع الإجازة:** {vacation['vacation_type']}")
                    st.write(f"**📅 الفترة:** من {vacation['start_date']} إلى {vacation['end_date']}")
                    st.write(f"**📝 السبب:** {vacation['reason']}")
                
                with col2:
                    if st.button("✅ موافقة", key=f"approve_{vacation['id']}", use_container_width=True):
                        conn.execute(
                            "UPDATE vacations SET status = 'مقبولة' WHERE id = ?",
                            (vacation['id'],)
                        )
                        conn.commit()
                        st.success("✅ تمت الموافقة على طلب الإجازة!")
                        st.rerun()
                
                with col3:
                    if st.button("❌ رفض", key=f"reject_{vacation['id']}", use_container_width=True):
                        conn.execute(
                            "UPDATE vacations SET status = 'مرفوضة' WHERE id = ?",
                            (vacation['id'],)
                        )
                        conn.commit()
                        st.error("❌ تم رفض طلب الإجازة!")
                        st.rerun()
        
        st.markdown("---")
    
    conn.close()

elif menu == "التقارير":
    st.header("📊 التقارير")
    
    conn = sqlite3.connect('vacation_system.db')
    
    tab1, tab2 = st.tabs(["تقارير الموظفين", "تقارير الإجازات"])
    
    with tab1:
        employees_df = pd.read_sql("SELECT * FROM employees ORDER BY name", conn)
        
        if not employees_df.empty:
            st.subheader("تقرير الموظفين")
            st.dataframe(employees_df[['employee_id', 'name', 'department', 'position']])
            
            # إحصائيات
            dept_counts = employees_df['department'].value_counts()
            st.bar_chart(dept_counts)
        else:
            st.info("لا توجد بيانات للموظفين")
    
    with tab2:
        vacations_df = pd.read_sql("SELECT * FROM vacations ORDER BY created_date DESC", conn)
        
        if not vacations_df.empty:
            st.subheader("تقرير طلبات الإجازة")
            
            # إضافة تلوين للحالات
            def color_status(status):
                if status == 'مقبولة':
                    return '🟢 مقبولة'
                elif status == 'مرفوضة':
                    return '🔴 مرفوضة'
                else:
                    return '🟡 معلقة'
            
            vacations_df['الحالة'] = vacations_df['status'].apply(color_status)
            st.dataframe(vacations_df[['employee_name', 'vacation_type', 'start_date', 'end_date', 'الحالة']])
            
            # إحصائيات الحالات
            status_counts = vacations_df['status'].value_counts()
            st.write("**إحصائيات الحالات:**")
            st.write(status_counts)
        else:
            st.info("لا توجد طلبات إجازة")
    
    conn.close()

# تذييل الصفحة
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "نظام إدارة الإجازات - مطار طابا الدولي ✈️<br>"
    "تم التطوير خصيصاً لإدارة الشؤون المالية والإدارية"
    "</div>",
    unsafe_allow_html=True
)
