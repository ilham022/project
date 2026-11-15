
import os
import sqlite3
from datetime import date

from flask import (
    Flask,
    abort,
    redirect,
    render_template_string,
    request,
    send_from_directory,
    url_for
)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'keuangan.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

def ambil_transaksi():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    data =conn.execute('SELECT * FROM transaksi ORDER BY date DESC, id DESC').fetchall()

    conn.close()
    return [dict(row) for row in data]



KATEGORI_VALID = {
    'pemasukan',
    'pengeluaran',
    'investasi',
    'tabungan'
}


@app.template_filter('rupiah')
def format_rupiah(amount):
    return f"Rp {amount:,.0f}".replace(',', '.')


@app.route('/')
def index():

    file_path = os.path.join(BASE_DIR, 'finance.html')

    with open(file_path, 'r', encoding='utf-8') as file:
        html = file.read()

    hari_ini = date.today()

    # Ambil semua transaksi dari database
    transaksi_list = ambil_transaksi()

    hari_ini = date.today()
    
    # Filter transaksi bulan ini
    transaksi_bulan_ini = [
        transaksi for transaksi in transaksi_list
        if transaksi['date'][:7] == hari_ini.strftime('%Y-%m')
    ]

    # Hitung pemasukan
    pemasukan = sum(
        t['amount'] for t in transaksi_bulan_ini
        if t['category'] == 'pemasukan'
    )

    # Hitung pengeluaran
    pengeluaran = sum(
        t['amount'] for t in transaksi_bulan_ini
        if t['category'] == 'pengeluaran'
    )

    # Hitung investasi
    investasi = sum(
        t['amount'] for t in transaksi_bulan_ini
        if t['category'] == 'investasi'
    )

    # Hitung tabungan
    tabungan = sum(
        t['amount'] for t in transaksi_bulan_ini
        if t['category'] == 'tabungan'
    )

    # Hitung cash flow dan saldo
    cashflow = pemasukan - pengeluaran
    saldo = cashflow - investasi - tabungan

    # Nama bulan
    daftar_bulan = [
        'Januari', 'Februari', 'Maret', 'April',
        'Mei', 'Juni', 'Juli', 'Agustus',
        'September', 'Oktober', 'November', 'Desember'
    ]

    nama_bulan = daftar_bulan[hari_ini.month - 1]

    # Alokasi dana
    total_alokasi = pemasukan

    alokasi = [
        {
            'name': 'Pengeluaran',
            'amount': pengeluaran,
            'class': 'danger'
        },
        {
            'name': 'Investasi',
            'amount': investasi,
            'class': 'success'
        },
        {
            'name': 'Tabungan',
            'amount': tabungan,
            'class': 'warning'
        }
    ]

    for item in alokasi:
        if total_alokasi > 0:
            item['percentage'] = round(
                item['amount'] / total_alokasi * 100
            )
        else:
            item['percentage'] = 0

    # Persentase menabung
    if pemasukan > 0:
        persentase_tabungan = round(
            tabungan / pemasukan * 100
        )
        persentase_investasi = round(
            investasi / pemasukan * 100
        )
    else:
        persentase_tabungan = 0
        persentase_investasi = 0

    return render_template_string(
        html,

        transaksi_list=sorted(
            transaksi_list,
            key=lambda item: item['date'],
            reverse=True
        ),

        pemasukan=pemasukan,
        pengeluaran=pengeluaran,
        investasi=investasi,
        saldo=saldo,
        tabungan=tabungan,
        cashflow=cashflow,

        nama_bulan=nama_bulan,
        tahun=hari_ini.year,
        tanggal_hari_ini=hari_ini.isoformat(),

        alokasi=alokasi,

        jumlah_transaksi=len(transaksi_bulan_ini),
        persentase_tabungan=persentase_tabungan,
        persentase_investasi=persentase_investasi
    )


@app.route('/style.css')
def style():
    return send_from_directory(BASE_DIR, 'styles.css')


@app.route('/add', methods=['POST'])
def add_transaction():

    name = request.form.get('name', '').strip()
    amount_text = request.form.get('amount', '')
    category = request.form.get('category', '')
    transaction_date = request.form.get('date', '')

    try:
        amount = int(amount_text)
        date.fromisoformat(transaction_date)

    except (ValueError, TypeError):
        abort(400, description='Jumlah uang atau tanggal tidak valid.')

    if amount <= 0 or not name or category not in KATEGORI_VALID:
        abort(400, description='Data transaksi tidak valid.')

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        'INSERT INTO transaksi (name, amount, category, date) VALUES (?, ?, ?, ?)',
        (name, amount, category, transaction_date)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000
    )
