# D:\OneDrive\Desktop\Projects\Vexapipe\App\utils\dialogs.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout)
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
        self.setModal(True)

        layout = QVBoxLayout()

        # Asset Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Asset Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Characters", "Props", "VFXs"])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Asset Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Asset Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Stage
        stage_layout = QHBoxLayout()
        stage_layout.addWidget(QLabel("Stage:"))
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["Modeling", "Texturing", "Rigging"])
        stage_layout.addWidget(self.stage_combo)
        layout.addLayout(stage_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        self.setLayout(layout)

    def get_data(self):
        return (self.type_combo.currentText(), self.name_edit.text(), self.stage_combo.currentText())

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