# D:\OneDrive\Desktop\Projects\Vexapipe\App\utils\dialogs.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QMessageBox, QFileDialog)
from .add_shot_dialog import AddShotDialog

class AddProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Project")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Project Name
        self.name_label = QLabel("Project Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        # Short Name
        self.short_label = QLabel("Short Name (optional):")
        self.short_input = QLineEdit()
        layout.addWidget(self.short_label)
        layout.addWidget(self.short_input)

        # Project Location
        self.location_label = QLabel("Project Location:")
        self.location_input = QLineEdit()
        self.location_input.setReadOnly(True)  # Chỉ đọc, không cho phép chỉnh sửa trực tiếp
        self.location_btn = QPushButton("Browse...")
        self.location_btn.clicked.connect(self.browse_location)
        layout.addWidget(self.location_label)
        layout.addWidget(self.location_input)
        layout.addWidget(self.location_btn)

        # Add button
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.accept)
        layout.addWidget(add_btn)

        self.setLayout(layout)

    def browse_location(self):
        location = QFileDialog.getExistingDirectory(self, "Select Project Location")
        if location:
            self.location_input.setText(location)

    def get_data(self):
        project_name = self.name_input.text().strip()
        short_name = self.short_input.text().strip()
        project_location = self.location_input.text().strip()
        return project_name, short_name, project_location

    
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
        self.users = users
        self.setWindowTitle("Login")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.accept)  # Chấp nhận khi nhấn nút Login
        layout.addWidget(login_btn)
        
        self.setLayout(layout)

    def get_data(self):
        return (self.username_input.text().strip(), self.password_input.text().strip())