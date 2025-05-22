import os
import json
import subprocess
import time
import shutil
import glob
import re
import cv2
import sip
import numpy as np
import tempfile
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QDesktopWidget, QHeaderView, QMenu, QApplication, QSplitter)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QPixmap, QIcon, QColor, QCursor, QFont
from PyQt5.QtCore import Qt, QSettings, QUrl, QEvent
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from utils.dialogs import AddAssetDialog, AddShotDialog

BASE_DIR = "D:/OneDrive/Desktop/Projects/Vexapine/App"

class AssetManager(QMainWindow):
    def __init__(self, project_path, show_lobby_callback, current_user):
        super().__init__()
        self.project_path = project_path
        self.show_lobby_callback = show_lobby_callback
        self.current_user = current_user
        self.project_name = os.path.basename(project_path)
        self.selected_asset = None
        
        self.pipeline_dir = os.path.join(self.project_path, "00_Pipeline")
        self.icons_dir = os.path.join(self.pipeline_dir, "icons")
        self.default_thumbnail = os.path.join(BASE_DIR, "Resources", "default_thumbnail.jpg")
        self.data_file = os.path.join(self.pipeline_dir, "data.json")
        self.users_file = os.path.join(os.path.dirname(os.path.dirname(self.project_path)), "users.json")
        
        self.blender_path = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"
        self.template_blend_file = os.path.join(BASE_DIR, "Resources", "template.blend")
        
        self.temp_video_fd, self.temp_video_path = tempfile.mkstemp(suffix=".mp4")
        os.close(self.temp_video_fd)

        self.setWindowTitle(f"Blender Asset Manager - {self.project_name} (Logged in as {self.current_user['username']})")
        
        self._create_initial_structure()
        
        self.settings = QSettings("MyCompany", "BlenderAssetManager")
        self.restoreGeometry(self.settings.value("AssetManager/geometry", b""))

        self.data = self.load_data()
        self.project_short = self.data.get("short", self.project_name)
        self.assets = self.data.get("assets", [])
        self.shots = self.data.get("shots", [])

        self.team_members = self.load_team_members()

        self.current_playblast_dir = None

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
        self.assets_btn = None
        self.shots_btn = None
        self.content_widget = None
        self.content_layout = None

        self.media_player = None
        self.video_widget = None

        self.scene_file_paths = {}

        self.selected_scene_item = None  # Theo dõi item được chọn trong scenes_list
        self.selected_scene_item_widget = None  # Theo dõi widget của item được chọn

        self.init_ui()

        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QWidget { background-color: #2b2b2b; color: #ffffff; }
            QListWidget { background-color: #3c3f41; border: 1px solid #555555; color: #ffffff; font-family: 'Arial'; font-size: 14px; }
            QListWidget::item:selected { background-color: #4a90e2; }
            QTabWidget::pane { border: 1px solid #555555; background-color: #3c3f41; }
            QTabBar::tab { background-color: #3c3f41; color: #ffffff; padding: 8px; font-family: 'Arial'; font-size: 12px; min-width: 100px; }
            QTabBar::tab:selected { background-color: #4a90e2; }
            QPushButton { background-color: #4a90e2; color: #ffffff; border: none; padding: 5px; border-radius: 3px; font-family: 'Arial'; font-size: 14px; }
            QPushButton:hover { background-color: #357abd; }
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
            .scene-title { font-weight: bold; font-size: 18px; }
            .scene-stage { background-color: red; border-radius: 3px; padding: 2px 8px; margin: 2px 0; display: inline-block; }
            .scene-date { font-size: 14px; margin-left: 10px; }
            .scene-creator { font-size: 14px; }
            .scene-thumbnail { max-width: 10%; height: auto; }
        """)

    def _create_initial_structure(self):
        folders = ["00_Pipeline", "01_Management", "02_Designs", "03_Production", "04_Resources"]
        for folder in folders:
            folder_path = os.path.join(self.project_path, folder)
            os.makedirs(folder_path, exist_ok=True)

    def closeEvent(self, event):
        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            self.media_player.setVideoOutput(None)
        if os.path.exists(self.temp_video_path):
            try:
                os.remove(self.temp_video_path)
            except PermissionError:
                self.status_label.setText(f"Warning: Could not delete {self.temp_video_path}...")
        if self.splitter:
            self.settings.setValue("splitter_state", self.splitter.saveState())
        self.settings.setValue("AssetManager/geometry", self.saveGeometry())
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
        return {"assets": [], "shots": [], "section_states": {"Characters": True, "Props": True, "VFXs": True}, "shot_section_state": True, "content_section_state": True, "short": ""}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            self.data["assets"] = self.assets
            self.data["shots"] = self.shots
            self.data["section_states"] = self.section_states
            self.data["shot_section_state"] = self.shot_section_state
            self.data["content_section_state"] = self.content_section_state
            self.data["short"] = self.project_short
            json.dump(self.data, f, indent=4)

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
            asset_list.setContextMenuPolicy(Qt.CustomContextMenu)
            asset_list.customContextMenuRequested.connect(self.show_context_menu)
            asset_list.itemClicked.connect(self.show_asset_details)
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
        self.shot_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.shot_list.customContextMenuRequested.connect(self.show_context_menu)
        self.shot_list.itemClicked.connect(self.show_shot_details)
        self.shot_list.setViewMode(QListWidget.ListMode)
        self.shot_list.setSpacing(5)
        self.shots_layout.addWidget(self.shot_list)

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

        scenes_layout = QVBoxLayout(self.scenes_tab)
        self.scenes_list = QListWidget()
        self.scenes_list.setViewMode(QListWidget.ListMode)
        self.scenes_list.setSpacing(5)
        self.scenes_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scenes_list.customContextMenuRequested.connect(self.show_context_menu)
        scenes_layout.addWidget(self.scenes_list)

        self.scenes_list.itemDoubleClicked.connect(self.open_scene_in_blender)

        tasks_layout = QVBoxLayout(self.tasks_tab)
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(5)
        self.asset_table.setHorizontalHeaderLabels(["Asset Name", "Asset Type", "Stage", "Status", "Assignee"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.setMinimumWidth(500)
        self.asset_table.setMinimumHeight(300)
        tasks_layout.addWidget(self.asset_table)

        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        media_layout = QVBoxLayout(self.media_tab)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(200)
        media_layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        media_controls = QHBoxLayout()
        play_btn = QPushButton("Play")
        play_btn.clicked.connect(self.media_player.play)
        media_controls.addWidget(play_btn)

        pause_btn = QPushButton("Pause")
        pause_btn.clicked.connect(self.media_player.pause)
        media_controls.addWidget(pause_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.media_player.stop)
        media_controls.addWidget(stop_btn)

        media_layout.addLayout(media_controls)

        products_layout = QVBoxLayout(self.products_tab)
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
        if not item:
            return

        if widget == self.scenes_list:
            display_name = item.data(Qt.UserRole)
            if not display_name or display_name == "No Blender files found in scenefiles directories.":
                return
            file_path = self.scene_file_paths.get(display_name)
            if not file_path:
                return
            folder_path = os.path.dirname(file_path)
        elif widget in self.asset_lists.values():
            asset_name = item.text()
            asset = next((a for a in self.assets if a["name"] == asset_name), None)
            if not asset:
                return
            asset_type = asset["type"].lower()
            folder_path = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
        elif widget == self.shot_list:
            shot_name = item.text()
            folder_path = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")

        menu = QMenu()
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
            self.delete_file(folder_path, os.path.basename(folder_path) if os.path.isdir(folder_path) else os.path.basename(os.path.dirname(folder_path)))

    def open_in_explorer(self, file_path):
        try:
            folder_path = os.path.dirname(file_path)
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
        folder_path = os.path.dirname(file_path)
        clipboard = QApplication.clipboard()
        clipboard.setText(folder_path)
        message = f"Copied folder path of '{os.path.basename(file_path)}' to clipboard..."
        if len(message) > 50:
            message = message[:47] + "..."
        self.status_label.setText(message)

    def delete_file(self, folder_path, display_name):
        reply = QMessageBox.question(self, "Xác nhận xóa", 
                                    f"Bạn có chắc muốn xóa '{display_name}' và các file liên quan không? Hành động này không thể hoàn tác!",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.isdir(folder_path):
                    shutil.rmtree(folder_path)
                else:
                    os.remove(folder_path)
                self.load_scenes_list()
                self.load_data_ui()
                message = f"Deleted '{display_name}' and related files..."
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

        if not self.selected_asset:
            self.scenes_list.addItem("Please select an asset to view scenes.")
            return

        asset_name = self.selected_asset["name"]
        asset_type = self.selected_asset["type"].lower()
        asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
        scenefiles_dir = os.path.join(asset_dir, "scenefiles")
        thumbnail_path = os.path.join(asset_dir, "thumbnail.jpg")

        if not os.path.exists(scenefiles_dir):
            self.scenes_list.addItem("No scenefiles directory found.")
            return

        for file_name in os.listdir(scenefiles_dir):
            if file_name.endswith(".blend"):
                file_path = os.path.join(scenefiles_dir, file_name)
                display_name = f"{asset_name} - {file_name}"

                # Lấy thông tin file
                latest_version = "v001"
                created_time = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%d/%m/%Y %H:%M")
                creator = self.current_user["username"]

                # Tạo custom widget cho item (Card_item)
                item_widget = QWidget()
                item_widget.setObjectName("card-item")  # Đặt tên để áp dụng CSS
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(10, 10, 10, 10)
                item_layout.setSpacing(10)

                # Thêm sự kiện hover
                def enter_event(event):
                    item_widget.setStyleSheet("QWidget#card-item { background-color: #555555; }")

                def leave_event(event):
                    if item_widget != self.selected_scene_item_widget:  # Kiểm tra nếu không phải item được chọn
                        item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; }")

                item_widget.enterEvent = enter_event
                item_widget.leaveEvent = leave_event

                # Widget 1: Thumbnail
                thumbnail_label = QLabel()
                thumbnail_label.setObjectName("scene-thumbnail")
                pixmap = QPixmap()
                if os.path.exists(thumbnail_path):
                    pixmap.load(thumbnail_path)
                elif os.path.exists(self.default_thumbnail):
                    pixmap.load(self.default_thumbnail)
                if not pixmap.isNull():
                    pixmap = pixmap.scaledToWidth(50, Qt.SmoothTransformation)
                    thumbnail_label.setPixmap(pixmap)
                thumbnail_label.setMinimumWidth(0)
                thumbnail_label.setMaximumWidth(50)
                thumbnail_label.setScaledContents(False)
                item_layout.addWidget(thumbnail_label, stretch=1)

                # Widget 2: Nội dung (theo chiều dọc)
                content_widget = QWidget()
                content_layout = QVBoxLayout(content_widget)
                content_layout.setContentsMargins(0, 0, 0, 0)
                content_layout.setSpacing(5)
                item_layout.addWidget(content_widget, stretch=9)

                # Tiêu đề: Vuna v001
                title_label = QLabel(f"{asset_name} {latest_version}")
                title_label.setObjectName("scene-title")
                content_layout.addWidget(title_label)

                # Widget phụ: Thông tin phụ và người tạo (theo chiều ngang)
                sub_widget = QWidget()
                sub_layout = QHBoxLayout(sub_widget)
                sub_layout.setContentsMargins(0, 0, 0, 0)
                sub_layout.setSpacing(10)

                # Thông tin phụ: Texturing và ngày giờ (theo chiều ngang)
                info_widget = QWidget()
                info_layout = QHBoxLayout(info_widget)
                info_layout.setContentsMargins(0, 0, 0, 0)
                info_layout.setSpacing(10)

                stage = next((s for s in ["Modeling", "Texturing", "Rigging"] if f"_{s}.blend" in file_name), "Unknown")
                stage_label = QLabel(stage)
                stage_label.setObjectName("scene-stage")
                info_layout.addWidget(stage_label)

                date_label = QLabel(created_time)
                date_label.setObjectName("scene-date")
                info_layout.addWidget(date_label)

                sub_layout.addWidget(info_widget)

                # Tên người làm: admin (căn trái)
                creator_label = QLabel(creator)
                creator_label.setObjectName("scene-creator")
                sub_layout.addWidget(creator_label, alignment=Qt.AlignLeft)

                content_layout.addWidget(sub_widget)

                # Tạo QListWidgetItem và gán widget
                item = QListWidgetItem(self.scenes_list)
                item.setSizeHint(item_widget.sizeHint())
                self.scenes_list.setItemWidget(item, item_widget)

                item.setData(Qt.UserRole, display_name)
                self.scene_file_paths[display_name] = file_path

                # Kết nối sự kiện click để cập nhật item được chọn
                item.setSelected(False)
                self.scenes_list.itemClicked.connect(self.on_scene_item_clicked)

        if self.scenes_list.count() == 0:
            self.scenes_list.addItem("No Blender files found in scenefiles directories.")

    def open_scene_in_blender(self, item):
        if not item:
            return

        # Xóa border của item trước đó (nếu có)
        if self.selected_scene_item_widget:
            self.selected_scene_item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; border: none; }")

        self.selected_scene_item = item
        self.selected_scene_item_widget = self.scenes_list.itemWidget(item)

        display_name = item.data(Qt.UserRole)
        if not display_name or display_name == "No Blender files found in scenefiles directories.":
            return

        # Áp dụng border màu xanh lam
        self.selected_scene_item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; border: 2px solid #4a90e2; }")

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
            subprocess.Popen([self.blender_path, file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    def switch_mode(self, mode):
        pass

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
        for shot in self.shots:
            self.shot_list.addItem(shot["name"])

        self.load_scenes_list()

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

            stage_item = QTableWidgetItem(asset.get("stage", "Modeling"))
            stage_item.setFlags(stage_item.flags() ^ Qt.ItemIsEditable)
            self.asset_table.setItem(row, 2, stage_item)

            status_combo = QComboBox()
            status_combo.addItems(status_options)
            current_status = asset.get("status", "To Do")
            status_combo.setCurrentText(current_status)
            status_combo.currentIndexChanged.connect(lambda index, r=row: self.on_status_changed(r, index))
            self.asset_table.setCellWidget(row, 3, status_combo)
            self.asset_table.setItem(row, 3, QTableWidgetItem())
            self.asset_table.item(row, 3).setBackground(QColor(status_colors[current_status]))

            assignee_combo = QComboBox()
            assignee_combo.addItem("")
            assignee_combo.addItems(self.team_members)
            current_assignee = asset.get("assignee", "")
            assignee_combo.setCurrentText(current_assignee)
            assignee_combo.currentIndexChanged.connect(lambda index, r=row: self.on_assignee_changed(r, index))
            self.asset_table.setCellWidget(row, 4, assignee_combo)

        self.asset_table.resizeColumnsToContents()
        self.asset_table.resizeRowsToContents()

    def on_status_changed(self, row, index):
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {"To Do": "#ff5555", "Inprogress": "#55aaff", "Pending Review": "#ffaa00", "Done": "#55ff55"}
        new_status = status_options[index]
        self.assets[row]["status"] = new_status
        self.save_data()
        self.asset_table.item(row, 3).setBackground(QColor(status_colors[new_status]))

    def on_assignee_changed(self, row, index):
        assignee_combo = self.asset_table.cellWidget(row, 4)
        new_assignee = assignee_combo.currentText()
        old_assignee = self.assets[row].get("assignee", "")
        self.assets[row]["assignee"] = new_assignee
        self.save_data()

        if new_assignee and new_assignee == self.current_user["username"] and new_assignee != old_assignee:
            asset_name = self.assets[row]["name"]
            msg = QMessageBox()
            msg.setWindowTitle("Task Assigned")
            msg.setText(f"You have been assigned to task: {asset_name}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.move(QDesktopWidget().availableGeometry().center() - msg.rect().center())
            msg.exec_()

    def create_video_from_frames(self, frames_dir):
        image_extensions = ("*.png", "*.jpg")
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(frames_dir, ext)))

        if not image_files:
            return False

        def extract_frame_number(filename):
            match = re.search(r'_(\d+)\.(png|jpg)$', filename)
            return int(match.group(1)) if match else float('inf')

        image_files = sorted(image_files, key=extract_frame_number)
        image_files = [f for f in image_files if extract_frame_number(f) != float('inf')]

        if not image_files:
            return False

        frame = cv2.imread(image_files[0])
        if frame is None:
            return False
        height, width, layers = frame.shape

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(self.temp_video_path, fourcc, 24.0, (width, height))

        for image_file in image_files:
            frame = cv2.imread(image_file)
            if frame is None:
                continue
            video_writer.write(frame)

        video_writer.release()
        return True

    def update_media_player(self):
        if not self.current_playblast_dir:
            if self.media_player:
                self.media_player.stop()
            return

        playblast_dir = os.path.join(self.current_playblast_dir, "playblast")
        if not os.path.exists(playblast_dir):
            try:
                os.makedirs(playblast_dir, exist_ok=True)
                message = f"Created playblast directory at {playblast_dir}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                if self.media_player:
                    self.media_player.stop()
                return
            except Exception as e:
                message = f"Failed to create playblast directory: {str(e)}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                if self.media_player:
                    self.media_player.stop()
                return

        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())

        if os.path.exists(self.temp_video_path):
            try:
                os.remove(self.temp_video_path)
            except PermissionError:
                message = f"Warning: Could not delete old {self.temp_video_path}..."
                if len(message) > 50:
                    message = message[:47] + "..."
                self.status_label.setText(message)
                return

        if self.create_video_from_frames(playblast_dir):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(self.temp_video_path)))
            message = f"Loaded playblast from {playblast_dir}..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)
        else:
            self.media_player.stop()
            message = f"No valid frames found in {playblast_dir}. Expected format: <prefix>_<number>.(png|jpg)..."
            if len(message) > 50:
                message = message[:47] + "..."
            self.status_label.setText(message)

    def show_asset_details(self, item):
        if not item:
            return
        asset_name = item.text()
        self.selected_asset = next((a for a in self.assets if a["name"] == asset_name), None)
        if self.selected_asset:
            asset_type = self.selected_asset["type"].lower()
            asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type}/{asset_name}")
            self.current_playblast_dir = asset_dir
            if self.tabs.currentWidget() == self.media_tab:
                self.update_media_player()
            self.load_scenes_list()

    def show_shot_details(self, item):
        if not item:
            return
        shot_name = item.text()
        for shot in self.shots:
            if shot["name"] == shot_name:
                shot_dir = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")
                self.current_playblast_dir = shot_dir
                if self.tabs.currentWidget() == self.media_tab:
                    self.update_media_player()
                break

    def add_asset(self):
        dialog = AddAssetDialog(self)
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            asset_type, asset_name, stage = dialog.get_data()
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
            latest_file = os.path.join(scenefiles_dir, f"{self.project_short}_{asset_name}_{stage}.blend")
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
                        # Tạo thư mục Resources nếu chưa tồn tại
                        resources_dir = os.path.dirname(self.template_blend_file)
                        os.makedirs(resources_dir, exist_ok=True)
                        # Tạo file template.blend rỗng nếu không tồn tại
                        try:
                            with open(self.template_blend_file, 'wb') as f:
                                f.write(b"BLENDER")  # Đầu file Blender hợp lệ
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
                "stage": stage,
                "status": "To Do",
                "assignee": "",
                "versions": [{
                    "version": "v001",
                    "description": "Initial version",
                    "file_path": f"03_Production/assets/{asset_type_lower}/{asset_name}/scenefiles/{self.project_short}_{asset_name}_{stage}.blend",
                    "thumbnail": f"03_Production/assets/{asset_type_lower}/{asset_name}/thumbnail.jpg"
                }]
            }
            self.assets.append(new_asset)
            self.save_data()
            self.load_data_ui()
            message = f"Asset '{asset_name}' (Type: {asset_type}, Stage: {stage}) created successfully!..."
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

            full_shot_name = f"{self.project_short}_{shot_name}"
            shot_dir = os.path.join(self.project_path, f"03_Production/sequencer/{full_shot_name}")
            old_dir = os.path.join(shot_dir, ".old")
            playblast_dir = os.path.join(shot_dir, "playblast")
            latest_file = os.path.join(shot_dir, f"{full_shot_name}.blend")

            try:
                os.makedirs(shot_dir, exist_ok=True)
                os.makedirs(old_dir, exist_ok=True)
                os.makedirs(playblast_dir, exist_ok=True)

                if not os.path.exists(latest_file):
                    if os.path.exists(self.template_blend_file):
                        shutil.copy(self.template_blend_file, latest_file)
                    else:
                        message = f"Error: Template file '{self.template_blend_file}' not found!..."
                        if len(message) > 50:
                            message = message[:47] + "..."
                        self.status_label.setText(message)
                        return
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
                    "file_path": f"03_Production/sequencer/{full_shot_name}/{full_shot_name}.blend"
                }]
            }
            self.shots.append(new_shot)
            self.save_data()
            self.load_data_ui()
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

                existing_asset = next((asset for asset in self.assets if asset["name"] == asset_name and asset["type"].lower() == asset_type), None)
                if existing_asset:
                    new_assets.append(existing_asset)
                else:
                    scenefiles_dir = os.path.join(asset_dir, "scenefiles")
                    if os.path.exists(scenefiles_dir):
                        blend_files = [f for f in os.listdir(scenefiles_dir) if f.endswith(".blend")]
                        if blend_files:
                            stage = next((s for s in ["Modeling", "Texturing", "Rigging"] if f"{self.project_short}_{asset_name}_{s}.blend" in blend_files), "Modeling")
                            versions = [{
                                "version": "v001",
                                "description": "Auto-refreshed version",
                                "file_path": f"03_Production/assets/{asset_type}/{asset_name}/scenefiles/{self.project_short}_{asset_name}_{stage}.blend",
                                "thumbnail": f"03_Production/assets/{asset_type}/{asset_name}/thumbnail.jpg"
                            }]
                            new_asset = {
                                "name": asset_name,
                                "type": asset_type.capitalize(),
                                "stage": stage,
                                "status": "To Do",
                                "assignee": "",
                                "versions": versions
                            }
                            new_assets.append(new_asset)

        for shot_name in os.listdir(sequencer_dir):
            shot_dir = os.path.join(sequencer_dir, shot_name)
            if not os.path.isdir(shot_dir):
                continue

            existing_shot = next((shot for shot in self.shots if shot["name"] == shot_name), None)
            if existing_shot:
                new_shots.append(existing_shot)
            else:
                versions = [{
                    "version": "v001",
                    "description": "Auto-refreshed version",
                    "file_path": f"03_Production/sequencer/{shot_name}/{shot_name}.blend"
                }]
                new_shot = {"name": shot_name, "versions": versions}
                new_shots.append(new_shot)

        self.assets = new_assets
        self.shots = new_shots
        self.save_data()
        self.load_data_ui()
        self.load_scenes_list()
        message = "Data refreshed successfully!..."
        if len(message) > 50:
            message = message[:47] + "..."
        self.status_label.setText(message)

    def on_scene_item_clicked(self, item):
        # Xóa border của item trước đó (nếu có)
        if self.selected_scene_item_widget:
            self.selected_scene_item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; border: none; }")

        self.selected_scene_item = item
        self.selected_scene_item_widget = self.scenes_list.itemWidget(item)

        display_name = item.data(Qt.UserRole)
        if display_name and display_name != "No Blender files found in scenefiles directories.":
            file_path = self.scene_file_paths.get(display_name)
            if file_path:
                folder_path = os.path.dirname(file_path)
                self.status_label.setText(f"Selected: {os.path.basename(folder_path)}...")
                # Áp dụng border màu xanh lam
                self.selected_scene_item_widget.setStyleSheet("QWidget#card-item { background-color: #3c3f41; border: 2px solid #4a90e2; }")

    def keyPressEvent(self, event):
        if self.selected_scene_item:
            display_name = self.selected_scene_item.data(Qt.UserRole)
            if display_name and display_name != "No Blender files found in scenefiles directories.":
                file_path = self.scene_file_paths.get(display_name)
                if file_path:
                    folder_path = os.path.dirname(file_path)
                    modifiers = event.modifiers()
                    if modifiers == Qt.ControlModifier:
                        if event.key() == Qt.Key_X:
                            self.delete_file(folder_path, os.path.basename(folder_path))
                            self.selected_scene_item = None
                            self.selected_scene_item_widget = None
                        elif event.key() == Qt.Key_E:
                            self.open_in_explorer(folder_path)
                        elif event.key() == Qt.Key_C:
                            self.copy_path(folder_path)
        super().keyPressEvent(event)