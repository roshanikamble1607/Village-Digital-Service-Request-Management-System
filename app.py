"""
Village Digital Service & Request Management System
BCA Mini Project - Flask Application Entry Point
Citizen Authentication & Village Services Application & Officer Management Module
"""

import os
import re
import time
import random
import csv
import io
from functools import wraps
import pymysql
import pymysql.cursors
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
    Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config

# Initialize Flask application
app = Flask(__name__)

# Load configuration settings from config.py
app.config.from_object(Config)

# Document Upload Configurations
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==============================================================
# Service Catalog & Allowed Categories (Requirement 2)
# ==============================================================
SERVICE_CATEGORIES = {
    "Certificate Requests": [
        "Residence Certificate",
        "Income Certificate",
        "Birth Certificate",
        "Death Certificate",
        "Caste Certificate",
        "Other Certificate"
    ],
    "Village Problems": [
        "Water Supply",
        "Streetlight Repair",
        "Road Repair",
        "Garbage Collection",
        "Drainage Problem",
        "Other Village Problem"
    ],
    "Other Services": [
        "Document Request",
        "Local Report Request",
        "Other Service Request"
    ]
}

# Status Definitions (Requirement 8)
STATUS_VALUES = [
    'Submitted',
    'Under Review',
    'Documents Required',
    'Approved',
    'Rejected',
    'Completed'
]


# ==============================================================
# Database Helper Function
# ==============================================================
def get_db_connection():
    """
    Establishes and returns a connection to the MySQL database.
    Returns None if connection fails to allow graceful error handling.
    """
    try:
        connection = pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            port=app.config['MYSQL_PORT'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return connection
    except pymysql.MySQLError as err:
        app.logger.error(f"Database Connection Error: {err}")
        return None


# ==============================================================
# Authentication Decorators
# ==============================================================
def login_required(f):
    """
    Decorator to restrict access to authenticated citizens only.
    Redirects unauthenticated visitors to the citizen login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def officer_required(f):
    """
    Decorator to restrict access to authenticated officers/Gram Sevaks only.
    Redirects unauthenticated visitors to the officer login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('officer_id'):
            flash("Please sign in with officer credentials to access the administrative portal.", "warning")
            return redirect(url_for('officer_login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================
# Helper Functions
# ==============================================================
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
MOBILE_REGEX = re.compile(r"^[0-9]{10}$")

def allowed_file(filename):
    """Check if uploaded file has an allowed extension (PDF, JPG, JPEG, PNG)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_application_number(cursor):
    """Generate a unique application number formatted like VSS-2026-XXXXXX."""
    year = time.strftime('%Y')
    while True:
        random_digits = ''.join(random.choices('0123456789', k=6))
        app_num = f"VSS-{year}-{random_digits}"
        cursor.execute("SELECT id FROM applications WHERE application_number = %s", (app_num,))
        if not cursor.fetchone():
            return app_num


# ==============================================================
# Error Handlers
# ==============================================================
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle uploads that exceed the 5 MB file size limit."""
    flash("The uploaded file exceeds the 5 MB maximum size limit. Please choose a smaller file.", "error")
    return redirect(request.url or url_for('dashboard'))


# ==============================================================
# Public & Citizen Authentication Routes
# ==============================================================

@app.route('/')
def home():
    """Home page route with latest public announcements."""
    db = get_db_connection()
    notices_list = []
    if db:
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, category, content, posted_by, created_at 
                    FROM notices 
                    WHERE is_active = 1 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                notices_list = cursor.fetchall()
        except pymysql.MySQLError as err:
            app.logger.error(f"Error fetching home notices: {err}")
        finally:
            db.close()

    return render_template('index.html', notices=notices_list)


@app.route('/notices')
def notices():
    """
    Public Village Notices & Announcements Board.
    Open to all citizens and visitors to view official Gram Panchayat announcements.
    """
    db = get_db_connection()
    notices_list = []
    if db:
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, category, content, posted_by, created_at 
                    FROM notices 
                    WHERE is_active = 1 
                    ORDER BY created_at DESC
                """)
                notices_list = cursor.fetchall()
        except pymysql.MySQLError as err:
            app.logger.error(f"Error fetching notices: {err}")
            flash("Could not load notices at this time.", "error")
        finally:
            db.close()

    return render_template('notices.html', notices=notices_list)


@app.route('/track', methods=['GET', 'POST'])
def track_application():
    """
    Public Application Tracking Route.
    Allows citizens and visitors to check live application status using their tracking number.
    """
    search_number = ''
    app_record = None

    if request.method == 'POST':
        search_number = request.form.get('application_number', '').strip().upper()
    elif request.args.get('app_num'):
        search_number = request.args.get('app_num', '').strip().upper()

    if search_number:
        db = get_db_connection()
        if db:
            try:
                with db.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, application_number, service_category, service_type,
                               subject, applicant_name, status, officer_remarks, created_at, updated_at
                        FROM applications
                        WHERE application_number = %s
                    """, (search_number,))
                    app_record = cursor.fetchone()
            except pymysql.MySQLError as err:
                app.logger.error(f"Error tracking application: {err}")
            finally:
                db.close()

    return render_template('track.html', app=app_record, search_number=search_number)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Citizen Registration Route."""
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        mobile = request.form.get('mobile', '').strip()
        village_name = request.form.get('village_name', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not all([full_name, email, mobile, village_name, address, password, confirm_password]):
            flash("All fields marked with an asterisk (*) are required.", "error")
            return render_template('register.html')

        if len(full_name) < 3:
            flash("Full Name must contain at least 3 characters.", "error")
            return render_template('register.html')

        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address.", "error")
            return render_template('register.html')

        if not MOBILE_REGEX.match(mobile):
            flash("Please enter a valid 10-digit mobile number.", "error")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter carefully.", "error")
            return render_template('register.html')

        db = get_db_connection()
        if not db:
            flash("Database connection error. Please verify MySQL service is running.", "error")
            return render_template('register.html')

        try:
            with db.cursor() as cursor:
                # Duplicate email check
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash("This email address is already registered. Please log in or use another email.", "error")
                    return render_template('register.html')

                # Duplicate mobile check
                cursor.execute("SELECT id FROM users WHERE mobile = %s", (mobile,))
                if cursor.fetchone():
                    flash("This mobile number is already registered. Please use another mobile number.", "error")
                    return render_template('register.html')

                password_hash = generate_password_hash(password)
                insert_query = """
                    INSERT INTO users (full_name, email, mobile, password_hash, address, village_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_query,
                    (full_name, email, mobile, password_hash, address, village_name)
                )

            flash("Registration successful! Please sign in with your email/mobile and password.", "success")
            return redirect(url_for('login'))

        except pymysql.MySQLError as err:
            app.logger.error(f"Error during citizen registration: {err}")
            flash("An error occurred while creating your account. Please try again.", "error")
            return render_template('register.html')
        finally:
            db.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Citizen Login Route."""
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip().lower()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash("Please enter both your email/mobile and password.", "error")
            return render_template('login.html')

        db = get_db_connection()
        if not db:
            flash("Database connection error. Please verify MySQL service is running.", "error")
            return render_template('login.html')

        try:
            with db.cursor() as cursor:
                query = """
                    SELECT id, full_name, email, mobile, password_hash, village_name, is_active
                    FROM users
                    WHERE email = %s OR mobile = %s
                """
                cursor.execute(query, (login_id, login_id))
                user = cursor.fetchone()

                if not user or not check_password_hash(user['password_hash'], password):
                    flash("Invalid email/mobile or password. Please try again.", "error")
                    return render_template('login.html')

                if not user['is_active']:
                    flash("Your citizen account is currently inactive. Please contact the village administrator.", "error")
                    return render_template('login.html')

                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['full_name']
                session['user_email'] = user['email']
                session['village_name'] = user['village_name']

                flash(f"Welcome back, {user['full_name']}!", "success")

                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('dashboard'))

        except pymysql.MySQLError as err:
            app.logger.error(f"Error during citizen login: {err}")
            flash("A database error occurred. Please try again.", "error")
            return render_template('login.html')
        finally:
            db.close()

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Citizen Dashboard Route (Protected).
    Displays dynamic counts for total applications, complaints, pending, and completed requests.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return render_template(
            'dashboard.html',
            total_applications=0,
            total_complaints=0,
            pending_requests=0,
            completed_requests=0,
            recent_applications=[]
        )

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            # 1. Total Applications
            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE user_id = %s", (user_id,))
            total_applications = cursor.fetchone()['cnt']

            # 2. Total Complaints (Village Problems)
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM applications WHERE user_id = %s AND service_category = 'Village Problems'",
                (user_id,)
            )
            total_complaints = cursor.fetchone()['cnt']

            # 3. Pending Requests
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM applications WHERE user_id = %s AND status IN ('Submitted', 'Under Review', 'Documents Required')",
                (user_id,)
            )
            pending_requests = cursor.fetchone()['cnt']

            # 4. Completed Requests
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM applications WHERE user_id = %s AND status IN ('Approved', 'Completed')",
                (user_id,)
            )
            completed_requests = cursor.fetchone()['cnt']

            # 5. Recent Submissions (Latest 5)
            cursor.execute("""
                SELECT id, application_number, service_category, service_type, status, created_at
                FROM applications
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (user_id,))
            recent_applications = cursor.fetchall()

        return render_template(
            'dashboard.html',
            total_applications=total_applications,
            total_complaints=total_complaints,
            pending_requests=pending_requests,
            completed_requests=completed_requests,
            recent_applications=recent_applications
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error loading dashboard: {err}")
        return render_template(
            'dashboard.html',
            total_applications=0,
            total_complaints=0,
            pending_requests=0,
            completed_requests=0,
            recent_applications=[]
        )
    finally:
        db.close()


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Citizen Profile Route (Protected)."""
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('dashboard'))

    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            village_name = request.form.get('village_name', '').strip()
            address = request.form.get('address', '').strip()

            if not all([full_name, village_name, address]):
                flash("Full Name, Village, and Address cannot be empty.", "error")
            elif len(full_name) < 3:
                flash("Full Name must contain at least 3 characters.", "error")
            else:
                with db.cursor() as cursor:
                    update_query = """
                        UPDATE users
                        SET full_name = %s, village_name = %s, address = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (full_name, village_name, address, session['user_id']))

                session['user_name'] = full_name
                session['village_name'] = village_name
                flash("Your profile has been updated successfully!", "success")

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, full_name, email, mobile, address, village_name, created_at, is_active FROM users WHERE id = %s",
                (session['user_id'],)
            )
            user = cursor.fetchone()

        if not user:
            flash("Citizen account not found.", "error")
            return redirect(url_for('logout'))

        return render_template('profile.html', user=user)

    except pymysql.MySQLError as err:
        app.logger.error(f"Error handling citizen profile: {err}")
        flash("An error occurred while accessing your profile.", "error")
        return redirect(url_for('dashboard'))
    finally:
        db.close()


@app.route('/logout')
def logout():
    """Citizen Logout Route."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))


# ==============================================================
# Village Services & Applications Routes (Citizen Side)
# ==============================================================

@app.route('/services')
def services():
    """
    Available Village Services Directory Route.
    Lists all services categorized into Certificates, Problems, and Other Services.
    """
    return render_template('services.html', categories=SERVICE_CATEGORIES)


@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    """
    Service Application Submission Route.
    Handles form inputs, validations, file uploads, and unique application number generation.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT full_name, mobile, address, village_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

        if request.method == 'POST':
            service_category = request.form.get('service_category', '').strip()
            service_type = request.form.get('service_type', '').strip()
            subject = request.form.get('subject', '').strip()
            description = request.form.get('description', '').strip()
            applicant_name = request.form.get('applicant_name', '').strip()
            mobile = request.form.get('mobile', '').strip()
            address = request.form.get('address', '').strip()

            # Server-Side Validations
            if not all([service_category, service_type, subject, description, applicant_name, mobile, address]):
                flash("All fields marked with an asterisk (*) are required.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            if service_category not in SERVICE_CATEGORIES:
                flash("Please select a valid service category.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            if service_type not in SERVICE_CATEGORIES[service_category]:
                flash("Please select a valid service type for the selected category.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            if len(subject) < 3:
                flash("Subject must contain at least 3 characters.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            if len(description) < 10:
                flash("Description must be at least 10 characters long to provide sufficient detail.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            if not MOBILE_REGEX.match(mobile):
                flash("Please enter a valid 10-digit mobile number.", "error")
                return render_template(
                    'apply.html',
                    categories=SERVICE_CATEGORIES,
                    user=user,
                    form_data=request.form,
                    selected_category=service_category,
                    selected_type=service_type
                )

            # Optional Supporting Document File Upload Handling
            uploaded_file = request.files.get('document')
            file_record = None
            if uploaded_file and uploaded_file.filename != '':
                if not allowed_file(uploaded_file.filename):
                    flash("Invalid file format. Only PDF, JPG, JPEG, and PNG files are allowed.", "error")
                    return render_template(
                        'apply.html',
                        categories=SERVICE_CATEGORIES,
                        user=user,
                        form_data=request.form,
                        selected_category=service_category,
                        selected_type=service_type
                    )

                original_filename = secure_filename(uploaded_file.filename)
                unique_filename = f"{int(time.time())}_{random.randint(1000, 9999)}_{original_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                uploaded_file.save(file_path)
                file_size = os.path.getsize(file_path)
                file_record = {
                    'file_name': unique_filename,
                    'original_name': original_filename,
                    'file_size': file_size
                }

            # Insert application record into MySQL
            with db.cursor() as cursor:
                app_number = generate_application_number(cursor)
                insert_sql = """
                    INSERT INTO applications (
                        application_number, user_id, service_category, service_type,
                        subject, description, applicant_name, mobile, address, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Submitted')
                """
                cursor.execute(insert_sql, (
                    app_number, user_id, service_category, service_type,
                    subject, description, applicant_name, mobile, address
                ))
                app_id = cursor.lastrowid

                # Associate uploaded document if present
                if file_record:
                    doc_sql = """
                        INSERT INTO application_documents (
                            application_id, user_id, file_name, original_name, file_size
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(doc_sql, (
                        app_id, user_id, file_record['file_name'],
                        file_record['original_name'], file_record['file_size']
                    ))

            flash(f"Application submitted successfully! Your Application Number is: {app_number}", "success")
            return redirect(url_for('application_detail', application_id=app_id))

        # GET request handling
        preselected_category = request.args.get('category', '')
        preselected_type = request.args.get('type', '')
        return render_template(
            'apply.html',
            categories=SERVICE_CATEGORIES,
            user=user,
            form_data={},
            selected_category=preselected_category,
            selected_type=preselected_type
        )

    except pymysql.MySQLError as err:
        app.logger.error(f"Error in application submission: {err}")
        flash("A database error occurred while submitting your application.", "error")
        return redirect(url_for('dashboard'))
    finally:
        db.close()


@app.route('/my-applications')
@login_required
def my_applications():
    """
    My Applications Route.
    Displays list of all applications submitted by the logged-in citizen.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, application_number, service_category, service_type, subject, status, created_at
                FROM applications
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            applications = cursor.fetchall()

        return render_template('my_applications.html', applications=applications)
    except pymysql.MySQLError as err:
        app.logger.error(f"Error fetching user applications: {err}")
        flash("Could not retrieve your applications.", "error")
        return redirect(url_for('dashboard'))
    finally:
        db.close()


@app.route('/application/<int:application_id>')
@login_required
def application_detail(application_id):
    """
    Application Details Route.
    Shows comprehensive request information, officer remarks, and document attachments.
    Enforces citizen ownership check.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('my_applications'))

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM applications WHERE id = %s", (application_id,))
            application = cursor.fetchone()

            if not application:
                flash("Application not found.", "error")
                return redirect(url_for('my_applications'))

            # Ownership security check
            if application['user_id'] != user_id:
                flash("Unauthorized access: You cannot view another citizen's application.", "error")
                return redirect(url_for('my_applications'))

            # Fetch attached supporting documents
            cursor.execute("""
                SELECT id, file_name, original_name, file_size, uploaded_at
                FROM application_documents
                WHERE application_id = %s
                ORDER BY uploaded_at DESC
            """, (application_id,))
            documents = cursor.fetchall()

        return render_template('application_detail.html', app=application, documents=documents)
    except pymysql.MySQLError as err:
        app.logger.error(f"Error loading application details: {err}")
        flash("Error retrieving application details.", "error")
        return redirect(url_for('my_applications'))
    finally:
        db.close()


@app.route('/application/<int:application_id>/upload', methods=['POST'])
@login_required
def upload_application_document(application_id):
    """
    Upload Supporting Document for an Application Route.
    Allows citizens to upload extra verification files to an existing application.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('application_detail', application_id=application_id))

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, user_id FROM applications WHERE id = %s", (application_id,))
            application = cursor.fetchone()

            if not application or application['user_id'] != user_id:
                flash("Unauthorized access to this application.", "error")
                return redirect(url_for('my_applications'))

        uploaded_file = request.files.get('document')
        if not uploaded_file or uploaded_file.filename == '':
            flash("Please select a file to upload.", "error")
            return redirect(url_for('application_detail', application_id=application_id))

        if not allowed_file(uploaded_file.filename):
            flash("Invalid file format. Only PDF, JPG, JPEG, and PNG files are allowed.", "error")
            return redirect(url_for('application_detail', application_id=application_id))

        original_filename = secure_filename(uploaded_file.filename)
        unique_filename = f"{int(time.time())}_{random.randint(1000, 9999)}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        uploaded_file.save(file_path)
        file_size = os.path.getsize(file_path)

        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO application_documents (
                    application_id, user_id, file_name, original_name, file_size
                ) VALUES (%s, %s, %s, %s, %s)
            """, (application_id, user_id, unique_filename, original_filename, file_size))

        flash("Supporting document uploaded successfully!", "success")
        return redirect(url_for('application_detail', application_id=application_id))

    except pymysql.MySQLError as err:
        app.logger.error(f"Error uploading document: {err}")
        flash("An error occurred while uploading the document.", "error")
        return redirect(url_for('application_detail', application_id=application_id))
    finally:
        db.close()


@app.route('/document/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    """
    Secure Document Download / View Route for Citizens.
    Ensures a citizen cannot access another citizen's uploaded files.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('my_applications'))

    user_id = session['user_id']
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT file_name, original_name, user_id
                FROM application_documents
                WHERE id = %s
            """, (doc_id,))
            doc = cursor.fetchone()

        if not doc or doc['user_id'] != user_id:
            flash("Unauthorized: You do not have permission to access this document.", "error")
            return redirect(url_for('my_applications'))

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            doc['file_name'],
            as_attachment=False,
            download_name=doc['original_name']
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error downloading document: {err}")
        flash("Could not access document.", "error")
        return redirect(url_for('my_applications'))
    finally:
        db.close()


@app.route('/application/<int:application_id>/certificate')
def view_certificate(application_id):
    """
    Official Certificate & Acknowledgement Slip Generator & Print View.
    Allows logged-in citizens (application owners) and administrative officers
    to generate and print official Gram Panchayat certificates or acknowledgement slips.
    """
    user_id = session.get('user_id')
    officer_id = session.get('officer_id')

    if not user_id and not officer_id:
        flash("Please log in to view or download certificates.", "error")
        return redirect(url_for('login'))

    db = get_db_connection()
    if not db:
        flash("Database connection error. Please verify MySQL service is running.", "error")
        return redirect(url_for('dashboard' if user_id else 'officer_dashboard'))

    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM applications WHERE id = %s", (application_id,))
            application = cursor.fetchone()

            if not application:
                flash("Application record not found.", "error")
                return redirect(url_for('my_applications' if user_id else 'officer_applications'))

            # Security: Citizens can only access their own application certificate
            if user_id and application['user_id'] != user_id:
                flash("Unauthorized access: You can only view certificates for your own applications.", "error")
                return redirect(url_for('my_applications'))

            cursor.execute("""
                SELECT full_name, email, mobile, village_name, address 
                FROM users 
                WHERE id = %s
            """, (application['user_id'],))
            citizen = cursor.fetchone()

        return render_template('certificate.html', app=application, citizen=citizen)

    except pymysql.MySQLError as err:
        app.logger.error(f"Error loading certificate view: {err}")
        flash("An error occurred while generating the certificate.", "error")
        return redirect(url_for('my_applications' if user_id else 'officer_applications'))
    finally:
        db.close()


# ==============================================================
# Gram Sevak / Officer Administrative Panel Routes
# ==============================================================

@app.route('/officer/login', methods=['GET', 'POST'])
def officer_login():
    """
    Officer Login Route.
    Authenticates Gram Sevak and administrative staff.
    """
    if session.get('officer_id'):
        return redirect(url_for('officer_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both officer email and password.", "error")
            return render_template('officer_login.html')

        db = get_db_connection()
        if not db:
            flash("Database connection error. Please verify MySQL service is running.", "error")
            return render_template('officer_login.html')

        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT id, full_name, email, designation, village_name, password_hash, is_active
                    FROM officers
                    WHERE email = %s
                """, (email,))
                officer = cursor.fetchone()

                if not officer or not check_password_hash(officer['password_hash'], password):
                    flash("Invalid officer credentials. Please check your email and password.", "error")
                    return render_template('officer_login.html')

                if not officer['is_active']:
                    flash("Your officer account has been deactivated. Please contact the district admin.", "error")
                    return render_template('officer_login.html')

                # Set officer session
                session.clear()
                session['officer_id'] = officer['id']
                session['officer_name'] = officer['full_name']
                session['officer_email'] = officer['email']
                session['officer_designation'] = officer['designation']
                session['officer_village'] = officer['village_name']
                session['role'] = 'officer'

                flash(f"Welcome to Administration Portal, {officer['full_name']}!", "success")
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/officer'):
                    return redirect(next_page)
                return redirect(url_for('officer_dashboard'))

        except pymysql.MySQLError as err:
            app.logger.error(f"Error during officer login: {err}")
            flash("A database error occurred. Please try again.", "error")
            return render_template('officer_login.html')
        finally:
            db.close()

    return render_template('officer_login.html')


@app.route('/officer/logout')
def officer_logout():
    """Officer Logout Route."""
    session.clear()
    flash("Officer session closed successfully.", "info")
    return redirect(url_for('officer_login'))


@app.route('/officer/dashboard')
@officer_required
def officer_dashboard():
    """
    Officer Dashboard Route.
    Displays global administration stats and recent applications requiring action.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('home'))

    try:
        with db.cursor() as cursor:
            # Metrics
            cursor.execute("SELECT COUNT(*) AS cnt FROM applications")
            total_applications = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE status IN ('Submitted', 'Under Review', 'Documents Required')")
            pending_applications = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE status = 'Approved'")
            approved_applications = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE status = 'Rejected'")
            rejected_applications = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE status = 'Completed'")
            completed_applications = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE service_category = 'Certificate Requests'")
            certificates_count = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE service_category = 'Village Problems'")
            problems_count = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM applications WHERE service_category = 'Other Services'")
            other_count = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            total_citizens = cursor.fetchone()['cnt']

            # Recent applications in queue
            cursor.execute("""
                SELECT id, application_number, applicant_name, mobile, service_category, service_type, status, created_at
                FROM applications
                ORDER BY 
                    CASE 
                        WHEN status = 'Submitted' THEN 1
                        WHEN status = 'Under Review' THEN 2
                        WHEN status = 'Documents Required' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT 8
            """)
            recent_applications = cursor.fetchall()

        return render_template(
            'officer_dashboard.html',
            total_applications=total_applications,
            pending_applications=pending_applications,
            approved_applications=approved_applications,
            rejected_applications=rejected_applications,
            completed_applications=completed_applications,
            certificates_count=certificates_count,
            problems_count=problems_count,
            other_count=other_count,
            total_citizens=total_citizens,
            recent_applications=recent_applications
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error in officer dashboard: {err}")
        flash("Could not fetch administrative metrics.", "error")
        return redirect(url_for('home'))
    finally:
        db.close()


@app.route('/officer/applications')
@officer_required
def officer_applications():
    """
    Officer Applications Master List.
    Supports multi-criteria filtering by category, status, and free-text search.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_dashboard'))

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()

    try:
        query = """
            SELECT id, application_number, applicant_name, mobile, service_category,
                   service_type, subject, status, created_at
            FROM applications
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (application_number LIKE %s OR applicant_name LIKE %s OR mobile LIKE %s OR subject LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        if category:
            query += " AND service_category = %s"
            params.append(category)

        if status:
            if status == 'Pending':
                query += " AND status IN ('Submitted', 'Under Review', 'Documents Required')"
            else:
                query += " AND status = %s"
                params.append(status)

        query += " ORDER BY created_at DESC"

        with db.cursor() as cursor:
            cursor.execute(query, tuple(params))
            applications = cursor.fetchall()

        return render_template(
            'officer_applications.html',
            applications=applications,
            current_search=search,
            current_category=category,
            current_status=status
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error fetching officer applications: {err}")
        flash("Could not retrieve applications.", "error")
        return redirect(url_for('officer_dashboard'))
    finally:
        db.close()


@app.route('/officer/application/<int:application_id>', methods=['GET', 'POST'])
@officer_required
def officer_application_detail(application_id):
    """
    Officer Review & Status Action Route.
    Allows inspecting citizen proofs and modifying application status and remarks.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_applications'))

    try:
        if request.method == 'POST':
            new_status = request.form.get('status', '').strip()
            officer_remarks = request.form.get('officer_remarks', '').strip()

            if new_status not in STATUS_VALUES:
                flash("Invalid status value selected.", "error")
            else:
                with db.cursor() as cursor:
                    update_sql = """
                        UPDATE applications
                        SET status = %s, officer_remarks = %s, updated_at = NOW()
                        WHERE id = %s
                    """
                    cursor.execute(update_sql, (new_status, officer_remarks or None, application_id))
                flash(f"Application #{application_id} status updated to '{new_status}' successfully!", "success")
                return redirect(url_for('officer_application_detail', application_id=application_id))

        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM applications WHERE id = %s", (application_id,))
            application = cursor.fetchone()

            if not application:
                flash("Application not found.", "error")
                return redirect(url_for('officer_applications'))

            cursor.execute("SELECT email, mobile, village_name FROM users WHERE id = %s", (application['user_id'],))
            citizen = cursor.fetchone()

            cursor.execute("""
                SELECT id, file_name, original_name, file_size, uploaded_at
                FROM application_documents
                WHERE application_id = %s
                ORDER BY uploaded_at DESC
            """, (application_id,))
            documents = cursor.fetchall()

        return render_template(
            'officer_application_detail.html',
            app=application,
            citizen=citizen,
            documents=documents,
            statuses=STATUS_VALUES
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error handling officer application detail: {err}")
        flash("An error occurred while updating the application.", "error")
        return redirect(url_for('officer_applications'))
    finally:
        db.close()


@app.route('/officer/document/<int:doc_id>')
@officer_required
def officer_download_document(doc_id):
    """
    Secure Document Viewer for Officers.
    Allows verified administrative officers to view applicant uploads.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_applications'))

    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT file_name, original_name FROM application_documents WHERE id = %s", (doc_id,))
            doc = cursor.fetchone()

        if not doc:
            flash("Document not found.", "error")
            return redirect(url_for('officer_applications'))

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            doc['file_name'],
            as_attachment=False,
            download_name=doc['original_name']
        )
    except pymysql.MySQLError as err:
        app.logger.error(f"Error downloading document for officer: {err}")
        flash("Could not access document.", "error")
        return redirect(url_for('officer_applications'))
    finally:
        db.close()


@app.route('/officer/citizens')
@officer_required
def officer_citizens():
    """
    Registered Citizens Directory for Officers.
    Displays all village residents and their application activity.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_dashboard'))

    search = request.args.get('q', '').strip()

    try:
        query = """
            SELECT u.id, u.full_name, u.email, u.mobile, u.village_name, u.address,
                   u.is_active, u.created_at,
                   COUNT(a.id) AS app_count
            FROM users u
            LEFT JOIN applications a ON u.id = a.user_id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (u.full_name LIKE %s OR u.mobile LIKE %s OR u.email LIKE %s OR u.address LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        query += " GROUP BY u.id ORDER BY u.created_at DESC"

        with db.cursor() as cursor:
            cursor.execute(query, tuple(params))
            citizens = cursor.fetchall()

        return render_template('officer_citizens.html', citizens=citizens, search_query=search)
    except pymysql.MySQLError as err:
        app.logger.error(f"Error fetching citizens directory: {err}")
        flash("Could not retrieve citizen directory.", "error")
        return redirect(url_for('officer_dashboard'))
    finally:
        db.close()


@app.route('/officer/notices')
@officer_required
def officer_notices():
    """
    Officer Notice Board Management Route.
    Allows Gram Sevak to view, publish, and delete village notices.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_dashboard'))

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, category, content, posted_by, is_active, created_at 
                FROM notices 
                ORDER BY created_at DESC
            """)
            notices_list = cursor.fetchall()
        return render_template('officer_notices.html', notices=notices_list)
    except pymysql.MySQLError as err:
        app.logger.error(f"Error fetching officer notices: {err}")
        flash("Could not retrieve notices.", "error")
        return redirect(url_for('officer_dashboard'))
    finally:
        db.close()


@app.route('/officer/notices/add', methods=['POST'])
@officer_required
def officer_add_notice():
    """
    Add / Publish New Village Notice Route.
    """
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'General').strip()
    content = request.form.get('content', '').strip()

    if not title or not content:
        flash("Title and Content are required fields.", "error")
        return redirect(url_for('officer_notices'))

    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_notices'))

    posted_by = session.get('officer_name', 'Gram Sevak')

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO notices (title, category, content, posted_by, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """, (title, category, content, posted_by))
        flash("Official Notice published successfully to the village board!", "success")
        return redirect(url_for('officer_notices'))
    except pymysql.MySQLError as err:
        app.logger.error(f"Error publishing notice: {err}")
        flash("Could not publish notice.", "error")
        return redirect(url_for('officer_notices'))
    finally:
        db.close()


@app.route('/officer/notices/delete/<int:notice_id>')
@officer_required
def officer_delete_notice(notice_id):
    """
    Delete Notice from Board Route.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_notices'))

    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM notices WHERE id = %s", (notice_id,))
        flash("Notice removed successfully from public board.", "success")
        return redirect(url_for('officer_notices'))
    except pymysql.MySQLError as err:
        app.logger.error(f"Error deleting notice: {err}")
        flash("Could not delete notice.", "error")
        return redirect(url_for('officer_notices'))
    finally:
        db.close()


@app.route('/officer/export/applications')
@officer_required
def officer_export_applications():
    """
    Export Applications to CSV Report for Gram Panchayat Administration.
    """
    db = get_db_connection()
    if not db:
        flash("Database connection error.", "error")
        return redirect(url_for('officer_dashboard'))

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT a.application_number, a.applicant_name, a.mobile, a.address,
                       a.service_category, a.service_type, a.subject, a.description,
                       a.status, a.officer_remarks, a.created_at, a.updated_at,
                       u.email, u.village_name
                FROM applications a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.created_at DESC
            """)
            records = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV Header Row
        writer.writerow([
            'Application Number',
            'Applicant Name',
            'Mobile',
            'Email',
            'Village',
            'Address',
            'Service Category',
            'Service Type',
            'Subject',
            'Description',
            'Status',
            'Officer Remarks',
            'Submitted At',
            'Last Updated At'
        ])

        # Write Data Rows
        for r in records:
            writer.writerow([
                r['application_number'],
                r['applicant_name'],
                r['mobile'],
                r.get('email') or '',
                r.get('village_name') or '',
                r['address'],
                r['service_category'],
                r['service_type'],
                r['subject'],
                r['description'],
                r['status'],
                r.get('officer_remarks') or '',
                r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r.get('created_at') else '',
                r['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if r.get('updated_at') else ''
            ])

        csv_data = output.getvalue()
        output.close()

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"village_applications_{timestamp}.csv"

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except pymysql.MySQLError as err:
        app.logger.error(f"Error exporting applications CSV: {err}")
        flash("Could not generate export report.", "error")
        return redirect(url_for('officer_applications'))
    finally:
        db.close()


# ==============================================================
# Development Server Runner
# ==============================================================
if __name__ == '__main__':
    app.run(debug=True)
