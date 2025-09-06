import sys
import os
import sqlite3
import hashlib
import datetime
from datetime import date, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QMessageBox, QComboBox, QDateEdit, QGroupBox,
                             QFormLayout, QDialog, QDialogButtonBox, QHeaderView,
                             QFileDialog, QInputDialog, QProgressBar, QProgressDialog)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon, QPixmap
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import threading

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do Cloudinary (para sincronização com nuvem)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Classe de sinais para comunicação entre threads
class SyncSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class DatabaseManager:
    def __init__(self):
        self.db_name = "finance_manager.db"
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de transações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabela de orçamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, category, month, year)
            )
        ''')
        
        # Tabela de metas financeiras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)

class AuthDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Autenticação")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Aplicar estilo
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.tab_widget = QTabWidget()
        self.login_tab = QWidget()
        self.register_tab = QWidget()
        
        self.setup_login_tab()
        self.setup_register_tab()
        
        self.tab_widget.addTab(self.login_tab, "Login")
        self.tab_widget.addTab(self.register_tab, "Registrar")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def setup_login_tab(self):
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Digite seu usuário")
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText("Digite sua senha")
        
        layout.addRow("Usuário:", self.login_username)
        layout.addRow("Senha:", self.login_password)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        layout.addRow(login_btn)
        
        self.login_tab.setLayout(layout)
    
    def setup_register_tab(self):
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Escolha um usuário")
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("Digite seu email")
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_password.setPlaceholderText("Crie uma senha")
        self.register_confirm_password = QLineEdit()
        self.register_confirm_password.setEchoMode(QLineEdit.Password)
        self.register_confirm_password.setPlaceholderText("Confirme a senha")
        
        layout.addRow("Usuário:", self.register_username)
        layout.addRow("Email:", self.register_email)
        layout.addRow("Senha:", self.register_password)
        layout.addRow("Confirmar Senha:", self.register_confirm_password)
        
        register_btn = QPushButton("Registrar")
        register_btn.clicked.connect(self.register)
        layout.addRow(register_btn)
        
        self.register_tab.setLayout(layout)
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self):
        username = self.login_username.text()
        password = self.login_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Erro", "Preencha todos os campos")
            return
        
        hashed_password = self.hash_password(password)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", 
                      (username, hashed_password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.user_id = user[0]
            self.username = user[1]
            self.accept()
        else:
            QMessageBox.warning(self, "Erro", "Usuário ou senha inválidos")
    
    def register(self):
        username = self.register_username.text()
        email = self.register_email.text()
        password = self.register_password.text()
        confirm_password = self.register_confirm_password.text()
        
        if not username or not email or not password or not confirm_password:
            QMessageBox.warning(self, "Erro", "Preencha todos os campos")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Erro", "As senhas não coincidem")
            return
        
        hashed_password = self.hash_password(password)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                          (username, hashed_password, email))
            conn.commit()
            QMessageBox.information(self, "Sucesso", "Usuário registrado com sucesso")
            self.tab_widget.setCurrentIndex(0)  # Volta para a aba de login
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erro", "Usuário ou email já existe")
        finally:
            conn.close()

class TransactionDialog(QDialog):
    def __init__(self, user_id, db_manager, transaction_id=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db_manager = db_manager
        self.transaction_id = transaction_id
        self.setWindowTitle("Adicionar Transação" if not transaction_id else "Editar Transação")
        self.setModal(True)
        self.setFixedSize(400, 350)
        
        # Aplicar estilo
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Receita", "Despesa"])
        
        self.category_combo = QComboBox()
        self.update_categories()
        
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QtGui.QDoubleValidator(0, 1000000, 2))
        self.amount_input.setPlaceholderText("0.00")
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Descrição da transação")
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        
        layout.addRow("Tipo:", self.type_combo)
        layout.addRow("Categoria:", self.category_combo)
        layout.addRow("Valor:", self.amount_input)
        layout.addRow("Descrição:", self.description_input)
        layout.addRow("Data:", self.date_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
        # Se estiver editando, carregue os dados
        if transaction_id:
            self.load_transaction_data()
    
    def update_categories(self):
        categories = ["Alimentação", "Transporte", "Moradia", "Saúde", "Educação", 
                     "Lazer", "Salário", "Freelance", "Investimentos", "Outros"]
        self.category_combo.clear()
        self.category_combo.addItems(categories)
    
    def load_transaction_data(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT type, category, amount, description, date FROM transactions WHERE id = ?", 
                      (self.transaction_id,))
        transaction = cursor.fetchone()
        conn.close()
        
        if transaction:
            type_index = 0 if transaction[0] == "Receita" else 1
            self.type_combo.setCurrentIndex(type_index)
            
            category_index = self.category_combo.findText(transaction[1])
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            self.amount_input.setText(str(transaction[2]))
            self.description_input.setText(transaction[3] if transaction[3] else "")
            
            date = QDate.fromString(transaction[4], "yyyy-MM-dd")
            self.date_input.setDate(date)
    
    def get_data(self):
        return {
            "type": self.type_combo.currentText(),
            "category": self.category_combo.currentText(),
            "amount": float(self.amount_input.text()),
            "description": self.description_input.text(),
            "date": self.date_input.date().toString("yyyy-MM-dd")
        }

class BudgetDialog(QDialog):
    def __init__(self, user_id, db_manager, budget_id=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db_manager = db_manager
        self.budget_id = budget_id
        self.setWindowTitle("Adicionar Orçamento" if not budget_id else "Editar Orçamento")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Aplicar estilo
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.category_combo = QComboBox()
        categories = ["Alimentação", "Transporte", "Moradia", "Saúde", "Educação", 
                     "Lazer", "Outros"]
        self.category_combo.addItems(categories)
        
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QtGui.QDoubleValidator(0, 1000000, 2))
        self.amount_input.setPlaceholderText("0.00")
        
        current_date = QDate.currentDate()
        self.month_combo = QComboBox()
        months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.month_combo.addItems(months)
        self.month_combo.setCurrentIndex(current_date.month() - 1)
        
        self.year_input = QLineEdit()
        self.year_input.setValidator(QtGui.QIntValidator(2000, 2100))
        self.year_input.setText(str(current_date.year()))
        
        layout.addRow("Categoria:", self.category_combo)
        layout.addRow("Valor:", self.amount_input)
        layout.addRow("Mês:", self.month_combo)
        layout.addRow("Ano:", self.year_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
        # Se estiver editando, carregue os dados
        if budget_id:
            self.load_budget_data()
    
    def load_budget_data(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category, amount, month, year FROM budgets WHERE id = ?", 
                      (self.budget_id,))
        budget = cursor.fetchone()
        conn.close()
        
        if budget:
            category_index = self.category_combo.findText(budget[0])
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            self.amount_input.setText(str(budget[1]))
            self.month_combo.setCurrentIndex(budget[2] - 1)
            self.year_input.setText(str(budget[3]))
    
    def get_data(self):
        return {
            "category": self.category_combo.currentText(),
            "amount": float(self.amount_input.text()),
            "month": self.month_combo.currentIndex() + 1,
            "year": int(self.year_input.text())
        }

class GoalDialog(QDialog):
    def __init__(self, user_id, db_manager, goal_id=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db_manager = db_manager
        self.goal_id = goal_id
        self.setWindowTitle("Adicionar Meta" if not goal_id else "Editar Meta")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Aplicar estilo
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QLineEdit, QDateEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QDateEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Ex: Viagem, Carro Novo, etc.")
        
        self.target_amount_input = QLineEdit()
        self.target_amount_input.setValidator(QtGui.QDoubleValidator(0, 1000000, 2))
        self.target_amount_input.setPlaceholderText("0.00")
        
        self.current_amount_input = QLineEdit()
        self.current_amount_input.setValidator(QtGui.QDoubleValidator(0, 1000000, 2))
        self.current_amount_input.setText("0")
        self.current_amount_input.setPlaceholderText("0.00")
        
        self.deadline_input = QDateEdit()
        self.deadline_input.setDate(QDate.currentDate().addMonths(1))
        self.deadline_input.setCalendarPopup(True)
        
        layout.addRow("Título:", self.title_input)
        layout.addRow("Valor Alvo:", self.target_amount_input)
        layout.addRow("Valor Atual:", self.current_amount_input)
        layout.addRow("Prazo:", self.deadline_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
        # Se estiver editando, carregue os dados
        if goal_id:
            self.load_goal_data()
    
    def load_goal_data(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, target_amount, current_amount, deadline FROM goals WHERE id = ?", 
                      (self.goal_id,))
        goal = cursor.fetchone()
        conn.close()
        
        if goal:
            self.title_input.setText(goal[0])
            self.target_amount_input.setText(str(goal[1]))
            self.current_amount_input.setText(str(goal[2]))
            
            deadline = QDate.fromString(goal[3], "yyyy-MM-dd")
            self.deadline_input.setDate(deadline)
    
    def get_data(self):
        return {
            "title": self.title_input.text(),
            "target_amount": float(self.target_amount_input.text()),
            "current_amount": float(self.current_amount_input.text()),
            "deadline": self.deadline_input.date().toString("yyyy-MM-dd")
        }

class FinanceChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Estilo do gráfico
        plt.style.use('seaborn-v0_8')
        self.ax.set_xlabel('Categorias')
        self.ax.set_ylabel('Valor (R$)')
        self.ax.set_title('Despesas por Categoria')
        self.fig.tight_layout()
    
    def plot_expenses(self, data):
        self.ax.clear()
        
        if not data:
            self.ax.text(0.5, 0.5, 'Nenhuma despesa encontrada', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=self.ax.transAxes, fontsize=12)
            self.draw()
            return
        
        categories = list(data.keys())
        values = list(data.values())
        
        # Cores para as barras
        colors = plt.cm.Set3(range(len(categories)))
        
        bars = self.ax.bar(categories, values, color=colors)
        self.ax.set_xlabel('Categorias')
        self.ax.set_ylabel('Valor (R$)')
        self.ax.set_title('Despesas por Categoria')
        
        # Rotacionar labels para melhor visualização
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        
        # Adicionar valores nas barras
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'R$ {height:.2f}',
                        ha='center', va='bottom', fontweight='bold')
        
        self.fig.tight_layout()
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self, user_id, username, db_manager):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.db_manager = db_manager
        self.sync_signals = SyncSignals()  # Instância dos sinais
        self.setWindowTitle(f"Controle Financeiro Pessoal - {username}")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_ui()
        self.load_data()
        self.update_dashboard()
        
        # Conecte os sinais aos slots
        self.sync_signals.progress.connect(self.update_sync_progress)
        self.sync_signals.finished.connect(self.sync_finished)
        self.sync_signals.error.connect(self.sync_error)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Aplicar estilo CSS moderno
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                selection-background-color: #e3f2fd;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #4CAF50;
            }
            QLabel {
                color: #333333;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
            QMenuBar {
                background-color: #f0f0f0;
                padding: 4px;
            }
            QMenuBar::item {
                padding: 4px 8px;
                background: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 4px 24px 4px 8px;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        layout = QVBoxLayout(central_widget)
        
        # Adicione um cabeçalho com o nome do usuário
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        welcome_label = QLabel(f"Bem-vindo, {self.username}!")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        
        date_label = QLabel(QDate.currentDate().toString("dd/MM/yyyy"))
        date_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                color: #7f8c8d;
            }
        """)
        
        header_layout.addWidget(welcome_label)
        header_layout.addStretch()
        header_layout.addWidget(date_label)
        
        layout.addWidget(header_widget)
        
        # Barra de menu
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("Arquivo")
        
        export_pdf_action = QtWidgets.QAction("Exportar PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        file_menu.addAction(export_pdf_action)
        
        export_excel_action = QtWidgets.QAction("Exportar Excel", self)
        export_excel_action.triggered.connect(self.export_excel)
        file_menu.addAction(export_excel_action)
        
        sync_action = QtWidgets.QAction("Sincronizar com Nuvem", self)
        sync_action.triggered.connect(self.sync_with_cloud)
        file_menu.addAction(sync_action)
        
        logout_action = QtWidgets.QAction("Sair", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        # Menu Transações
        transaction_menu = menubar.addMenu("Transações")
        
        add_transaction_action = QtWidgets.QAction("Adicionar Transação", self)
        add_transaction_action.triggered.connect(self.add_transaction)
        transaction_menu.addAction(add_transaction_action)
        
        # Menu Orçamentos
        budget_menu = menubar.addMenu("Orçamentos")
        
        add_budget_action = QtWidgets.QAction("Adicionar Orçamento", self)
        add_budget_action.triggered.connect(self.add_budget)
        budget_menu.addAction(add_budget_action)
        
        # Menu Metas
        goal_menu = menubar.addMenu("Metas")
        
        add_goal_action = QtWidgets.QAction("Adicionar Meta", self)
        add_goal_action.triggered.connect(self.add_goal)
        goal_menu.addAction(add_goal_action)
        
        # Widget de abas
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Dashboard
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tab_widget.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # Transações
        self.transactions_tab = QWidget()
        self.setup_transactions_tab()
        self.tab_widget.addTab(self.transactions_tab, "💳 Transações")
        
        # Orçamentos
        self.budgets_tab = QWidget()
        self.setup_budgets_tab()
        self.tab_widget.addTab(self.budgets_tab, "💰 Orçamentos")
        
        # Metas
        self.goals_tab = QWidget()
        self.setup_goals_tab()
        self.tab_widget.addTab(self.goals_tab, "🎯 Metas")
    
    def setup_dashboard_tab(self):
        layout = QVBoxLayout(self.dashboard_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Resumo financeiro com cards
        summary_group = QGroupBox("Resumo Financeiro")
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(15)
        
        # Card de Receitas
        income_card = QWidget()
        income_card.setStyleSheet("""
            QWidget {
                background-color: #4CAF50;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                color: white;
            }
        """)
        income_layout = QVBoxLayout(income_card)
        income_title = QLabel("Receitas")
        income_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.income_label = QLabel("R$ 0.00")
        self.income_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        income_layout.addWidget(income_title)
        income_layout.addWidget(self.income_label)
        
        # Card de Despesas
        expense_card = QWidget()
        expense_card.setStyleSheet("""
            QWidget {
                background-color: #f44336;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                color: white;
            }
        """)
        expense_layout = QVBoxLayout(expense_card)
        expense_title = QLabel("Despesas")
        expense_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.expense_label = QLabel("R$ 0.00")
        self.expense_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        expense_layout.addWidget(expense_title)
        expense_layout.addWidget(self.expense_label)
        
        # Card de Saldo
        balance_card = QWidget()
        balance_card.setStyleSheet("""
            QWidget {
                background-color: #2196F3;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                color: white;
            }
        """)
        balance_layout = QVBoxLayout(balance_card)
        balance_title = QLabel("Saldo")
        balance_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.balance_label = QLabel("R$ 0.00")
        self.balance_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        balance_layout.addWidget(balance_title)
        balance_layout.addWidget(self.balance_label)
        
        summary_layout.addWidget(income_card)
        summary_layout.addWidget(expense_card)
        summary_layout.addWidget(balance_card)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Gráfico e alertas em layout horizontal
        chart_alerts_layout = QHBoxLayout()
        
        # Gráfico
        chart_group = QGroupBox("Despesas por Categoria")
        chart_layout = QVBoxLayout()
        self.chart = FinanceChart(self, width=6, height=4, dpi=100)
        chart_layout.addWidget(self.chart)
        chart_group.setLayout(chart_layout)
        chart_group.setMinimumWidth(500)
        
        # Alertas e metas em layout vertical
        alerts_goals_layout = QVBoxLayout()
        
        # Alertas de orçamento
        self.budget_alerts_group = QGroupBox("⚠️ Alertas de Orçamento")
        self.budget_alerts_layout = QVBoxLayout()
        self.budget_alerts_group.setLayout(self.budget_alerts_layout)
        
        # Progresso de metas
        self.goals_progress_group = QGroupBox("🎯 Progresso de Metas")
        self.goals_progress_layout = QVBoxLayout()
        self.goals_progress_group.setLayout(self.goals_progress_layout)
        
        alerts_goals_layout.addWidget(self.budget_alerts_group)
        alerts_goals_layout.addWidget(self.goals_progress_group)
        alerts_goals_layout.setStretch(0, 1)
        alerts_goals_layout.setStretch(1, 1)
        
        chart_alerts_layout.addWidget(chart_group)
        chart_alerts_layout.addLayout(alerts_goals_layout)
        chart_alerts_layout.setStretch(0, 2)
        chart_alerts_layout.setStretch(1, 1)
        
        layout.addLayout(chart_alerts_layout)
    
    def setup_transactions_tab(self):
        layout = QVBoxLayout(self.transactions_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Filtros
        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["Todos", "Receita", "Despesa"])
        
        self.filter_category_combo = QComboBox()
        self.filter_category_combo.addItems(["Todas", "Alimentação", "Transporte", "Moradia", 
                                           "Saúde", "Educação", "Lazer", "Salário", 
                                           "Freelance", "Investimentos", "Outros"])
        
        self.filter_start_date = QDateEdit()
        self.filter_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.filter_start_date.setCalendarPopup(True)
        
        self.filter_end_date = QDateEdit()
        self.filter_end_date.setDate(QDate.currentDate())
        self.filter_end_date.setCalendarPopup(True)
        
        filter_btn = QPushButton("Filtrar")
        filter_btn.clicked.connect(self.apply_filters)
        
        filter_layout.addWidget(QLabel("Tipo:"))
        filter_layout.addWidget(self.filter_type_combo)
        filter_layout.addWidget(QLabel("Categoria:"))
        filter_layout.addWidget(self.filter_category_combo)
        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.filter_start_date)
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.filter_end_date)
        filter_layout.addWidget(filter_btn)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Tabela de transações
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels(["ID", "Tipo", "Categoria", "Valor", "Descrição", "Data"])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_btn = QPushButton("➕ Adicionar")
        add_btn.clicked.connect(self.add_transaction)
        
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.clicked.connect(self.edit_transaction)
        
        delete_btn = QPushButton("🗑️ Excluir")
        delete_btn.clicked.connect(self.delete_transaction)
        
        action_layout.addWidget(add_btn)
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addStretch()
        
        layout.addWidget(self.transactions_table)
        layout.addLayout(action_layout)
    
    def setup_budgets_tab(self):
        layout = QVBoxLayout(self.budgets_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Filtros
        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        self.budget_month_combo = QComboBox()
        months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.budget_month_combo.addItems(months)
        self.budget_month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        
        self.budget_year_input = QLineEdit()
        self.budget_year_input.setValidator(QtGui.QIntValidator(2000, 2100))
        self.budget_year_input.setText(str(QDate.currentDate().year()))
        
        filter_btn = QPushButton("Filtrar")
        filter_btn.clicked.connect(self.load_budgets)
        
        filter_layout.addWidget(QLabel("Mês:"))
        filter_layout.addWidget(self.budget_month_combo)
        filter_layout.addWidget(QLabel("Ano:"))
        filter_layout.addWidget(self.budget_year_input)
        filter_layout.addWidget(filter_btn)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Tabela de orçamentos
        self.budgets_table = QTableWidget()
        self.budgets_table.setColumnCount(5)
        self.budgets_table.setHorizontalHeaderLabels(["ID", "Categoria", "Valor", "Mês", "Ano"])
        self.budgets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_btn = QPushButton("➕ Adicionar")
        add_btn.clicked.connect(self.add_budget)
        
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.clicked.connect(self.edit_budget)
        
        delete_btn = QPushButton("🗑️ Excluir")
        delete_btn.clicked.connect(self.delete_budget)
        
        action_layout.addWidget(add_btn)
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addStretch()
        
        layout.addWidget(self.budgets_table)
        layout.addLayout(action_layout)
    
    def setup_goals_tab(self):
        layout = QVBoxLayout(self.goals_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tabela de metas
        self.goals_table = QTableWidget()
        self.goals_table.setColumnCount(5)
        self.goals_table.setHorizontalHeaderLabels(["ID", "Título", "Valor Alvo", "Valor Atual", "Prazo"])
        self.goals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Botões de ação
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_btn = QPushButton("➕ Adicionar")
        add_btn.clicked.connect(self.add_goal)
        
        edit_btn = QPushButton("✏️ Editar")
        edit_btn.clicked.connect(self.edit_goal)
        
        delete_btn = QPushButton("🗑️ Excluir")
        delete_btn.clicked.connect(self.delete_goal)
        
        contribute_btn = QPushButton("💰 Contribuir")
        contribute_btn.clicked.connect(self.contribute_to_goal)
        
        action_layout.addWidget(add_btn)
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addWidget(contribute_btn)
        action_layout.addStretch()
        
        layout.addWidget(self.goals_table)
        layout.addLayout(action_layout)
    
    def load_data(self):
        self.load_transactions()
        self.load_budgets()
        self.load_goals()
    
    def load_transactions(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, type, category, amount, description, date 
            FROM transactions 
            WHERE user_id = ?
            ORDER BY date DESC
        """
        
        cursor.execute(query, (self.user_id,))
        transactions = cursor.fetchall()
        conn.close()
        
        self.transactions_table.setRowCount(len(transactions))
        
        for row, transaction in enumerate(transactions):
            for col, value in enumerate(transaction):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                # Colorir receitas e despesas
                if col == 1:  # Coluna do tipo
                    if value == "Receita":
                        item.setForeground(QtGui.QColor(0, 128, 0))  # Verde
                    else:
                        item.setForeground(QtGui.QColor(255, 0, 0))  # Vermelho
                
                self.transactions_table.setItem(row, col, item)
    
    def load_budgets(self):
        month = self.budget_month_combo.currentIndex() + 1
        year = int(self.budget_year_input.text())
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, category, amount, month, year 
            FROM budgets 
            WHERE user_id = ? AND month = ? AND year = ?
            ORDER BY category
        """
        
        cursor.execute(query, (self.user_id, month, year))
        budgets = cursor.fetchall()
        conn.close()
        
        self.budgets_table.setRowCount(len(budgets))
        
        for row, budget in enumerate(budgets):
            for col, value in enumerate(budget):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                # Converter número do mês para nome
                if col == 3:
                    months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                    item.setText(months[value - 1])
                
                self.budgets_table.setItem(row, col, item)
    
    def load_goals(self):
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, title, target_amount, current_amount, deadline 
            FROM goals 
            WHERE user_id = ?
            ORDER BY deadline
        """
        
        cursor.execute(query, (self.user_id,))
        goals = cursor.fetchall()
        conn.close()
        
        self.goals_table.setRowCount(len(goals))
        
        for row, goal in enumerate(goals):
            for col, value in enumerate(goal):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                # Colorir progresso das metas
                if col == 3 and col > 1:  # Coluna do valor atual
                    target = float(goal[2])
                    current = float(value)
                    if current >= target:
                        item.setForeground(QtGui.QColor(0, 128, 0))  # Verde
                    elif current >= target * 0.7:
                        item.setForeground(QtGui.QColor(255, 165, 0))  # Laranja
                
                self.goals_table.setItem(row, col, item)
    
    def apply_filters(self):
        filter_type = self.filter_type_combo.currentText()
        filter_category = self.filter_category_combo.currentText()
        start_date = self.filter_start_date.date().toString("yyyy-MM-dd")
        end_date = self.filter_end_date.date().toString("yyyy-MM-dd")
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, type, category, amount, description, date 
            FROM transactions 
            WHERE user_id = ? 
            AND date BETWEEN ? AND ?
        """
        
        params = [self.user_id, start_date, end_date]
        
        if filter_type != "Todos":
            query += " AND type = ?"
            params.append(filter_type)
        
        if filter_category != "Todas":
            query += " AND category = ?"
            params.append(filter_category)
        
        query += " ORDER BY date DESC"
        
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        conn.close()
        
        self.transactions_table.setRowCount(len(transactions))
        
        for row, transaction in enumerate(transactions):
            for col, value in enumerate(transaction):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                # Colorir receitas e despesas
                if col == 1:  # Coluna do tipo
                    if value == "Receita":
                        item.setForeground(QtGui.QColor(0, 128, 0))  # Verde
                    else:
                        item.setForeground(QtGui.QColor(255, 0, 0))  # Vermelho
                
                self.transactions_table.setItem(row, col, item)
    
    def update_dashboard(self):
        # Calcular totais
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Receitas
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Receita'", 
                      (self.user_id,))
        total_income = cursor.fetchone()[0] or 0
        
        # Despesas
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Despesa'", 
                      (self.user_id,))
        total_expense = cursor.fetchone()[0] or 0
        
        # Saldo
        balance = total_income - total_expense
        
        # Atualizar labels
        self.income_label.setText(f"R$ {total_income:.2f}")
        self.expense_label.setText(f"R$ {total_expense:.2f}")
        self.balance_label.setText(f"R$ {balance:.2f}")
        
        # Colorir saldo
        if balance < 0:
            self.balance_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #f44336;")
        else:
            self.balance_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: white;")
        
        # Gráfico de despesas por categoria
        cursor.execute("""
            SELECT category, SUM(amount) 
            FROM transactions 
            WHERE user_id = ? AND type = 'Despesa'
            GROUP BY category
        """, (self.user_id,))
        
        expenses_by_category = {row[0]: row[1] for row in cursor.fetchall()}
        self.chart.plot_expenses(expenses_by_category)
        
        # Alertas de orçamento
        self.update_budget_alerts()
        
        # Progresso de metas
        self.update_goals_progress()
        
        conn.close()
    
    def update_budget_alerts(self):
        # Limpar alertas anteriores
        for i in reversed(range(self.budget_alerts_layout.count())):
            widget = self.budget_alerts_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        current_month = QDate.currentDate().month()
        current_year = QDate.currentDate().year()
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Buscar orçamentos do mês atual
        cursor.execute("""
            SELECT category, amount 
            FROM budgets 
            WHERE user_id = ? AND month = ? AND year = ?
        """, (self.user_id, current_month, current_year))
        
        budgets = cursor.fetchall()
        
        for category, budget_amount in budgets:
            # Buscar despesas da categoria no mês atual
            first_day = date(current_year, current_month, 1)
            if current_month < 12:
                last_day = date(current_year, current_month + 1, 1) - timedelta(days=1)
            else:
                last_day = date(current_year, 12, 31)
            
            cursor.execute("""
                SELECT SUM(amount) 
                FROM transactions 
                WHERE user_id = ? AND type = 'Despesa' AND category = ? 
                AND date BETWEEN ? AND ?
            """, (self.user_id, category, first_day.isoformat(), last_day.isoformat()))
            
            expenses = cursor.fetchone()[0] or 0
            percentage = (expenses / budget_amount) * 100 if budget_amount > 0 else 0
            
            if percentage >= 80:
                alert_color = "red" if percentage >= 100 else "orange"
                alert_text = f"<font color='{alert_color}'><b>Alerta:</b> {category} - {percentage:.1f}% do orçamento utilizado (R$ {expenses:.2f} / R$ {budget_amount:.2f})</font>"
                alert_label = QLabel(alert_text)
                alert_label.setWordWrap(True)
                self.budget_alerts_layout.addWidget(alert_label)
        
        # Se não houver alertas
        if self.budget_alerts_layout.count() == 0:
            alert_label = QLabel("<font color='green'>Nenhum alerta de orçamento</font>")
            self.budget_alerts_layout.addWidget(alert_label)
        
        conn.close()
    
    def update_goals_progress(self):
        # Limpar progresso anterior
        for i in reversed(range(self.goals_progress_layout.count())):
            widget = self.goals_progress_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Buscar metas
        cursor.execute("SELECT id, title, target_amount, current_amount FROM goals WHERE user_id = ?", 
                      (self.user_id,))
        
        goals = cursor.fetchall()
        
        for goal_id, title, target_amount, current_amount in goals:
            progress_percentage = (current_amount / target_amount) * 100 if target_amount > 0 else 0
            
            goal_group = QGroupBox(title)
            goal_layout = QVBoxLayout()
            
            progress_label = QLabel(f"Progresso: R$ {current_amount:.2f} / R$ {target_amount:.2f} ({progress_percentage:.1f}%)")
            progress_bar = QProgressBar()
            progress_bar.setValue(int(progress_percentage))
            
            # Colorir a barra de progresso
            if progress_percentage >= 100:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            elif progress_percentage >= 70:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
            else:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2196F3; }")
            
            goal_layout.addWidget(progress_label)
            goal_layout.addWidget(progress_bar)
            goal_group.setLayout(goal_layout)
            
            self.goals_progress_layout.addWidget(goal_group)
        
        # Se não houver metas
        if self.goals_progress_layout.count() == 0:
            goal_label = QLabel("Nenhuma meta definida")
            self.goals_progress_layout.addWidget(goal_label)
        
        conn.close()
    
    def add_transaction(self):
        dialog = TransactionDialog(self.user_id, self.db_manager, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO transactions (user_id, type, category, amount, description, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.user_id, data["type"], data["category"], data["amount"], 
                 data["description"], data["date"]))
            
            conn.commit()
            conn.close()
            
            self.load_transactions()
            self.update_dashboard()
    
    def edit_transaction(self):
        selected_row = self.transactions_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione uma transação para editar")
            return
        
        transaction_id = int(self.transactions_table.item(selected_row, 0).text())
        
        dialog = TransactionDialog(self.user_id, self.db_manager, transaction_id, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE transactions 
                SET type = ?, category = ?, amount = ?, description = ?, date = ?
                WHERE id = ? AND user_id = ?
            """, (data["type"], data["category"], data["amount"], data["description"], 
                 data["date"], transaction_id, self.user_id))
            
            conn.commit()
            conn.close()
            
            self.load_transactions()
            self.update_dashboard()
    
    def delete_transaction(self):
        selected_row = self.transactions_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione uma transação para excluir")
            return
        
        transaction_id = int(self.transactions_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(self, "Confirmar", 
                                    "Tem certeza que deseja excluir esta transação?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", 
                          (transaction_id, self.user_id))
            
            conn.commit()
            conn.close()
            
            self.load_transactions()
            self.update_dashboard()
    
    def add_budget(self):
        dialog = BudgetDialog(self.user_id, self.db_manager, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO budgets (user_id, category, amount, month, year)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.user_id, data["category"], data["amount"], 
                     data["month"], data["year"]))
                
                conn.commit()
                QMessageBox.information(self, "Sucesso", "Orçamento adicionado com sucesso")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erro", "Já existe um orçamento para esta categoria neste mês")
            finally:
                conn.close()
            
            self.load_budgets()
            self.update_dashboard()
    
    def edit_budget(self):
        selected_row = self.budgets_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione um orçamento para editar")
            return
        
        budget_id = int(self.budgets_table.item(selected_row, 0).text())
        
        dialog = BudgetDialog(self.user_id, self.db_manager, budget_id, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE budgets 
                    SET category = ?, amount = ?, month = ?, year = ?
                    WHERE id = ? AND user_id = ?
                """, (data["category"], data["amount"], data["month"], 
                     data["year"], budget_id, self.user_id))
                
                conn.commit()
                QMessageBox.information(self, "Sucesso", "Orçamento atualizado com sucesso")
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erro", "Já existe um orçamento para esta categoria neste mês")
            finally:
                conn.close()
            
            self.load_budgets()
            self.update_dashboard()
    
    def delete_budget(self):
        selected_row = self.budgets_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione um orçamento para excluir")
            return
        
        budget_id = int(self.budgets_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(self, "Confirmar", 
                                    "Tem certeza que deseja excluir este orçamento?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM budgets WHERE id = ? AND user_id = ?", 
                          (budget_id, self.user_id))
            
            conn.commit()
            conn.close()
            
            self.load_budgets()
            self.update_dashboard()
    
    def add_goal(self):
        dialog = GoalDialog(self.user_id, self.db_manager, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO goals (user_id, title, target_amount, current_amount, deadline)
                VALUES (?, ?, ?, ?, ?)
            """, (self.user_id, data["title"], data["target_amount"], 
                 data["current_amount"], data["deadline"]))
            
            conn.commit()
            conn.close()
            
            self.load_goals()
            self.update_dashboard()
    
    def edit_goal(self):
        selected_row = self.goals_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione uma meta para editar")
            return
        
        goal_id = int(self.goals_table.item(selected_row, 0).text())
        
        dialog = GoalDialog(self.user_id, self.db_manager, goal_id, parent=self)
        if dialog.exec_():
            data = dialog.get_data()
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE goals 
                SET title = ?, target_amount = ?, current_amount = ?, deadline = ?
                WHERE id = ? AND user_id = ?
            """, (data["title"], data["target_amount"], data["current_amount"], 
                 data["deadline"], goal_id, self.user_id))
            
            conn.commit()
            conn.close()
            
            self.load_goals()
            self.update_dashboard()
    
    def delete_goal(self):
        selected_row = self.goals_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione uma meta para excluir")
            return
        
        goal_id = int(self.goals_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(self, "Confirmar", 
                                    "Tem certeza que deseja excluir esta meta?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", 
                          (goal_id, self.user_id))
            
            conn.commit()
            conn.close()
            
            self.load_goals()
            self.update_dashboard()
    
    def contribute_to_goal(self):
        selected_row = self.goals_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Erro", "Selecione uma meta para contribuir")
            return
        
        goal_id = int(self.goals_table.item(selected_row, 0).text())
        current_amount = float(self.goals_table.item(selected_row, 3).text())
        target_amount = float(self.goals_table.item(selected_row, 2).text())
        
        amount, ok = QInputDialog.getDouble(self, "Contribuir para Meta", 
                                           "Valor da contribuição:", 
                                           decimals=2, min=0.01, max=target_amount - current_amount)
        
        if ok:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE goals 
                SET current_amount = current_amount + ?
                WHERE id = ? AND user_id = ?
            """, (amount, goal_id, self.user_id))
            
            # Registrar a contribuição como uma transação
            cursor.execute("""
                INSERT INTO transactions (user_id, type, category, amount, description, date)
                VALUES (?, 'Despesa', 'Meta Financeira', ?, 'Contribuição para meta', ?)
            """, (self.user_id, amount, QDate.currentDate().toString("yyyy-MM-dd")))
            
            conn.commit()
            conn.close()
            
            self.load_goals()
            self.load_transactions()
            self.update_dashboard()
    
    def export_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "", "PDF Files (*.pdf)")
        
        if not file_path:
            return
        
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        heading_style = styles["Heading2"]
        normal_style = styles["Normal"]
        
        # Título
        elements.append(Paragraph("Relatório Financeiro Pessoal", title_style))
        elements.append(Paragraph(f"Usuário: {self.username}", normal_style))
        elements.append(Paragraph(f"Data: {QDate.currentDate().toString('dd/MM/yyyy')}", normal_style))
        elements.append(Paragraph("<br/>", normal_style))
        
        # Resumo
        elements.append(Paragraph("Resumo Financeiro", heading_style))
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Receita'", 
                      (self.user_id,))
        total_income = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Despesa'", 
                      (self.user_id,))
        total_expense = cursor.fetchone()[0] or 0
        
        balance = total_income - total_expense
        
        summary_data = [
            ["Receitas", f"R$ {total_income:.2f}"],
            ["Despesas", f"R$ {total_expense:.2f}"],
            ["Saldo", f"R$ {balance:.2f}"]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
        ]))
        
        elements.append(summary_table)
        elements.append(Paragraph("<br/>", normal_style))
        
        # Transações recentes
        elements.append(Paragraph("Últimas Transações", heading_style))
        
        cursor.execute("""
            SELECT type, category, amount, description, date 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 10
        """, (self.user_id,))
        
        transactions = cursor.fetchall()
        
        if transactions:
            trans_data = [["Tipo", "Categoria", "Valor", "Descrição", "Data"]]
            
            for trans in transactions:
                trans_data.append([
                    trans[0], trans[1], f"R$ {trans[2]:.2f}", 
                    trans[3] or "", trans[4]
                ])
            
            trans_table = Table(trans_data)
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(trans_table)
        else:
            elements.append(Paragraph("Nenhuma transação encontrada.", normal_style))
        
        elements.append(Paragraph("<br/>", normal_style))
        
        # Metas
        elements.append(Paragraph("Metas Financeiras", heading_style))
        
        cursor.execute("SELECT title, target_amount, current_amount, deadline FROM goals WHERE user_id = ?", 
                      (self.user_id,))
        
        goals = cursor.fetchall()
        
        if goals:
            goals_data = [["Título", "Valor Alvo", "Valor Atual", "Progresso", "Prazo"]]
            
            for goal in goals:
                progress = (goal[2] / goal[1]) * 100 if goal[1] > 0 else 0
                goals_data.append([
                    goal[0], f"R$ {goal[1]:.2f}", f"R$ {goal[2]:.2f}", 
                    f"{progress:.1f}%", goal[3]
                ])
            
            goals_table = Table(goals_data)
            goals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(goals_table)
        else:
            elements.append(Paragraph("Nenhuma meta encontrada.", normal_style))
        
        conn.close()
        
        # Gerar PDF
        doc.build(elements)
        QMessageBox.information(self, "Sucesso", "PDF exportado com sucesso")
    
    def export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Excel", "", "Excel Files (*.xlsx)")
        
        if not file_path:
            return
        
        conn = self.db_manager.get_connection()
        
        # Transações
        transactions_df = pd.read_sql_query(
            "SELECT type, category, amount, description, date FROM transactions WHERE user_id = ?", 
            conn, params=[self.user_id]
        )
        
        # Orçamentos
        budgets_df = pd.read_sql_query(
            "SELECT category, amount, month, year FROM budgets WHERE user_id = ?", 
            conn, params=[self.user_id]
        )
        
        # Metas
        goals_df = pd.read_sql_query(
            "SELECT title, target_amount, current_amount, deadline FROM goals WHERE user_id = ?", 
            conn, params=[self.user_id]
        )
        
        conn.close()
        
        # Criar arquivo Excel com múltiplas abas
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            transactions_df.to_excel(writer, sheet_name='Transações', index=False)
            budgets_df.to_excel(writer, sheet_name='Orçamentos', index=False)
            goals_df.to_excel(writer, sheet_name='Metas', index=False)
        
        QMessageBox.information(self, "Sucesso", "Excel exportado com sucesso")
    
    def sync_with_cloud(self):
        # Mostrar diálogo de progresso
        self.progress_dialog = QProgressDialog("Sincronizando com a nuvem...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowTitle("Sincronização")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.cancel_sync)
        self.progress_dialog.show()
        
        # Executar sincronização em thread separada
        self.sync_thread = threading.Thread(target=self.sync_thread_function)
        self.sync_thread.daemon = True
        self.sync_thread.start()
    
    def sync_thread_function(self):
        try:
            self.sync_signals.progress.emit(10)
            
            # Exportar dados para um arquivo temporário
            temp_file = "temp_finance_data.xlsx"
            
            conn = self.db_manager.get_connection()
            
            # Transações
            transactions_df = pd.read_sql_query(
                "SELECT * FROM transactions WHERE user_id = ?", 
                conn, params=[self.user_id]
            )
            
            # Orçamentos
            budgets_df = pd.read_sql_query(
                "SELECT * FROM budgets WHERE user_id = ?", 
                conn, params=[self.user_id]
            )
            
            # Metas
            goals_df = pd.read_sql_query(
                "SELECT * FROM goals WHERE user_id = ?", 
                conn, params=[self.user_id]
            )
            
            conn.close()
            
            self.sync_signals.progress.emit(30)
            
            # Criar arquivo Excel temporário
            with pd.ExcelWriter(temp_file, engine='openpyxl') as writer:
                transactions_df.to_excel(writer, sheet_name='Transações', index=False)
                budgets_df.to_excel(writer, sheet_name='Orçamentos', index=False)
                goals_df.to_excel(writer, sheet_name='Metas', index=False)
            
            self.sync_signals.progress.emit(60)
            
            # Fazer upload para o Cloudinary
            response = cloudinary.uploader.upload(
                temp_file,
                public_id=f"finance_app/{self.user_id}_{int(datetime.datetime.now().timestamp())}",
                resource_type="raw"
            )
            
            self.sync_signals.progress.emit(90)
            
            # Remover arquivo temporário
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            self.sync_signals.progress.emit(100)
            self.sync_signals.finished.emit()
            
        except Exception as e:
            self.sync_signals.error.emit(str(e))
    
    def update_sync_progress(self, value):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(value)
    
    def sync_finished(self):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.accept()
        QMessageBox.information(self, "Sucesso", "Sincronização concluída com sucesso")
    
    def sync_error(self, error_msg):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.reject()
        QMessageBox.warning(self, "Erro", f"Falha na sincronização: {error_msg}")
    
    def cancel_sync(self):
        # Implementar cancelamento se necessário
        pass
    
    def logout(self):
        self.close()

class FinanceApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.db_manager = DatabaseManager()
        self.auth_dialog = AuthDialog(self.db_manager)
        self.main_window = None
        
        if self.auth_dialog.exec_():
            self.main_window = MainWindow(
                self.auth_dialog.user_id, 
                self.auth_dialog.username, 
                self.db_manager
            )
            self.main_window.show()
        else:
            self.quit()

def main():
    app = FinanceApp(sys.argv)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()