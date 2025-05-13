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
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QDesktopWidget)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QPixmap, QIcon, QColor
from PyQt5.QtCore import Qt, QSettings, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from utils.paths import get_project_data_path
from utils.dialogs import AddAssetDialog, AddShotDialog

BLENDER_PATH = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"
RESOURCES_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/App/Resources"
TEMPLATE_BLEND_FILE = os.path.join(RESOURCES_DIR, "template.blend")
DEFAULT_THUMBNAIL = os.path.join(RESOURCES_DIR, "default_thumbnail.jpg")
USERS_FILE = "D:/OneDrive/Desktop/Projects/Vexapipe/App/users.json"
TEMP_VIDEO_PATH = os.path.join(RESOURCES_DIR, "temp_playblast.mp4")

class AssetManager(QMainWindow):
    def __init__(self, project_path, show_lobby_callback, current_user):
        super().__init__()
        self.project_path = project_path
        self.show_lobby_callback = show_lobby_callback
        self.current_user = current_user
        self.project_name = os.path.basename(project_path)
        self.icons_dir = os.path.join(RESOURCES_DIR, "ProjectData", self.project_name, "icons")
        self.setWindowTitle(f"Blender Asset Manager - {self.project_name} (Logged in as {self.current_user['username']})")
        
        # Tạo cấu trúc thư mục ban đầu cho dự án
        self._create_initial_structure()
        
        self.settings = QSettings("MyCompany", "BlenderAssetManager")
        self.restoreGeometry(self.settings.value("AssetManager/geometry", b""))

        self.data_file = get_project_data_path(project_path)
        self.data = self.load_data()
        self.project_short = self.data.get("short", self.project_name)
        self.assets = self.data.get("assets", [])
        self.shots = self.data.get("shots", [])

        self.team_members = self.load_team_members()

        self.current_file = None
        self.current_thumbnail = None
        self.current_playblast_dir = None

        self.section_states = {
            "Characters": True,
            "Props": True,
            "VFXs": True
        }
        self.shot_section_state = self.data.get("shot_section_state", True)

        self.asset_lists = {
            "Characters": None,
            "Props": None,
            "VFXs": None
        }
        self.shot_list = None

        self.left_widget = None
        self.asset_table = None

        self.current_mode = "Assets"
        self.assets_btn = None
        self.shots_btn = None
        self.content_widget = None
        self.content_layout = None

        self.media_player = None
        self.video_widget = None

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
            QPushButton#modeButton {
                background-color: #3c3f41;
                color: #ffffff;
                border: none;
                padding: 5px;
                font-family: 'Arial';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#modeButton:hover {
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

    def _create_initial_structure(self):
        """Tạo cấu trúc thư mục ban đầu cho dự án."""
        folders = [
            "00_Pipeline",
            "01_Management",
            "02_Designs",
            "03_Production",
            "04_Resources"
        ]
        for folder in folders:
            folder_path = os.path.join(self.project_path, folder)
            os.makedirs(folder_path, exist_ok=True)

    def closeEvent(self, event):
        # Dừng và giải phóng QMediaPlayer
        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())  # Xóa media để giải phóng file
            self.media_player.setVideoOutput(None)  # Ngắt kết nối video output

        # Xóa file video tạm thời
        if os.path.exists(TEMP_VIDEO_PATH):
            try:
                os.remove(TEMP_VIDEO_PATH)
            except PermissionError:
                # Nếu không xóa được, ghi log hoặc bỏ qua
                self.status_label.setText(f"Warning: Could not delete {TEMP_VIDEO_PATH}. File in use.")
        
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
        return {
            "assets": [],
            "shots": [],
            "section_states": {"Characters": True, "Props": True, "VFXs": True},
            "shot_section_state": True,
            "short": ""
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            self.data["assets"] = self.assets
            self.data["shots"] = self.shots
            self.data["section_states"] = self.section_states
            self.data["shot_section_state"] = self.shot_section_state
            self.data["short"] = self.project_short
            json.dump(self.data, f, indent=4)

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

        mode_btn_layout = QHBoxLayout()
        self.assets_btn = QPushButton("Assets")
        self.assets_btn.setObjectName("modeButton")
        self.assets_btn.clicked.connect(lambda: self.switch_mode("Assets"))
        mode_btn_layout.addWidget(self.assets_btn)

        self.shots_btn = QPushButton("Shots")
        self.shots_btn.setObjectName("modeButton")
        self.shots_btn.clicked.connect(lambda: self.switch_mode("Shots"))
        mode_btn_layout.addWidget(self.shots_btn)
        left_layout.addLayout(mode_btn_layout)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        left_layout.addWidget(self.content_widget)

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

        # Tab Scenes (trống)
        scenes_layout = QVBoxLayout(self.scenes_tab)
        scenes_layout.addStretch()

        # Tab Tasks (chứa asset_table)
        tasks_layout = QVBoxLayout(self.tasks_tab)
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(5)  # Thêm cột Stage
        self.asset_table.setHorizontalHeaderLabels(["Asset Name", "Asset Type", "Stage", "Status", "Assignee"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        tasks_layout.addWidget(self.asset_table)

        # Tab Media
        media_layout = QVBoxLayout(self.media_tab)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(200)
        media_layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        # Nút điều khiển media
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

        # Tab Products và Libraries (trống)
        products_layout = QVBoxLayout(self.products_tab)
        libraries_layout = QVBoxLayout(self.libraries_tab)

        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)

        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.thumbnail_label)

        self.description_label = QLabel("Scene: \nVersion: \nCreated: ")
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

        self.switch_mode("Assets")

    def switch_mode(self, mode):
        self.current_mode = mode

        if mode == "Assets":
            self.assets_btn.setStyleSheet("QPushButton#modeButton { background-color: #4a90e2; }")
            self.shots_btn.setStyleSheet("QPushButton#modeButton { background-color: #3c3f41; }")
        else:
            self.assets_btn.setStyleSheet("QPushButton#modeButton { background-color: #3c3f41; }")
            self.shots_btn.setStyleSheet("QPushButton#modeButton { background-color: #4a90e2; }")

        # Xóa tất cả các widget trong content_layout hiện tại
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # Ngắt kết nối widget khỏi layout
            del item

        if mode == "Assets":
            for asset_type in ["Characters", "Props", "VFXs"]:
                if self.asset_lists[asset_type] is None:
                    # Tạo mới section button và list widget
                    section_btn = QPushButton(asset_type)
                    section_btn.setObjectName("sectionButton")
                    section_btn.setProperty("asset_type", asset_type)
                    down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                    if os.path.exists(down_arrow_path):
                        section_btn.setIcon(QIcon(down_arrow_path))
                    else:
                        section_btn.setText(f"{asset_type} ▼")
                    section_btn.clicked.connect(lambda checked, at=asset_type: self.toggle_section(at))
                    self.content_layout.addWidget(section_btn)

                    asset_list = QListWidget()
                    asset_list.itemClicked.connect(self.show_asset_details)
                    self.asset_lists[asset_type] = asset_list
                    self.content_layout.addWidget(asset_list)
                else:
                    # Thêm lại section button và list widget
                    section_btn = None
                    for btn in self.content_widget.findChildren(QPushButton):
                        if btn.property("asset_type") == asset_type:
                            section_btn = btn
                            break
                    if section_btn:
                        self.content_layout.addWidget(section_btn)
                    self.content_layout.addWidget(self.asset_lists[asset_type])

            add_asset_btn = QPushButton("Add Asset")
            add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
            if os.path.exists(add_icon_path):
                add_asset_btn.setIcon(QIcon(add_icon_path))
            add_asset_btn.clicked.connect(self.add_asset)
            self.content_layout.addWidget(add_asset_btn)

            self.load_data_ui()
        else:
            if self.shot_list is None:
                # Tạo mới shot section button và list widget
                shot_section_btn = QPushButton("Shots")
                shot_section_btn.setObjectName("sectionButton")
                down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                if os.path.exists(down_arrow_path):
                    shot_section_btn.setIcon(QIcon(down_arrow_path))
                else:
                    shot_section_btn.setText("Shots ▼")
                shot_section_btn.clicked.connect(self.toggle_shot_section)
                self.content_layout.addWidget(shot_section_btn)

                self.shot_list = QListWidget()
                self.shot_list.itemClicked.connect(self.show_shot_details)
                self.shot_list.setViewMode(QListWidget.ListMode)
                self.shot_list.setSpacing(5)
                self.content_layout.addWidget(self.shot_list)

                add_shot_btn = QPushButton("Add Shot")
                add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
                if os.path.exists(add_icon_path):
                    add_shot_btn.setIcon(QIcon(add_icon_path))
                add_shot_btn.clicked.connect(self.add_shot)
                self.content_layout.addWidget(add_shot_btn)
            else:
                # Thêm lại shot section button và list widget
                shot_section_btn = None
                for btn in self.content_widget.findChildren(QPushButton):
                    if btn.text().startswith("Shots"):
                        shot_section_btn = btn
                        break
                if shot_section_btn:
                    self.content_layout.addWidget(shot_section_btn)
                self.content_layout.addWidget(self.shot_list)

                add_shot_btn = QPushButton("Add Shot")
                add_icon_path = os.path.join(self.icons_dir, "add_icon.png")
                if os.path.exists(add_icon_path):
                    add_shot_btn.setIcon(QIcon(add_icon_path))
                add_shot_btn.clicked.connect(self.add_shot)
                self.content_layout.addWidget(add_shot_btn)

            self.load_data_ui()

    def toggle_section(self, asset_type):
        self.section_states[asset_type] = not self.section_states[asset_type]
        asset_list = self.asset_lists[asset_type]
        asset_list.setVisible(self.section_states[asset_type])

        section_btn = None
        for btn in self.content_widget.findChildren(QPushButton):
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

    def toggle_shot_section(self):
        self.shot_section_state = not self.shot_section_state
        self.shot_list.setVisible(self.shot_section_state)

        shot_section_btn = None
        for btn in self.content_widget.findChildren(QPushButton):
            if btn.text().startswith("Shots"):
                shot_section_btn = btn
                break

        if shot_section_btn:
            shot_count = len(self.shots)
            if self.shot_section_state:
                down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                if os.path.exists(down_arrow_path):
                    shot_section_btn.setIcon(QIcon(down_arrow_path))
                else:
                    shot_section_btn.setText(f"Shots ({shot_count}) ▼")
            else:
                right_arrow_path = os.path.join(self.icons_dir, "right_arrow.png")
                if os.path.exists(right_arrow_path):
                    shot_section_btn.setIcon(QIcon(right_arrow_path))
                else:
                    shot_section_btn.setText(f"Shots ({shot_count}) ►")

        self.data["shot_section_state"] = self.shot_section_state
        self.save_data()

    def load_data_ui(self):
        if self.current_mode == "Assets":
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
                for btn in self.content_widget.findChildren(QPushButton):
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

            self.update_asset_table()
        else:
            if self.shot_list:
                self.shot_list.clear()

            for shot in self.shots:
                self.shot_list.addItem(shot["name"])

            shot_section_btn = None
            for btn in self.content_widget.findChildren(QPushButton):
                if btn.text().startswith("Shots"):
                    shot_section_btn = btn
                    break
            if shot_section_btn:
                shot_count = len(self.shots)
                shot_section_btn.setText(f"Shots ({shot_count})")
                if self.shot_section_state:
                    down_arrow_path = os.path.join(self.icons_dir, "down_arrow.png")
                    if os.path.exists(down_arrow_path):
                        shot_section_btn.setIcon(QIcon(down_arrow_path))
                    else:
                        shot_section_btn.setText(f"Shots ({shot_count}) ▼")
                else:
                    right_arrow_path = os.path.join(self.icons_dir, "right_arrow.png")
                    if os.path.exists(right_arrow_path):
                        shot_section_btn.setIcon(QIcon(right_arrow_path))
                    else:
                        shot_section_btn.setText(f"Shots ({shot_count}) ►")
            self.shot_list.setVisible(self.shot_section_state)

    def update_asset_table(self):
        self.asset_table.setRowCount(len(self.assets))
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {
            "To Do": "#ff5555",
            "Inprogress": "#55aaff",
            "Pending Review": "#ffaa00",
            "Done": "#55ff55"
        }

        for row, asset in enumerate(self.assets):
            name_item = QTableWidgetItem(asset["name"])
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.asset_table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem(asset["type"])
            type_item.setFlags(type_item.flags() ^ Qt.ItemIsEditable)
            self.asset_table.setItem(row, 1, type_item)

            stage_item = QTableWidgetItem(asset.get("stage", "Modeling"))  # Giá trị mặc định là Modeling
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

    def on_status_changed(self, row, index):
        status_options = ["To Do", "Inprogress", "Pending Review", "Done"]
        status_colors = {
            "To Do": "#ff5555",
            "Inprogress": "#55aaff",
            "Pending Review": "#ffaa00",
            "Done": "#55ff55"
        }
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
        # Tìm tất cả các file ảnh trong thư mục playblast (hỗ trợ .png và .jpg)
        image_extensions = ("*.png", "*.jpg")
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(frames_dir, ext)))

        if not image_files:
            return False

        # Sử dụng regular expression để nhận diện và sắp xếp các file theo số thứ tự
        # Mẫu tên file: <prefix>_<số thứ tự>.<extension>
        # Ví dụ: frame_0001.png, v1_0001.png, v2_0002.jpg, ...
        def extract_frame_number(filename):
            # Tìm số thứ tự trong tên file (ví dụ: 0001 trong v1_0001.png)
            match = re.search(r'_(\d+)\.(png|jpg)$', filename)
            if match:
                return int(match.group(1))  # Trả về số thứ tự dưới dạng số nguyên
            return float('inf')  # Nếu không tìm thấy, xếp cuối danh sách

        # Sắp xếp các file theo số thứ tự
        image_files = sorted(image_files, key=extract_frame_number)

        # Loại bỏ các file không khớp với mẫu (nếu có)
        image_files = [f for f in image_files if extract_frame_number(f) != float('inf')]

        if not image_files:
            return False

        # Đọc ảnh đầu tiên để lấy kích thước
        frame = cv2.imread(image_files[0])
        if frame is None:
            return False
        height, width, layers = frame.shape

        # Tạo video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(TEMP_VIDEO_PATH, fourcc, 24.0, (width, height))

        # Ghi từng frame vào video
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
                self.status_label.setText(f"Created playblast directory at {playblast_dir}. Please add frame images (e.g., v1_0001.png).")
                if self.media_player:
                    self.media_player.stop()
                return
            except Exception as e:
                self.status_label.setText(f"Failed to create playblast directory: {str(e)}")
                if self.media_player:
                    self.media_player.stop()
                return

        # Dừng media player và xóa file cũ
        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())  # Giải phóng file cũ

        if os.path.exists(TEMP_VIDEO_PATH):
            try:
                os.remove(TEMP_VIDEO_PATH)
            except PermissionError:
                self.status_label.setText(f"Warning: Could not delete old {TEMP_VIDEO_PATH}. File in use.")
                return

        # Tạo video từ chuỗi ảnh
        if self.create_video_from_frames(playblast_dir):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(TEMP_VIDEO_PATH)))
            self.status_label.setText(f"Loaded playblast from {playblast_dir}")
        else:
            self.media_player.stop()
            self.status_label.setText(f"No valid frames found in {playblast_dir}. Expected format: <prefix>_<number>.(png|jpg), e.g., v1_0001.png")

    def show_asset_details(self, item):
        if not item:
            return
        asset_name = item.text()
        for row, asset in enumerate(self.assets):
            if asset["name"] == asset_name:
                asset_type = asset.get("type", "Unknown")
                stage = asset.get("stage", "Modeling")
                latest_file = f"{self.project_short}_{asset_name}_{stage}.blend"
                latest_file_path = os.path.join(self.project_path, f"03_Production/assets/{asset_type.lower()}/{asset_name}/scenefiles/{latest_file}")
                
                asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type.lower()}/{asset_name}")
                scenefiles_dir = os.path.join(asset_dir, "scenefiles")
                old_dir = os.path.join(scenefiles_dir, ".old")
                latest_version = "v001"

                if os.path.exists(old_dir):
                    old_files = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]
                    version_files = [f for f in old_files if f.startswith(f"{self.project_short}_{asset_name}_{stage}_v") and f.endswith(".blend")]
                    if version_files:
                        versions = []
                        for f in version_files:
                            try:
                                version_str = f.replace(f"{self.project_short}_{asset_name}_{stage}_v", "").replace(".blend", "")
                                version_num = int(version_str)
                                versions.append(version_num)
                            except ValueError:
                                continue
                        if versions:
                            max_version = max(versions)
                            latest_version = f"v{max_version + 1:03d}"

                created_time = "Unknown"
                if os.path.exists(latest_file_path):
                    created_time = datetime.fromtimestamp(os.path.getctime(latest_file_path)).strftime("%Y-%m-%d %H:%M:%S")

                self.description_label.setText(
                    f"Scene: {latest_file}\n"
                    f"Version: {latest_version}\n"
                    f"Created: {created_time}"
                )

                self.current_thumbnail = os.path.join(asset_dir, "thumbnail.jpg")
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

                self.current_playblast_dir = asset_dir
                self.update_media_player()

                if self.asset_table and isinstance(self.asset_table, QTableWidget):
                    try:
                        if not sip.isdeleted(self.asset_table):
                            self.asset_table.clearSelection()
                    except SystemError:
                        pass
                if self.shot_list and isinstance(self.shot_list, QListWidget):
                    try:
                        if not sip.isdeleted(self.shot_list):
                            self.shot_list.clearSelection()
                    except SystemError:
                        pass
                if self.asset_table and isinstance(self.asset_table, QTableWidget):
                    try:
                        if not sip.isdeleted(self.asset_table):
                            self.asset_table.selectRow(row)
                            self.asset_table.setFocus()
                    except SystemError:
                        pass
                break

    def show_shot_details(self, item):
        if not item:
            return
        shot_name = item.text()
        for shot in self.shots:
            if shot["name"] == shot_name:
                latest_file = f"{shot_name}.blend"
                latest_file_path = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}/{shot_name}.blend")
                
                shot_dir = os.path.join(self.project_path, f"03_Production/sequencer/{shot_name}")
                old_dir = os.path.join(shot_dir, ".old")
                latest_version = "v001"

                if os.path.exists(old_dir):
                    old_files = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]
                    version_files = [f for f in old_files if f.startswith(f"{shot_name}_v") and f.endswith(".blend")]
                    if version_files:
                        versions = []
                        for f in version_files:
                            try:
                                version_str = f.replace(f"{shot_name}_v", "").replace(".blend", "")
                                version_num = int(version_str)
                                versions.append(version_num)
                            except ValueError:
                                continue
                        if versions:
                            max_version = max(versions)
                            latest_version = f"v{max_version + 1:03d}"

                created_time = "Unknown"
                if os.path.exists(latest_file_path):
                    created_time = datetime.fromtimestamp(os.path.getctime(latest_file_path)).strftime("%Y-%m-%d %H:%M:%S")

                self.description_label.setText(
                    f"Scene: {latest_file}\n"
                    f"Version: {latest_version}\n"
                    f"Created: {created_time}"
                )

                self.current_thumbnail = None
                self.thumbnail_label.setPixmap(QPixmap())

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

                self.current_playblast_dir = shot_dir
                self.update_media_player()

                if self.asset_table and isinstance(self.asset_table, QTableWidget):
                    try:
                        if not sip.isdeleted(self.asset_table):
                            self.asset_table.clearSelection()
                    except SystemError:
                        pass
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
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            asset_type, asset_name, stage = dialog.get_data()  # Cập nhật để lấy stage
            if not asset_name:
                self.status_label.setText("Asset name cannot be empty!")
                return

            asset_type_lower = asset_type.lower()
            asset_dir = os.path.join(self.project_path, f"03_Production/assets/{asset_type_lower}/{asset_name}")
            scenefiles_dir = os.path.join(asset_dir, "scenefiles")
            textures_dir = os.path.join(asset_dir, "textures")
            outputs_dir = os.path.join(asset_dir, "outputs")
            old_dir = os.path.join(scenefiles_dir, ".old")
            latest_file = os.path.join(scenefiles_dir, f"{self.project_short}_{asset_name}_{stage}.blend")

            try:
                os.makedirs(asset_dir, exist_ok=True)
                os.makedirs(scenefiles_dir, exist_ok=True)
                os.makedirs(textures_dir, exist_ok=True)
                os.makedirs(outputs_dir, exist_ok=True)
                os.makedirs(old_dir, exist_ok=True)

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
                "stage": stage,  # Thêm trường stage
                "status": "To Do",
                "assignee": "",
                "versions": [
                    {
                        "version": "v001",
                        "description": "Initial version",
                        "file_path": f"03_Production/assets/{asset_type_lower}/{asset_name}/scenefiles/{self.project_short}_{asset_name}_{stage}.blend",
                        "thumbnail": f"03_Production/assets/{asset_type_lower}/{asset_name}/thumbnail.jpg"
                    }
                ]
            }
            self.assets.append(new_asset)
            self.save_data()
            self.load_data_ui()
            self.status_label.setText(f"Asset '{asset_name}' (Type: {asset_type}, Stage: {stage}) created successfully!")

    def add_shot(self):
        dialog = AddShotDialog(self)
        dialog.move(QDesktopWidget().availableGeometry().center() - dialog.rect().center())
        if dialog.exec_():
            shot_name = dialog.get_data()
            if not shot_name:
                self.status_label.setText("Shot name cannot be empty!")
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
                    if os.path.exists(TEMPLATE_BLEND_FILE):
                        shutil.copy(TEMPLATE_BLEND_FILE, latest_file)
                    else:
                        self.status_label.setText(f"Error: Template file '{TEMPLATE_BLEND_FILE}' not found!")
                        return
            except Exception as e:
                self.status_label.setText(f"Error creating directory or files: {str(e)}")
                return

            new_shot = {
                "name": full_shot_name,
                "versions": [
                    {
                        "version": "v001",
                        "description": "Initial version",
                        "file_path": f"03_Production/sequencer/{full_shot_name}/{full_shot_name}.blend"
                    }
                ]
            }
            self.shots.append(new_shot)
            self.save_data()
            self.load_data_ui()
            self.status_label.setText(f"Shot '{full_shot_name}' created successfully!")

    def refresh_data(self):
        assets_dir = os.path.join(self.project_path, "03_Production", "assets")
        if not os.path.exists(assets_dir):
            self.status_label.setText("Assets directory not found!")
            return

        sequencer_dir = os.path.join(self.project_path, "03_Production", "sequencer")
        if not os.path.exists(sequencer_dir):
            self.status_label.setText("Sequencer directory not found!")
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
                new_shot = {
                    "name": shot_name,
                    "versions": versions
                }
                new_shots.append(new_shot)

        self.assets = new_assets
        self.shots = new_shots
        self.save_data()
        self.load_data_ui()
        self.status_label.setText("Data refreshed successfully!")