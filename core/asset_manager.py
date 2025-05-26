import os
import json
import subprocess
import time
import shutil
import glob
import re
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QDesktopWidget, 
                             QHeaderView, QMenu, QApplication, QSplitter, QLineEdit, QFormLayout, QDialog, QScrollArea, QGridLayout)
from PyQt5.QtGui import QPixmap, QIcon, QColor, QCursor, QFont, QDrag
from PyQt5.QtCore import Qt, QSettings, QEvent, QPoint, QMimeData, QUrl, QSize

BASE_DIR = "F:/GitHub/Vexapipe"

# Custom QPushButton subclass to support drag-and-drop and context menu
class DraggableButton(QPushButton):
    def __init__(self, file_path, asset_manager, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.asset_manager = asset_manager  # Reference to AssetManager
        self.start_pos = None
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
        else:
            self.start_pos = None

    def mouseMoveEvent(self, event):
        if not self.start_pos:
            return
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        if not self.file_path or not os.path.exists(self.file_path):
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self.file_path)])
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def show_context_menu(self, position):
        menu = QMenu()

        if not os.path.exists(self.file_path):
            return

        open_in_explorer = menu.addAction("Open in Explorer")
        open_in_explorer.setShortcut("Ctrl+E")
        copy_path = menu.addAction("Copy đường dẫn")
        copy_path.setShortcut("Ctrl+C")
        delete = menu.addAction("Delete")
        delete.setShortcut("Ctrl+X")

        action = menu.exec_(self.mapToGlobal(position))
        if action == open_in_explorer:
            self.open_in_explorer()
        elif action == copy_path:
            self.copy_path()
        elif action == delete:
            self.delete_file()

    def open_in_explorer(self):
        try:
            folder_path = os.path.dirname(self.file_path)
            os.startfile(folder_path)
            message = f"Opened folder '{os.path.basename(folder_path)}' in Explorer..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.asset_manager.status_label.setText(message)  # Use asset_manager reference
        except Exception as e:
            message = f"Error opening Explorer: {str(e)}..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.asset_manager.status_label.setText(message)  # Use asset_manager reference

    def copy_path(self):
        clipboard = QApplication.clipboard()
        folder_path = os.path.dirname(self.file_path)
        clipboard.setText(folder_path)
        message = f"Copied folder path of '{os.path.basename(folder_path)}' to clipboard..."
        if len(message) > 50:
            message = message[:47] + "..."
        self.asset_manager.status_label.setText(message)  # Use asset_manager reference

    def delete_file(self):
        if not os.path.isfile(self.file_path):
            message = f"Error: '{os.path.basename(self.file_path)}' is not a valid file..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.asset_manager.status_label.setText(message)  # Use asset_manager reference
            return

        reply = QMessageBox.question(self, "Xác nhận xóa",
                                    f"Bạn có chắc muốn xóa file '{os.path.basename(self.file_path)}' không? Hành động này không thể hoàn tác!",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.file_path)
                message = f"Deleted '{os.path.basename(self.file_path)}' successfully..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.asset_manager.status_label.setText(message)  # Use asset_manager reference
                # Reload the products list after deletion
                self.asset_manager.load_products_list()
            except Exception as e:
                message = f"Error deleting: {str(e)}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.asset_manager.status_label.setText(message)  # Use asset_manager reference

class AddAssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Asset")
        self.layout = QFormLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Characters", "Props", "VFXs"])
        self.layout.addRow("Asset Type:", self.type_combo)

        self.name_edit = QLineEdit()
        self.layout.addRow("Asset Name:", self.name_edit)

        self.buttons = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.buttons.addWidget(self.ok_btn)
        self.buttons.addWidget(self.cancel_btn)
        self.layout.addRow(self.buttons)

    def get_data(self):
        return self.type_combo.currentText(), self.name_edit.text()

class AddShotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Shot")
        self.layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.layout.addRow("Shot Name:", self.name_edit)

        self.buttons = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.buttons.addWidget(self.ok_btn)
        self.buttons.addWidget(self.cancel_btn)
        self.layout.addRow(self.buttons)

    def get_data(self):
        return self.name_edit.text()

class AssetManager(QMainWindow):
    def __init__(self, project_path, show_lobby_callback, current_user):
        super().__init__()
        self.project_path = project_path
        self.show_lobby_callback = show_lobby_callback
        self.current_user = current_user
        self.project_name = os.path.basename(project_path)
        self.selected_asset = None
        self.selected_shot = None
        
        self.pipeline_dir = os.path.join(self.project_path, "00_Pipeline")
        self.icons_dir = os.path.join(self.pipeline_dir, "icons")
        self.default_thumbnail = os.path.join(BASE_DIR, "Resources", "default_thumbnail.jpg")
        self.data_file = os.path.join(self.pipeline_dir, "data.json")
        self.assets_dir = os.path.join(self.pipeline_dir, "assets")
        self.users_file = os.path.join(os.path.dirname(os.path.dirname(self.project_path)), "users.json")
        
        self.blender_path = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"
        self.template_blend_file = os.path.join(BASE_DIR, "Resources", "template.blend")
        
        self.setWindowTitle(f"Blender Asset Manager - {self.project_name} (Logged in as {self.current_user['username']})")
        
        self._create_initial_structure()
        
        self.settings = QSettings("MyCompany", "BlenderAssetManager")
        self.restoreGeometry(self.settings.value("AssetManager/geometry", b""))

        self.data = self.load_data()
        self.project_short = self.data.get("short", self.project_name)
        self.assets = self.load_assets()
        self.shots = self.data.get("shots", [])

        self.team_members = self.load_team_members()

        self.section_states = {
            "Characters": True,
            "Props": True,
            "VFXs": True
        }
        self.shot_section_state = self.data.get("shot_section_state", True)
        self.content_section_state = self.data.get("content_section_state", True)

        self.asset_lists = {
            "Characters": None,
            "Props": None,
            "VFXs": None
        }
        self.shot_list = None

        self.left_widget = None
        self.asset_table = None
        self.splitter = None

        self.current_mode = "Assets"
        self.products_grid = None

        self.scene_file_paths = {}
        self.product_file_paths = {}

        self.selected_scene_item = None
        self.selected_scene_item_widget = None
        self.selected_product_item = None
        self.selected_product_item_widget = None

        self.init_ui()

        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QWidget { background-color: #2b2b2b; color: #ffffff; }
            QListWidget#assetList { 
                background-color: #3c3f41; 
                border: 1px solid #555555; 
                color: #ffffff; 
                font-family: 'Arial'; 
                font-size: 14px; 
            }
            QListWidget#assetList::item:selected { 
                background-color: #4a90e2; 
            }
            QListWidget#shotList { 
                background-color: #3c3f41; 
                border: 1px solid #555555; 
                color: #ffffff; 
                font-family: 'Arial'; 
                font-size: 14px; 
            }
            QListWidget#shotList::item:selected { 
                background-color: #4a90e2; }
            QListWidget#shotList::item:hover { 
                background-color: #555555; }
            QTabWidget::pane { border: 1px solid #555555; background-color: #3c3f41; }
            QTabBar::tab { background-color: #3c3f41; color: #ffffff; padding: 8px; font-family: 'Arial'; font-size: 12px; min-width: 100px; }
            QTabBar::tab:selected { background-color: #4a90e2; }
            QPushButton { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; padding: 10px; border-radius: 5px; font-family: 'Arial'; font-size: 14px; }
            QPushButton:hover { background-color: #4a90e2; }
            QPushButton:disabled { background-color: #555555; }
            QLabel { color: #ffffff; font-family: 'Arial'; font-size: 14px; }
            QPushButton#sectionButton { background-color: #3c3f41; color: #ffffff; border: none; padding: 5px; text-align: left; font-family: 'Arial'; font-size: 14px; font-weight: bold; }
            QPushButton#sectionButton:hover { background-color: #4a90e2; }
            QPushButton#modeButton { background-color: #3c3f41; color: #ffffff; border: none; padding: 5px; font-family: 'Arial'; font-size: 14px; font-weight: bold; }
            QPushButton#modeButton:hover { background-color: #4a90e2; }
            QTableWidget { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; font-family: 'Arial'; font-size: 14px; }
            QTableWidget::item { background-color: #3c3f41; border: 1px solid #555555; }
            QTableWidget::item:selected { background-color: #4a90e2; }
            QComboBox { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; padding: 3px; }
            QComboBox::drop-down { border: none; }
            .project-title, .scene-title, .product-title { font-weight: bold; font-size: 16px; }
            .project-info, .scene-stage, .product-version { font-size: 14px; }
            .scene-date, .product-format { font-size: 14px; }
            .scene-creator { font-size: 14px; }
            .project-thumbnail, .scene-thumbnail, .product-thumbnail { max-width: 100px; height: auto; }
            QWidget#card-item { border-radius: 5px; padding: 10px; }
        """)

    def _create_initial_structure(self):
        folders = ["00_Pipeline", "00_Pipeline/assets", "01_Management", "02_Designs", "03_Production", "04_Resources"]
        for folder in folders:
            folder_path = os.path.join(self.project_path, folder)
            os.makedirs(folder_path, exist_ok=True)

    def closeEvent(self, event):
        if self.splitter:
            self.settings.setValue("splitter_state", self.splitter.saveState())
        self.settings.setValue("AssetManager/geometry", self.saveGeometry())
        if self.selected_asset:
            self.settings.setValue("selected_asset", self.selected_asset["name"])
        else:
            self.settings.remove("selected_asset")
        if self.selected_shot:
            self.settings.setValue("selected_shot", self.selected_shot["name"])
        else:
            self.settings.remove("selected_shot")
        super().closeEvent(event)

    def load_team_members(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                users_data = json.load(f)
                return [user["username"] for user in users_data["users"]]
        return []

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {"shots": [], "section_states": {"Characters": True, "Props": True, "VFXs": True}, "shot_section_state": True, "content_section_state": True, "short": ""}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            self.data["shots"] = self.shots
            self.data["section_states"] = self.section_states
            self.data["shot_section_state"] = self.shot_section_state
            self.data["content_section_state"] = self.content_section_state
            self.data["short"] = self.project_short
            json.dump(self.data, f, indent=4)

    def load_assets(self):
        assets = []
        if not os.path.exists(self.assets_dir):
            return assets
        for asset_file in os.listdir(self.assets_dir):
            if asset_file.endswith(".json"):
                asset_path = os.path.join(self.assets_dir, asset_file)
                try:
                    with open(asset_path, 'r') as f:
                        asset_data = json.load(f)
                        assets.append(asset_data)
                except Exception as e:
                    print(f"Error loading asset {asset_file}: {str(e)}")
        return assets

    def save_asset(self, asset):
        asset_file = os.path.join(self.assets_dir, f"{asset['name']}.json")
        with open(asset_file, 'w') as f:
            json.dump(asset, f, indent=4)

    def delete_asset_file(self, asset_name):
        asset_file = os.path.join(self.assets_dir, f"{asset_name}.json")
        if os.path.exists(asset_file):
            try:
                os.remove(asset_file)
            except Exception as e:
                print(f"Error deleting asset file {asset_file}: {str(e)}")

    def select_asset_in_list(self, asset_name):
        for asset_type in self.asset_lists:
            asset_list = self.asset_lists[asset_type]
            if asset_list:
                items = [asset_list.item(i) for i in range(asset_list.count())]
                for item in items:
                    if item and item.text() == asset_name:
                        if not self.section_states[asset_type]:
                            self.toggle_section(asset_type)
                        for other_type in self.asset_lists:
                            self.asset_lists[other_type].clearSelection()
                        asset_list.setCurrentItem(item)
                        self.show_asset_details(item)
                        self.scenes_list.repaint()
                        QApplication.processEvents()
                        return True
        for asset_type in ["Characters", "Props", "VFXs"]:
            asset_list = self.asset_lists[asset_type]
            if asset_list and asset_list.count() > 0:
                item = asset_list.item(0)
                if not self.section_states[asset_type]:
                    self.toggle_section(asset_type)
                for other_type in self.asset_lists:
                    self.asset_lists[other_type].clearSelection()
                asset_list.setCurrentItem(item)
                self.show_asset_details(item)
                self.scenes_list.repaint()
                QApplication.processEvents()
                return True
        return False

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        self.left_widget.setMinimumWidth(300)
        
        home_btn = QPushButton("Home")
        home_icon_path = os.path.join(self.icons_dir, "home_icon.png")
        if os.path.exists(home_icon_path):
            home_btn.setIcon(QIcon(home_icon_path))
        home_btn.clicked.connect(self.show_lobby_callback)
        left_layout.addWidget(home_btn)

        self.left_tabs = QTabWidget()
        self.assets_tab = QWidget()
        self.shots_tab = QWidget()

        assets_icon_path = os.path.join(self.icons_dir, "assets_icon.png")
        shots_icon_path = os.path.join(self.icons_dir, "shots_icon.png")

        self.left_tabs.addTab(self.assets_tab, QIcon(assets_icon_path) if os.path.exists(assets_icon_path) else QIcon(), "Assets")
        self.left_tabs.addTab(self.shots_tab, QIcon(shots_icon_path) if os.path.exists(shots_icon_path) else QIcon(), "Shots")
        self.left_tabs.currentChanged.connect(self.on_tab_changed)

        self.left_tabs.tabBar().setMinimumSize(100, 30)
        self.left_tabs.tabBar().setUsesScrollButtons(False)

        assets_layout = QVBoxLayout(self.assets_tab)
        self.assets_widget = QWidget()
        self.assets_layout = QVBoxLayout(self.assets_widget)
        self.assets_layout.setContentsMargins(10, 0, 0, 0)
        self.assets_layout.setSpacing(5)

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
            self.assets_layout.addWidget(section_btn)

            asset_list = QListWidget()
            asset_list.setObjectName("assetList")
            asset_list.setContextMenuPolicy(Qt.CustomContextMenu)
            asset_list.customContextMenuRequested.connect(self.show_context_menu)
            asset_list.itemClicked.connect(self.show_asset_details)
            asset_list.setSelectionMode(QListWidget.SingleSelection)
            self.asset_lists[asset_type] = asset_list
            self.assets_layout.addWidget(asset_list)

        self.add_asset_btn = QPushButton("Add Asset")
        add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
        if os.path.exists(add_icon_path):
            self.add_asset_btn.setIcon(QIcon(add_icon_path))
        self.add_asset_btn.clicked.connect(self.add_asset)
        self.assets_layout.addWidget(self.add_asset_btn)

        assets_layout.addWidget(self.assets_widget)

        shots_layout = QVBoxLayout(self.shots_tab)
        self.shots_widget = QWidget()
        self.shots_layout = QVBoxLayout(self.shots_widget)
        self.shots_layout.setContentsMargins(10, 0, 0, 0)
        self.shots_layout.setSpacing(5)

        self.shot_list = QListWidget()
        self.shot_list.setObjectName("shotList")
        self.shot_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.shot_list.customContextMenuRequested.connect(self.show_context_menu)
        self.shot_list.itemClicked.connect(self.show_shot_details)
        self.shot_list.setViewMode(QListWidget.ListMode)
        self.shot_list.setSpacing(5)
        shots_layout.addWidget(self.shot_list)

        self.add_shot_btn = QPushButton("Add Shot")
        add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
        if os.path.exists(add_icon_path):
            self.add_shot_btn.setIcon(QIcon(add_icon_path))
        self.add_shot_btn.clicked.connect(self.add_shot)
        self.shots_layout.addWidget(self.add_shot_btn)

        shots_layout.addWidget(self.shots_widget)

        left_layout.addWidget(self.left_tabs)

        refresh_btn = QPushButton("Refresh")
        refresh_icon_path = os.path.join(self.icons_dir, "refresh_icon.png")
        if os.path.exists(refresh_icon_path):
            refresh_btn.setIcon(QIcon(refresh_icon_path))
        refresh_btn.clicked.connect(self.refresh_data)
        left_layout.addWidget(refresh_btn)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_widget.setMinimumWidth(600)

        self.tabs = QTabWidget()
        self.scenes_tab = QWidget()
        self.products_tab = QWidget()
        self.media_tab = QWidget()
        self.libraries_tab = QWidget()
        self.tasks_tab = QWidget()

        scenes_icon_path = os.path.join(self.icons_dir, "scenes_icon.png")
        products_icon_path = os.path.join(self.icons_dir, "products_icon.png")
        media_icon_path = os.path.join(self.icons_dir, "media_icon.png")
        libraries_icon_path = os.path.join(self.icons_dir, "libraries_icon.png")
        tasks_icon_path = os.path.join(self.icons_dir, "tasks_icon.png")

        self.tabs.addTab(self.scenes_tab, QIcon(scenes_icon_path) if os.path.exists(scenes_icon_path) else QIcon(), "Scenes")
        self.tabs.addTab(self.products_tab, QIcon(products_icon_path) if os.path.exists(products_icon_path) else QIcon(), "Products")
        self.tabs.addTab(self.media_tab, QIcon(media_icon_path) if os.path.exists(media_icon_path) else QIcon(), "Media")
        self.tabs.addTab(self.libraries_tab, QIcon(libraries_icon_path) if os.path.exists(libraries_icon_path) else QIcon(), "Libraries")
        self.tabs.addTab(self.tasks_tab, QIcon(tasks_icon_path) if os.path.exists(tasks_icon_path) else QIcon(), "Tasks")

        self.tabs.tabBar().setMinimumSize(100, 30)
        self.tabs.tabBar().setUsesScrollButtons(False)
        self.tabs.currentChanged.connect(self.on_right_tab_changed)

        scenes_layout = QVBoxLayout(self.scenes_tab)
        self.scenes_list = QListWidget()
        self.scenes_list.setViewMode(QListWidget.ListMode)
        self.scenes_list.setSpacing(5)
        self.scenes_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scenes_list.customContextMenuRequested.connect(self.show_context_menu)
        self.scenes_list.itemSelectionChanged.connect(self.on_scene_selection_changed)
        scenes_layout.addWidget(self.scenes_list)

        self.scenes_list.itemDoubleClicked.connect(self.open_scene_in_blender)
        self.scenes_list.viewport().installEventFilter(self)
        self.scenes_list.installEventFilter(self)  # Install event filter for key presses

        products_layout = QVBoxLayout(self.products_tab)
        self.products_scroll_area = QScrollArea()
        self.products_scroll_area.setWidgetResizable(True)
        self.products_widget = QWidget()
        self.products_grid = QGridLayout(self.products_widget)
        self.products_scroll_area.setWidget(self.products_widget)
        products_layout.addWidget(self.products_scroll_area)
        self.products_widget.installEventFilter(self)

        media_layout = QVBoxLayout(self.media_tab)
        # Để trống tab Media

        tasks_layout = QVBoxLayout(self.tasks_tab)
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(4)
        self.asset_table.setHorizontalHeaderLabels(["Asset Name", "Asset Type", "Status", "Assignee"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.setMinimumWidth(500)
        self.asset_table.setMinimumHeight(300)
        tasks_layout.addWidget(self.asset_table)

        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        libraries_layout = QVBoxLayout(self.libraries_tab)

        right_layout.addWidget(self.tabs)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { background-color: #3c3f41; padding: 5px; color: #aaaaaa; }")
        right_layout.addWidget(self.status_label)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        main_layout.addWidget(self.splitter)

        self.splitter.restoreState(self.settings.value("splitter_state", b""))

        main_layout.setSpacing(10)
        left_layout.setSpacing(10)
        right_layout.setSpacing(10)

        self.load_data_ui()

        if self.left_tabs.currentIndex() == 0:
            selected_asset_name = self.settings.value("selected_asset", "")
            if selected_asset_name:
                self.select_asset_in_list(selected_asset_name)
            else:
                for asset_type in ["Characters", "Props", "VFXs"]:
                    asset_list = self.asset_lists[asset_type]
                    if asset_list and asset_list.count() > 0:
                        item = asset_list.item(0)
                        if not self.section_states[asset_type]:
                            self.toggle_section(asset_type)
                        for other_type in self.asset_lists:
                            self.asset_lists[other_type].clearSelection()
                        asset_list.setCurrentItem(item)
                        self.show_asset_details(item)
                        break

    def on_scene_selection_changed(self):
        selected_items = self.scenes_list.selectedItems()
        
        # Reset the previous selection's style
        if self.selected_scene_item_widget:
            try:
                self.selected_scene_item_widget.setStyleSheet("""
                    QWidget#card-item, QWidget#card-item * { background-color: #3c3f41; border: none; border-radius: 5px; padding: 10px; }
                """)
            except RuntimeError:
                pass

        if selected_items:
            item = selected_items[0]
            display_name = item.data(Qt.UserRole)
            if display_name and display_name != "No Blender files found in scenefiles directories.":
                self.selected_scene_item = item
                self.selected_scene_item_widget = self.scenes_list.itemWidget(item)
                try:
                    self.selected_scene_item_widget.setStyleSheet("""
                        QWidget#card-item { background-color: #3c3f41; border: 2px solid #4a90e2; border-radius: 5px; padding: 10px; }
                        QWidget#card-item * { background-color: #3c3f41; }
                    """)
                    message = f"Selected scene: {display_name}..."
                    if len(message) > 50:
                        message = message[:47] + "..."
                    self.status_label.setText(message)
                except RuntimeError:
                    self.status_label.setText("Error updating scene selection.")
        else:
            self.selected_scene_item = None
            self.selected_scene_item_widget = None
            self.status_label.setText("No scene selected.")

    def eventFilter(self, source, event):
        # Handle mouse events for selection in Scenes tab
        if source == self.scenes_list.viewport() and event.type() == QEvent.MouseButtonPress:
            pos = event.pos()
            item = self.scenes_list.itemAt(pos)
            if not item:
                self.scenes_list.clearSelection()
                if self.selected_scene_item_widget:
                    try:
                        self.selected_scene_item_widget.setStyleSheet("""
                            QWidget#card-item, QWidget#card-item * { background-color: #3c3f41; border: none; }
                        """)
                        self.selected_scene_item = None
                        self.selected_scene_item_widget = None
                        self.status_label.setText("No scene selected.")
                    except RuntimeError as e:
                        print(f"RuntimeError in eventFilter: {str(e)}")
        # Handle mouse events for selection in Products tab
        elif source == self.products_widget and event.type() == QEvent.MouseButtonPress:
            pos = event.pos()
            for i in reversed(range(self.products_grid.count())):
                widget = self.products_grid.itemAt(i).widget()
                if widget and isinstance(widget, QPushButton) and widget.geometry().contains(pos):
                    if widget != self.selected_product_item_widget:
                        if self.selected_product_item_widget:
                            try:
                                self.selected_product_item_widget.setStyleSheet("""
                                    QPushButton { background-color: #3c3f41; border: none; }
                                """)
                            except RuntimeError as e:
                                print(f"RuntimeError in eventFilter: {str(e)}")
                        self.selected_product_item_widget = widget
                        try:
                            widget.setStyleSheet("""
                                QPushButton { background-color: #3c3f41; border: 2px solid #4a90e2; }
                            """)
                        except RuntimeError as e:
                            print(f"RuntimeError in eventFilter: {str(e)}")
                        message = f"Selected product: {widget.text()}..."
                        if len(message) > 50:
                            message = message[:47] + "..."
                        self.status_label.setText(message)
                    break
            else:
                if self.selected_product_item_widget:
                    try:
                        self.selected_product_item_widget.setStyleSheet("""
                            QPushButton { background-color: #3c3f41; border: none; }
                        """)
                        self.selected_product_item_widget = None
                        self.status_label.setText("No product selected.")
                    except RuntimeError as e:
                        print(f"RuntimeError in eventFilter: {str(e)}")
        # Handle key press events for Scenes tab shortcuts
        elif source == self.scenes_list and event.type() == QEvent.KeyPress:
            if self.scenes_list.hasFocus():
                selected_items = self.scenes_list.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    display_name = item.data(Qt.UserRole)
                    if display_name and display_name != "No Blender files found in scenefiles directories.":
                        file_path = self.scene_file_paths.get(display_name)
                        if file_path:
                            # Ctrl+E: Open in Explorer
                            if event.key() == Qt.Key_E and event.modifiers() == Qt.ControlModifier:
                                self.open_in_explorer(file_path)
                                return True
                            # Ctrl+C: Copy Path
                            elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
                                self.copy_path(file_path)
                                return True
                            # Ctrl+X: Delete
                            elif event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
                                self.delete_file(file_path, os.path.basename(file_path), self.scenes_list, item)
                                return True
        return super().eventFilter(source, event)

    def toggle_section(self, asset_type):
        self.section_states[asset_type] = not self.section_states[asset_type]
        asset_list = self.asset_lists[asset_type]
        asset_list.setVisible(self.section_states[asset_type])

        section_btn = None
        for btn in self.assets_widget.findChildren(QPushButton):
            if btn.property("asset_type") == asset_type:
                section_btn = btn
                break

        if section_btn:
            type_counts = {"Characters": 0, "Props": 0, "VFXs": 0}
            for asset in self.assets:
                at = asset["type"]
                if at in type_counts:
                    type_counts[at] += 1
            if self.section_states[asset_type]:
                down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                if os.path.exists(down_arrow_path):
                    section_btn.setIcon(QIcon(down_arrow_path))
                else:
                    section_btn.setText(f"{asset_type} ({type_counts[asset_type]}) ▼")
            else:
                right_arrow_path = os.path.join(self.icons_dir, "right_arrow.png")
                if os.path.exists(right_arrow_path):
                    section_btn.setIcon(QIcon(right_arrow_path))
                else:
                    section_btn.setText(f"{asset_type} ({type_counts[asset_type]}) ►")
        else:
            print(f"Warning: Could not find section button for {asset_type}")

        self.data["section_states"] = self.section_states
        self.save_data()

    def show_context_menu(self, position):
        widget = self.sender()
        if not widget:
            return

        item = widget.itemAt(position)
        menu = QMenu()

        if widget == self.scenes_list and not item:
            if self.selected_asset:
                asset_name = self.selected_asset["name"]
                asset_type = self.selected_asset["type"].lower()
                scenefiles_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}/scenefiles")
                existing_files = [f.lower() for f in os.listdir(scenefiles_dir) if f.endswith(".blend")] if os.path.exists(scenefiles_dir) else []

                if f"{self.project_short}_{asset_name}_modeling.blend".lower() not in existing_files:
                    modeling_action = menu.addAction("Modeling")
                    modeling_action.triggered.connect(lambda: self.create_scene_file("Modeling"))
                if f"{self.project_short}_{asset_name}_texturing.blend".lower() not in existing_files:
                    texturing_action = menu.addAction("Texturing")
                    texturing_action.triggered.connect(lambda: self.create_scene_file("Texturing"))
                if f"{self.project_short}_{asset_name}_rigging.blend".lower() not in existing_files:
                    rigging_action = menu.addAction("Rigging")
                    rigging_action.triggered.connect(lambda: self.create_scene_file("Rigging"))
            elif self.selected_shot:
                shot_name = self.selected_shot["name"]
                scenefiles_dir = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}/scenefiles")
                existing_files = [f.lower() for f in os.listdir(scenefiles_dir) if f.endswith(".blend")] if os.path.exists(scenefiles_dir) else []

                if f"{self.project_short}_{shot_name}_blocking.blend".lower() not in existing_files:
                    blocking_action = menu.addAction("Blocking")
                    blocking_action.triggered.connect(lambda: self.create_scene_file("Blocking"))
                if f"{self.project_short}_{shot_name}_animation.blend".lower() not in existing_files:
                    animation_action = menu.addAction("Animation")
                    animation_action.triggered.connect(lambda: self.create_scene_file("Animation"))
                if f"{self.project_short}_{shot_name}_lighting.blend".lower() not in existing_files:
                    lighting_action = menu.addAction("Lighting")
                    lighting_action.triggered.connect(lambda: self.create_scene_file("Lighting"))
                if f"{self.project_short}_{shot_name}_vfx.blend".lower() not in existing_files:
                    vfx_action = menu.addAction("VFX")
                    vfx_action.triggered.connect(lambda: self.create_scene_file("VFX"))
            else:
                return

            if not menu.isEmpty():
                menu.exec_(widget.viewport().mapToGlobal(position))
            return

        if widget == self.scenes_list:
            display_name = item.data(Qt.UserRole)
            if not display_name or display_name == "No Blender files found in scenefiles directories.":
                return
            file_path = self.scene_file_paths.get(display_name)
            if not file_path:
                return
            folder_path = os.path.dirname(file_path)
            path_for_delete = file_path
            display_name_for_delete = os.path.basename(file_path)
        elif widget in self.asset_lists.values():
            if item is None:
                return
            asset_name = item.text()
            asset = next((a for a in self.assets if a["name"] == asset_name), None)
            if not asset:
                return
            asset_type = asset["type"].lower()
            folder_path = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
            path_for_delete = folder_path
            display_name_for_delete = asset_name
        elif widget == self.shot_list:
            if item is None:
                return
            shot_name = item.text()
            folder_path = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")
            path_for_delete = folder_path
            display_name_for_delete = shot_name

        open_in_explorer = menu.addAction("Open in Explorer")
        open_in_explorer.setShortcut("Ctrl+E")
        copy_path = menu.addAction("Copy đường dẫn")
        copy_path.setShortcut("Ctrl+C")
        delete = menu.addAction("Delete")
        delete.setShortcut("Ctrl+X")

        action = menu.exec_(widget.viewport().mapToGlobal(position))
        if action == open_in_explorer:
            self.open_in_explorer(folder_path)
        elif action == copy_path:
            self.copy_path(folder_path)
        elif action == delete:
            self.delete_file(path_for_delete, display_name_for_delete, widget, item)

    def create_scene_file(self, stage):
        if not self.selected_asset and not self.selected_shot:
            self.status_label.setText("No asset or shot selected.")
            return

        if self.selected_asset:
            name = self.selected_asset["name"]
            asset_type = self.selected_asset["type"].lower()
            scenefiles_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{name}/scenefiles")
            file_name = f"{self.project_short}_{name}_{stage.lower()}.blend"
        elif self.selected_shot:
            name = self.selected_shot["name"]
            scenefiles_dir = os.path.join(self.project_path, f"03_Production/sequencer/{name}/scenefiles")
            file_name = f"{self.project_short}_{name}_{stage.lower()}.blend"

        os.makedirs(scenefiles_dir, exist_ok=True)
        file_path = os.path.join(scenefiles_dir, file_name)

        try:
            if not os.path.exists(self.template_blend_file):
                resources_dir = os.path.dirname(self.template_blend_file)
                os.makedirs(resources_dir, exist_ok=True)
                with open(self.template_blend_file, 'wb') as f:
                    f.write(b"BLENDER")
                self.status_label.setText(f"Created template file at '{self.template_blend_file}'...")
            shutil.copy(self.template_blend_file, file_path)
            self.load_scenes_list()
            self.status_label.setText(f"Created {file_name} successfully...")
        except Exception as e:
            self.status_label.setText(f"Error creating {file_name}: {str(e)}...")

    def open_in_explorer(self, file_path):
        try:
            folder_path = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
            os.startfile(folder_path)
            message = f"Opened folder '{os.path.basename(folder_path)}' in Explorer..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
        except Exception as e:
            message = f"Error opening Explorer: {str(e)}..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)

    def copy_path(self, file_path):
        folder_path = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
        clipboard = QApplication.clipboard()
        clipboard.setText(folder_path)
        message = f"Copied folder path of '{os.path.basename(folder_path)}' to clipboard..."
        if len(message) > 50:
            message = message[:47] + "..."
        self.status_label.setText(message)

    def delete_file(self, path, display_name, widget=None, item=None):
        is_scene_file = widget == self.scenes_list
        is_asset = widget in self.asset_lists.values()
        is_shot = widget == self.shot_list

        if is_scene_file:
            if not os.path.isfile(path):
                self.status_label.setText(f"Error: '{display_name}' is not a valid file.")
                return
            prompt = f"Bạn có chắc muốn xóa file '{display_name}' không? Hành động này không thể hoàn tác!"
        else:
            if not os.path.isdir(path):
                self.status_label.setText(f"Error: '{display_name}' is not a valid directory.")
                return
            prompt = f"Bạn có chắc muốn xóa thư mục '{display_name}' và tất cả nội dung bên trong không? Hành động này không thể hoàn tác!"

        reply = QMessageBox.question(self, "Xác nhận xóa", 
                                    prompt,
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if is_scene_file:
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                
                if is_asset:
                    asset_name = item.text()
                    self.delete_asset_file(asset_name)
                    self.assets = [a for a in self.assets if a["name"] != asset_name]
                    self.save_data()
                    self.load_data_ui()
                    if self.selected_asset and self.selected_asset["name"] == asset_name:
                        self.selected_asset = None
                        self.load_scenes_list()
                        for asset_type in ["Characters", "Props", "VFXs"]:
                            asset_list = self.asset_lists[asset_type]
                            if asset_list and asset_list.count() > 0:
                                item = asset_list.item(0)
                                if not self.section_states[asset_type]:
                                    self.toggle_section(asset_type)
                                for other_type in self.asset_lists:
                                    self.asset_lists[other_type].clearSelection()
                                asset_list.setCurrentItem(item)
                                self.show_asset_details(item)
                                break
                elif is_shot:
                    shot_name = item.text()
                    self.shots = [s for s in self.shots if s["name"] != shot_name]
                    self.save_data()
                    self.load_data_ui()
                    if self.selected_shot and self.selected_shot["name"] == shot_name:
                        self.selected_shot = None
                        self.load_scenes_list()
                else:
                    self.load_scenes_list()
                
                message = f"Deleted '{display_name}' successfully..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
            except Exception as e:
                message = f"Error deleting: {str(e)}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)

    def load_scenes_list(self):
        self.scenes_list.clear()
        self.scene_file_paths.clear()
        self.selected_scene_item = None
        self.selected_scene_item_widget = None

        if not self.selected_asset and not self.selected_shot:
            self.scenes_list.addItem("Please select an asset or shot to view scenes.")
            return

        if self.selected_asset:
            asset_name = self.selected_asset["name"]
            asset_type = self.selected_asset["type"].lower()
            asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
            scenefiles_dir = os.path.join(asset_dir, "scenefiles")
            thumbnail_path = os.path.join(asset_dir, "thumbnail.jpg")
        elif self.selected_shot:
            shot_name = self.selected_shot["name"]
            asset_dir = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")
            scenefiles_dir = os.path.join(asset_dir, "scenefiles")
            thumbnail_path = os.path.join(asset_dir, "thumbnail.jpg")
            asset_name = shot_name

        if not os.path.exists(scenefiles_dir):
            self.scenes_list.addItem("No scenefiles directory found.")
            print(f"Scenefiles directory not found: {scenefiles_dir}")
            return

        blend_files = [f for f in os.listdir(scenefiles_dir) if f.endswith(".blend")]

        for file_name in blend_files:
            file_path = os.path.join(scenefiles_dir, file_name)
            display_name = f"{asset_name} - {file_name}"

            latest_version = "v001"
            created_time = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%d/%m/%Y %H:%M")
            creator = self.current_user["username"]

            stage = None
            for s in ["modeling", "texturing", "rigging", "blocking", "animation", "lighting", "vfx"]:
                if f"_{s}.blend" in file_name.lower():
                    stage = s.capitalize()
                    break
            if not stage:
                stage = "Unknown"

            item_widget = QWidget()
            item_widget.setObjectName("card-item")
            item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; border-radius: 5px; padding: 10px; }")
            item_widget.setMouseTracking(True)

            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.setSpacing(10)

            def enter_event(event, widget=item_widget):
                if widget != self.selected_scene_item_widget:
                    widget.setStyleSheet("""
                        QWidget#card-item { background-color: #555555; border-radius: 5px; padding: 10px; }
                        QWidget#card-item * { background-color: #555555; }
                    """)

            def leave_event(event, widget=item_widget):
                if widget != self.selected_scene_item_widget:
                    widget.setStyleSheet("""
                        QWidget#card-item { background-color: #3c3f41; border-radius: 5px; padding: 10px; }
                        QWidget#card-item * { background-color: #3c3f41; }
                    """)

            item_widget.enterEvent = enter_event
            item_widget.leaveEvent = leave_event

            thumbnail_label = QLabel()
            thumbnail_label.setObjectName("scene-thumbnail")
            pixmap = QPixmap()
            if os.path.exists(thumbnail_path):
                pixmap.load(thumbnail_path)
            elif os.path.exists(self.default_thumbnail):
                pixmap.load(self.default_thumbnail)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(100, Qt.SmoothTransformation)
                thumbnail_label.setPixmap(pixmap)
            else:
                message = f"Warning: No valid thumbnail found at {thumbnail_path} or {self.default_thumbnail}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
            thumbnail_label.setMinimumWidth(0)
            thumbnail_label.setMaximumWidth(100)
            thumbnail_label.setScaledContents(False)
            item_layout.addWidget(thumbnail_label, stretch=1)

            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(5)
            item_layout.addWidget(content_widget, stretch=9)

            title_label = QLabel(stage)
            title_label.setObjectName("scene-title")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            content_layout.addWidget(title_label)

            sub_widget = QWidget()
            sub_layout = QHBoxLayout(sub_widget)
            sub_layout.setContentsMargins(0, 0, 0, 0)
            sub_layout.setSpacing(10)

            info_widget = QWidget()
            info_layout = QHBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(10)

            stage_label = QLabel(latest_version)
            stage_label.setObjectName("scene-stage")
            info_layout.addWidget(stage_label)

            date_label = QLabel(created_time)
            date_label.setObjectName("scene-date")
            info_layout.addWidget(date_label)

            sub_layout.addWidget(info_widget)

            creator_label = QLabel(creator)
            creator_label.setObjectName("scene-creator")
            sub_layout.addWidget(creator_label, alignment=Qt.AlignLeft)

            content_layout.addWidget(sub_widget)

            item = QListWidgetItem(self.scenes_list)
            item.setSizeHint(item_widget.sizeHint())
            self.scenes_list.setItemWidget(item, item_widget)

            item.setData(Qt.UserRole, display_name)
            self.scene_file_paths[display_name] = file_path

            item.setSelected(False)

        if self.scenes_list.count() == 0:
            self.scenes_list.addItem("No Blender files found in scenefiles directories.")
        
        self.scenes_list.repaint()
        QApplication.processEvents()

    def load_products_list(self):
        # Xóa các widget cũ trong grid
        for i in reversed(range(self.products_grid.count())):
            widget = self.products_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.product_file_paths.clear()
        self.selected_product_item = None
        self.selected_product_item_widget = None

        if not self.selected_asset and not self.selected_shot:
            no_products_btn = QPushButton("Please select an asset or shot to view products.")
            no_products_btn.setFixedSize(200, 150)
            no_products_btn.setEnabled(False)
            self.products_grid.addWidget(no_products_btn, 0, 0)
            return

        if self.selected_asset:
            asset_name = self.selected_asset["name"]
            asset_type = self.selected_asset["type"].lower()
            asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
            outputs_dir = os.path.join(asset_dir, "outputs")
            old_dir = os.path.join(outputs_dir, ".old")
            thumbnail_path = self.default_thumbnail
        elif self.selected_shot:
            shot_name = self.selected_shot["name"]
            asset_dir = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")
            outputs_dir = os.path.join(asset_dir, "outputs")
            old_dir = os.path.join(outputs_dir, ".old")
            thumbnail_path = self.default_thumbnail
            asset_name = shot_name

        if not os.path.exists(outputs_dir):
            no_products_btn = QPushButton("No outputs directory found.")
            no_products_btn.setFixedSize(200, 150)
            no_products_btn.setEnabled(False)
            self.products_grid.addWidget(no_products_btn, 0, 0)
            print(f"Outputs directory not found: {outputs_dir}")
            return

        product_files = [f for f in os.listdir(outputs_dir) if f.endswith((".usd", ".fbx", ".abc")) and f.startswith(f"{self.project_short}_{asset_name}_")]

        row = 0
        col = 0
        product_found = False
        for file_name in product_files:
            file_path = os.path.join(outputs_dir, file_name)
            display_name = file_name  # Use file_name as the key for consistency

            stage = None
            for s in ["model", "rig", "animation"]:
                if f"_{s}." in file_name.lower():
                    stage = s.capitalize()
                    break
            if not stage:
                stage = "Unknown"

            latest_version = "v001"
            if os.path.exists(old_dir):
                old_files = [f for f in os.listdir(old_dir) if f.startswith(f"{self.project_short}_{asset_name}_{stage.lower()}") and f.endswith(file_name[-4:])]
                if old_files:
                    versions = [int(re.search(r'_v(\d{3})\.', f).group(1)) for f in old_files if re.search(r'_v(\d{3})\.', f)]
                    if versions:
                        latest_version = f"v{max(versions):03d}"

            file_format = os.path.splitext(file_name)[1][1:].lower()

            # Use DraggableButton with reference to self (AssetManager)
            product_btn = DraggableButton(file_path, self)  # Pass self as asset_manager
            product_btn.setFixedSize(200, 150)

            # Tìm thumbnail
            if os.path.exists(thumbnail_path):
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    product_btn.setIcon(QIcon(pixmap))
                    product_btn.setIconSize(QSize(180, 120))
            else:
                default_icon_path = os.path.join(BASE_DIR, "Resources", "default_icons", "default_product_icon.png")
                if os.path.exists(default_icon_path):
                    product_btn.setIcon(QIcon(default_icon_path))
                    product_btn.setIconSize(QSize(180, 120))
                else:
                    product_btn.setText(f"{stage}\n({file_format})")

            product_btn.setText(file_name)
            self.products_grid.addWidget(product_btn, row, col)

            self.product_file_paths[display_name] = file_path  # Store file_path with display_name (file_name)

            col += 1
            if col > 3:
                col = 0
                row += 1

            product_found = True

        if not product_found:
            no_products_btn = QPushButton("No product files found in outputs directory.")
            no_products_btn.setFixedSize(200, 150)
            no_products_btn.setEnabled(False)
            self.products_grid.addWidget(no_products_btn, 0, 0)

        self.products_widget.repaint()
        self.products_scroll_area.repaint()
        QApplication.processEvents()

    def open_scene_in_blender(self, item):
        if not item:
            return

        display_name = item.data(Qt.UserRole)
        if not display_name or display_name == "No Blender files found in scenefiles directories.":
            return

        file_path = self.scene_file_paths.get(display_name)
        if not file_path or not os.path.exists(file_path):
            message = f"File '{display_name}' not found..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
            return

        try:
            with open(file_path, "rb") as f:
                header = f.read(7)
                if header != b"BLENDER":
                    message = f"Error: '{file_path}' is not a valid Blender file..."
                    if len(message) > 50:
                        message = message[:47] + "..."
                    self.status_label.setText(message)
                    return
            subprocess.Popen([self.blender_path, file_path], creationflags=subprocess.DETACHED_PROCESS)
            message = f"Opened '{os.path.basename(file_path)}' in Blender..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
        except FileNotFoundError:
            message = f"Blender executable not found at: {self.blender_path}..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
        except Exception as e:
            message = f"Error: {str(e)}..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)

    def load_data_ui(self):
        type_counts = {"Characters": 0, "Props": 0, "VFXs": 0}
        for asset in self.assets:
            asset_type = asset["type"]
            if asset_type in type_counts:
                type_counts[asset_type] += 1

        for asset_type in self.asset_lists:
            if self.asset_lists[asset_type]:
                self.asset_lists[asset_type].clear()

        for asset in self.assets:
            asset_type = asset["type"]
            if asset_type in self.asset_lists:
                self.asset_lists[asset_type].addItem(asset["name"])

        for asset_type in self.asset_lists:
            section_btn = None
            for btn in self.assets_widget.findChildren(QPushButton):
                if btn.property("asset_type") == asset_type:
                    section_btn = btn
                    break
            if section_btn:
                section_btn.setText(f"{asset_type} ({type_counts[asset_type]})")
                if self.section_states[asset_type]:
                    down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                    if os.path.exists(down_arrow_path):
                        section_btn.setIcon(QIcon(down_arrow_path))
                    else:
                        section_btn.setText(f"{asset_type} ({type_counts[asset_type]}) ▼")
                else:
                    right_arrow_path = os.path.join(self.icons_dir, "right_arrow.png")
                    if os.path.exists(right_arrow_path):
                        section_btn.setIcon(QIcon(right_arrow_path))
                    else:
                        section_btn.setText(f"{asset_type} ({type_counts[asset_type]}) ►")
            self.asset_lists[asset_type].setVisible(self.section_states[asset_type])

        if self.shot_list:
            self.shot_list.clear()
        for shot in sorted(self.shots, key=lambda x: x["name"]):
            self.shot_list.addItem(shot["name"])

        self.update_asset_table()

    def update_asset_table(self):
        self.asset_table.setRowCount(len(self.assets))
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {"To Do": "#ff5555", "Inprogress": "#55aaff", "Pending Review": "#ffaa00", "Done": "#55ff55"}

        for row, asset in enumerate(self.assets):
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
        self.asset_table.resizeRowsToContents()

    def on_status_changed(self, row, index):
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {"To Do": "#ff5555", "Inprogress": "#55aaff", "Pending Review": "#ffaa00", "Done": "#55ff55"}
        new_status = status_options[index]
        self.assets[row]["status"] = new_status
        self.save_asset(self.assets[row])
        self.asset_table.item(row, 2).setBackground(QColor(status_colors[new_status]))

    def on_assignee_changed(self, row, index):
        assignee_combo = self.asset_table.cellWidget(row, 3)
        new_assignee = assignee_combo.currentText()
        old_assignee = self.assets[row].get("assignee", "")
        self.assets[row]["assignee"] = new_assignee
        self.save_asset(self.assets[row])

        if new_assignee and new_assignee == self.current_user["username"] and new_assignee != old_assignee:
            asset_name = self.assets[row]["name"]
            msg = QMessageBox()
            msg.setWindowTitle("Task Assigned")
            msg.setText(f"You have been assigned to task: {asset_name}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.move(QDesktopWidget().availableGeometry().center() - msg.rect().center())
            msg.exec_()

    def show_asset_details(self, item):
        if not item:
            print("No item provided to show_asset_details")
            return
        asset_name = item.text()
        self.selected_asset = next((a for a in self.assets if a["name"] == asset_name), None)
        self.selected_shot = None
        if self.selected_asset:
            for asset_type in self.asset_lists:
                self.asset_lists[asset_type].clearSelection()
            for asset_type in self.asset_lists:
                asset_list = self.asset_lists[asset_type]
                items = [asset_list.item(i) for i in range(asset_list.count())]
                for i in items:
                    if i and i.text() == asset_name:
                        asset_list.setCurrentItem(i)
                        break
            asset_type = self.selected_asset["type"].lower()
            self.settings.setValue("selected_asset", asset_name)
            self.settings.remove("selected_shot")
            self.load_scenes_list()
            if self.tabs.currentWidget() == self.products_tab:
                self.load_products_list()

    def show_shot_details(self, item):
        if not item:
            return
        shot_name = item.text()
        self.selected_shot = next((s for s in self.shots if s["name"] == shot_name), None)
        self.selected_asset = None
        if self.selected_shot:
            self.settings.setValue("selected_shot", shot_name)
            self.settings.remove("selected_asset")
            self.load_scenes_list()
            if self.tabs.currentWidget() == self.products_tab:
                self.load_products_list()

    def on_tab_changed(self, index):
        if index == 0:  # Assets tab
            if self.selected_asset and self.select_asset_in_list(self.selected_asset["name"]):
                pass
            else:
                selected_asset_name = self.settings.value("selected_asset", "")
                if selected_asset_name and self.select_asset_in_list(selected_asset_name):
                    pass
                else:
                    for asset_type in ["Characters", "Props", "VFXs"]:
                        asset_list = self.asset_lists[asset_type]
                        if asset_list and asset_list.count() > 0:
                            item = asset_list.item(0)
                            if not self.section_states[asset_type]:
                                self.toggle_section(asset_type)
                            for other_type in self.asset_lists:
                                self.asset_lists[other_type].clearSelection()
                            asset_list.setCurrentItem(item)
                            self.show_asset_details(item)
                            break
                    else:
                        self.scenes_list.clear()
                        self.products_grid = None  # Reset grid
                        self.load_products_list()
                        self.scenes_list.addItem("No assets available.")
                        self.scenes_list.repaint()
        elif index == 1:  # Shots tab
            if not self.selected_shot and self.shot_list.count() > 0:
                self.shot_list.setCurrentRow(0)
                first_shot_item = self.shot_list.item(0)
                if first_shot_item:
                    self.show_shot_details(first_shot_item)
            elif self.selected_shot:
                items = [self.shot_list.item(i) for i in range(self.shot_list.count())]
                for item in items:
                    if item and item.text() == self.selected_shot["name"]:
                        self.shot_list.setCurrentItem(item)
                        self.show_shot_details(item)
                        break
            else:
                self.scenes_list.clear()
                self.products_grid = None  # Reset grid
                self.load_products_list()
                self.scenes_list.addItem("Please select a shot to view scenes.")
                self.scenes_list.repaint()

    def on_right_tab_changed(self, index):
        if self.tabs.widget(index) == self.products_tab:
            self.load_products_list()

    def add_asset(self):
        dialog = AddAssetDialog(self)
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            asset_type, asset_name = dialog.get_data()
            if not asset_name:
                message = "Asset name cannot be empty!..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                return

            asset_type_lower = asset_type.lower()
            asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type_lower}/{asset_name}")
            scenefiles_dir = os.path.join(asset_dir, "scenefiles")
            textures_dir = os.path.join(asset_dir, "textures")
            outputs_dir = os.path.join(asset_dir, "outputs")
            playblast_dir = os.path.join(asset_dir, "playblast")
            old_dir = os.path.join(scenefiles_dir, ".old")
            latest_file = os.path.join(scenefiles_dir, f"{self.project_short}_{asset_name}_modeling.blend")
            thumbnail_path = os.path.join(asset_dir, "thumbnail.jpg")

            try:
                os.makedirs(asset_dir, exist_ok=True)
                os.makedirs(scenefiles_dir, exist_ok=True)
                os.makedirs(textures_dir, exist_ok=True)
                os.makedirs(outputs_dir, exist_ok=True)
                os.makedirs(playblast_dir, exist_ok=True)
                os.makedirs(old_dir, exist_ok=True)

                if not os.path.exists(latest_file):
                    if not os.path.exists(self.template_blend_file):
                        resources_dir = os.path.dirname(self.template_blend_file)
                        os.makedirs(resources_dir, exist_ok=True)
                        try:
                            with open(self.template_blend_file, 'wb') as f:
                                f.write(b"BLENDER")
                            message = f"Created template file at '{self.template_blend_file}'..."
                            if len(message) > 50:
                                message = message[:47] + "..."
                            self.status_label.setText(message)
                        except Exception as e:
                            message = f"Error creating template file: {str(e)}..."
                            if len(message) > 50:
                                message = message[:47] + "..."
                            self.status_label.setText(message)
                            return
                    shutil.copy(self.template_blend_file, latest_file)

                if not os.path.exists(thumbnail_path) and os.path.exists(self.default_thumbnail):
                    shutil.copy(self.default_thumbnail, thumbnail_path)

            except Exception as e:
                message = f"Error creating directory or files: {str(e)}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                return

            new_asset = {
                "name": asset_name,
                "type": asset_type,
                "status": "To Do",
                "assignee": "",
                "versions": [{
                    "version": "v001",
                    "description": "Initial version",
                    "file_path": f"03_Production/assets/{asset_type_lower}/{asset_name}/scenefiles/{self.project_short}_{asset_name}_modeling.blend",
                    "thumbnail": f"03_Production/assets/{asset_type_lower}/{asset_name}/thumbnail.jpg"
                }]
            }
            self.assets.append(new_asset)
            self.save_asset(new_asset)
            self.load_data_ui()
            self.selected_asset = new_asset
            self.selected_shot = None
            self.settings.setValue("selected_asset", asset_name)
            self.settings.remove("selected_shot")
            self.select_asset_in_list(asset_name)
            message = f"Asset '{asset_name}' (Type: {asset_type}) created successfully!..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)

    def add_shot(self):
        dialog = AddShotDialog(self)
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            shot_name = dialog.get_data()
            if not shot_name:
                message = "Shot name cannot be empty!..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                return

            full_shot_name = shot_name
            shot_dir = os.path.join(self.project_path, f"03_Production/sequencer/{full_shot_name}")
            scenefiles_dir = os.path.join(shot_dir, "scenefiles")
            old_dir = os.path.join(scenefiles_dir, ".old")
            playblast_dir = os.path.join(shot_dir, "playblast")
            latest_file = os.path.join(scenefiles_dir, f"{self.project_short}_{full_shot_name}_blocking.blend")
            thumbnail_path = os.path.join(shot_dir, "thumbnail.jpg")

            try:
                os.makedirs(shot_dir, exist_ok=True)
                os.makedirs(scenefiles_dir, exist_ok=True)
                os.makedirs(old_dir, exist_ok=True)
                os.makedirs(playblast_dir, exist_ok=True)

                if not os.path.exists(latest_file):
                    if not os.path.exists(self.template_blend_file):
                        resources_dir = os.path.dirname(self.template_blend_file)
                        os.makedirs(resources_dir, exist_ok=True)
                        try:
                            with open(self.template_blend_file, 'wb') as f:
                                f.write(b"BLENDER")
                            message = f"Created template file at '{self.template_blend_file}'..."
                            if len(message) > 50:
                                message = message[:47] + "..."
                            self.status_label.setText(message)
                        except Exception as e:
                            message = f"Error creating template file: {str(e)}..."
                            if len(message) > 50:
                                message = message[:47] + "..."
                            self.status_label.setText(message)
                            return
                    shutil.copy(self.template_blend_file, latest_file)

                if not os.path.exists(thumbnail_path) and os.path.exists(self.default_thumbnail):
                    shutil.copy(self.default_thumbnail, thumbnail_path)

            except Exception as e:
                message = f"Error creating directory or files: {str(e)}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                return

            new_shot = {
                "name": full_shot_name,
                "versions": [{
                    "version": "v001",
                    "description": "Initial version",
                    "file_path": f"03_Production/sequencer/{full_shot_name}/scenefiles/{self.project_short}_{full_shot_name}_blocking.blend"
                }]
            }
            self.shots.append(new_shot)
            self.save_data()
            self.load_data_ui()
            self.selected_shot = new_shot
            self.selected_asset = None
            self.settings.setValue("selected_shot", full_shot_name)
            self.settings.remove("selected_asset")
            items = [self.shot_list.item(i) for i in range(self.shot_list.count())]
            for item in items:
                if item and item.text() == full_shot_name:
                    self.shot_list.setCurrentItem(item)
                    self.show_shot_details(item)
                    break
            message = f"Shot '{full_shot_name}' created successfully!..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)

    def refresh_data(self):
        assets_dir = os.path.join(self.project_path, "03_Production", "assets")
        if not os.path.exists(assets_dir):
            message = "Assets directory not found!..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
            return

        sequencer_dir = os.path.join(self.project_path, "03_Production", "sequencer")
        if not os.path.exists(sequencer_dir):
            message = "Sequencer directory not found!..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
            return

        new_assets = []
        new_shots = []
        asset_types = ["characters", "props", "vfxs"]

        for asset_type in asset_types:
            type_dir = os.path.join(assets_dir, asset_type)
            if not os.path.exists(type_dir):
                continue

            for asset_name in os.listdir(type_dir):
                asset_dir = os.path.join(type_dir, asset_name)
                if not os.path.isdir(asset_dir):
                    continue

                asset_file = os.path.join(self.assets_dir, f"{asset_name}.json")
                if os.path.exists(asset_file):
                    try:
                        with open(asset_file, 'r') as f:
                            existing_asset = json.load(f)
                            new_assets.append(existing_asset)
                    except Exception as e:
                        print(f"Error loading asset {asset_name}: {str(e)}")
                else:
                    scenefiles_dir = os.path.join(asset_dir, "scenefiles")
                    if os.path.exists(scenefiles_dir):
                        blend_files = [f for f in os.listdir(scenefiles_dir) if f.endswith(".blend")]
                        if blend_files:
                            versions = [{
                                "version": "v001",
                                "description": "Auto-refreshed version",
                                "file_path": f"03_Production/assets/{asset_type}/{asset_name}/scenefiles/{self.project_short}_{asset_name}_modeling.blend",
                                "thumbnail": f"03_Production/assets/{asset_type}/{asset_name}/thumbnail.jpg"
                            }]
                            new_asset = {
                                "name": asset_name,
                                "type": asset_type.capitalize(),
                                "status": "To Do",
                                "assignee": "",
                                "versions": versions
                            }
                            new_assets.append(new_asset)
                            self.save_asset(new_asset)

        for shot_name in os.listdir(sequencer_dir):
            shot_dir = os.path.join(sequencer_dir, shot_name)