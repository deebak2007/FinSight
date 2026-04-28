from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import sqlite3, json, calendar
from collections import defaultdict
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'financeapp-secret-key-2024'
DB_PATH = os.path.join(os.path.dirname(__file__), 'finance.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            monthly_limit REAL DEFAULT 0,
            category_limits TEXT DEFAULT '{}'
        );
        """)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    with get_db() as conn:
        if conn.execute("SELECT id FROM users WHERE email=?", (data['email'],)).fetchone():
            return jsonify({'error': 'Email already registered'}), 400
        if conn.execute("SELECT id FROM users WHERE username=?", (data['username'],)).fetchone():
            return jsonify({'error': 'Username taken'}), 400
        cur = conn.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
            (data['username'], data['email'], generate_password_hash(data['password'])))
        uid = cur.lastrowid
        conn.execute("INSERT INTO budget (user_id,monthly_limit) VALUES (?,?)", (uid, 50000))
    session['user_id'] = uid
    session['username'] = data['username']
    return jsonify({'message': 'Registered', 'username': data['username']})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (data['email'],)).fetchone()
    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'message': 'Logged in', 'username': user['username']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/me')
@login_required
def me():
    with get_db() as conn:
        user = conn.execute("SELECT username,email FROM users WHERE id=?", (session['user_id'],)).fetchone()
    return jsonify(dict(user))

CATEGORIES = {
    'income':  ['Salary','Freelance','Investment','Gift','Other Income'],
    'expense': ['Food','Transport','Rent','Shopping','Bills','Health','Entertainment','Education','Travel','Other']
}

@app.route('/api/categories')
def categories():
    return jsonify(CATEGORIES)

@app.route('/api/transactions', methods=['GET','POST'])
@login_required
def transactions():
    uid = session['user_id']
    if request.method == 'POST':
        d = request.json
        with get_db() as conn:
            cur = conn.execute("INSERT INTO transactions (user_id,amount,category,type,date,notes) VALUES (?,?,?,?,?,?)",
                (uid, float(d['amount']), d['category'], d['type'], d['date'], d.get('notes','')))
        return jsonify({'message':'Added','id':cur.lastrowid})

    sql = "SELECT * FROM transactions WHERE user_id=?"
    params = [uid]
    for key, col in [('category','category'),('type','type')]:
        val = request.args.get(key)
        if val: sql += f" AND {col}=?"; params.append(val)
    if request.args.get('date_from'): sql += " AND date>=?"; params.append(request.args['date_from'])
    if request.args.get('date_to'):   sql += " AND date<=?"; params.append(request.args['date_to'])
    sql += " ORDER BY date DESC"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/transactions/<int:txn_id>', methods=['DELETE'])
@login_required
def delete_transaction(txn_id):
    with get_db() as conn:
        r = conn.execute("SELECT id FROM transactions WHERE id=? AND user_id=?", (txn_id, session['user_id'])).fetchone()
        if not r: return jsonify({'error':'Not found'}), 404
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    return jsonify({'message':'Deleted'})

@app.route('/api/dashboard')
@login_required
def dashboard_data():
    uid = session['user_id']
    now = datetime.now()
    month_start = now.replace(day=1).date().isoformat()
    with get_db() as conn:
        all_txns = [dict(r) for r in conn.execute("SELECT * FROM transactions WHERE user_id=?", (uid,)).fetchall()]
        budget_row = conn.execute("SELECT * FROM budget WHERE user_id=?", (uid,)).fetchone()

    month_txns = [t for t in all_txns if t['date'] >= month_start]
    total_income  = sum(t['amount'] for t in all_txns if t['type']=='income')
    total_expense = sum(t['amount'] for t in all_txns if t['type']=='expense')
    month_income  = sum(t['amount'] for t in month_txns if t['type']=='income')
    month_expense = sum(t['amount'] for t in month_txns if t['type']=='expense')
    cat_breakdown = defaultdict(float)
    for t in month_txns:
        if t['type']=='expense': cat_breakdown[t['category']] += t['amount']
    budget_limit = budget_row['monthly_limit'] if budget_row else 0
    return jsonify({
        'balance': total_income - total_expense,
        'total_income': total_income, 'total_expense': total_expense,
        'month_income': month_income, 'month_expense': month_expense,
        'category_breakdown': dict(cat_breakdown),
        'budget_limit': budget_limit,
        'budget_remaining': budget_limit - month_expense,
        'budget_used_pct': round((month_expense/budget_limit*100) if budget_limit else 0, 1)
    })

@app.route('/api/charts/monthly-trend')
@login_required
def monthly_trend():
    uid = session['user_id']
    now = datetime.now()
    result = []
    with get_db() as conn:
        for i in range(5,-1,-1):
            d = now - timedelta(days=30*i)
            y, m = d.year, d.month
            start = f"{y}-{m:02d}-01"
            end   = f"{y}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}"
            rows = conn.execute("SELECT type,SUM(amount) as total FROM transactions WHERE user_id=? AND date>=? AND date<=? GROUP BY type", (uid,start,end)).fetchall()
            inc = exp = 0
            for r in rows:
                if r['type']=='income': inc=r['total']
                else: exp=r['total']
            result.append({'label':d.strftime('%b %Y'),'income':inc,'expense':exp})
    return jsonify(result)

@app.route('/api/insights')
@login_required
def insights():
    uid = session['user_id']
    now = datetime.now()
    month_start = now.replace(day=1).date().isoformat()
    prev_end = now.replace(day=1).date() - timedelta(days=1)
    prev_start = prev_end.replace(day=1).isoformat()
    with get_db() as conn:
        all_txns = [dict(r) for r in conn.execute("SELECT * FROM transactions WHERE user_id=?", (uid,)).fetchall()]
        budget_row = conn.execute("SELECT * FROM budget WHERE user_id=?", (uid,)).fetchone()

    this_month = [t for t in all_txns if t['date']>=month_start and t['type']=='expense']
    prev_month = [t for t in all_txns if prev_start<=t['date']<=prev_end.isoformat() and t['type']=='expense']
    this_cat, prev_cat = defaultdict(float), defaultdict(float)
    for t in this_month: this_cat[t['category']] += t['amount']
    for t in prev_month: prev_cat[t['category']] += t['amount']

    insights_list, alerts = [], []
    for cat, amt in this_cat.items():
        if cat in prev_cat and prev_cat[cat]>0:
            pct = ((amt-prev_cat[cat])/prev_cat[cat])*100
            if pct>20: insights_list.append({'icon':'📈','text':f'You spent {pct:.0f}% more on {cat} this month (₹{amt:,.0f} vs ₹{prev_cat[cat]:,.0f})','type':'warning'})
            elif pct<-20: insights_list.append({'icon':'📉','text':f'Great! You spent {abs(pct):.0f}% less on {cat} this month','type':'success'})

    day_spend = defaultdict(float)
    for t in this_month:
        try: day_spend[datetime.strptime(t['date'],'%Y-%m-%d').strftime('%A')] += t['amount']
        except: pass
    if day_spend:
        top_day = max(day_spend, key=day_spend.get)
        insights_list.append({'icon':'📅','text':f'Your highest spending day is {top_day} (₹{day_spend[top_day]:,.0f})','type':'info'})
    if this_cat:
        top_cat = max(this_cat, key=this_cat.get)
        total_exp = sum(this_cat.values())
        pct = (this_cat[top_cat]/total_exp*100) if total_exp else 0
        insights_list.append({'icon':'🏆','text':f'{top_cat} is your biggest expense ({pct:.0f}% of total spending)','type':'info'})

    budget_limit = budget_row['monthly_limit'] if budget_row else 0
    if budget_limit>0:
        total_exp = sum(t['amount'] for t in this_month)
        pct_used = total_exp/budget_limit*100
        if pct_used>=100: alerts.append({'icon':'🚨','text':f"Budget exceeded! Spent ₹{total_exp:,.0f} of ₹{budget_limit:,.0f}",'type':'danger'})
        elif pct_used>=80: alerts.append({'icon':'⚠️','text':f'Warning: {pct_used:.0f}% of budget used','type':'warning'})

    months_data = []
    for i in range(1,4):
        ms_d = (now.replace(day=1).date()-timedelta(days=30*i)).replace(day=1)
        ms = ms_d.isoformat()
        me = f"{ms_d.year}-{ms_d.month:02d}-{calendar.monthrange(ms_d.year,ms_d.month)[1]:02d}"
        m_exp = sum(t['amount'] for t in all_txns if t['type']=='expense' and ms<=t['date']<=me)
        if m_exp>0: months_data.append(m_exp)
    prediction = None
    if months_data:
        avg = sum(months_data)/len(months_data)
        days_passed = now.day
        days_in_month = calendar.monthrange(now.year,now.month)[1]
        cur_exp = sum(t['amount'] for t in this_month)
        projected = (cur_exp/days_passed)*days_in_month if days_passed>0 else avg
        prediction = round((avg+projected)/2)

    return jsonify({'insights':insights_list,'alerts':alerts,'prediction':prediction})

@app.route('/api/budget', methods=['GET','PUT'])
@login_required
def budget():
    uid = session['user_id']
    with get_db() as conn:
        row = conn.execute("SELECT * FROM budget WHERE user_id=?", (uid,)).fetchone()
        if request.method=='PUT':
            data = request.json
            if row: conn.execute("UPDATE budget SET monthly_limit=?,category_limits=? WHERE user_id=?",
                                  (float(data['monthly_limit']),json.dumps(data.get('category_limits',{})),uid))
            else: conn.execute("INSERT INTO budget (user_id,monthly_limit,category_limits) VALUES (?,?,?)",
                               (uid,float(data['monthly_limit']),json.dumps(data.get('category_limits',{}))))
            return jsonify({'message':'Budget updated'})
    return jsonify({'monthly_limit':row['monthly_limit'] if row else 0,
                    'category_limits':json.loads(row['category_limits']) if row else {}})

@app.route('/api/seed-demo', methods=['POST'])
@login_required
def seed_demo():
    import random
    uid = session['user_id']
    now = datetime.now()
    cats_e = ['Food','Transport','Rent','Shopping','Bills','Health','Entertainment']
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE user_id=?", (uid,))
        rows = []
        for i in range(5,-1,-1):
            base = now-timedelta(days=30*i)
            y,m = base.year,base.month
            days_in = calendar.monthrange(y,m)[1]
            rows.append((uid,random.randint(45000,55000),'Salary','income',f"{y}-{m:02d}-01",'Monthly salary'))
            for _ in range(random.randint(15,25)):
                day = random.randint(1,days_in)
                cat = random.choices(cats_e,weights=[25,15,10,15,10,10,15])[0]
                lo,hi = {'Food':(200,2000),'Transport':(100,800),'Rent':(8000,12000),'Shopping':(500,5000),'Bills':(500,3000),'Health':(200,3000),'Entertainment':(200,2000)}[cat]
                rows.append((uid,random.randint(lo,hi),cat,'expense',f"{y}-{m:02d}-{day:02d}",''))
        conn.executemany("INSERT INTO transactions (user_id,amount,category,type,date,notes) VALUES (?,?,?,?,?,?)", rows)
    return jsonify({'message':'Demo data seeded!'})

if __name__ == '__main__':
    init_db()
    print("\n✅  FinSight is running!")
    print("   Open: http://localhost:5001\n")
    app.run(debug=True, port=5001)
