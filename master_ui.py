# master_ui.py

import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QTabWidget,
    QMenuBar, QPushButton, QVBoxLayout, QDialog, QApplication, QHBoxLayout as QHBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from asset import AssetTab
from shot import ShotTab
from tab_scene import SceneTab
from tab_product import ProductTab
from tab_library import LibraryTab
from login import clear_session, LoginDialog
from project import ProjectSelectionDialog

BASE_DIR            = os.path.dirname(__file__)
LATEST_PROJECT_FILE = os.path.join(BASE_DIR, "data", "latest_project.json")
LATEST_USER_FILE    = os.path.join(BASE_DIR, "data", "latest_user.json")


class DClickButton(QPushButton):
    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        else:
            super().mouseDoubleClickEvent(e)


class MasterUI(QMainWindow):
    def __init__(self, username, project):
        super().__init__()
        self.username = username
        self.project  = project

        self.setWindowTitle("VexaPipe")
        self.setGeometry(100, 100, 1000, 600)

        central = QWidget(self)
        self.setCentralWidget(central)
        h_main = QHBoxLayout(central)
        h_main.setContentsMargins(0, 0, 0, 0)
        h_main.setSpacing(0)

        # —————— 1) AssetTab & ShotTab bên trái ——————
        self.asset_tab = AssetTab(project_root=self.project["path"], username=self.username)
        self.shot_tab  = ShotTab(project_root=self.project["path"], username=self.username)

        # Kết nối signal
        self.asset_tab.asset_selected.connect(self.on_asset_selected)
        self.shot_tab.shot_selected.connect(self.on_shot_selected)

        # Splitter giữa trái/phải
        splitter = QSplitter(Qt.Horizontal)
        h_main.addWidget(splitter)

        # Tab widget bên trái
        self.left_tabs = QTabWidget()
        self.left_tabs.addTab(self.asset_tab, "Asset")
        self.left_tabs.addTab(self.shot_tab,  "Shot")
        splitter.addWidget(self.left_tabs)

        data_dir = os.path.join(self.project["path"], "00_Pipeline", "data")
        asset_file = os.path.join(data_dir, "latest_asset.json")
        shot_file  = os.path.join(data_dir, "latest_shot.json")

        if os.path.exists(asset_file):
            self.left_tabs.setCurrentIndex(0)
        elif os.path.exists(shot_file):
            self.left_tabs.setCurrentIndex(1)
        else:
            self.left_tabs.setCurrentIndex(0)        

        # Khi user đổi tab (Asset ↔ Shot), load ngay giá trị “latest”
        self.left_tabs.currentChanged.connect(self.on_left_tab_changed)

        # —————— 2) Tab Preset bên phải ——————
        self.scene_tab   = SceneTab()
        self.product_tab = ProductTab()
        self.library_tab = LibraryTab()

        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self.scene_tab,   "Scene")
        self.right_tabs.addTab(self.product_tab, "Product")
        self.right_tabs.addTab(self.library_tab,  "Library")
        splitter.addWidget(self.right_tabs)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        # —————— 3) Menu bar + user/project buttons ——————
        bar = self.menuBar()
        bar.addMenu("Options")
        bar.addMenu("Help")

        self.user_btn = DClickButton(f"👤 {self.username}")
        self.user_btn.setFlat(True)
        self.user_btn.doubleClicked.connect(self.on_user_logout)

        self.proj_btn = DClickButton(f"📁 {self.project['name']}")
        self.proj_btn.setFlat(True)
        self.proj_btn.doubleClicked.connect(self.on_project_hub)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFlat(True)
        self.refresh_btn.clicked.connect(self.on_refresh)
        style = """
        QPushButton {
            border-radius: 4px;
            padding: 4px 8px;
            background-color: transparent;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        """
        self.user_btn.setStyleSheet(style)
        self.proj_btn.setStyleSheet(style)
        self.proj_btn.setFixedWidth(120)
        self.refresh_btn.setStyleSheet(style)

        corner = QWidget()
        h_corner = QHBox(corner)
        h_corner.setContentsMargins(0, 0, 10, 0)
        h_corner.addStretch()
        h_corner.addWidget(self.user_btn)
        h_corner.addWidget(self.proj_btn)
        h_corner.addWidget(self.refresh_btn)
        bar.setCornerWidget(corner, Qt.TopRightCorner)

        # Cuối __init__, load “latest” dựa trên tab hiện tại
        self._load_latest_on_start()

        settings_file = os.path.join(BASE_DIR, "data", "window_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.resize(data.get("width", 1000), data.get("height", 600))
                    self.move(data.get("x", 100), data.get("y", 100))
            except Exception:
                pass

    def _get_pipeline_data_dir(self):
        """
        Trả về <project_root>/00_Pipeline/data, tạo nếu cần.
        """
        data_dir = os.path.join(self.project["path"], "00_Pipeline", "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def _load_latest_on_start(self):
        """
        Khi khởi app, lấy tab hiện tại (Asset hoặc Shot) và load “latest” tương ứng.
        """
        idx = self.left_tabs.currentIndex()
        self._load_latest_for_tab(idx)

    def on_left_tab_changed(self, idx):
        """
        Khi user đổi qua lại giữa Asset (0) và Shot (1), load ngay giá trị “latest” tương ứng.
        """
        self._load_latest_for_tab(idx)

    def _load_latest_for_tab(self, idx):
        """
        idx == 0 → Asset tab: đọc latest_asset.json, gọi on_asset_selected
        idx == 1 → Shot tab: đọc latest_shot.json, gọi on_shot_selected
        """
        data_dir = self._get_pipeline_data_dir()

        if idx == 0:
            # Asset tab
            latest_file = os.path.join(data_dir, "latest_asset.json")
            if os.path.exists(latest_file):
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    asset_path = data.get("asset_path", "")
                    if asset_path and os.path.isdir(asset_path):
                        # Gọi chỉ khi folder còn tồn tại
                        self.on_asset_selected(asset_path)
                except Exception:
                    pass

        elif idx == 1:
            # Shot tab
            latest_file = os.path.join(data_dir, "latest_shot.json")
            if os.path.exists(latest_file):
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    shot_path = data.get("shot_path", "")
                    if shot_path and os.path.isdir(shot_path):
                        self.on_shot_selected(shot_path)
                except Exception:
                    pass

    def on_asset_selected(self, asset_path):
        """
        Khi user chọn asset:
        Load 3 folder con: scenefiles, outputs, textures → 3 tab Preset
        """
        folder_scene = os.path.join(asset_path, "scenefiles")
        self.scene_tab.load_from(folder_scene)

        folder_prod = os.path.join(asset_path, "outputs")
        self.product_tab.load_from(folder_prod)

        folder_lib = os.path.join(asset_path, "textures")
        self.library_tab.load_from(folder_lib)

    def on_shot_selected(self, shot_folder):
        """
        Khi user chọn (hoặc tạo mới) shot:
        Load 3 folder con: scenefiles, outputs, textures → 3 tab Preset
        """
        folder_scene = os.path.join(shot_folder, "scenefiles")
        folder_prod  = os.path.join(shot_folder, "outputs")
        folder_lib   = os.path.join(shot_folder, "textures")

        self.scene_tab.load_from(folder_scene)
        self.product_tab.load_from(folder_prod)
        self.library_tab.load_from(folder_lib)

    def on_user_logout(self):
        """
        Đăng xuất: xóa latest_user.json, mở LoginDialog, update user.
        """
        if os.path.exists(LATEST_USER_FILE):
            os.remove(LATEST_USER_FILE)

        dlg = LoginDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            new_user = dlg.user_edit.text().strip()
            os.makedirs(os.path.dirname(LATEST_USER_FILE), exist_ok=True)
            with open(LATEST_USER_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_user": new_user}, f, ensure_ascii=False, indent=2)
            self.username = new_user
            self.user_btn.setText(f"👤 {self.username}")
            if self.project and os.path.isdir(self.project["path"]):
                self.asset_tab.username = self.username
                self.asset_tab.load_assets()
        else:
            QApplication.instance().quit()

    def on_project_hub(self):
        """
        Chọn dự án mới → update project_root, ghi latest_project.json,
        reload AssetTab, clear 3 tab Preset.
        """
        dlg = ProjectSelectionDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            proj = dlg.get_selected()
            if proj:
                self.project = proj
                self.proj_btn.setText(f"📁 {proj['name']}")

                os.makedirs(os.path.dirname(LATEST_PROJECT_FILE), exist_ok=True)
                with open(LATEST_PROJECT_FILE, "w", encoding="utf-8") as f:
                    json.dump(proj, f, ensure_ascii=False, indent=2)

                # Cập nhật AssetTab và ShotTab
                self.asset_tab.project_root = proj["path"]
                self.asset_tab.load_assets()
                self.shot_tab.project_root = proj["path"]
                self.shot_tab.load_shots()

                # Clear 3 tab Preset
                self.scene_tab.load_from("")
                self.product_tab.load_from("")
                self.library_tab.load_from("")

    def closeEvent(self, event):
        """Ghi nhớ kích thước và vị trí cửa sổ khi đóng ứng dụng."""
        settings_file = os.path.join(BASE_DIR, "data", "window_settings.json")
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        data = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        }
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to save window state:", e)
        super().closeEvent(event)

    def on_refresh(self):
        """
        Reload lại toàn bộ AssetTab và ShotTab (bên trái),
        và chỉ reload tab bên phải đang hiển thị (scene/product/library) nếu có asset đang chọn.
        """
        if not self.project:
            return

        # Xoá tab cũ bên trái
        self.left_tabs.removeTab(0)
        self.left_tabs.removeTab(0)

        # Tạo lại AssetTab và ShotTab
        self.asset_tab = AssetTab(project_root=self.project["path"], username=self.username)
        self.shot_tab  = ShotTab(project_root=self.project["path"], username=self.username)

        # Kết nối lại signal
        self.asset_tab.asset_selected.connect(self.on_asset_selected)
        self.shot_tab.shot_selected.connect(self.on_shot_selected)

        # Thêm lại vào tab widget bên trái
        self.left_tabs.insertTab(0, self.asset_tab, "Asset")
        self.left_tabs.insertTab(1, self.shot_tab, "Shot")
        self.left_tabs.setCurrentIndex(0)





