# Village Digital Service & Request Management System

A BCA Mini Project designed to provide a unified digital platform for village citizens to submit and manage service requests, certificate applications, reports, grievances, and civic problem resolution with real-time status tracking and a dedicated Gram Sevak / Officer administration panel.

---

## 🛠️ Technology Stack

* **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
* **Backend:** Python Flask
* **Database:** MySQL (`village_service_db`)
* **Template Engine:** Jinja2
* **Security:** Werkzeug Password Hashing (`generate_password_hash`, `check_password_hash`), Session Authentication, Parameterized SQL Queries, Cross-User Access Control

---

## 📁 Project Folder Structure

```text
Village_Service_System/
│
├── app.py                           # Main Flask app (Auth + Services + Applications + Officer Panel)
├── config.py                        # MySQL database and Flask configuration settings
├── requirements.txt                 # Python dependencies (Flask, PyMySQL, python-dotenv)
├── .env                             # Local environment configuration (DB credentials)
├── .env.example                     # Environment variables template
│
├── database/
│   └── schema.sql                   # MySQL schema (users, applications, application_documents, officers)
│
├── templates/
│   ├── base.html                    # Master layout (session-aware navbar for Citizen/Officer/Guest)
│   ├── index.html                   # Public landing page
│   ├── register.html                # Citizen registration with validation
│   ├── login.html                   # Citizen login
│   ├── dashboard.html               # Citizen dashboard with dynamic counts & quick actions
│   ├── profile.html                 # Citizen profile management
│   ├── services.html                # Village service directory & catalog
│   ├── apply.html                   # Application submission form with file upload
│   ├── my_applications.html         # Citizen's submitted applications list
│   ├── application_detail.html      # Application details, officer remarks & document manager
│   ├── track.html                   # Public live application status tracking
│   ├── officer_login.html           # Gram Sevak / Administrative Officer sign in
│   ├── officer_dashboard.html       # Officer dashboard with metrics & review queue
│   ├── officer_applications.html    # Master applications list with search & filters
│   ├── officer_application_detail.html # Split review screen & status/remarks action form
│   └── officer_citizens.html        # Registered village citizens directory
│
├── static/
│   ├── css/
│   │   └── style.css                # Clean e-governance responsive styling & status badges
│   ├── js/
│   │   └── script.js                # Client-side JavaScript
│   └── uploads/                     # Secure directory for citizen uploaded documents
│
└── README.md                        # Project documentation and guide
```

---

## 🗄️ MySQL Database Setup

1. Start your MySQL Server (via **XAMPP Control Panel**, **WAMP**, or **MySQL80 Windows Service**).
2. The database name is `village_service_db`.
3. The SQL schema file [**`database/schema.sql`**](file:///c:/Users/Dell/Desktop/Village_Service_System/database/schema.sql) contains four tables:
   * **`users`**: Citizen accounts (Name, Email, Mobile, Password Hash, Village, Address).
   * **`applications`**: Citizen applications and problem reports (Application No, Category, Type, Subject, Description, Status, Remarks).
   * **`application_documents`**: Uploaded supporting documents linked to applications.
   * **`officers`**: Gram Sevak and administrative staff accounts.

---

## 🔑 Default Login Credentials for Demo & Testing

### 1. Gram Sevak / Officer Account:
* **URL:** `http://127.0.0.1:5000/officer/login`
* **Email:** `officer@village.gov.in`
* **Password:** `officer123`
* **Role:** Gram Sevak (Sundarpur Gram Panchayat)

### 2. Citizen Account:
* **URL:** `http://127.0.0.1:5000/register` or `http://127.0.0.1:5000/login`
* Register your own citizen account or use your registered email/mobile.

---

## 🚀 How to Run the Application

1. Open VS Code Terminal:
   ```powershell
   python app.py
   ```
2. Open your browser:
   ```text
   http://127.0.0.1:5000/
   ```

---

## 🌟 Complete System Modules

### A. Citizen Portal
* **Registration & Login:** Secure password hashing and duplicate prevention.
* **Service Catalog (`/services`):** Browse Certificate Requests, Village Problems, and Other Services.
* **Direct Application (`/apply`):** Dynamic dropdowns, auto-prefilled profile data, unique application number generation (`VSS-2026-XXXXXX`), and optional file upload (PDF/JPG/PNG up to 5 MB).
* **My Applications (`/my-applications`):** Complete application history with color-coded status badges.
* **Application Details (`/application/<id>`):** Full request view, officer remarks, attached documents, and ability to upload additional documents.
* **Official Certificate & Slip Printing (`/application/<id>/certificate`):** Print-ready certificate with Gram Panchayat seal, watermark, and QR verification badge.
* **Dynamic Dashboard (`/dashboard`):** Real-time metrics for total applications, complaints, pending, and completed requests.

### B. Gram Sevak / Officer Admin Panel
* **Officer Dashboard (`/officer/dashboard`):** High-level metrics for received, pending, approved, rejected, and completed requests, plus category breakdown and pending review queue.
* **Applications Management (`/officer/applications`):** Master list with multi-criteria search (by Application Number, Applicant Name, Mobile, Subject) and filters by Category and Status.
* **Review & Action Screen (`/officer/application/<id>`):** Inspect citizen details, view uploaded documents, update status (`Under Review`, `Documents Required`, `Approved`, `Rejected`, `Completed`), and write official remarks with quick-chip suggestions.
* **Official Notice Board Management (`/officer/notices`):** Publish and manage public village circulars and alerts.
* **CSV Data Export (`/officer/export/applications`):** One-click download of all application records into an Excel-compatible CSV report.
* **Citizens Directory (`/officer/citizens`):** Directory of registered village residents with their application volume.

### C. Public Services & Transparency
* **Public Tracking (`/track`):** Instant tracking for citizens without logging in by entering their application number.
* **Village Notices Board (`/notices`):** Live public notices, meeting schedules, alerts, and welfare scheme updates.
