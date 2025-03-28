# main.py
import os
import json
import sys
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from core.asset_manager import AssetManager
from utils.paths import get_projects_data_path
from utils.dialogs import AddProjectDialog

DEFAULT_PROJECT_THUMBNAIL = "D:/OneDrive/Desktop/Projects/default_project_thumbnail.jpg"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blender Asset Manager")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.project_list = QListWidget()
        # Thiết lập chế độ hiển thị dạng lưới (IconMode)
        self.project_list.setViewMode(QListWidget.IconMode)
        self.project_list.setIconSize(QSize(150, 150))  # Kích thước hình ảnh
        self.project_list.setGridSize(QSize(200, 200))  # Kích thước ô
        self.project_list.setSpacing(10)  # Khoảng cách giữa các ô
        self.project_list.setWrapping(True)  # Tự động xuống dòng
        self.project_list.setResizeMode(QListWidget.Adjust)  # Điều chỉnh kích thước ô tự động
        self.project_list.itemDoubleClicked.connect(self.open_project)
        self.layout.addWidget(self.project_list)

        self.add_project_btn = QPushButton("Add New Project")
        self.add_project_btn.clicked.connect(self.add_project)
        self.layout.addWidget(self.add_project_btn)

        self.load_projects()

        # Áp dụng style cho MainWindow
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QListWidget {
                background-color: #2b2b2b;  /* Màu nền của toàn bộ danh sách */
                border: none;
            }
            QListWidget::item {
                background-color: #3c3f41;  /* Màu nền của từng ô */
                border: 1px solid #555555;  /* Viền của từng ô */
                border-radius: 5px;  /* Bo góc */
                color: #ffffff;  /* Màu chữ */
                font-family: 'Arial';
                font-size: 14px;
                padding: 5px;  /* Khoảng cách bên trong ô */
            }
            QListWidget::item:selected {
                background-color: #4a90e2;  /* Màu khi chọn */
                border: 1px solid #4a90e2;  /* Viền khi chọn */
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
                    # Thiết lập hình ảnh đại diện
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
                project_short = project_name  # Nếu Short rỗng, dùng Project Name

            projects_dir = os.path.dirname(get_projects_data_path())
            project_path = os.path.join(projects_dir, project_name)
            os.makedirs(project_path, exist_ok=True)

            # Tạo thư mục icons trong project_path
            icons_dir = os.path.join(project_path, "icons")
            os.makedirs(icons_dir, exist_ok=True)

            # Sao chép hình ảnh mặc định vào thư mục dự án
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
                "thumbnail": project_thumbnail  # Lưu đường dẫn thumbnail
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
        self.asset_manager = AssetManager(project_path, self.show_lobby)
        self.asset_manager.show()
        self.hide()

    def show_lobby(self):
        self.show()
        self.asset_manager.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())