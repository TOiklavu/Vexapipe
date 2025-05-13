import os
import json
import shutil
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QGridLayout, QScrollArea, QInputDialog, QMessageBox)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize
from utils.paths import resource_path
from core.asset_manager import AssetManager

class Lobby(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Lobby")
        self.setGeometry(100, 100, 800, 600)

        self.projects_dir = resource_path("Projects")
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir)

        self.last_project_file = resource_path("last_project.json")
        self.current_project_window = None

        self.init_ui()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 10px;
                border-radius: 5px;
                font-family: 'Arial';
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a90e2;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
            }
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        title_label = QLabel("Projects")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.grid_layout = QGridLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        self.load_projects()

    def load_projects(self):
        # Xóa các widget cũ trong grid
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Thêm ô "New Project"
        new_project_btn = QPushButton()
        new_project_btn.setFixedSize(200, 150)
        new_project_btn.setText("New Project")
        new_project_btn.clicked.connect(self.create_new_project)
        self.grid_layout.addWidget(new_project_btn, 0, 0)

        # Quét thư mục Projects để hiển thị các dự án
        if not os.path.exists(self.projects_dir):
            QMessageBox.warning(self, "Warning", f"Projects directory not found at: {self.projects_dir}")
            return

        row = 0
        col = 1
        project_found = False
        for project_name in os.listdir(self.projects_dir):
            project_path = os.path.join(self.projects_dir, project_name)
            # Kiểm tra xem có phải là thư mục không
            if not os.path.isdir(project_path):
                continue

            # Kiểm tra file data.json, nếu không có thì tạo mới
            data_file = os.path.join(project_path, "data.json")
            if not os.path.exists(data_file):
                try:
                    with open(data_file, 'w') as f:
                        json.dump({"assets": [], "shots": [], "section_states": {"Characters": True, "Props": True, "VFXs": True}, "shot_section_state": True}, f, indent=4)
                    QMessageBox.information(self, "Info", f"Created missing data.json for project: {project_name}")
                except Exception as e:
                    QMessageBox.warning(self, "Warning", f"Failed to create data.json for {project_name}: {str(e)}")
                    continue

            project_found = True
            project_btn = QPushButton()
            project_btn.setFixedSize(200, 150)

            # Tìm thumbnail (nếu có)
            thumbnail_path = os.path.join(project_path, "thumbnail.jpg")
            if os.path.exists(thumbnail_path):
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    project_btn.setIcon(QIcon(pixmap))
                    project_btn.setIconSize(QSize(180, 120))
            else:
                default_icon_path = resource_path("default_icons/default_project_icon.png")
                if os.path.exists(default_icon_path):
                    project_btn.setIcon(QIcon(default_icon_path))
                    project_btn.setIconSize(QSize(180, 120))
                else:
                    project_btn.setText(project_name + "\n(No Icon)")

            project_btn.setText(project_name)
            project_btn.clicked.connect(lambda checked, path=project_path: self.open_project(path))
            self.grid_layout.addWidget(project_btn, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1

        if not project_found:
            QMessageBox.information(self, "Info", "No existing projects found. Create a new project to start.")

        def create_new_project(self):
            project_name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
            if not ok or not project_name:
                return

            project_path = os.path.join(self.projects_dir, project_name)
            if os.path.exists(project_path):
                QMessageBox.warning(self, "Error", "Project already exists!")
                return

            try:
                os.makedirs(project_path)
                os.makedirs(os.path.join(project_path, "assets/Props"))
                os.makedirs(os.path.join(project_path, "assets/VFXs"))
                os.makedirs(os.path.join(project_path, "assets/Characters"))
                os.makedirs(os.path.join(project_path, "sequencer"))
                os.makedirs(os.path.join(project_path, "icons"))

                with open(os.path.join(project_path, "data.json"), 'w') as f:
                    json.dump({"assets": [], "shots": [], "section_states": {"Characters": True, "Props": True, "VFXs": True}, "shot_section_state": True}, f, indent=4)

                src_icons = resource_path("default_icons")
                dst_icons = os.path.join(project_path, "icons")
                if os.path.exists(src_icons):
                    for icon in os.listdir(src_icons):
                        shutil.copy(os.path.join(src_icons, icon), dst_icons)
                else:
                    QMessageBox.warning(self, "Warning", "Default icons directory not found. Please ensure the 'default_icons' directory exists in Resources.")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
                return

            self.load_projects()
            self.open_project(project_path)

    def open_project(self, project_path):
        with open(self.last_project_file, 'w') as f:
            json.dump({"last_project": project_path}, f, indent=4)

        if self.current_project_window:
            self.current_project_window.close()

        self.current_project_window = AssetManager(project_path, self.show_lobby)
        self.current_project_window.show()
        self.hide()

    def show_lobby(self):
        if self.current_project_window:
            self.current_project_window.close()
            self.current_project_window = None
        self.show()
        self.load_projects()

    def get_last_project(self):
        if os.path.exists(self.last_project_file):
            with open(self.last_project_file, 'r') as f:
                data = json.load(f)
                last_project = data.get("last_project")
                if last_project and os.path.exists(last_project):
                    return last_project
        return None