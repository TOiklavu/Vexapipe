# D:\OneDrive\Desktop\Projects\Vexapipe\main.py
import os
import json
import sys
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QDesktopWidget
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize, QSettings
from core.asset_manager import AssetManager
from utils.paths import get_projects_data_path
from utils.dialogs import AddProjectDialog, LoginDialog

BASE_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/App"
RESOURCES_DIR = os.path.join(BASE_DIR, "Resources")
PROJECTS_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/Projects"
PROJECT_DATA_DIR = os.path.join(RESOURCES_DIR, "ProjectData")

DEFAULT_PROJECT_THUMBNAIL = os.path.join(RESOURCES_DIR, "default_project_thumbnail.jpg")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
LAST_LOGIN_FILE = os.path.join(BASE_DIR, "last_login.json")
LAST_PROJECT_FILE = os.path.join(BASE_DIR, "last_project.json")
DEFAULT_ICONS_DIR = os.path.join(RESOURCES_DIR, "default_icons")

class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle(f"Blender Asset Manager - Logged in as {self.current_user['username']}")
        
        # Khôi phục vị trí và kích thước cửa sổ
        self.settings = QSettings("MyCompany", "BlenderAssetManager")
        self.restoreGeometry(self.settings.value("MainWindow/geometry", b""))
        
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

        # Thêm nút Logout
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        self.layout.addWidget(self.logout_btn)

        self.add_project_btn = QPushButton("Add New Project")
        self.add_project_btn.clicked.connect(self.add_project)
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

    def closeEvent(self, event):
        # Lưu vị trí và kích thước cửa sổ khi đóng
        self.settings.setValue("MainWindow/geometry", self.saveGeometry())
        super().closeEvent(event)

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
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            project_name, project_short = dialog.get_data()
            if not project_name:
                return
            if not project_short:
                project_short = project_name

            # Tạo thư mục dự án trong Projects (chỉ chứa assets)
            project_path = os.path.join(PROJECTS_DIR, project_name)
            os.makedirs(project_path, exist_ok=True)
            assets_dir = os.path.join(project_path, "assets")
            os.makedirs(assets_dir, exist_ok=True)

            # Tạo thư mục trong ProjectData để lưu dữ liệu
            project_data_dir = os.path.join(PROJECT_DATA_DIR, project_name)
            os.makedirs(project_data_dir, exist_ok=True)

            # Tạo thư mục icons trong ProjectData và sao chép các file icon
            project_icons_dir = os.path.join(project_data_dir, "icons")
            os.makedirs(project_icons_dir, exist_ok=True)
            if os.path.exists(DEFAULT_ICONS_DIR):
                for icon_file in os.listdir(DEFAULT_ICONS_DIR):
                    src_path = os.path.join(DEFAULT_ICONS_DIR, icon_file)
                    dst_path = os.path.join(project_icons_dir, icon_file)
                    if os.path.isfile(src_path) and not os.path.exists(dst_path):
                        shutil.copy(src_path, dst_path)

            # Lưu thumbnail vào ProjectData
            project_thumbnail = os.path.join(project_data_dir, "thumbnail.jpg")
            if os.path.exists(DEFAULT_PROJECT_THUMBNAIL) and not os.path.exists(project_thumbnail):
                shutil.copy(DEFAULT_PROJECT_THUMBNAIL, project_thumbnail)

            # Lưu projects.json
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

            # Lưu data.json vào ProjectData
            project_data_file = os.path.join(project_data_dir, "data.json")
            with open(project_data_file, 'w') as f:
                json.dump({
                    "assets": [],
                    "section_states": {"Characters": True, "Props": True, "VFXs": True},
                    "short": project_short
                }, f, indent=4)

    def open_project(self, item):
        project_path = item.data(Qt.UserRole)
        # Lưu dự án đang mở vào last_project.json
        with open(LAST_PROJECT_FILE, 'w') as f:
            json.dump({"last_project_path": project_path}, f, indent=4)
        self.asset_manager = AssetManager(project_path, self.show_lobby, self.current_user)
        self.asset_manager.show()
        self.hide()

    def show_lobby(self):
        self.show()
        self.asset_manager.close()

    def logout(self):
        # Xóa file last_login.json
        if os.path.exists(LAST_LOGIN_FILE):
            os.remove(LAST_LOGIN_FILE)
        self.close()
        # Hiển thị lại dialog đăng nhập
        current_user = login()
        if current_user:
            new_window = MainWindow(current_user)
            new_window.show()
        else:
            sys.exit()

def login():
    dialog = LoginDialog()
    # Đặt dialog ở giữa màn hình
    dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
    if dialog.exec_():
        username, password = dialog.get_data()
        if not username or not password:
            msg = QMessageBox()
            msg.setWindowTitle("Login Failed")
            msg.setText("Username and password cannot be empty!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.move(QDesktopWidget().availableGeometry().center() - msg.rect().center())
            msg.exec_()
            return None

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users_data = json.load(f)
                for user in users_data["users"]:
                    if user["username"] == username and user["password"] == password:
                        # Lưu thông tin đăng nhập vào last_login.json
                        with open(LAST_LOGIN_FILE, 'w') as f:
                            json.dump(user, f, indent=4)
                        return user
        msg = QMessageBox()
        msg.setWindowTitle("Login Failed")
        msg.setText("Invalid username or password!")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.move(QDesktopWidget().availableGeometry().center() - msg.rect().center())
        msg.exec_()
    return None

def check_last_login():
    if os.path.exists(LAST_LOGIN_FILE):
        with open(LAST_LOGIN_FILE, 'r') as f:
            last_user = json.load(f)
            # Kiểm tra xem thông tin có hợp lệ không
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as uf:
                    users_data = json.load(uf)
                    for user in users_data["users"]:
                        if (user["username"] == last_user["username"] and 
                            user["password"] == last_user["password"]):
                            return last_user
    return None

def check_last_project():
    if os.path.exists(LAST_PROJECT_FILE):
        with open(LAST_PROJECT_FILE, 'r') as f:
            data = json.load(f)
            last_project_path = data.get("last_project_path", "")
            if last_project_path and os.path.exists(last_project_path):
                return last_project_path
    return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    current_user = check_last_login()
    if not current_user:
        while not current_user:
            current_user = login()
            if not current_user:
                if QMessageBox.question(None, "Exit", "Do you want to exit the application?",
                                        QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                    sys.exit()

    # Luôn tạo MainWindow
    main_window = MainWindow(current_user)

    # Kiểm tra dự án cuối cùng được mở
    last_project_path = check_last_project()
    if last_project_path:
        # Nếu có dự án cuối cùng, mở AssetManager và ẩn MainWindow
        asset_manager = AssetManager(last_project_path, main_window.show_lobby, current_user)
        main_window.asset_manager = asset_manager  # Lưu tham chiếu đến AssetManager
        asset_manager.show()
        main_window.hide()
    else:
        # Nếu không, hiển thị MainWindow
        main_window.show()

    sys.exit(app.exec_())