# 💎 FinSight — Personal Finance Assistant

A full-stack web app to track income, expenses, visualize spending, get smart insights, and manage budgets.

---

## 🗂 Project Structure

```
financeapp/
├── app.py               ← Flask backend (all routes + logic)
├── requirements.txt     ← Python dependencies
├── templates/
│   ├── index.html       ← Login / Register page
│   └── dashboard.html   ← Main app (dashboard, history, insights, budget)
└── finance.db           ← SQLite database (auto-created on first run)
```

---

## ⚙️ Setup & Run

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 🔑 Features

| Feature | Description |
|---|---|
| 🔐 Auth | Register & login with hashed passwords |
| ➕ Add Transactions | Income or expense with category, date, notes |
| 📊 Dashboard | Balance, monthly stats, budget gauge |
| 📈 Charts | Line chart (6-month trend), Pie (categories), Bar (income vs expense) |
| 📋 History | Filter by date, category, type; delete transactions |
| 🧠 Insights | Month-over-month comparison, top spending day, category analysis |
| 🚨 Alerts | Budget warnings when you're near/over limit |
| 🔮 Prediction | Projected monthly spend based on 3-month average |
| 💰 Budget | Set monthly total + per-category limits |
| 🎲 Demo Data | Load 6 months of realistic sample data instantly |

---

## 🗄️ Database Schema

```sql
-- Users
users(id, username, email, password, created_at)

-- Transactions
transactions(id, user_id, amount, category, type, date, notes, created_at)

-- Budgets
budget(id, user_id, monthly_limit, category_limits)
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Create account |
| POST | `/api/login` | Login |
| POST | `/api/logout` | Logout |
| GET | `/api/me` | Current user info |
| GET/POST | `/api/transactions` | List / Add transactions |
| DELETE | `/api/transactions/:id` | Delete transaction |
| GET | `/api/dashboard` | Dashboard stats |
| GET | `/api/charts/monthly-trend` | 6-month chart data |
| GET | `/api/insights` | Insights + alerts + prediction |
| GET/PUT | `/api/budget` | Get / Update budget |
| GET | `/api/categories` | All categories |
| POST | `/api/seed-demo` | Load demo data |

---

## 🛠 Tech Stack

- **Backend**: Flask (Python) + SQLAlchemy + SQLite
- **Frontend**: Vanilla HTML/CSS/JS + Chart.js
- **Auth**: Werkzeug password hashing + Flask session
- **Charts**: Chart.js (CDN)
- **Fonts**: Syne + DM Sans (Google Fonts)

---

## 💡 Tips

- Click **"Load Demo Data"** on the Add Transaction page to instantly populate 6 months of sample data
- Set a monthly budget in the **Budget** section to get alerts
- Insights appear after you have 2+ months of data for comparison
