# utils/dialogs.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox

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
        self.type_input = QComboBox()  # Thay QLineEdit bằng QComboBox
        self.type_input.addItems(["Characters", "Props", "VFXs"])  # Thêm các lựa chọn
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

    def get_data(self):
        return self.type_input.currentText(), self.name_input.text()  # Lấy giá trị từ QComboBox