# TechBlogs - Django Blog Web Application (Base Setup)

This is the initial clean Django project framework setup for the TechBlogs web application. 

*Note: All active application features, CRUD workflows, templates, and DataTables are implemented on the **`feature/blog-crud`** branch.*

---

## 🛠️ Installation & Base Setup

To run the base project setup locally:

### 1. Initialize Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1
```

### 2. Install Project Dependencies
```bash
pip install django django-ajax-datatable pillow
```

### 3. Run Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` to confirm the default Django installation page loads successfully.

---

## 🌿 Feature Branch Development
To view or work on the blog management dashboard, switch to the feature branch:
```bash
git checkout feature/blog-crud
```
