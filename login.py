import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt

BASE_DIR = os.path.dirname(__file__)
USERS_FILE      = os.path.join(BASE_DIR, "data", "users.json")
LATEST_USER_FILE = os.path.join(BASE_DIR, "data", "latest_user.json")

def load_session():
    if not os.path.exists(LATEST_USER_FILE):
        return None
    try:
        with open(LATEST_USER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_user")
    except Exception:
        return None

def save_session(username):
    os.makedirs(os.path.dirname(LATEST_USER_FILE), exist_ok=True)
    with open(LATEST_USER_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_user": username}, f, ensure_ascii=False, indent=2)

def clear_session():
    if os.path.exists(LATEST_USER_FILE):
        os.remove(LATEST_USER_FILE)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập")
        self.setModal(True)
        self.resize(300, 120)

        # Form user/password
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        form.addRow("User:", self.user_edit)
        form.addRow("Password:", self.pass_edit)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.handle_login)
        buttons.rejected.connect(self.reject)

        # Layout chính
        main = QVBoxLayout(self)
        main.addLayout(form)
        main.addWidget(buttons)

        # Load danh sách user
        if not os.path.exists(USERS_FILE):
            QMessageBox.critical(self, "Lỗi", f"Không tìm thấy {USERS_FILE}")
            self.reject()
            return

        with open(USERS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        self.users = data.get("users", [])

        # Nếu có file latest_user.json, pre-fill ô user
        last = load_session()
        if last:
            self.user_edit.setText(last)
            
    def handle_login(self):
        uname = self.user_edit.text().strip()
        pwd   = self.pass_edit.text()
        for u in self.users:
            if u.get("username") == uname and u.get("password") == pwd:
                save_session(uname)
                return self.accept()
        QMessageBox.warning(self, "Thất bại", "User hoặc mật khẩu không đúng.")
