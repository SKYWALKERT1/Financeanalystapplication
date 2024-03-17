import sys
import sqlite3
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QComboBox, QRadioButton, QButtonGroup, QLabel, QDialog, QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from qdarkstyle import load_stylesheet
import numpy as np

class ExchangeRateThread(QThread):
    ratesFetched = pyqtSignal(dict)

    def run(self):
        rates = {}
        for currency in ['USD', 'EUR', 'GBP']:
            try:
                response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{currency}")#Request money value
                data = response.json()
                rates[currency] = round(data['rates']['TRY'], 3)
            except Exception as e:
                print(f"Error fetching exchange rates: {e}")
        self.ratesFetched.emit(rates)

class GraphWindow(QDialog):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle('Grafik Analizi')# Application distribution
        self.setGeometry(100, 100, 640, 480)
        self.data = data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.canvas = FigureCanvas(Figure(figsize=(5, 4)))
        layout.addWidget(self.canvas)

        self.plot()

    def plot(self):
        ax = self.canvas.figure.subplots()
        sns.barplot(x=[item['Kategori'] for item in self.data], y=[item['Miktar'] for item in self.data], ax=ax)
        ax.set_title('Kategoriye Göre Gelir ve Giderler')
        ax.set_ylabel('Miktar')
        ax.set_xlabel('Kategori')
        self.canvas.draw()

class GelirGiderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Kişisel Gelir ve Gider Takip Uygulaması')
        self.setGeometry(100, 100, 600, 450)
        self.initUI()
        self.initDB()
        self.fetchExchangeRates()

    def fetchExchangeRates(self):
        self.exchangeRateThread = ExchangeRateThread()
        self.exchangeRateThread.ratesFetched.connect(self.updateExchangeRates)
        self.exchangeRateThread.start()

    def updateExchangeRates(self, rates):
        self.exchange_rates = rates

    def initUI(self):
        self.setLayout(QVBoxLayout())

        self.amountEdit = QLineEdit(placeholderText='Miktar')
        self.layout().addWidget(self.amountEdit)

        self.categoryCombo = QComboBox()
        self.categoryCombo.addItems(['Maaş', 'Kira', 'Faturalar', 'Alışveriş'])# week analyst categories
        self.layout().addWidget(self.categoryCombo)

        self.currencyGroup = QButtonGroup(self)
        currencyLayout = QHBoxLayout()
        for currency in ['TL', 'USD', 'EUR', 'GBP']:
            radioButton = QRadioButton(currency)
            if currency == 'TL':
                radioButton.setChecked(True)
            self.currencyGroup.addButton(radioButton)
            currencyLayout.addWidget(radioButton)
        self.layout().addLayout(currencyLayout)

        self.addButton = QPushButton('Ekle')
        self.addButton.clicked.connect(self.addItem)
        self.layout().addWidget(self.addButton)

        self.deleteButton = QPushButton('Sil')
        self.deleteButton.clicked.connect(self.deleteItem)
        self.layout().addWidget(self.deleteButton)

        self.graphAnalysisButton = QPushButton('Grafik Analizi')
        self.graphAnalysisButton.clicked.connect(self.showGraphAnalysis)# Graphic Analyst QPushButton
        self.layout().addWidget(self.graphAnalysisButton)

        self.financeAnalysisButton = QPushButton('Finans Analizi')
        self.financeAnalysisButton.clicked.connect(self.showFinanceAnalysis)# Graphic Analyst QPushButton
        self.layout().addWidget(self.financeAnalysisButton)

        self.exportExcelButton = QPushButton('Excel\'e Aktar')
        self.exportExcelButton.clicked.connect(self.exportToExcelDialog)# Excel  Saved QPushButton
        self.layout().addWidget(self.exportExcelButton)

        self.itemList = QListWidget()
        self.layout().addWidget(self.itemList)

        self.totalLabel = QLabel('Toplam: 0 TL')
        self.layout().addWidget(self.totalLabel)

    def initDB(self):
        self.conn = sqlite3.connect('gelir_gider.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS kayitlar
                          (id INTEGER PRIMARY KEY, kategori TEXT, miktar REAL, para_birimi TEXT)''')# SQLİTE3 Create table keys
        self.conn.commit()
        self.loadItems()

    def addItem(self):
        amount = self.amountEdit.text()
        category = self.categoryCombo.currentText()
        selected_currency = self.currencyGroup.checkedButton().text()
        amount = float(amount) if category == 'Maaş' else -abs(float(amount))

        if selected_currency != 'TL':
            amount *= self.exchange_rates.get(selected_currency, 1)

        self.c.execute('INSERT INTO kayitlar (kategori, miktar, para_birimi) VALUES (?, ?, ?)', (category, amount, selected_currency))
        self.conn.commit()
        self.loadItems()

    def deleteItem(self):
        selectedItems = self.itemList.selectedItems()
        if selectedItems:
            selectedItemText = selectedItems[0].text()
            itemId = selectedItemText.split(':')[0]
            self.c.execute('DELETE FROM kayitlar WHERE id=?', (itemId,))
            self.conn.commit()
            self.loadItems()

    def loadItems(self):
        self.itemList.clear()
        self.c.execute('SELECT id, kategori, miktar, para_birimi FROM kayitlar ORDER BY id DESC')
        for row in self.c.fetchall():
            self.itemList.addItem(f"{row[0]}: {row[1]}, {row[2]:.2f} {row[3]}")
        self.calculateTotal()

    def calculateTotal(self):
        self.c.execute('SELECT SUM(miktar) FROM kayitlar')
        total = self.c.fetchone()[0] or 0
        self.totalLabel.setText(f'Toplam: {total:.2f} TL')

    def showGraphAnalysis(self):
        self.c.execute('SELECT kategori AS Kategori, SUM(miktar) AS Miktar FROM kayitlar GROUP BY kategori')
        data = [{'Kategori': row[0], 'Miktar': row[1]} for row in self.c.fetchall()]
        graphWindow = GraphWindow(data)
        graphWindow.exec()

    def showFinanceAnalysis(self):
        self.financeAnalysisButton.hide()
        self.MonthAnalysisButton = QPushButton('Aylık Analiz')
        self.MonthAnalysisButton.clicked.connect(lambda: self.showAnalysis('Aylık Analiz', 'aylik_analiz'))# Month  Analyst QPushButton
        self.layout().addWidget(self.MonthAnalysisButton)

        self.SixMonthAnalysisButton = QPushButton('6 Aylık Analiz')
        self.SixMonthAnalysisButton.clicked.connect(lambda: self.showAnalysis('6 Aylık Analiz', 'alti_aylik_analiz'))# Six Month Analyst QPushButton
        self.layout().addWidget(self.SixMonthAnalysisButton)

        self.OneYearAnalysisButton = QPushButton('1 Yıllık Analiz')
        self.OneYearAnalysisButton.clicked.connect(lambda: self.showAnalysis('Yıllık Analiz', 'yillik_analiz'))# One Year Analyst QPushButton
        self.layout().addWidget(self.OneYearAnalysisButton)


    def showAnalysis(self, analysis_type, table_name):
        analysis_dialog = AylikAnalizDialog(self.conn, analysis_type, table_name, self.exchange_rates)
        analysis_dialog.exec()

    def exportToExcelDialog(self):
        options = ["Kayıtlar", "Aylik Analiz", "Alti Aylık Analiz", "Yillik Analiz"]
        table, _ = QInputDialog.getItem(self, "Tablo Seçimi", "Hangi tabloyu Excel'e aktarmak istiyorsunuz?", options, 0, False)
        if table:
            if table == "Kayıtlar":
                self.exportToExcel('kayitlar')
            elif table == "Aylik Analiz":
                self.exportToExcel('aylik_analiz')
            elif table == "Alti Aylık Analiz":
                self.exportToExcel('alti_aylik_analiz')
            elif table == "Yillik Analiz":
                self.exportToExcel('yillik_analiz')

    def exportToExcel(self, table_name):
        try:
            # Veritabanındaki tabloyu oku ve DataFrame'e yükle
            df = pd.read_sql(f'SELECT * FROM {table_name}', self.conn)

            # Dosya adını belirle
            defaultFileName = "gelir_gider.xlsx"
            
            # Dosya yolunu belirtmeden sadece dosya adını seçmesi için QFileDialog kullan
            filePath, _ = QFileDialog.getSaveFileName(self, "Excel'e Aktar", defaultFileName, "Excel Files (*.xlsx)")

            if filePath:
                # Dosya adı ".xlsx" ile bitmiyorsa ekle
                if not filePath.endswith('.xlsx'):
                    filePath += '.xlsx'
                
                # DataFrame'i Excel dosyasına dönüştür ve belirtilen dosya yoluna kaydet
                df.to_excel(filePath, index=False)
                QMessageBox.information(self, "Başarılı", "Veriler Excel dosyasına başarıyla aktarıldı.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Veriler Excel'e aktarılırken bir hata oluştu:\n{e}")

class AylikAnalizDialog(QDialog):
    def __init__(self, conn, analysis_type, table_name, exchange_rates):
        super().__init__()
        self.conn = conn
        self.c = self.conn.cursor()
        self.analysis_type = analysis_type
        self.table_name = table_name
        self.exchange_rates = exchange_rates
        self.setWindowTitle(f'{analysis_type} Analiz')
        self.setGeometry(100, 100, 800, 600)
        self.initUI()
        self.initDB()

    def initDB(self):
        self.c.execute(f'''CREATE TABLE IF NOT EXISTS {self.table_name}
                          (id INTEGER PRIMARY KEY, hafta INTEGER, kategori TEXT, miktar REAL, para_birimi TEXT, analiz_tipi TEXT)''')
        self.conn.commit()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.weekCombo = QComboBox()
        weeks = [f"{i}. Hafta" for i in range(1, 5)] if self.analysis_type == "Aylık Analiz" else [f"{i}. Hafta" for i in range(1, 25)] if self.analysis_type == "Alti Aylık Analiz" else [f"{i}. Hafta" for i in range(1, 49)]
        self.weekCombo.addItems(weeks)
        layout.addWidget(self.weekCombo)

        self.categoryCombo = QComboBox()
        categories = ['Maaşlar', 'Sigortalar', 'Ek Ödemeler', 'Kira Gideri', 'Faturalar', 'Vergiler', 'Malzeme ve Stok Giderleri', 'Bakım ve Onarım', 'Pazarlama ve Reklam', 'Ofis Malzemeleri ve Yazılım Lisansları', 'Ürün Satışları', 'Hizmet Gelirleri', 'Diğer Gelirler']
        self.categoryCombo.addItems(categories)
        layout.addWidget(self.categoryCombo)

        self.amountEdit = QLineEdit(placeholderText='Miktar')
        layout.addWidget(self.amountEdit)

        self.currencyGroup = QButtonGroup(self)
        currencyLayout = QHBoxLayout()
        for currency in ['TL', 'USD', 'EUR', 'GBP']:
            radioButton = QRadioButton(currency)
            if currency == 'TL':
                radioButton.setChecked(True)
            self.currencyGroup.addButton(radioButton)
            currencyLayout.addWidget(radioButton)
        layout.addLayout(currencyLayout)

        self.addButton = QPushButton('Ekle')
        self.addButton.clicked.connect(self.addItem)
        layout.addWidget(self.addButton)

        self.deleteButton = QPushButton('Sil')
        self.deleteButton.clicked.connect(self.deleteItem)
        layout.addWidget(self.deleteButton)

        self.graphAnalysisButton = QPushButton('Grafik Analizi')
        self.graphAnalysisButton.clicked.connect(self.showLinearAnalysis)
        layout.addWidget(self.graphAnalysisButton)

        self.itemList = QListWidget()
        layout.addWidget(self.itemList)

        self.totalLabel = QLabel('Toplam: 0 TL')
        layout.addWidget(self.totalLabel)

    def addItem(self):
        hafta = self.weekCombo.currentIndex() + 1
        kategori = self.categoryCombo.currentText()
        miktar = float(self.amountEdit.text())
        para_birimi = self.currencyGroup.checkedButton().text()
        analiz_tipi = self.analysis_type

        if kategori in ['Maaşlar', 'Sigortalar', 'Ek Ödemeler', 'Kira Gideri', 'Faturalar', 'Vergiler', 'Malzeme ve Stok Giderleri', 'Bakım ve Onarım', 'Pazarlama ve Reklam', 'Ofis Malzemeleri ve Yazılım Lisansları']:
            miktar = -abs(miktar)
        else:
            miktar = abs(miktar)

        self.c.execute(f'INSERT INTO {self.table_name} (hafta, kategori, miktar, para_birimi, analiz_tipi) VALUES (?, ?, ?, ?, ?)', (hafta, kategori, miktar, para_birimi, analiz_tipi))
        self.conn.commit()
        self.loadItems()
        self.calculateTotal()

    def deleteItem(self):
        selectedItems = self.itemList.selectedItems()
        if selectedItems:
            selectedItemText = selectedItems[0].text()
            itemId = selectedItemText.split(':')[0]
            self.c.execute(f'DELETE FROM {self.table_name} WHERE id=?', (itemId,))
            self.conn.commit()
            self.loadItems()
            self.calculateTotal()
    

    def showLinearAnalysis(self):               
        dialog = QDialog(self)
        dialog.setWindowTitle('Detaylı Analiz Grafiği')
        dialog.setGeometry(100, 100, 1600, 800)  # Pencere boyutunu ve yüksekliğini ayarla
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        canvas = FigureCanvas(Figure(figsize=(15, 10)))  
        layout.addWidget(canvas)

        # GridSpec ile subplot düzenini ayarla
        gs = canvas.figure.add_gridspec(2, 2, hspace=0.5, wspace=0.3)  # hspace değerini artır

        ax1 = canvas.figure.add_subplot(gs[0, 0])
        weekly_totals = self.calculateWeeklyTotals()
        ax1.plot(range(1, len(weekly_totals)+1), weekly_totals, '-o', label='Toplam Miktar')#Linear + Scatter Analyst
        ax1.set_title(f'{self.analysis_type} Haftalık Toplam Analizi')
        ax1.set_xlabel('Hafta')
        ax1.set_ylabel('Toplam Miktar')
        ax1.legend()
        ax1.grid(True)

        ax2 = canvas.figure.add_subplot(gs[0, 1])
        ax2.plot(range(1, len(weekly_totals)+1), weekly_totals, '--r', label='Toplam Miktar (Aralıklı Çizgi)')
        ax2.set_title(f'{self.analysis_type} Haftalık Toplam Analizi (Aralıklı Çizgi)')#Linear Analyst
        ax2.set_xlabel('Hafta')
        ax2.set_ylabel('Toplam Miktar')
        ax2.legend()
        ax2.grid(True)

        ax3 = canvas.figure.add_subplot(gs[1, 0])
        category_totals = self.calculateCategoryTotals()
        categories = list(category_totals.keys())
        amounts = list(category_totals.values())
        ax3.bar(categories, amounts)
        ax3.set_title('Kategoriye Göre Toplam Miktar')
        ax3.set_xlabel('Kategori')
        ax3.set_ylabel('Miktar')
        ax3.tick_params(axis='x', rotation=90)

        ax4 = canvas.figure.add_subplot(gs[1, 1])
        weeks = [f'Hafta {i+1}' for i in range(len(weekly_totals))]  # Hafta sayısını dinamik olarak belirle
        y_pos = np.arange(len(weeks))  # Haftaların y pozisyonlarını belirle
        ax4.barh(y_pos, weekly_totals, align='center', height=0.5, label='Haftalık Toplam Miktar')  # stick high
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels(weeks, fontsize=5)  # ylabel name fontsize
        ax4.set_xlabel('Toplam Miktar')
        ax4.set_ylabel('Hafta')
        ax4.set_title(f'{self.analysis_type} Haftalık Toplam Miktar Grafiği')
        ax4.legend()


        canvas.figure.subplots_adjust(bottom=0.385, top=0.9, hspace=0.5, wspace=0.3)  # bottom ve hspace ayarlandı
        
        canvas.draw()
        dialog.exec()

    def calculateCategoryTotals(self):
        self.c.execute(f'SELECT kategori, SUM(miktar) FROM {self.table_name} WHERE analiz_tipi=? GROUP BY kategori', (self.analysis_type,))
        return {row[0]: row[1] for row in self.c.fetchall()}

    def calculateWeeklyTotals(self):
    # Analiz tipine göre hafta sayısını belirle
        if self.analysis_type == "Aylık Analiz":
            weeks_range = range(1, 5)  # Aylık analiz için 4 hafta
        elif self.analysis_type == "6 Aylık Analiz":
            weeks_range = range(1, 25)  # Altı aylık analiz için 24 hafta
        elif self.analysis_type == "1 Yıllık Analiz":
            weeks_range = range(1, 49)  # Year Analyst
        else:
            weeks_range = range(1, 5)  # Varsayılan Analyst

        weekly_totals = []
        for week in weeks_range:
            self.c.execute(f'SELECT SUM(miktar) FROM {self.table_name} WHERE hafta=? AND analiz_tipi=?', (week, self.analysis_type))# Table extraction conditions by analysis type
            total = self.c.fetchone()[0] or 0
            weekly_totals.append(total)
        return weekly_totals


    def loadItems(self):
        self.itemList.clear()
        self.c.execute(f'SELECT id, hafta, kategori, miktar, para_birimi FROM {self.table_name} WHERE analiz_tipi=?', (self.analysis_type,))
        for row in self.c.fetchall():
            self.itemList.addItem(f"{row[0]}: Hafta {row[1]}, {row[2]}, {row[3]:.2f} {row[4]}")

    def calculateTotal(self):
        self.c.execute(f'SELECT SUM(miktar) FROM {self.table_name} WHERE analiz_tipi=?', (self.analysis_type,)) # Total money according to entered categories
        total = self.c.fetchone()[0] or 0
        self.totalLabel.setText(f'Toplam: {total:.2f} TL')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())
    window = GelirGiderApp()
    window.show()
    sys.exit(app.exec())