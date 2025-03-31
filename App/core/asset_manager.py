# D:\OneDrive\Desktop\Projects\Vexapipe\App\core\asset_manager.py
import os
import json
import subprocess
import time
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QDesktopWidget)
from PyQt5.QtGui import QPixmap, QIcon, QColor
from PyQt5.QtCore import Qt, QSettings
from utils.paths import get_project_data_path
from utils.dialogs import AddAssetDialog

BLENDER_PATH = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"
RESOURCES_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/App/Resources"
TEMPLATE_BLEND_FILE = os.path.join(RESOURCES_DIR, "template.blend")
DEFAULT_THUMBNAIL = os.path.join(RESOURCES_DIR, "default_thumbnail.jpg")
USERS_FILE = "D:/OneDrive/Desktop/Projects/Vexapipe/App/users.json"

class AssetManager(QMainWindow):
    def __init__(self, project_path, show_lobby_callback, current_user):
        super().__init__()
        self.project_path = project_path
        self.show_lobby_callback = show_lobby_callback
        self.current_user = current_user
        self.project_name = os.path.basename(project_path)
        self.icons_dir = os.path.join(RESOURCES_DIR, "ProjectData", self.project_name, "icons")
        self.setWindowTitle(f"Blender Asset Manager - {self.project_name} (Logged in as {self.current_user['username']})")
        
        # Khôi phục vị trí và kích thước cửa sổ
        self.settings = QSettings("MyCompany", "BlenderAssetManager")
        self.restoreGeometry(self.settings.value("AssetManager/geometry", b""))

        self.data_file = get_project_data_path(project_path)
        self.assets = self.load_data()
        self.project_short = self.assets.get("short", self.project_name)

        self.team_members = self.load_team_members()

        self.current_file = None
        self.current_thumbnail = None

        self.section_states = {
            "Characters": True,
            "Props": True,
            "VFXs": True
        }

        self.asset_lists = {
            "Characters": None,
            "Props": None,
            "VFXs": None
        }

        self.left_widget = None
        self.asset_table = None

        self.init_ui()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QListWidget {
                background-color: #3c3f41;
                border: 1px solid #555555;
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3f41;
            }
            QTabBar::tab {
                background-color: #3c3f41;
                color: #ffffff;
                padding: 8px;
                font-family: 'Arial';
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
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
            QLabel {
                color: #ffffff;
                font-family: 'Arial';
                font-size: 14px;
            }
            QPushButton#sectionButton {
                background-color: #3c3f41;
                color: #ffffff;
                border: none;
                padding: 5px;
                text-align: left;
                font-family: 'Arial';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#sectionButton:hover {
                background-color: #4a90e2;
            }
            QTableWidget {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: 'Arial';
                font-size: 14px;
            }
            QTableWidget::item {
                background-color: #3c3f41;
                border: 1px solid #555555;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
            }
            QComboBox {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

    def closeEvent(self, event):
        # Lưu vị trí và kích thước cửa sổ khi đóng
        self.settings.setValue("AssetManager/geometry", self.saveGeometry())
        super().closeEvent(event)

    def load_team_members(self):
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users_data = json.load(f)
                return [user["username"] for user in users_data["users"]]
        return []

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {"assets": [], "section_states": {"Characters": True, "Props": True, "VFXs": True}, "short": ""}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            self.assets["short"] = self.project_short
            json.dump(self.assets, f, indent=4)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        
        home_btn = QPushButton("Home")
        home_icon_path = os.path.join(self.icons_dir, "home_icon.png")
        if os.path.exists(home_icon_path):
            home_btn.setIcon(QIcon(home_icon_path))
        home_btn.clicked.connect(self.show_lobby_callback)
        left_layout.addWidget(home_btn)

        left_layout.addWidget(QLabel("Assets"))

        for asset_type in ["Characters", "Props", "VFXs"]:
            section_btn = QPushButton(asset_type)
            section_btn.setObjectName("sectionButton")
            section_btn.setProperty("asset_type", asset_type)
            down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
            if os.path.exists(down_arrow_path):
                section_btn.setIcon(QIcon(down_arrow_path))
            else:
                section_btn.setText(f"{asset_type} ▼")
            section_btn.clicked.connect(lambda checked, at=asset_type: self.toggle_section(at))
            left_layout.addWidget(section_btn)

            asset_list = QListWidget()
            asset_list.itemClicked.connect(self.show_asset_details)
            self.asset_lists[asset_type] = asset_list
            left_layout.addWidget(asset_list)

        add_asset_btn = QPushButton("Add Asset")
        add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
        if os.path.exists(add_icon_path):
            add_asset_btn.setIcon(QIcon(add_icon_path))
        add_asset_btn.clicked.connect(self.add_asset)
        left_layout.addWidget(add_asset_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_icon_path = os.path.join(self.icons_dir, "refresh_icon.png")
        if os.path.exists(refresh_icon_path):
            refresh_btn.setIcon(QIcon(refresh_icon_path))
        refresh_btn.clicked.connect(self.refresh_data)
        left_layout.addWidget(refresh_btn)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.tabs = QTabWidget()
        self.scenes_tab = QWidget()
        self.products_tab = QWidget()
        self.media_tab = QWidget()
        self.libraries_tab = QWidget()

        scenes_icon_path = os.path.join(self.icons_dir, "scenes_icon.png")
        products_icon_path = os.path.join(self.icons_dir, "products_icon.png")
        media_icon_path = os.path.join(self.icons_dir, "media_icon.png")
        libraries_icon_path = os.path.join(self.icons_dir, "libraries_icon.png")

        self.tabs.addTab(self.scenes_tab, QIcon(scenes_icon_path) if os.path.exists(scenes_icon_path) else QIcon(), "Scenes")
        self.tabs.addTab(self.products_tab, QIcon(products_icon_path) if os.path.exists(products_icon_path) else QIcon(), "Products")
        self.tabs.addTab(self.media_tab, QIcon(media_icon_path) if os.path.exists(media_icon_path) else QIcon(), "Media")
        self.tabs.addTab(self.libraries_tab, QIcon(libraries_icon_path) if os.path.exists(libraries_icon_path) else QIcon(), "Libraries")

        scenes_layout = QVBoxLayout(self.scenes_tab)
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(4)
        self.asset_table.setHorizontalHeaderLabels(["Asset Name", "Asset Type", "Status", "Assignee"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        scenes_layout.addWidget(self.asset_table)

        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)

        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.thumbnail_label)

        self.description_label = QLabel("Scene: \nName: \nVersion: \nNote: \nCreated: ")
        self.description_label.setStyleSheet("QLabel { background-color: #3c3f41; padding: 10px; }")
        self.description_label.setMouseTracking(True)
        self.description_label.mouseDoubleClickEvent = self.open_in_blender
        info_layout.addWidget(self.description_label)

        detail_layout.addWidget(info_panel)

        self.open_file_btn = QPushButton("Open in Blender")
        blender_icon_path = os.path.join(self.icons_dir, "blender_icon.png")
        if os.path.exists(blender_icon_path):
            self.open_file_btn.setIcon(QIcon(blender_icon_path))
        self.open_file_btn.clicked.connect(self.open_in_blender)
        detail_layout.addWidget(self.open_file_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { background-color: #3c3f41; padding: 5px; color: #aaaaaa; }")

        right_layout.addWidget(self.tabs)
        right_layout.addWidget(self.detail_widget)
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(self.left_widget, 1)
        main_layout.addWidget(right_widget, 3)

        main_layout.setSpacing(10)
        left_layout.setSpacing(10)
        right_layout.setSpacing(10)
        detail_layout.setSpacing(10)

        self.load_assets()

    def toggle_section(self, asset_type):
        self.section_states[asset_type] = not self.section_states[asset_type]
        asset_list = self.asset_lists[asset_type]
        asset_list.setVisible(self.section_states[asset_type])

        section_btn = None
        for btn in self.left_widget.findChildren(QPushButton):
            if btn.property("asset_type") == asset_type:
                section_btn = btn
                break

        if section_btn:
            if self.section_states[asset_type]:
                down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                if os.path.exists(down_arrow_path):
                    section_btn.setIcon(QIcon(down_arrow_path))
                else:
                    section_btn.setText(f"{asset_type} ▼")
            else:
                right_arrow_path = os.path.join(self.icons_dir, "right_arrow.png")
                if os.path.exists(right_arrow_path):
                    section_btn.setIcon(QIcon(right_arrow_path))
                else:
                    section_btn.setText(f"{asset_type} ►")
        else:
            print(f"Warning: Could not find section button for {asset_type}")

        self.assets["section_states"] = self.section_states
        self.save_data()

    def load_assets(self):
        type_counts = {"Characters": 0, "Props": 0, "VFXs": 0}
        for asset in self.assets["assets"]:
            asset_type = asset["type"]
            if asset_type in type_counts:
                type_counts[asset_type] += 1

        for asset_type in self.asset_lists:
            self.asset_lists[asset_type].clear()

        for asset in self.assets["assets"]:
            asset_type = asset["type"]
            if asset_type in self.asset_lists:
                self.asset_lists[asset_type].addItem(asset["name"])

        for asset_type in self.asset_lists:
            section_btn = None
            for btn in self.left_widget.findChildren(QPushButton):
                if btn.property("asset_type") == asset_type:
                    section_btn = btn
                    break
            if section_btn:
                section_btn.setText(f"{asset_type} ({type_counts[asset_type]})")
            self.asset_lists[asset_type].setVisible(self.section_states[asset_type])

        self.update_asset_table()

    def update_asset_table(self):
        self.asset_table.setRowCount(len(self.assets["assets"]))
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {
            "To Do": "#ff5555",
            "Inprogress": "#55aaff",
            "Pending Review": "#ffaa00",
            "Done": "#55ff55"
        }

        for row, asset in enumerate(self.assets["assets"]):
            name_item = QTableWidgetItem(asset["name"])
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.asset_table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem(asset["type"])
            type_item.setFlags(type_item.flags() ^ Qt.ItemIsEditable)
            self.asset_table.setItem(row, 1, type_item)

            status_combo = QComboBox()
            status_combo.addItems(status_options)
            current_status = asset.get("status", "To Do")
            status_combo.setCurrentText(current_status)
            status_combo.currentIndexChanged.connect(lambda index, r=row: self.on_status_changed(r, index))
            self.asset_table.setCellWidget(row, 2, status_combo)
            self.asset_table.setItem(row, 2, QTableWidgetItem())
            self.asset_table.item(row, 2).setBackground(QColor(status_colors[current_status]))

            assignee_combo = QComboBox()
            assignee_combo.addItem("")
            assignee_combo.addItems(self.team_members)
            current_assignee = asset.get("assignee", "")
            assignee_combo.setCurrentText(current_assignee)
            assignee_combo.currentIndexChanged.connect(lambda index, r=row: self.on_assignee_changed(r, index))
            self.asset_table.setCellWidget(row, 3, assignee_combo)

        self.asset_table.resizeColumnsToContents()

    def on_status_changed(self, row, index):
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {
            "To Do": "#ff5555",
            "Inprogress": "#55aaff",
            "Pending Review": "#ffaa00",
            "Done": "#55ff55"
        }
        new_status = status_options[index]
        self.assets["assets"][row]["status"] = new_status
        self.save_data()
        self.asset_table.item(row, 2).setBackground(QColor(status_colors[new_status]))

    def on_assignee_changed(self, row, index):
        assignee_combo = self.asset_table.cellWidget(row, 3)
        new_assignee = assignee_combo.currentText()
        old_assignee = self.assets["assets"][row].get("assignee", "")
        self.assets["assets"][row]["assignee"] = new_assignee
        self.save_data()

        # Hiển thị thông báo nếu người được assign là người đang đăng nhập
        if new_assignee and new_assignee == self.current_user["username"] and new_assignee != old_assignee:
            asset_name = self.assets["assets"][row]["name"]
            msg = QMessageBox()
            msg.setWindowTitle("Task Assigned")
            msg.setText(f"You have been assigned to task: {asset_name}")
            msg.setStandardButtons(QMessageBox.Ok)
            # Đặt pop-up ở giữa màn hình
            msg.move(QDesktopWidget().availableGeometry().center() - msg.rect().center())
            msg.exec_()

    def show_asset_details(self, item):
        asset_name = item.text()
        for row, asset in enumerate(self.assets["assets"]):
            if asset["name"] == asset_name:
                asset_type = asset.get("type", "Unknown")
                latest_file = f"{self.project_short}_{asset_name}.blend"
                latest_file_path = os.path.join(self.project_path, f"assets/{asset_type.lower()}/{asset_name}/{self.project_short}_{asset_name}.blend")
                
                # Xác định phiên bản
                asset_dir = os.path.join(self.project_path, f"assets/{asset_type.lower()}/{asset_name}")
                old_dir = os.path.join(asset_dir, ".old")
                latest_version = "v001"  # Mặc định là v001

                if os.path.exists(old_dir):
                    # Liệt kê các file trong thư mục .old
                    old_files = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]
                    # Tìm các file có định dạng <project_short>_<asset_name>_vXXX.blend
                    version_files = [f for f in old_files if f.startswith(f"{self.project_short}_{asset_name}_v") and f.endswith(".blend")]
                    if version_files:
                        # Lấy số phiên bản từ tên file (ví dụ: v001 -> 001)
                        versions = []
                        for f in version_files:
                            try:
                                version_str = f.replace(f"{self.project_short}_{asset_name}_v", "").replace(".blend", "")
                                version_num = int(version_str)
                                versions.append(version_num)
                            except ValueError:
                                continue
                        if versions:
                            # Tìm phiên bản cao nhất và tăng lên 1
                            max_version = max(versions)
                            latest_version = f"v{max_version + 1:03d}"  # Ví dụ: 2 -> v003

                created_time = "Unknown"
                if os.path.exists(latest_file_path):
                    created_time = datetime.fromtimestamp(os.path.getctime(latest_file_path)).strftime("%Y-%m-%d %H:%M:%S")

                self.description_label.setText(
                    f"Scene: {latest_file}\n"
                    f"Version: {latest_version}\n"
                    f"Created: {created_time}"
                )

                self.current_thumbnail = os.path.join(self.project_path, f"assets/{asset_type.lower()}/{asset_name}/thumbnail.jpg")
                if self.current_thumbnail and os.path.exists(self.current_thumbnail):
                    pixmap = QPixmap(self.current_thumbnail)
                    if not pixmap.isNull():
                        self.thumbnail_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                    else:
                        pixmap = QPixmap(DEFAULT_THUMBNAIL)
                        self.thumbnail_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                else:
                    pixmap = QPixmap(DEFAULT_THUMBNAIL)
                    self.thumbnail_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))

                self.current_file = latest_file_path
                if not os.path.exists(self.current_file):
                    self.open_file_btn.setEnabled(False)
                    self.description_label.setText(
                        f"Scene: {latest_file}\n"
                        f"Version: {latest_version}\n"
                        f"Created: {created_time} (File not found)"
                    )
                else:
                    self.open_file_btn.setEnabled(True)

                self.asset_table.clearSelection()
                self.asset_table.selectRow(row)
                self.asset_table.setFocus()
                break

    def open_in_blender(self, event=None):
        if self.current_file and os.path.exists(self.current_file):
            try:
                with open(self.current_file, "rb") as f:
                    header = f.read(7)
                    if header != b"BLENDER":
                        self.status_label.setText(f"Error: '{self.current_file}' is not a valid Blender file")
                        return
                process = subprocess.Popen([BLENDER_PATH, self.current_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.status_label.setText(f"Opened '{os.path.basename(self.current_file)}' in Blender")
            except FileNotFoundError:
                self.status_label.setText(f"Blender executable not found at: {BLENDER_PATH}")
            except Exception as e:
                self.status_label.setText(f"Error: {str(e)}")
        else:
            self.status_label.setText("No valid file to open")

    def add_asset(self):
        dialog = AddAssetDialog(self)
        # Đặt dialog ở giữa màn hình
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            asset_type, asset_name = dialog.get_data()
            if not asset_name:
                self.status_label.setText("Asset name cannot be empty!")
                return

            asset_type_lower = asset_type.lower()
            asset_dir = os.path.join(self.project_path, f"assets/{asset_type_lower}/{asset_name}")
            textures_dir = os.path.join(asset_dir, "textures")
            outputs_dir = os.path.join(asset_dir, "outputs")
            latest_file = os.path.join(asset_dir, f"{self.project_short}_{asset_name}.blend")

            try:
                os.makedirs(asset_dir, exist_ok=True)
                os.makedirs(textures_dir, exist_ok=True)
                os.makedirs(outputs_dir, exist_ok=True)

                if not os.path.exists(latest_file):
                    if os.path.exists(TEMPLATE_BLEND_FILE):
                        shutil.copy(TEMPLATE_BLEND_FILE, latest_file)
                    else:
                        self.status_label.setText(f"Error: Template file '{TEMPLATE_BLEND_FILE}' not found!")
                        return
            except Exception as e:
                self.status_label.setText(f"Error creating directory or files: {str(e)}")
                return

            new_asset = {
                "name": asset_name,
                "type": asset_type,
                "status": "To Do",
                "assignee": "",
                "versions": [
                    {
                        "version": "v001",
                        "description": "Initial version",
                        "file_path": f"assets/{asset_type_lower}/{asset_name}/{self.project_short}_{asset_name}.blend",
                        "thumbnail": f"assets/{asset_type_lower}/{asset_name}/thumbnail.jpg"
                    }
                ]
            }
            self.assets["assets"].append(new_asset)
            self.save_data()
            self.load_assets()
            self.status_label.setText(f"Asset '{asset_name}' (Type: {asset_type}) created successfully!")

    def refresh_data(self):
        assets_dir = os.path.join(self.project_path, "assets")
        if not os.path.exists(assets_dir):
            self.status_label.setText("Assets directory not found!")
            return

        new_assets = []
        asset_types = ["props", "vfxs", "characters"]

        for asset_type in asset_types:
            type_dir = os.path.join(assets_dir, asset_type)
            if not os.path.exists(type_dir):
                continue

            for asset_name in os.listdir(type_dir):
                asset_dir = os.path.join(type_dir, asset_name)
                if not os.path.isdir(asset_dir):
                    continue

                versions = []
                versions.append({
                    "version": "v001",
                    "description": "Auto-refreshed version",
                    "file_path": f"assets/{asset_type}/{asset_name}/{self.project_short}_{asset_name}.blend",
                    "thumbnail": f"assets/{asset_type}/{asset_name}/thumbnail.jpg"
                })

                versions.sort(key=lambda x: x["version"])

                if versions:
                    existing_asset = next((asset for asset in self.assets["assets"] if asset["name"] == asset_name and asset["type"].lower() == asset_type), None)
                    if existing_asset:
                        new_asset = existing_asset
                    else:
                        new_asset = {
                            "name": asset_name,
                            "type": asset_type.capitalize(),
                            "status": "To Do",
                            "assignee": "",
                            "versions": versions
                        }
                    new_assets.append(new_asset)

        self.assets["assets"] = new_assets
        self.save_data()
        self.load_assets()
        self.status_label.setText("Data refreshed successfully!")