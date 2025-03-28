# utils/dialogs.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox

class AddProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Project")
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        self.name_label = QLabel("Project Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        self.short_label = QLabel("Short Name (Abbreviation):")
        self.short_input = QLineEdit()
        layout.addWidget(self.short_label)
        layout.addWidget(self.short_input)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn)

        self.setLayout(layout)

    def get_data(self):
        return self.name_input.text(), self.short_input.text()

class AddAssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Asset")
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        self.type_label = QLabel("Asset Type:")
        self.type_input = QComboBox()
        self.type_input.addItems(["Characters", "Props", "VFXs"])
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_input)

        self.name_label = QLabel("Asset Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn)

        self.setLayout(layout)

        # Áp dụng style cho dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
            }
            QLineEdit, QComboBox {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
                font-family: 'Arial';
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: none;
                padding: 5px;
                border-radius: 3px;
                font-family: 'Arial';
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)

    def get_data(self):
        return self.type_input.currentText(), self.name_input.text()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.accept)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

        # Áp dụng style cho dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
                font-family: 'Arial';
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: none;
                padding: 5px;
                border-radius: 3px;
                font-family: 'Arial';
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)

    def get_data(self):
        return self.username_input.text(), self.password_input.text()