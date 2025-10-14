import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
import hashlib
import time
import plotly.express as px

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة الإجازات - المطار",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS مخصص للعربية
st.markdown("""
<style>
    .main .block-container {
        direction: rtl;
        text-align: right;
    }
    .stButton button {
        width: 100%;
    }
    .success-msg {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-msg {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# وظائف قاعدة البيانات
def الحصول_على_الاتصال():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="نظام_إجازات_المطار",
        charset='utf8mb4'
    )

def تشفير_كلمة_المرور(كلمة_المرور):
    return hashlib.sha256(كلمة_المرور.encode()).hexdigest()

def تهيئة_قاعدة_البيانات():
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor()
        
        # إنشاء الجداول
        جداول = [
            """
            CREATE TABLE IF NOT EXISTS المستخدمين (
                معرف INT AUTO_INCREMENT PRIMARY KEY,
                اسم_المستخدم VARCHAR(50) UNIQUE NOT NULL,
                كلمة_المرور VARCHAR(255) NOT NULL,
                اسم_الموظف VARCHAR(100) NOT NULL,
                نوع_المستخدم ENUM('موظف', 'مدير', 'مسؤول_إداري', 'مدير_النظام') NOT NULL,
                القسم VARCHAR(100),
                المدير_المباشر INT,
                الحالة ENUM('نشط', 'غير نشط') DEFAULT 'نشط',
                تاريخ_الإنشاء TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS أنواع_الإجازات (
                معرف INT AUTO_INCREMENT PRIMARY KEY,
                اسم_الإجازة VARCHAR(100) NOT NULL,
                الوصف TEXT,
                الحالة ENUM('مفعل', 'غير مفعل') DEFAULT 'مفعل'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS أرصدة_الإجازات (
                معرف INT AUTO_INCREMENT PRIMARY KEY,
                معرف_الموظف INT NOT NULL,
                رصيد_السنة_الحالية INT DEFAULT 0,
                رصيد_العام_السابق_1 INT DEFAULT 0,
                رصيد_العام_السابق_2 INT DEFAULT 0,
                السنة INT NOT NULL,
                تاريخ_التحديث TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS طلبات_الإجازة (
                معرف INT AUTO_INCREMENT PRIMARY KEY,
                معرف_الموظف INT NOT NULL,
                نوع_الإجازة INT NOT NULL,
                تاريخ_البدء DATE NOT NULL,
                تاريخ_الانتهاء DATE NOT NULL,
                عدد_الأيام INT NOT NULL,
                السبب TEXT,
                الحالة ENUM('قيد المراجعة', 'معتمد', 'مرفوض', 'ملغي') DEFAULT 'قيد المراجعة',
                ملاحظات_المدير TEXT,
                معرف_المدير_الموافق INT,
                تاريخ_الطلب TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for جدول in جداول:
            cursor.execute(جدول)
        
        # إضافة المستخدم الافتراضي
        كلمة_مرور_مشفرة = تشفير_كلمة_المرور('4856739')
        cursor.execute("""
            INSERT IGNORE INTO المستخدمين 
            (اسم_المستخدم, كلمة_المرور, اسم_الموظف, نوع_المستخدم, القسم) 
            VALUES (%s, %s, %s, %s, %s)
        """, ('5485', كلمة_مرور_مشفرة, 'المسؤول العام', 'مدير_النظام', 'الإدارة العامة'))
        
        # إضافة أنواع الإجازات
        أنواع_الإجازات = [
            ('إجازة اعتيادية', 'الإجازة الاعتيادية السنوية'),
            ('إجازة عرضة', 'إجازة العرضة'),
            ('إجازة بدل راحة', 'بدل الراحة'),
            ('إجازة بدل عمل', 'بدل العمل'),
            ('إجازة بدون مرتب', 'إجازة بدون مرتب'),
            ('إجازة مرضية', 'الإجازة المرضية'),
            ('إجازة طارئة', 'الإجازة الطارئة'),
            ('إجازة دراسية', 'الإجازة الدراسية'),
            ('إجازة حج / عمرة', 'إجازة الحج أو العمرة'),
            ('إجازة مرافقة مريض', 'إجازة مرافقة المريض')
        ]
        
        for نوع_إجازة in أنواع_الإجازات:
            cursor.execute("INSERT IGNORE INTO أنواع_الإجازات (اسم_الإجازة, الوصف) VALUES (%s, %s)", نوع_إجازة)
        
        connection.commit()
        cursor.close()
        connection.close()
        st.success("✅ تم تهيئة قاعدة البيانات بنجاح")
        
    except Exception as e:
        st.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

# صفحة تسجيل الدخول
def صفحة_تسجيل_الدخول():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>✈️ نظام إدارة الإجازات - المطار</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("تسجيل الدخول"):
            st.subheader("تسجيل الدخول")
            اسم_المستخدم = st.text_input("اسم المستخدم")
            كلمة_المرور = st.text_input("كلمة المرور", type="password")
            زر_الدخول = st.form_submit_button("🚀 دخول إلى النظام")
            
            if زر_الدخول:
                if اسم_المستخدم and كلمة_المرور:
                    try:
                        connection = الحصول_على_الاتصال()
                        cursor = connection.cursor(dictionary=True)
                        cursor.execute("SELECT * FROM المستخدمين WHERE اسم_المستخدم = %s AND الحالة = 'نشط'", (اسم_المستخدم,))
                        مستخدم = cursor.fetchone()
                        
                        if مستخدم and مستخدم['كلمة_المرور'] == تشفير_كلمة_المرور(كلمة_المرور):
                            st.session_state.معرف_المستخدم = مستخدم['معرف']
                            st.session_state.اسم_المستخدم = مستخدم['اسم_المستخدم']
                            st.session_state.اسم_الموظف = مستخدم['اسم_الموظف']
                            st.session_state.نوع_المستخدم = مستخدم['نوع_المستخدم']
                            st.session_state.القسم = مستخدم['القسم']
                            st.success(f"✅ مرحباً {مستخدم['اسم_الموظف']}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
                    except Exception as e:
                        st.error(f"❌ خطأ في الاتصال: {e}")
                else:
                    st.error("❌ يرجى إدخال اسم المستخدم وكلمة المرور")
        
        st.markdown("---")
        st.info("""
        **المستخدم الافتراضي للاختبار:**
        - **اسم المستخدم:** 5485
        - **كلمة المرور:** 4856739
        """)

# لوحة تحكم الموظف
def لوحة_الموظف():
    st.sidebar.title(f"مرحباً، {st.session_state.اسم_الموظف}")
    st.sidebar.markdown(f"**القسم:** {st.session_state.القسم}")
    
    قائمة_الموظف = ["الرئيسية", "طلب إجازة جديدة", "طلباتي", "رصيد الإجازات", "الإشعارات"]
    اختيار = st.sidebar.selectbox("القائمة", قائمة_الموظف)
    
    if اختيار == "الرئيسية":
        الرئيسية_الموظف()
    elif اختيار == "طلب إجازة جديدة":
        طلب_إجازة_جديدة()
    elif اختيار == "طلباتي":
        عرض_طلباتي()
    elif اختيار == "رصيد الإجازات":
        عرض_رصيد_الإجازات()

def الرئيسية_الموظف():
    st.title("🏠 لوحة تحكم الموظف")
    
    # إحصائيات سريعة
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        # عدد الطلبات
        cursor.execute("""
            SELECT COUNT(*) as عدد FROM طلبات_الإجازة 
            WHERE معرف_الموظف = %s
        """, (st.session_state.معرف_المستخدم,))
        عدد_الطلبات = cursor.fetchone()['عدد']
        
        # الطلبات قيد المراجعة
        cursor.execute("""
            SELECT COUNT(*) as عدد FROM طلبات_الإجازة 
            WHERE معرف_الموظف = %s AND الحالة = 'قيد المراجعة'
        """, (st.session_state.معرف_المستخدم,))
        طلبات_معلقة = cursor.fetchone()['عدد']
        
        # الرصيد
        cursor.execute("""
            SELECT * FROM أرصدة_الإجازات 
            WHERE معرف_الموظف = %s ORDER BY السنة DESC LIMIT 1
        """, (st.session_state.معرف_المستخدم,))
        رصيد = cursor.fetchone()
        
        with col1:
            st.metric("إجمالي الطلبات", عدد_الطلبات)
        with col2:
            st.metric("طلبات قيد المراجعة", طلبات_معلقة)
        with col3:
            if رصيد:
                st.metric("رصيد السنة الحالية", رصيد['رصيد_السنة_الحالية'])
            else:
                st.metric("رصيد السنة الحالية", 0)
        
        # آخر الطلبات
        st.subheader("📋 آخر طلبات الإجازة")
        cursor.execute("""
            SELECT ط.*, ن.اسم_الإجازة 
            FROM طلبات_الإجازة ط 
            JOIN أنواع_الإجازات ن ON ط.نوع_الإجازة = ن.معرف 
            WHERE ط.معرف_الموظف = %s 
            ORDER BY ط.تاريخ_الطلب DESC 
            LIMIT 10
        """, (st.session_state.معرف_المستخدم,))
        طلبات = cursor.fetchall()
        
        if طلبات:
            بيانات_الجدول = []
            for طلب in طلبات:
                بيانات_الجدول.append({
                    "نوع الإجازة": طلب['اسم_الإجازة'],
                    "من": طلب['تاريخ_البدء'],
                    "إلى": طلب['تاريخ_الانتهاء'],
                    "عدد الأيام": طلب['عدد_الأيام'],
                    "الحالة": طلب['الحالة'],
                    "تاريخ الطلب": طلب['تاريخ_الطلب']
                })
            
            st.dataframe(بيانات_الجدول, use_container_width=True)
        else:
            st.info("لا توجد طلبات إجازة حتى الآن")
            
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
    finally:
        cursor.close()
        connection.close()

def طلب_إجازة_جديدة():
    st.title("📝 طلب إجازة جديدة")
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        # الحصول على أنواع الإجازات
        cursor.execute("SELECT * FROM أنواع_الإجازات WHERE الحالة = 'مفعل'")
        أنواع_الإجازات = cursor.fetchall()
        
        # الحصول على الرصيد
        cursor.execute("SELECT * FROM أرصدة_الإجازات WHERE معرف_الموظف = %s ORDER BY السنة DESC LIMIT 1", (st.session_state.معرف_المستخدم,))
        رصيد = cursor.fetchone()
        
        with st.form("طلب إجازة"):
            col1, col2 = st.columns(2)
            
            with col1:
                نوع_الإجازة = st.selectbox("نوع الإجازة", options=[نوع['معرف'] for نوع in أنواع_الإجازات], 
                                          format_func=lambda x: next((نوع['اسم_الإجازة'] for نوع in أنواع_الإجازات if نوع['معرف'] == x), ''))
                تاريخ_البدء = st.date_input("تاريخ البدء", min_value=datetime.now().date())
                السبب = st.text_area("سبب الإجازة")
            
            with col2:
                # عرض معلومات الرصيد
                if رصيد:
                    st.info(f"""
                    **رصيد الإجازات المتاح:**
                    - السنة الحالية: {رصيد['رصيد_السنة_الحالية']} يوم
                    - العام السابق 1: {رصيد['رصيد_العام_السابق_1']} يوم
                    - العام السابق 2: {رصيد['رصيد_العام_السابق_2']} يوم
                    """)
                else:
                    st.warning("لا يوجد رصيد إجازات متاح")
                
                تاريخ_الانتهاء = st.date_input("تاريخ الانتهاء", min_value=datetime.now().date())
            
            if st.form_submit_button("تقديم طلب الإجازة"):
                if تاريخ_البدء and تاريخ_الانتهاء:
                    if تاريخ_الانتهاء >= تاريخ_البدء:
                        عدد_الأيام = (تاريخ_الانتهاء - تاريخ_البدء).days + 1
                        
                        if رصيد and رصيد['رصيد_السنة_الحالية'] >= عدد_الأيام:
                            # إدخال طلب الإجازة
                            cursor.execute("""
                                INSERT INTO طلبات_الإجازة 
                                (معرف_الموظف, نوع_الإجازة, تاريخ_البدء, تاريخ_الانتهاء, عدد_الأيام, السبب) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (st.session_state.معرف_المستخدم, نوع_الإجازة, تاريخ_البدء, تاريخ_الانتهاء, عدد_الأيام, السبب))
                            
                            connection.commit()
                            st.success("✅ تم تقديم طلب الإجازة بنجاح وسيتم مراجعته قريباً")
                        else:
                            st.error("❌ رصيد الإجازات غير كاف")
                    else:
                        st.error("❌ تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء")
                else:
                    st.error("❌ يرجى ملء جميع الحقول")
                    
    except Exception as e:
        st.error(f"خطأ: {e}")
    finally:
        cursor.close()
        connection.close()

def عرض_طلباتي():
    st.title("📋 طلبات الإجازة الخاصة بي")
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ط.*, ن.اسم_الإجازة 
            FROM طلبات_الإجازة ط 
            JOIN أنواع_الإجازات ن ON ط.نوع_الإجازة = ن.معرف 
            WHERE ط.معرف_الموظف = %s 
            ORDER BY ط.تاريخ_الطلب DESC
        """, (st.session_state.معرف_المستخدم,))
        طلبات = cursor.fetchall()
        
        if طلبات:
            for طلب in طلبات:
                with st.expander(f"{طلب['اسم_الإجازة']} - {طلب['تاريخ_البدء']} إلى {طلب['تاريخ_الانتهاء']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("عدد الأيام", طلب['عدد_الأيام'])
                    col2.metric("الحالة", طلب['الحالة'])
                    col3.metric("تاريخ الطلب", طلب['تاريخ_الطلب'].strftime('%Y-%m-%d'))
                    
                    if طلب['السبب']:
                        st.write(f"**السبب:** {طلب['السبب']}")
                    if طلب['ملاحظات_المدير']:
                        st.write(f"**ملاحظات المدير:** {طلب['ملاحظات_المدير']}")
        else:
            st.info("لا توجد طلبات إجازة")
            
    except Exception as e:
        st.error(f"خطأ في تحميل الطلبات: {e}")
    finally:
        cursor.close()
        connection.close()

def عرض_رصيد_الإجازات():
    st.title("💰 رصيد الإجازات")
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM أرصدة_الإجازات 
            WHERE معرف_الموظف = %s ORDER BY السنة DESC
        """, (st.session_state.معرف_المستخدم,))
        الأرصدة = cursor.fetchall()
        
        if الأرصدة:
            for رصيد in الأرصدة:
                st.subheader(f"سنة {رصيد['السنة']}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("رصيد السنة الحالية", رصيد['رصيد_السنة_الحالية'])
                col2.metric("رصيد العام السابق 1", رصيد['رصيد_العام_السابق_1'])
                col3.metric("رصيد العام السابق 2", رصيد['رصيد_العام_السابق_2'])
                
                st.markdown("---")
        else:
            st.warning("لا يوجد رصيد إجازات مسجل")
            
    except Exception as e:
        st.error(f"خطأ في تحميل الأرصدة: {e}")
    finally:
        cursor.close()
        connection.close()

# لوحة تحكم مدير النظام
def لوحة_مدير_النظام():
    st.sidebar.title(f"مدير النظام - {st.session_state.اسم_الموظف}")
    
    قائمة_المدير = ["الرئيسية", "إدارة المستخدمين", "الطلبات المعلقة", "التقارير", "إدارة الأرصدة"]
    اختيار = st.sidebar.selectbox("القائمة", قائمة_المدير)
    
    if اختيار == "الرئيسية":
        الرئيسية_مدير_النظام()
    elif اختيار == "إدارة المستخدمين":
        إدارة_المستخدمين()

def الرئيسية_مدير_النظام():
    st.title("👨‍💼 لوحة تحكم مدير النظام")
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        # إحصائيات
        col1, col2, col3, col4 = st.columns(4)
        
        cursor.execute("SELECT COUNT(*) as عدد FROM المستخدمين")
        عدد_الموظفين = cursor.fetchone()['عدد']
        
        cursor.execute("SELECT COUNT(*) as عدد FROM طلبات_الإجازة WHERE الحالة = 'قيد المراجعة'")
        طلبات_معلقة = cursor.fetchone()['عدد']
        
        cursor.execute("SELECT COUNT(*) as عدد FROM طلبات_الإجازة WHERE الحالة = 'معتمد'")
        طلبات_معتمدة = cursor.fetchone()['عدد']
        
        with col1:
            st.metric("إجمالي الموظفين", عدد_الموظفين)
        with col2:
            st.metric("طلبات قيد المراجعة", طلبات_معلقة)
        with col3:
            st.metric("طلبات معتمدة", طلبات_معتمدة)
        
        # رسم بياني
        st.subheader("📊 إحصائيات الطلبات")
        cursor.execute("""
            SELECT الحالة, COUNT(*) as العدد 
            FROM طلبات_الإجازة 
            GROUP BY الحالة
        """)
        بيانات = cursor.fetchall()
        
        if بيانات:
            df = pd.DataFrame(بيانات)
            fig = px.pie(df, values='العدد', names='الحالة', title="توزيع طلبات الإجازة حسب الحالة")
            st.plotly_chart(fig)
            
    except Exception as e:
        st.error(f"خطأ في تحميل الإحصائيات: {e}")
    finally:
        cursor.close()
        connection.close()

def إدارة_المستخدمين():
    st.title("👥 إدارة المستخدمين")
    
    try:
        connection = الحصول_على_الاتصال()
        cursor = connection.cursor(dictionary=True)
        
        # عرض المستخدمين الحاليين
        cursor.execute("""
            SELECT u.*, m.اسم_الموظف as اسم_المدير 
            FROM المستخدمين u 
            LEFT JOIN المستخدمين m ON u.المدير_المباشر = m.معرف 
            ORDER BY u.تاريخ_الإنشاء DESC
        """)
        المستخدمين = cursor.fetchall()
        
        if المستخدمين:
            st.subheader("المستخدمون الحاليون")
            بيانات_الجدول = []
            for مستخدم in المستخدمين:
                بيانات_الجدول.append({
                    "اسم المستخدم": مستخدم['اسم_المستخدم'],
                    "اسم الموظف": مستخدم['اسم_الموظف'],
                    "نوع المستخدم": مستخدم['نوع_المستخدم'],
                    "القسم": مستخدم['القسم'],
                    "الحالة": مستخدم['الحالة']
                })
            
            st.dataframe(بيانات_الجدول, use_container_width=True)
        
        # إضافة مستخدم جديد
        st.subheader("إضافة مستخدم جديد")
        with st.form("إضافة مستخدم"):
            col1, col2 = st.columns(2)
            
            with col1:
                اسم_المستخدم = st.text_input("اسم المستخدم")
                كلمة_المرور = st.text_input("كلمة المرور", type="password")
                اسم_الموظف = st.text_input("اسم الموظف")
            
            with col2:
                نوع_المستخدم = st.selectbox("نوع المستخدم", ["موظف", "مدير", "مسؤول_إداري", "مدير_النظام"])
                القسم = st.text_input("القسم")
            
            if st.form_submit_button("إضافة مستخدم"):
                if اسم_المستخدم and كلمة_المرور and اسم_الموظف:
                    try:
                        كلمة_مرور_مشفرة = تشفير_كلمة_المرور(كلمة_المرور)
                        cursor.execute("""
                            INSERT INTO المستخدمين 
                            (اسم_المستخدم, كلمة_المرور, اسم_الموظف, نوع_المستخدم, القسم) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (اسم_المستخدم, كلمة_مرور_مشفرة, اسم_الموظف, نوع_المستخدم, القسم))
                        
                        connection.commit()
                        st.success("✅ تم إضافة المستخدم بنجاح")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ في إضافة المستخدم: {e}")
                else:
                    st.error("❌ يرجى ملء جميع الحقول المطلوبة")
                    
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
    finally:
        cursor.close()
        connection.close()

# التطبيق الرئيسي
def main():
    # تهيئة قاعدة البيانات
    تهيئة_قاعدة_البيانات()
    
    # التحقق من تسجيل الدخول
    if 'معرف_المستخدم' not in st.session_state:
        صفحة_تسجيل_الدخول()
    else:
        # إضافة زر تسجيل الخروج في السايدبار
        with st.sidebar:
            if st.button("🚪 تسجيل الخروج"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # توجيه حسب نوع المستخدم
        if st.session_state.نوع_المستخدم == 'موظف':
            لوحة_الموظف()
        elif st.session_state.نوع_المستخدم == 'مدير_النظام':
            لوحة_مدير_النظام()
        else:
            st.warning("لوحة التحكم قيد التطوير لنوع المستخدم هذا")

if __name__ == "__main__":
    main()
