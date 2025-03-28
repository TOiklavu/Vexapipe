# main.py
import os
import json
import sys
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from core.asset_manager import AssetManager
from utils.paths import get_projects_data_path
from utils.dialogs import AddProjectDialog, LoginDialog

DEFAULT_PROJECT_THUMBNAIL = "D:/OneDrive/Desktop/Projects/Vexapipe/default_project_thumbnail.jpg"
USERS_FILE = "D:/OneDrive/Desktop/Projects/Vexapipe/users.json"

class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user  # Lưu thông tin người dùng hiện tại
        self.setWindowTitle(f"Blender Asset Manager - Logged in as {self.current_user['username']}")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.project_list = QListWidget()
        self.project_list.setViewMode(QListWidget.IconMode)
        self.project_list.setIconSize(QSize(150, 150))
        self.project_list.setGridSize(QSize(200, 200))
        self.project_list.setSpacing(10)
        self.project_list.setWrapping(True)
        self.project_list.setResizeMode(QListWidget.Adjust)
        self.project_list.itemDoubleClicked.connect(self.open_project)
        self.layout.addWidget(self.project_list)

        self.add_project_btn = QPushButton("Add New Project")
        self.add_project_btn.clicked.connect(self.add_project)
        # Phân quyền: Chỉ admin mới được tạo dự án
        if self.current_user["role"] != "admin":
            self.add_project_btn.setEnabled(False)
            self.add_project_btn.setToolTip("Only admin can create new projects")
        self.layout.addWidget(self.add_project_btn)

        self.load_projects()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QListWidget {
                background-color: #2b2b2b;
                border: none;
            }
            QListWidget::item {
                background-color: #3c3f41;
                border: 1px solid #555555;
                border-radius: 5px;
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                border: 1px solid #4a90e2;
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
            QPushButton:disabled {
                background-color: #555555;
            }
        """)

    def load_projects(self):
        self.project_list.clear()
        data_file = get_projects_data_path()
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for project in data["projects"]:
                    item = QListWidgetItem()
                    item.setText(project["name"])
                    item.setData(Qt.UserRole, project["path"])
                    thumbnail_path = project.get("thumbnail", DEFAULT_PROJECT_THUMBNAIL)
                    if os.path.exists(thumbnail_path):
                        pixmap = QPixmap(thumbnail_path)
                        if not pixmap.isNull():
                            item.setIcon(QIcon(pixmap))
                        else:
                            item.setIcon(QIcon(DEFAULT_PROJECT_THUMBNAIL))
                    else:
                        item.setIcon(QIcon(DEFAULT_PROJECT_THUMBNAIL))
                    self.project_list.addItem(item)

    def add_project(self):
        dialog = AddProjectDialog(self)
        if dialog.exec_():
            project_name, project_short = dialog.get_data()
            if not project_name:
                return
            if not project_short:
                project_short = project_name

            projects_dir = os.path.dirname(get_projects_data_path())
            project_path = os.path.join(projects_dir, project_name)
            os.makedirs(project_path, exist_ok=True)

            icons_dir = os.path.join(project_path, "icons")
            os.makedirs(icons_dir, exist_ok=True)

            project_thumbnail = os.path.join(project_path, "thumbnail.jpg")
            if os.path.exists(DEFAULT_PROJECT_THUMBNAIL) and not os.path.exists(project_thumbnail):
                shutil.copy(DEFAULT_PROJECT_THUMBNAIL, project_thumbnail)

            data_file = get_projects_data_path()
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"projects": []}

            data["projects"].append({
                "name": project_name,
                "short": project_short,
                "path": project_path,
                "thumbnail": project_thumbnail
            })

            with open(data_file, 'w') as f:
                json.dump(data, f, indent=4)

            self.load_projects()

            project_data_file = os.path.join(project_path, "data.json")
            with open(project_data_file, 'w') as f:
                json.dump({
                    "assets": [],
                    "section_states": {"Characters": True, "Props": True, "VFXs": True},
                    "short": project_short
                }, f, indent=4)

    def open_project(self, item):
        project_path = item.data(Qt.UserRole)
        self.asset_manager = AssetManager(project_path, self.show_lobby, self.current_user)
        self.asset_manager.show()
        self.hide()

    def show_lobby(self):
        self.show()
        self.asset_manager.close()

def login():
    dialog = LoginDialog()
    if dialog.exec_():
        username, password = dialog.get_data()
        if not username or not password:
            QMessageBox.warning(None, "Login Failed", "Username and password cannot be empty!")
            return None

        # Đọc file users.json
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users_data = json.load(f)
                for user in users_data["users"]:
                    if user["username"] == username and user["password"] == password:
                        return user
        QMessageBox.warning(None, "Login Failed", "Invalid username or password!")
    return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    current_user = None
    while not current_user:
        current_user = login()
        if not current_user:
            # Nếu người dùng đóng dialog mà không đăng nhập, thoát chương trình
            if QMessageBox.question(None, "Exit", "Do you want to exit the application?",
                                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                sys.exit()
    window = MainWindow(current_user)
    window.show()
    sys.exit(app.exec_())