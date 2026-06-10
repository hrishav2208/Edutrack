# EduTrack

EduTrack is a comprehensive educational institution management platform designed to streamline student directory information, attendance tracking, marks management, notifications, and financial operations.

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Folder Structure](#folder-structure)
- [Technical Documentation](#technical-documentation)
- [Deployment](#deployment)
- [License](#license)

## Features
- **Student Directory**: Manage profiles, roles, and branch details.
- **Attendance Management**: Track attendance records for students and staff.
- **Marks & Grading**: Log exam details, marks, and student performance.
- **In-App Messaging & Notifications**: Dynamic messaging and email notifications (using EmailJS/OTP verification).
- **Financial Tracking**: Invoice management, fees, and payments.
- **Face Recognition**: Security and auto-attendance options.
- **PDF Report Generation**: Automated PDF documents for technical guidelines and student details.

## Tech Stack
- **Backend**: Python, Flask, SQLAlchemy, Flask-Migrate
- **Database**: PostgreSQL (psycopg2-binary)
- **Server**: Gunicorn
- **Deployment**: Docker, Docker Compose

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- Virtual environment tool (`venv` or `virtualenv`)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/hrishav2208/Edutrack.git
   cd Edutrack
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Configure environment variables by copying `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure you set the following variables:
- `DATABASE_URL`: PostgreSQL connection string.
- `SECRET_KEY`: Secret key for session encryption.
- `EMAILJS_SERVICE_ID` & `EMAILJS_TEMPLATE_ID`: For notification delivery.

## Folder Structure
```text
Edutrack/
├── app/                  # Application core package
│   ├── attendance.py     # Attendance module
│   ├── auth.py           # User authentication & access roles
│   ├── config.py         # Config loader
│   ├── directory.py      # Student & branch directory
│   ├── models.py         # SQLAlchemy DB models
│   ├── notifications.py  # Messaging & notifications dispatch
│   └── reports.py        # Grade & system reporting
├── migrations/           # Database schema migrations
├── static/               # Client-side static assets (JS, CSS)
├── templates/            # HTML templates
├── wsgi.py               # WSGI application entrypoint
└── requirements.txt      # Dependency specification
```
