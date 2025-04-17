# D:\OneDrive\Desktop\Projects\Vexapipe\App\utils\dialogs.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QComboBox, QPushButton, QLabel
from .add_shot_dialog import AddShotDialog

class AddProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Project")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()

        self.name_label = QLabel("Project Name:")
        layout.addWidget(self.name_label)

        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        self.short_label = QLabel("Short Name (optional):")
        layout.addWidget(self.short_label)

        self.short_input = QLineEdit()
        layout.addWidget(self.short_input)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.accept)
        layout.addWidget(self.add_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def get_data(self):
        return self.name_input.text().strip(), self.short_input.text().strip()

class AddAssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Asset")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()

        self.type_label = QLabel("Asset Type:")
        layout.addWidget(self.type_label)

        self.type_input = QComboBox()
        self.type_input.addItems(["Characters", "Props", "VFXs"])
        layout.addWidget(self.type_input)

        self.name_label = QLabel("Asset Name:")
        layout.addWidget(self.name_label)

        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.accept)
        layout.addWidget(self.add_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def get_data(self):
        return self.type_input.currentText(), self.name_input.text().strip()

class LoginDialog(QDialog):
    def __init__(self, users, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()

        self.username_label = QLabel("Username:")
        layout.addWidget(self.username_label)

        self.username_input = QComboBox()
        self.username_input.addItems([user["username"] for user in users])
        self.username_input.setEditable(True)
        layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:")
        layout.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.accept)
        layout.addWidget(self.login_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def get_credentials(self):
        return self.username_input.currentText().strip(), self.password_input.text().strip()