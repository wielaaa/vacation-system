import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime, date, timedelta
import json
from typing import Dict, List, Optional

# إعداد الصفحة
st.set_page_config(
    page_title="نظام إدارة الإجازات - مطار طابا الدولي",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# نظام التشفير
def hash_password(password: str, salt: str = None) -> tuple:
    """تشفير كلمة المرور"""
    if salt is None:
        salt = secrets.token_hex(16)
    encoded_password = (password + salt).encode('utf-8')
    hashed_password = hashlib.sha256(encoded_password).hexdigest()
    return hashed_password, salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """التحقق من كلمة المرور"""
    new_hash, _ = hash_password(password, salt)
    return new_hash == hashed_password

# قاعدة البيانات
def init_database():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect('vacation_system.db', check_same_thread=False)
    c = conn.cursor()
    
    # جدول الموظفين
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            direct_manager_id TEXT,
            hire_date DATE,
            is_active BOOLEAN DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            employee_id TEXT UNIQUE,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
        )
    ''')
    
    # جدول أرصدة الإجازات
    c.execute('''
        CREATE TABLE IF NOT EXISTS vacation_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            regular_balance INTEGER DEFAULT 0,
            sick_balance INTEGER DEFAULT 0,
            emergency_balance INTEGER DEFAULT 0,
            other_balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_by TEXT,
            approved_by TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
        )
    ''')
    
    # جدول طلبات الإجازة
    c.execute('''
        CREATE TABLE IF NOT EXISTS vacation_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            vacation_type TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            days_count INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            direct_manager_approval TEXT,
            admin_approval TEXT,
            rejection_reason TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
        )
    ''')
    
    # جدول الإشعارات
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # جدول سجلات النظام
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    return conn

# نظام المصادقة
def login_user(username: str, password: str) -> Optional[Dict]:
    """تسجيل دخول المستخدم"""
    conn = init_database()
    c = conn.cursor()
    
    c.execute('''
        SELECT u.*, e.name, e.department, e.position, e.direct_manager_id
        FROM users u 
        LEFT JOIN employees e ON u.employee_id = e.employee_id 
        WHERE u.username = ? AND u.is_active = 1
    ''', (username,))
    
    user = c.fetchone()
    conn.close()
    
    if user and verify_password(password, user[2], user[3]):
        return {
            'id': user[0],
            'username': user[1],
            'employee_id': user[4],
            'role': user[5],
            'name': user[7],
            'department': user[8],
            'position': user[9],
            'direct_manager_id': user[10]
        }
    return None

def check_permission(required_role: str = None) -> bool:
    """التحقق من صلاحية المستخدم"""
    if 'user' not in st.session_state:
        return False
    
    user_role = st.session_state.user['role']
    
    # ترتيب الصلاحيات
    role_hierarchy = {
        'employee': 1,
        'direct_manager': 2,
        'admin_officer': 3,
        'admin': 4
    }
    
    if required_role:
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
    
    return True

# واجهة تسجيل الدخول
def login_interface():
    """واجهة تسجيل الدخول"""
    st.title("✈️ نظام إدارة الإجازات - مطار طابا الدولي")
    st.markdown("---")
    
    with st.form("login_form"):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("https://cdn-icons-png.flaticon.com/512/824/824239.png", width=150)
        
        with col2:
            username = st.text_input("اسم المستخدم", placeholder="أدخل الكود الوظيفي")
            password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
            
            if st.form_submit_button("تسجيل الدخول", use_container_width=True):
                if username and password:
                    user = login_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success(f"مرحباً بك {user['name']}!")
                        st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
                else:
                    st.error("الرجاء إدخال اسم المستخدم وكلمة المرور")
    
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "نظام إدارة الإجازات الإلكتروني - مطار طابا الدولي<br>"
        "الإصدار 2.0 - تم التطوير خصيصاً لمتطلبات المطار"
        "</div>",
        unsafe_allow_html=True
    )

def get_role_name(role_code: str) -> str:
    """الحصول على اسم الدور"""
    roles = {
        'employee': 'موظف',
        'direct_manager': 'رئيس مباشر',
        'admin_officer': 'مسؤول إداري',
        'admin': 'مدير النظام'
    }
    return roles.get(role_code, role_code)

# الواجهة الرئيسية
def main_interface():
    """الواجهة الرئيسية للنظام"""
    
    # الشريط الجانبي
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/824/824239.png", width=80)
        st.title(f"مرحباً, {st.session_state.user['name']}")
        st.write(f"**الوظيفة:** {st.session_state.user['position']}")
        st.write(f"**القسم:** {st.session_state.user['department']}")
        st.write(f"**الدور:** {get_role_name(st.session_state.user['role'])}")
        st.markdown("---")
        
        # القائمة الجانبية حسب الصلاحيات
        menu_options = ["الرئيسية"]
        
        if st.session_state.user['role'] in ['employee', 'direct_manager', 'admin_officer', 'admin']:
            menu_options.extend(["طلب إجازة", "طلباتي", "رصيد الإجازات"])
        
        if st.session_state.user['role'] in ['direct_manager', 'admin']:
            menu_options.append("مراجعة الطلبات")
        
        if st.session_state.user['role'] in ['admin_officer', 'admin']:
            menu_options.append("إدارة الأرصدة")
        
        if st.session_state.user['role'] == 'admin':
            menu_options.extend(["إدارة المستخدمين", "التقارير", "سجلات النظام"])
        
        menu_options.append("الإشعارات")
        
        selected_menu = st.selectbox("القائمة الرئيسية", menu_options)
        
        st.markdown("---")
        if st.button("تسجيل الخروج", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # عرض المحتوى حسب القائمة المختارة
    if selected_menu == "الرئيسية":
        show_dashboard()
    elif selected_menu == "طلب إجازة":
        show_vacation_request()
    elif selected_menu == "طلباتي":
        show_my_requests()
    elif selected_menu == "رصيد الإجازات":
        show_vacation_balance()
    elif selected_menu == "مراجعة الطلبات":
        show_review_requests()
    elif selected_menu == "إدارة الأرصدة":
        show_balance_management()
    elif selected_menu == "إدارة المستخدمين":
        show_user_management()
    elif selected_menu == "التقارير":
        show_reports()
    elif selected_menu == "سجلات النظام":
        show_audit_logs()
    elif selected_menu == "الإشعارات":
        show_notifications()

# لوحة التحكم
def show_dashboard():
    """عرض لوحة التحكم"""
    st.header("🏠 لوحة التحكم الرئيسية")
    
    conn = init_database()
    
    # إحصائيات سريعة
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        employees_count = pd.read_sql("SELECT COUNT(*) FROM employees WHERE is_active = 1", conn).iloc[0,0]
        st.metric("إجمالي الموظفين", employees_count)
    
    with col2:
        vacations_count = pd.read_sql("SELECT COUNT(*) FROM vacation_requests", conn).iloc[0,0]
        st.metric("طلبات الإجازة", vacations_count)
    
    with col3:
        pending_count = pd.read_sql("SELECT COUNT(*) FROM vacation_requests WHERE status = 'pending'", conn).iloc[0,0]
        st.metric("طلبات معلقة", pending_count)
    
    with col4:
        st.metric("حالة النظام", "🟢 نشط")
    
    # قسم الطلبات الحديثة
    st.subheader("آخر الطلبات")
    
    if st.session_state.user['role'] == 'employee':
        recent_requests = pd.read_sql('''
            SELECT vr.*, e.name as employee_name 
            FROM vacation_requests vr 
            JOIN employees e ON vr.employee_id = e.employee_id 
            WHERE vr.employee_id = ?
            ORDER BY vr.created_date DESC LIMIT 10
        ''', conn, params=(st.session_state.user['employee_id'],))
    elif st.session_state.user['role'] == 'direct_manager':
        recent_requests = pd.read_sql('''
            SELECT vr.*, e.name as employee_name 
            FROM vacation_requests vr 
            JOIN employees e ON vr.employee_id = e.employee_id 
            WHERE e.direct_manager_id = ?
            ORDER BY vr.created_date DESC LIMIT 10
        ''', conn, params=(st.session_state.user['employee_id'],))
    else:
        recent_requests = pd.read_sql('''
            SELECT vr.*, e.name as employee_name 
            FROM vacation_requests vr 
            JOIN employees e ON vr.employee_id = e.employee_id 
            ORDER BY vr.created_date DESC LIMIT 10
        ''', conn)
    
    if not recent_requests.empty:
        def style_status(status):
            if status == 'approved':
                return '🟢 معتمدة'
            elif status == 'rejected':
                return '🔴 مرفوضة'
            elif status == 'pending':
                return '🟡 قيد المراجعة'
            else:
                return status
        
        recent_requests['الحالة'] = recent_requests['status'].apply(style_status)
        st.dataframe(recent_requests[['employee_name', 'vacation_type', 'start_date', 'end_date', 'days_count', 'الحالة']])
    else:
        st.info("لا توجد طلبات حديثة")
    
    conn.close()

# طلب إجازة
def show_vacation_request():
    """عرض نموذج طلب الإجازة"""
    st.header("📝 تقديم طلب إجازة جديد")
    
    conn = init_database()
    
    with st.form("vacation_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            vacation_types = [
                "إجازة اعتيادية", "إجازة عرضة", "إجازة بدل راحة", "إجازة بدل عمل",
                "إجازة بدون مرتب", "إجازة مرضية", "إجازة طارئة", "إجازة دراسية",
                "إجازة حج / عمرة", "إجازة مرافقة مريض", "إجازة أخرى"
            ]
            vacation_type = st.selectbox("نوع الإجازة *", vacation_types)
            
            start_date = st.date_input("تاريخ بداية الإجازة *", min_value=date.today())
            end_date = st.date_input("تاريخ نهاية الإجازة *", min_value=date.today())
        
        with col2:
            if start_date and end_date:
                days_count = (end_date - start_date).days + 1
                if days_count > 0:
                    st.info(f"**عدد أيام الإجازة:** {days_count} يوم")
                else:
                    st.error("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
            
            reason = st.text_area("سبب الإجازة *", height=100, 
                                placeholder="يرجى توضيح سبب طلب الإجازة...")
        
        if vacation_type in ["إجازة اعتيادية", "إجازة عرضة"]:
            balance_info = get_vacation_balance(st.session_state.user['employee_id'])
            if balance_info:
                current_year = date.today().year
                regular_balance = balance_info.get(current_year, {}).get('regular_balance', 0)
                st.info(f"**الرصيد المتاح للإجازة الاعتيادية:** {regular_balance} يوم")
        
        submitted = st.form_submit_button("تقديم طلب الإجازة", use_container_width=True)
        
        if submitted:
            if not all([vacation_type, start_date, end_date, reason]):
                st.error("الرجاء ملء جميع الحقول الإلزامية (*)")
            elif start_date > end_date:
                st.error("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
            else:
                days_count = (end_date - start_date).days + 1
                
                try:
                    conn.execute('''
                        INSERT INTO vacation_requests 
                        (employee_id, vacation_type, start_date, end_date, days_count, reason, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    ''', (st.session_state.user['employee_id'], vacation_type, 
                          start_date, end_date, days_count, reason))
                    
                    conn.commit()
                    send_notification_to_manager(st.session_state.user['employee_id'], 
                                               f"طلب إجازة جديد من {st.session_state.user['name']}")
                    
                    st.success("✅ تم تقديم طلب الإجازة بنجاح وتم إرساله للرئيس المباشر للمراجعة")
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء حفظ الطلب: {str(e)}")
    
    conn.close()

def get_vacation_balance(employee_id: str) -> Dict:
    """الحصول على رصيد إجازات الموظف"""
    conn = init_database()
    
    current_year = date.today().year
    balance_df = pd.read_sql('''
        SELECT year, regular_balance, sick_balance, emergency_balance, other_balance, status
        FROM vacation_balances 
        WHERE employee_id = ? AND status = 'approved'
        ORDER BY year DESC
    ''', conn, params=(employee_id,))
    
    conn.close()
    
    if balance_df.empty:
        return None
    
    balance_info = {}
    for _, row in balance_df.iterrows():
        balance_info[row['year']] = {
            'regular_balance': row['regular_balance'],
            'sick_balance': row['sick_balance'],
            'emergency_balance': row['emergency_balance'],
            'other_balance': row['other_balance']
        }
    
    return balance_info

def send_notification_to_manager(employee_id: str, message: str):
    """إرسال إشعار للرئيس المباشر"""
    conn = init_database()
    
    manager_df = pd.read_sql('''
        SELECT direct_manager_id FROM employees WHERE employee_id = ?
    ''', conn, params=(employee_id,))
    
    if not manager_df.empty and manager_df.iloc[0]['direct_manager_id']:
        manager_id = manager_df.iloc[0]['direct_manager_id']
        
        user_df = pd.read_sql('''
            SELECT id FROM users WHERE employee_id = ?
        ''', conn, params=(manager_id,))
        
        if not user_df.empty:
            user_id = user_df.iloc[0]['id']
            
            conn.execute('''
                INSERT INTO notifications (user_id, title, message)
                VALUES (?, 'طلب إجازة جديد', ?)
            ''', (user_id, message))
            
            conn.commit()
    
    conn.close()

def show_my_requests():
    """عرض طلبات الإجازة الخاصة بالموظف"""
    st.header("📋 طلبات الإجازة الخاصة بي")
    
    conn = init_database()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        status_filter = st.selectbox("تصفية حسب الحالة", 
                                   ["الكل", "قيد المراجعة", "معتمدة", "مرفوضة"])
    
    status_map = {
        "الكل": None,
        "قيد المراجعة": "pending",
        "معتمدة": "approved", 
        "مرفوضة": "rejected"
    }
    
    query = '''
        SELECT vr.*, e.name as employee_name,
               dm.name as manager_name
        FROM vacation_requests vr 
        JOIN employees e ON vr.employee_id = e.employee_id 
        LEFT JOIN employees dm ON e.direct_manager_id = dm.employee_id
        WHERE vr.employee_id = ?
    '''
    
    params = [st.session_state.user['employee_id']]
    
    if status_filter != "الكل":
        query += " AND vr.status = ?"
        params.append(status_map[status_filter])
    
    query += " ORDER BY vr.created_date DESC"
    
    my_requests = pd.read_sql(query, conn, params=params)
    
    if not my_requests.empty:
        def style_status(status):
            if status == 'approved':
                return '🟢 معتمدة'
            elif status == 'rejected':
                return '🔴 مرفوضة'
            elif status == 'pending':
                return '🟡 قيد المراجعة'
            else:
                return status
        
        my_requests['الحالة'] = my_requests['status'].apply(style_status)
        my_requests['المدير المباشر'] = my_requests['manager_name']
        
        display_columns = ['vacation_type', 'start_date', 'end_date', 'days_count', 'الحالة', 'المدير المباشر']
        if 'rejection_reason' in my_requests.columns:
            my_requests['سبب الرفض'] = my_requests['rejection_reason'].fillna('')
            display_columns.append('سبب الرفض')
        
        st.dataframe(my_requests[display_columns], use_container_width=True)
        
        pending_requests = my_requests[my_requests['status'] == 'pending']
        if not pending_requests.empty:
            st.subheader("إلغاء الطلبات المعلقة")
            request_to_cancel = st.selectbox(
                "اختر طلب للإلغاء",
                options=pending_requests['id'].tolist(),
                format_func=lambda x: f"{pending_requests[pending_requests['id']==x]['vacation_type'].iloc[0]} - {pending_requests[pending_requests['id']==x]['start_date'].iloc[0]}"
            )
            
            if st.button("إلغاء الطلب المحدد", type="secondary"):
                conn.execute(
                    "UPDATE vacation_requests SET status = 'cancelled' WHERE id = ?",
                    (request_to_cancel,)
                )
                conn.commit()
                st.success("✅ تم إلغاء الطلب بنجاح")
                st.rerun()
    else:
        st.info("لا توجد طلبات إجازة")
    
    conn.close()

def show_vacation_balance():
    """عرض رصيد الإجازات"""
    st.header("💰 رصيد الإجازات")
    
    employee_id = st.session_state.user['employee_id']
    balance_info = get_vacation_balance(employee_id)
    
    if not balance_info:
        st.warning("لا يوجد رصيد مسجل لك حتى الآن")
        return
    
    current_year = date.today().year
    
    st.subheader(f"رصيد السنة الحالية ({current_year})")
    
    if current_year in balance_info:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("الإجازة الاعتيادية", f"{balance_info[current_year]['regular_balance']} يوم")
        
        with col2:
            st.metric("الإجازة المرضية", f"{balance_info[current_year]['sick_balance']} يوم")
        
        with col3:
            st.metric("الإجازة الطارئة", f"{balance_info[current_year]['emergency_balance']} يوم")
        
        with col4:
            st.metric("إجازات أخرى", f"{balance_info[current_year]['other_balance']} يوم")
    
    previous_years = {k: v for k, v in balance_info.items() if k < current_year}
    if previous_years:
        st.subheader("أرصدة السنوات السابقة")
        
        for year, balance in sorted(previous_years.items(), reverse=True):
            with st.expander(f"رصيد عام {year}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write(f"**اعتيادية:** {balance['regular_balance']} يوم")
                
                with col2:
                    st.write(f"**مرضية:** {balance['sick_balance']} يوم")
                
                with col3:
                    st.write(f"**طارئة:** {balance['emergency_balance']} يوم")
                
                with col4:
                    st.write(f"**أخرى:** {balance['other_balance']} يوم")

def show_review_requests():
    """مراجعة طلبات الإجازة (للرؤساء المباشرين والمديرين)"""
    if not check_permission('direct_manager'):
        st.error("❌ غير مصرح لك بالوصول لهذه الصفحة")
        return
    
    st.header("📋 مراجعة طلبات الإجازة")
    
    conn = init_database()
    
    if st.session_state.user['role'] == 'direct_manager':
        requests_df = pd.read_sql('''
            SELECT vr.*, e.name as employee_name, e.department,
                   e.position, vb.regular_balance, vb.sick_balance
            FROM vacation_requests vr 
            JOIN employees e ON vr.employee_id = e.employee_id 
            LEFT JOIN vacation_balances vb ON (vr.employee_id = vb.employee_id AND vb.year = ?)
            WHERE e.direct_manager_id = ? AND vr.status = 'pending'
            ORDER BY vr.created_date DESC
        ''', conn, params=(date.today().year, st.session_state.user['employee_id']))
    else:
        requests_df = pd.read_sql('''
            SELECT vr.*, e.name as employee_name, e.department,
                   e.position, dm.name as manager_name,
                   vb.regular_balance, vb.sick_balance
            FROM vacation_requests vr 
            JOIN employees e ON vr.employee_id = e.employee_id 
            LEFT JOIN employees dm ON e.direct_manager_id = dm.employee_id
            LEFT JOIN vacation_balances vb ON (vr.employee_id = vb.employee_id AND vb.year = ?)
            WHERE vr.status = 'pending'
            ORDER BY vr.created_date DESC
        ''', conn, params=(date.today().year,))
    
    if requests_df.empty:
        st.success("🎉 لا توجد طلبات إجازة معلقة تحتاج المراجعة")
        conn.close()
        return
    
    for _, request in requests_df.iterrows():
        with st.container():
            st.markdown("---")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**👤 الموظف:** {request['employee_name']}")
                st.write(f"**📋 القسم:** {request['department']} - {request['position']}")
                st.write(f"**🎯 نوع الإجازة:** {request['vacation_type']}")
                st.write(f"**📅 الفترة:** من {request['start_date']} إلى {request['end_date']}")
                st.write(f"**⏰ المدة:** {request['days_count']} يوم")
                st.write(f"**📝 السبب:** {request['reason']}")
                
                if pd.notna(request['regular_balance']):
                    st.write(f"**💰 الرصيد المتاح:** {request['regular_balance']} يوم")
            
            with col2:
                st.write("**قرار المراجعة:**")
                
                col_approve, col_reject = st.columns(2)
                
                with col_approve:
                    if st.button("✅ موافقة", key=f"approve_{request['id']}", use_container_width=True):
                        conn.execute('''
                            UPDATE vacation_requests 
                            SET status = 'approved', direct_manager_approval = ?
                            WHERE id = ?
                        ''', (st.session_state.user['employee_id'], request['id']))
                        
                        deduct_vacation_balance(request['employee_id'], request['vacation_type'], request['days_count'])
                        
                        conn.commit()
                        
                        send_notification_to_employee(
                            request['employee_id'],
                            f"تمت الموافقة على طلب إجازتك من {request['start_date']} إلى {request['end_date']}"
                        )
                        
                        st.success("✅ تمت الموافقة على الطلب!")
                        st.rerun()
                
                with col_reject:
                    with st.popover("❌ رفض", use_container_width=True):
                        rejection_reason = st.text_area("سبب الرفض", key=f"reject_reason_{request['id']}")
                        if st.button("تأكيد الرفض", key=f"confirm_reject_{request['id']}"):
                            if rejection_reason:
                                conn.execute('''
                                    UPDATE vacation_requests 
                                    SET status = 'rejected', direct_manager_approval = ?,
                                        rejection_reason = ?
                                    WHERE id = ?
                                ''', (st.session_state.user['employee_id'], rejection_reason, request['id']))
                                
                                conn.commit()
                                
                                send_notification_to_employee(
                                    request['employee_id'],
                                    f"تم رفض طلب إجازتك. السبب: {rejection_reason}"
                                )
                                
                                st.success("✅ تم رفض الطلب!")
                                st.rerun()
                            else:
                                st.error("الرجاء إدخال سبب الرفض")
    
    conn.close()

def deduct_vacation_balance(employee_id: str, vacation_type: str, days: int):
    """خصم أيام الإجازة من الرصيد"""
    conn = init_database()
    
    current_year = date.today().year
    
    try:
        balance_column = 'regular_balance'
        
        if 'مرضية' in vacation_type:
            balance_column = 'sick_balance'
        elif 'طارئة' in vacation_type:
            balance_column = 'emergency_balance'
        elif 'عرضة' in vacation_type:
            balance_column = 'other_balance'
        
        conn.execute(f'''
            UPDATE vacation_balances 
            SET {balance_column} = {balance_column} - ?
            WHERE employee_id = ? AND year = ? AND status = 'approved'
        ''', (days, employee_id, current_year))
        
        conn.commit()
        
    except Exception as e:
        st.error(f"خطأ في خصم الرصيد: {str(e)}")
    finally:
        conn.close()

def send_notification_to_employee(employee_id: str, message: str):
    """إرسال إشعار للموظف"""
    conn = init_database()
    
    user_df = pd.read_sql('''
        SELECT id FROM users WHERE employee_id = ?
    ''', conn, params=(employee_id,))
    
    if not user_df.empty:
        user_id = user_df.iloc[0]['id']
        
        conn.execute('''
            INSERT INTO notifications (user_id, title, message)
            VALUES (?, 'تحديث حالة طلب الإجازة', ?)
        ''', (user_id, message))
        
        conn.commit()
    
    conn.close()

def show_balance_management():
    """إدارة أرصدة الإجازات (للمسؤول الإداري)"""
    if not check_permission('admin_officer'):
        st.error("❌ غير مصرح لك بالوصول لهذه الصفحة")
        return
    
    st.header("💰 إدارة أرصدة الإجازات")
    
    conn = init_database()
    
    tab1, tab2, tab3 = st.tabs(["إضافة رصيد جديد", "تعديل الأرصدة", "الطلبات المنتظرة"])
    
    with tab1:
        st.subheader("إضافة رصيد إجازات جديد")
        
        with st.form("add_balance_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                employees_df = pd.read_sql('''
                    SELECT employee_id, name, department 
                    FROM employees 
                    WHERE is_active = 1 
                    ORDER BY name
                ''', conn)
                
                employee_id = st.selectbox(
                    "اختر الموظف *",
                    options=employees_df['employee_id'].tolist(),
                    format_func=lambda x: f"{employees_df[employees_df['employee_id']==x]['name'].iloc[0]} - {employees_df[employees_df['employee_id']==x]['department'].iloc[0]}"
                )
                
                year = st.number_input("السنة *", min_value=2020, max_value=2030, value=date.today().year)
            
            with col2:
                regular_balance = st.number_input("رصيد الإجازة الاعتيادية *", min_value=0, value=21)
                sick_balance = st.number_input("رصيد الإجازة المرضية", min_value=0, value=30)
                emergency_balance = st.number_input("رصيد الإجازة الطارئة", min_value=0, value=7)
                other_balance = st.number_input("رصيد الإجازات الأخرى", min_value=0, value=0)
            
            if st.form_submit_button("إضافة الرصيد", use_container_width=True):
                existing_balance = pd.read_sql('''
                    SELECT id FROM vacation_balances 
                    WHERE employee_id = ? AND year = ?
                ''', conn, params=(employee_id, year))
                
                if not existing_balance.empty:
                    st.error("⚠️ يوجد رصيد مسجل already لهذا الموظف لنفس السنة")
                else:
                    conn.execute('''
                        INSERT INTO vacation_balances 
                        (employee_id, year, regular_balance, sick_balance, emergency_balance, other_balance, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (employee_id, year, regular_balance, sick_balance, emergency_balance, other_balance, st.session_state.user['employee_id']))
                    
                    conn.commit()
                    
                    send_notification_to_admin(
                        f"طلب اعتماد رصيد إجازات جديد للموظف {employees_df[employees_df['employee_id']==employee_id]['name'].iloc[0]} للسنة {year}"
                    )
                    
                    st.success("✅ تم إضافة الرصيد بنجاح وتم إرساله للمدير للموافقة")
    
    with tab2:
        st.subheader("تعديل الأرصدة الحالية")
        
        balances_df = pd.read_sql('''
            SELECT vb.*, e.name as employee_name, e.department,
                   u1.name as created_by_name, u2.name as approved_by_name
            FROM vacation_balances vb
            JOIN employees e ON vb.employee_id = e.employee_id
            LEFT JOIN employees u1 ON vb.created_by = u1.employee_id
            LEFT JOIN employees u2 ON vb.approved_by = u2.employee_id
            WHERE vb.status = 'approved'
            ORDER BY vb.year DESC, e.name
        ''', conn)
        
        if not balances_df.empty:
            st.dataframe(balances_df[['employee_name', 'department', 'year', 'regular_balance', 'sick_balance', 'emergency_balance', 'other_balance']])
        else:
            st.info("لا توجد أرصدة معتمدة")
    
    with tab3:
        st.subheader("طلبات الأرصدة المنتظرة الموافقة")
        
        pending_balances = pd.read_sql('''
            SELECT vb.*, e.name as employee_name, e.department,
                   u1.name as created_by_name
            FROM vacation_balances vb
            JOIN employees e ON vb.employee_id = e.employee_id
            LEFT JOIN employees u1 ON vb.created_by = u1.employee_id
            WHERE vb.status = 'pending'
            ORDER BY vb.created_date DESC
        ''', conn)
        
        if not pending_balances.empty:
            for _, balance in pending_balances.iterrows():
                with st.container():
                    st.markdown("---")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**👤 الموظف:** {balance['employee_name']} - {balance['department']}")
                        st.write(f"**📅 السنة:** {balance['year']}")
                        st.write(f"**💰 الرصيد المقترح:**")
                        st.write(f"  - اعتيادية: {balance['regular_balance']} يوم")
                        st.write(f"  - مرضية: {balance['sick_balance']} يوم") 
                        st.write(f"  - طارئة: {balance['emergency_balance']} يوم")
                        st.write(f"  - أخرى: {balance['other_balance']} يوم")
                        st.write(f"**📤 مقدم الطلب:** {balance['created_by_name']}")
                    
                    with col2:
                        if st.session_state.user['role'] == 'admin':
                            st.write("**موافقة الإدارة:**")
                            
                            if st.button("✅ اعتماد", key=f"approve_balance_{balance['id']}", use_container_width=True):
                                conn.execute('''
                                    UPDATE vacation_balances 
                                    SET status = 'approved', approved_by = ?
                                    WHERE id = ?
                                ''', (st.session_state.user['employee_id'], balance['id']))
                                
                                conn.commit()
                                
                                send_notification_to_employee(
                                    balance['employee_id'],
                                    f"تم اعتماد رصيد إجازاتك للسنة {balance['year']}"
                                )
                                
                                st.success("✅ تم اعتماد الرصيد بنجاح!")
                                st.rerun()
                            
                            if st.button("❌ رفض", key=f"reject_balance_{balance['id']}", use_container_width=True):
                                conn.execute('''
                                    UPDATE vacation_balances 
                                    SET status = 'rejected', approved_by = ?
                                    WHERE id = ?
                                ''', (st.session_state.user['employee_id'], balance['id']))
                                
                                conn.commit()
                                st.success("✅ تم رفض الرصيد!")
                                st.rerun()
                        else:
                            st.info("⏳ بانتظار موافقة المدير")
        else:
            st.info("لا توجد طلبات أرصدة منتظرة")
    
    conn.close()

def send_notification_to_admin(message: str):
    """إرسال إشعار لمدير النظام"""
    conn = init_database()
    
    admins_df = pd.read_sql('''
        SELECT id FROM users WHERE role = 'admin' AND is_active = 1
    ''', conn)
    
    for _, admin in admins_df.iterrows():
        conn.execute('''
            INSERT INTO notifications (user_id, title, message)
            VALUES (?, 'طلب اعتماد رصيد', ?)
        ''', (admin['id'], message))
    
    conn.commit()
    conn.close()

def show_user_management():
    """إدارة المستخدمين (للمدير فقط)"""
    if not check_permission('admin'):
        st.error("❌ غير مصرح لك بالوصول لهذه الصفحة")
        return
    
    st.header("👨‍💼 إدارة المستخدمين والموظفين")
    
    conn = init_database()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "إضافة موظف جديد", 
        "عرض الموظفين", 
        "إدارة المستخدمين",
        "الهيكل التنظيمي"
    ])
    
    with tab1:
        st.subheader("إضافة موظف جديد")
        
        with st.form("add_employee_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                employee_id = st.text_input("الرقم الوظيفي *", placeholder="مثال: EMP001")
                name = st.text_input("اسم الموظف *", placeholder="الاسم الثلاثي")
                department = st.selectbox("القسم *", [
                    "الإدارة العامة", "الشؤون الإدارية", "شؤون الموظفين", 
                    "الأمن والسلامة", "التشغيل", "الصيانة", 
                    "الجودة", "المالية", "التجارية", "خدمات الركاب"
                ])
                
            with col2:
                position = st.text_input("المسمى الوظيفي *", placeholder="مثال: مدير قسم")
                
                managers_df = pd.read_sql('''
                    SELECT employee_id, name, department 
                    FROM employees 
                    WHERE is_active = 1 
                    ORDER BY name
                ''', conn)
                
                direct_manager_id = st.selectbox(
                    "الرئيس المباشر",
                    options=[""] + managers_df['employee_id'].tolist(),
                    format_func=lambda x: "بدون رئيس مباشر" if x == "" else 
                    f"{managers_df[managers_df['employee_id']==x]['name'].iloc[0]} - {managers_df[managers_df['employee_id']==x]['department'].iloc[0]}"
                )
                
                hire_date = st.date_input("تاريخ التعيين *", value=date.today())
            
            if st.form_submit_button("إضافة الموظف", use_container_width=True):
                if not all([employee_id, name, department, position, hire_date]):
                    st.error("الرجاء ملء جميع الحقول الإلزامية (*)")
                else:
                    try:
                        conn.execute('''
                            INSERT INTO employees 
                            (employee_id, name, department, position, direct_manager_id, hire_date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (employee_id, name, department, position, 
                              direct_manager_id if direct_manager_id else None, hire_date))
                        
                        conn.commit()
                        st.success(f"✅ تم إضافة الموظف {name} بنجاح")
                        
                    except sqlite3.IntegrityError:
                        st.error("⚠️ الرقم الوظيفي مسجل مسبقاً")
    
    with tab2:
        st.subheader("قائمة الموظفين")
        
        col1, col2 = st.columns(2)
        with col1:
            department_filter = st.selectbox(
                "تصفية حسب القسم",
                ["الكل"] + [
                    "الإدارة العامة", "الشؤون الإدارية", "شؤون الموظفين", 
                    "الأمن والسلامة", "التشغيل", "الصيانة", 
                    "الجودة", "المالية", "التجارية", "خدمات الركاب"
                ]
            )
        
        with col2:
            status_filter = st.selectbox("حالة الموظف", ["نشط", "جميع"])
        
        query = '''
            SELECT e.*, m.name as manager_name,
                   (SELECT COUNT(*) FROM vacation_requests vr WHERE vr.employee_id = e.employee_id) as request_count
            FROM employees e
            LEFT JOIN employees m ON e.direct_manager_id = m.employee_id
            WHERE 1=1
        '''
        
        params = []
        
        if department_filter != "الكل":
            query += " AND e.department = ?"
            params.append(department_filter)
        
        if status_filter == "نشط":
            query += " AND e.is_active = 1"
        
        query += " ORDER BY e.department, e.name"
        
        employees_df = pd.read_sql(query, conn, params=params)
        
        if not employees_df.empty:
            employees_display = employees_df.copy()
            employees_display['الحالة'] = employees_display['is_active'].apply(lambda x: '🟢 نشط' if x == 1 else '🔴 غير نشط')
            employees_display['الرئيس المباشر'] = employees_display['manager_name'].fillna('لا يوجد')
            
            st.dataframe(
                employees_display[[
                    'employee_id', 'name', 'department', 'position', 
                    'الرئيس المباشر', 'hire_date', 'الحالة', 'request_count'
                ]],
                use_container_width=True
            )
        else:
            st.info("لا توجد بيانات موظفين")
    
    with tab3:
        st.subheader("إدارة حسابات المستخدمين")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            users_df = pd.read_sql('''
                SELECT u.*, e.name as employee_name, e.department,
                       e.position, e.is_active as employee_active
                FROM users u
                LEFT JOIN employees e ON u.employee_id = e.employee_id
                ORDER BY u.created_date DESC
            ''', conn)
            
            if not users_df.empty:
                users_display = users_df.copy()
                users_display['الدور'] = users_display['role'].apply(get_role_name)
                users_display['حالة المستخدم'] = users_display['is_active'].apply(lambda x: '🟢 نشط' if x == 1 else '🔴 معطل')
                users_display['حالة الموظف'] = users_display['employee_active'].apply(lambda x: '🟢 نشط' if x == 1 else '🔴 غير نشط')
                
                st.dataframe(
                    users_display[['username', 'employee_name', 'department', 'الدور', 'حالة المستخدم', 'حالة الموظف']],
                    use_container_width=True
                )
            else:
                st.info("لا توجد حسابات مستخدمين")
        
        with col2:
            st.subheader("إنشاء حساب جديد")
            
            with st.form("create_user_form"):
                employees_without_account = pd.read_sql('''
                    SELECT employee_id, name, department 
                    FROM employees 
                    WHERE is_active = 1 
                    AND employee_id NOT IN (SELECT employee_id FROM users WHERE employee_id IS NOT NULL)
                    ORDER BY name
                ''', conn)
                
                if employees_without_account.empty:
                    st.info("جميع الموظفين لديهم حسابات")
                else:
                    employee_id = st.selectbox(
                        "اختر الموظف",
                        options=employees_without_account['employee_id'].tolist(),
                        format_func=lambda x: f"{employees_without_account[employees_without_account['employee_id']==x]['name'].iloc[0]} - {employees_without_account[employees_without_account['employee_id']==x]['department'].iloc[0]}"
                    )
                    
                    username = st.text_input("اسم المستخدم", placeholder="مثل: EMP001")
                    password = st.text_input("كلمة المرور", type="password")
                    role = st.selectbox(
                        "الدور",
                        options=['employee', 'direct_manager', 'admin_officer', 'admin'],
                        format_func=get_role_name
                    )
                    
                    if st.form_submit_button("إنشاء الحساب", use_container_width=True):
                        if not all([employee_id, username, password, role]):
                            st.error("الرجاء ملء جميع الحقول")
                        else:
                            hashed_password, salt = hash_password(password)
                            
                            try:
                                conn.execute('''
                                    INSERT INTO users (username, password_hash, salt, employee_id, role)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (username, hashed_password, salt, employee_id, role))
                                
                                conn.commit()
                                st.success("✅ تم إنشاء الحساب بنجاح")
                                
                            except sqlite3.IntegrityError:
                                st.error("⚠️ اسم المستخدم مسجل مسبقاً")
    
    with tab4:
        st.subheader("الهيكل التنظيمي")
        
        org_df = pd.read_sql('''
            SELECT e.employee_id, e.name, e.department, e.position,
                   e.direct_manager_id, m.name as manager_name
            FROM employees e
            LEFT JOIN employees m ON e.direct_manager_id = m.employee_id
            WHERE e.is_active = 1
            ORDER BY e.department, e.name
        ''', conn)
        
        if not org_df.empty:
            departments = org_df['department'].unique()
            
            for dept in departments:
                with st.expander(f"📁 قسم {dept}"):
                    dept_employees = org_df[org_df['department'] == dept]
                    
                    for _, emp in dept_employees.iterrows():
                        col1, col2, col3 = st.columns([3, 2, 2])
                        
                        with col1:
                            st.write(f"**{emp['name']}** - {emp['position']}")
                        
                        with col2:
                            if pd.notna(emp['manager_name']):
                                st.write(f"↳ المدير: {emp['manager_name']}")
                        
                        with col3:
                            requests_count = pd.read_sql('''
                                SELECT COUNT(*) FROM vacation_requests 
                                WHERE employee_id = ?
                            ''', conn, params=(emp['employee_id'],)).iloc[0,0]
                            
                            st.write(f"📊 {requests_count} طلب")
        
        else:
            st.info("لا توجد بيانات للعرض")
    
    conn.close()

def show_reports():
    """التقارير والإحصائيات"""
    if not check_permission('admin'):
        st.error("❌ غير مصرح لك بالوصول لهذه الصفحة")
        return
    
    st.header("📊 التقارير والإحصائيات")
    
    conn = init_database()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "نظرة عامة", 
        "تقارير الإجازات", 
        "إحصائيات الأقسام",
        "تقارير مخصصة"
    ])
    
    with tab1:
        st.subheader("نظرة عامة على النظام")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_employees = pd.read_sql(
                "SELECT COUNT(*) FROM employees WHERE is_active = 1", 
                conn
            ).iloc[0,0]
            st.metric("إجمالي الموظفين", total_employees)
        
        with col2:
            total_requests = pd.read_sql(
                "SELECT COUNT(*) FROM vacation_requests", 
                conn
            ).iloc[0,0]
            st.metric("إجمالي طلبات الإجازة", total_requests)
        
        with col3:
            approved_requests = pd.read_sql(
                "SELECT COUNT(*) FROM vacation_requests WHERE status = 'approved'", 
                conn
            ).iloc[0,0]
            st.metric("الطلبات المعتمدة", approved_requests)
        
        with col4:
            pending_requests = pd.read_sql(
                "SELECT COUNT(*) FROM vacation_requests WHERE status = 'pending'", 
                conn
            ).iloc[0,0]
            st.metric("الطلبات المعلقة", pending_requests)
        
        st.subheader("طلبات الإجازة خلال السنة")
        
        monthly_requests = pd.read_sql('''
            SELECT strftime('%Y-%m', created_date) as month, 
                   COUNT(*) as request_count,
               SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count
            FROM vacation_requests 
            WHERE strftime('%Y', created_date) = ?
            GROUP BY strftime('%Y-%m', created_date)
            ORDER BY month
        ''', conn, params=(str(date.today().year),))
        
        if not monthly_requests.empty:
            st.line_chart(monthly_requests.set_index('month')[['request_count', 'approved_count']])
        else:
            st.info("لا توجد بيانات للعرض")
    
    with tab2:
        st.subheader("تقارير تفصيلية للإجازات")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("من تاريخ", value=date.today().replace(month=1, day=1))
            end_date = st.date_input("إلى تاريخ", value=date.today())
        
        with col2:
            report_type = st.selectbox("نوع التقرير", [
                "جميع الطلبات",
                "الطلبات المعتمدة فقط", 
                "الطلبات المرفوضة فقط",
                "الطلبات المعلقة فقط"
            ])
            
            department_filter = st.selectbox("القسم", ["الكل"] + [
                "الإدارة العامة", "الشؤون الإدارية", "شؤون الموظفين", 
                "الأمن والسلامة", "التشغيل", "الصيانة", 
                "الجودة", "المالية", "التجارية", "خدمات الركاب"
            ])
        
        if st.button("إنشاء التقرير", use_container_width=True):
            query = '''
                SELECT vr.*, e.name as employee_name, e.department,
                       e.position, dm.name as manager_name
                FROM vacation_requests vr
                JOIN employees e ON vr.employee_id = e.employee_id
                LEFT JOIN employees dm ON e.direct_manager_id = dm.employee_id
                WHERE vr.created_date BETWEEN ? AND ?
            '''
            
            params = [start_date, end_date]
            
            if report_type != "جميع الطلبات":
                status_map = {
                    "الطلبات المعتمدة فقط": "approved",
                    "الطلبات المرفوضة فقط": "rejected", 
                    "الطلبات المعلقة فقط": "pending"
                }
                query += " AND vr.status = ?"
                params.append(status_map[report_type])
            
            if department_filter != "الكل":
                query += " AND e.department = ?"
                params.append(department_filter)
            
            query += " ORDER BY vr.created_date DESC"
            
            report_df = pd.read_sql(query, conn, params=params)
            
            if not report_df.empty:
                report_display = report_df.copy()
                report_display['الحالة'] = report_display['status'].apply(
                    lambda x: '🟢 معتمدة' if x == 'approved' else 
                             '🔴 مرفوضة' if x == 'rejected' else '🟡 قيد المراجعة'
                )
                
                st.dataframe(
                    report_display[[
                        'employee_name', 'department', 'vacation_type',
                        'start_date', 'end_date', 'days_count', 'الحالة',
                        'manager_name', 'created_date'
                    ]],
                    use_container_width=True
                )
                
                csv = report_display.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "📥 تصدير التقرير كـ CSV",
                    data=csv,
                    file_name=f"تقرير_الإجازات_{start_date}_إلى_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("لا توجد بيانات تطابق معايير البحث")
    
    with tab3:
        st.subheader("إحصائيات الأقسام")
        
        dept_stats = pd.read_sql('''
            SELECT e.department,
                   COUNT(DISTINCT e.employee_id) as employee_count,
                   COUNT(vr.id) as total_requests,
                   SUM(CASE WHEN vr.status = 'approved' THEN 1 ELSE 0 END) as approved_requests,
                   SUM(CASE WHEN vr.status = 'pending' THEN 1 ELSE 0 END) as pending_requests,
                   AVG(CASE WHEN vr.status = 'approved' THEN vr.days_count ELSE 0 END) as avg_days
            FROM employees e
            LEFT JOIN vacation_requests vr ON e.employee_id = vr.employee_id
            WHERE e.is_active = 1
            GROUP BY e.department
            ORDER BY total_requests DESC
        ''', conn)
        
        if not dept_stats.empty:
            st.dataframe(dept_stats, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("الطلبات حسب القسم")
                st.bar_chart(dept_stats.set_index('department')['total_requests'])
            
            with col2:
                st.subheader("متوسط أيام الإجازة")
                st.bar_chart(dept_stats.set_index('department')['avg_days'])
        else:
            st.info("لا توجد بيانات إحصائية")
    
    with tab4:
        st.subheader("تقارير مخصصة")
        
        st.info("""
        **التقارير المتاحة:**
        - تقرير الموظفين بدون طلبات إجازة
        - تقرير أرصدة الإجازات المنخفضة
        - تقرير الطلبات خلال إجازات الأعياد
        """)
        
        custom_report = st.selectbox("اختر التقرير", [
            "الموظفين بدون طلبات إجازة",
            "أرصدة الإجازات المنخفضة",
            "الطلبات خلال إجازات الأعياد"
        ])
        
        if st.button("إنشاء التقرير المخصص", use_container_width=True):
            if custom_report == "الموظفين بدون طلبات إجازة":
                no_requests_df = pd.read_sql('''
                    SELECT e.employee_id, e.name, e.department, e.position, e.hire_date
                    FROM employees e
                    LEFT JOIN vacation_requests vr ON e.employee_id = vr.employee_id
                    WHERE e.is_active = 1 AND vr.id IS NULL
                    ORDER BY e.hire_date DESC
                ''', conn)
                
                if not no_requests_df.empty:
                    st.dataframe(no_requests_df, use_container_width=True)
                else:
                    st.success("🎉 جميع الموظفين قدموا طلبات إجازة على الأقل مرة واحدة")
            
            elif custom_report == "أرصدة الإجازات المنخفضة":
                low_balance_df = pd.read_sql('''
                    SELECT e.employee_id, e.name, e.department, e.position,
                           vb.regular_balance, vb.sick_balance, vb.emergency_balance
                    FROM employees e
                    JOIN vacation_balances vb ON e.employee_id = vb.employee_id
                    WHERE vb.year = ? AND vb.status = 'approved'
                    AND (vb.regular_balance < 7 OR vb.sick_balance < 7 OR vb.emergency_balance < 3)
                    ORDER BY vb.regular_balance ASC
                ''', conn, params=(date.today().year,))
                
                if not low_balance_df.empty:
                    st.warning("⚠️ الموظفين ذوي الأرصدة المنخفضة")
                    st.dataframe(low_balance_df, use_container_width=True)
                else:
                    st.success("🎉 لا توجد أرصدة منخفضة")
    
    conn.close()

def show_audit_logs():
    """سجلات النظام"""
    if not check_permission('admin'):
        st.error("❌ غير مصرح لك بالوصول لهذه الصفحة")
        return
    
    st.header("📋 سجلات النظام")
    
    conn = init_database()
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_filter = st.selectbox("الفترة", [
            "آخر 7 أيام", "آخر 30 يوم", "آخر 90 يوم", "السنة الحالية", "الكل"
        ])
    
    with col2:
        action_filter = st.selectbox("نوع الإجراء", [
            "الكل", "تسجيل دخول", "طلب إجازة", "موافقة", "رفض", "إنشاء حساب"
        ])
    
    query = '''
        SELECT al.*, u.username, e.name as user_name
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        LEFT JOIN employees e ON u.employee_id = e.employee_id
        WHERE 1=1
    '''
    
    params = []
    
    if days_filter != "الكل":
        if days_filter == "آخر 7 أيام":
            date_filter = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        elif days_filter == "آخر 30 يوم":
            date_filter = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif days_filter == "آخر 90 يوم":
            date_filter = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        else:
            date_filter = date.today().replace(month=1, day=1).strftime('%Y-%m-%d')
        
        query += " AND al.created_date >= ?"
        params.append(date_filter)
    
    if action_filter != "الكل":
        action_map = {
            "تسجيل دخول": "login",
            "طلب إجازة": "vacation_request", 
            "موافقة": "approval",
            "رفض": "rejection",
            "إنشاء حساب": "user_creation"
        }
        query += " AND al.action = ?"
        params.append(action_map[action_filter])
    
    query += " ORDER BY al.created_date DESC"
    
    logs_df = pd.read_sql(query, conn, params=params)
    
    if not logs_df.empty:
        st.dataframe(
            logs_df[['created_date', 'user_name', 'username', 'action', 'details', 'ip_address']],
            use_container_width=True
        )
        
        st.subheader("إحصائيات السجلات")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_logs = len(logs_df)
            st.metric("إجمالي السجلات", total_logs)
        
        with col2:
            unique_users = logs_df['user_id'].nunique()
            st.metric("عدد المستخدمين", unique_users)
        
        with col3:
            most_common_action = logs_df['action'].mode()[0] if not logs_df.empty else "لا يوجد"
            st.metric("أكثر إجراء", most_common_action)
    
    else:
        st.info("لا توجد سجلات تطابق معايير البحث")
    
    conn.close()

def show_notifications():
    """عرض الإشعارات"""
    st.header("🔔 الإشعارات")
    
    conn = init_database()
    
    notifications_df = pd.read_sql('''
        SELECT id, title, message, is_read, created_date
        FROM notifications 
        WHERE user_id = ?
        ORDER BY created_date DESC
    ''', conn, params=(st.session_state.user['id'],))
    
    if notifications_df.empty:
        st.info("🎉 لا توجد إشعارات جديدة")
    else:
        unread_count = len(notifications_df[notifications_df['is_read'] == 0])
        
        if unread_count > 0:
            st.success(f"لديك {unread_count} إشعار غير مقروء")
        
        for _, notification in notifications_df.iterrows():
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    if notification['is_read'] == 0:
                        st.markdown(f"### 🔵 {notification['title']}")
                    else:
                        st.markdown(f"### ⚪ {notification['title']}")
                    
                    st.write(notification['message'])
                    st.caption(f"📅 {notification['created_date']}")
                
                with col2:
                    if notification['is_read'] == 0:
                        if st.button("تم القراءة", key=f"read_{notification['id']}", use_container_width=True):
                            conn.execute('''
                                UPDATE notifications 
                                SET is_read = 1 
                                WHERE id = ?
                            ''', (notification['id'],))
                            conn.commit()
                            st.rerun()
        
        if unread_count > 0:
            if st.button("标记 الكل كمقروء", use_container_width=True):
                conn.execute('''
                    UPDATE notifications 
                    SET is_read = 1 
                    WHERE user_id = ? AND is_read = 0
                ''', (st.session_state.user['id'],))
                conn.commit()
                st.success("✅ تم标记 جميع الإشعارات كمقروءة")
                st.rerun()
    
    conn.close()

def initialize_sample_data():
    """تهيئة بيانات نموذجية للنظام"""
    conn = init_database()
    
    employees_count = pd.read_sql("SELECT COUNT(*) FROM employees", conn).iloc[0,0]
    
    if employees_count > 0:
        conn.close()
        return
    
    st.info("🔧 جاري تهيئة البيانات النموذجية للنظام...")
    
    try:
        sample_employees = [
            ('ADM001', 'أحمد محمد علي', 'الإدارة العامة', 'مدير عام', None, '2020-01-01'),
            ('ADM002', 'فاطمة خالد حسن', 'الشؤون الإدارية', 'مدير شؤون الموظفين', 'ADM001', '2020-02-01'),
            ('MGR001', 'خالد عبدالله سالم', 'التشغيل', 'مدير التشغيل', 'ADM001', '2020-03-01'),
            ('MGR002', 'سارة عبدالرحمن', 'خدمات الركاب', 'مدير الخدمات', 'ADM001', '2020-03-15'),
            ('EMP001', 'محمد إبراهيم كامل', 'التشغيل', 'مهندس تشغيل', 'MGR001', '2021-01-15'),
            ('EMP002', 'لينا مصطفى أحمد', 'خدمات الركاب', 'مساعد ركاب', 'MGR002', '2021-02-01'),
            ('EMP003', 'يوسف حمزة علي', 'الأمن والسلامة', 'ضابط أمن', 'MGR001', '2021-03-01'),
            ('EMP004', 'هدى عمر عبدالله', 'المالية', 'محاسب', 'ADM002', '2021-04-01'),
        ]
        
        for emp in sample_employees:
            conn.execute('''
                INSERT OR IGNORE INTO employees 
                (employee_id, name, department, position, direct_manager_id, hire_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', emp)
        
        sample_users = [
            ('admin', 'ADM001', 'admin', 'admin123'),
            ('admin2', 'ADM002', 'admin_officer', 'admin123'),
            ('mgr1', 'MGR001', 'direct_manager', 'mgr123'),
            ('mgr2', 'MGR002', 'direct_manager', 'mgr123'),
            ('emp1', 'EMP001', 'employee', 'emp123'),
            ('emp2', 'EMP002', 'employee', 'emp123'),
            ('emp3', 'EMP003', 'employee', 'emp123'),
            ('emp4', 'EMP004', 'employee', 'emp123'),
        ]
        
        for username, emp_id, role, password in sample_users:
            hashed_password, salt = hash_password(password)
            conn.execute('''
                INSERT OR IGNORE INTO users 
                (username, password_hash, salt, employee_id, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, hashed_password, salt, emp_id, role))
        
        current_year = date.today().year
        sample_balances = [
            ('EMP001', current_year, 21, 30, 7, 0, 'approved', 'ADM002'),
            ('EMP002', current_year, 21, 30, 7, 0, 'approved', 'ADM002'),
            ('EMP003', current_year, 21, 30, 7, 0, 'approved', 'ADM002'),
            ('EMP004', current_year, 21, 30, 7, 0, 'approved', 'ADM002'),
        ]
        
        for balance in sample_balances:
            conn.execute('''
                INSERT OR IGNORE INTO vacation_balances 
                (employee_id, year, regular_balance, sick_balance, emergency_balance, other_balance, status, approved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', balance)
        
        conn.commit()
        st.success("✅ تم تهيئة البيانات النموذجية بنجاح!")
        
    except Exception as e:
        st.error(f"❌ خطأ في تهيئة البيانات: {str(e)}")
    
    conn.close()

def main():
    """الدالة الرئيسية لتشغيل النظام"""
    initialize_sample_data()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_interface()
    else:
        main_interface()






