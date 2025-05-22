# D:\OneDrive\Desktop\Projects\Vexapipe\App\utils\add_shot_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel

class AddShotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Shot")
        self.setFixedSize(300, 150)

        layout = QVBoxLayout()

        self.name_label = QLabel("Shot Name (e.g., 001):")
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
        return self.name_input.text().strip()