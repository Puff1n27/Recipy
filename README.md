# ReciPy

ReciPy is a Flask web application for tracking daily expenses. It lets users
create an account, scan receipts with OCR, review extracted details, and
manage expenses from a dashboard.

## Features

- User registration, login, logout, and session-based authentication
- Receipt image scanning with PaddleOCR
- Japanese and English receipt language detection
- Automatic extraction of shop name, date, and total amount
- Add, view, edit, and delete expenses
- Monthly and yearly spending totals
- Monthly spending and category breakdowns
- SQLite by default, with support for another SQLAlchemy database URL

## Tech stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Login
- PaddleOCR and Pillow
- Vanilla HTML, CSS, and JavaScript

## Getting started

### Prerequisites

- Python 3.10 or newer
- A working C/C++ build environment may be required by some OCR dependencies

### Installation

1. Clone the repository and enter the project directory:

   ```bash
   git clone https://github.com/Puff1n27/Recipy.git
   cd Recipy
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   ```

   On Windows:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   On macOS/Linux:

   ```bash
   source venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the development server:

   ```bash
   python app.py
   ```

   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser.

The SQLite database is created automatically when the application starts.
PaddleOCR may download model files on first use.

## API overview

All expense endpoints require an authenticated session. JSON request bodies
should use the fields shown below.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create an account |
| `POST` | `/api/auth/login` | Sign in |
| `POST` | `/api/auth/logout` | Sign out |
| `GET` | `/api/auth/status` | Check authentication status |
| `GET` | `/api/auth/me` | Get the current user |
| `POST` | `/api/scan` | Upload a receipt image as `file` |
| `GET` | `/api/expenses/` | List the current user's expenses |
| `POST` | `/api/expenses/` | Create one or more expenses |
| `GET` | `/api/expenses/<id>` | Get one expense |
| `PUT` | `/api/expenses/<id>` | Update an expense |
| `DELETE` | `/api/expenses/<id>` | Delete an expense |
| `GET` | `/api/expenses/stats` | Get dashboard statistics |

Example expense payload:

```json
{
  "shop_name": "Example Store",
  "date": "2026-09-04",
  "total_amount": 1280,
  "currency": "JPY",
  "category": "Food",
  "notes": "Weekly groceries"
}
```

## Project structure

```text
.
├── app.py                 # Flask application and receipt scan endpoint
├── config.py              # Environment-based configuration
├── models.py              # User and Expense database models
├── routes/
│   ├── auth.py            # Authentication endpoints
│   └── expenses.py        # Expense and dashboard endpoints
├── services/
│   └── ocr_service.py     # OCR result parsing and language detection
├── static/                # CSS and client-side JavaScript
└── templates/             # Flask HTML templates
```

## Security notes

- Set a strong, unique `SECRET_KEY` outside local development.
- Use `DEBUG=False` in production.
- Configure a production database instead of relying on the default SQLite
  file for multi-user deployments.
- Run the application behind a production WSGI server and HTTPS in production.

## License

No license has been specified yet.
