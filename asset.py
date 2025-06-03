# asset.py

import os
import time
import json
import shutil
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QScrollArea,
    QDialog, QFormLayout, QDialogButtonBox, QLineEdit,
    QComboBox, QLabel, QShortcut, QMessageBox, QMenu,
    QSizePolicy, QToolButton, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPixmap,QFont

from tab_presets import CustomItemWidget

BASE_DIR       = os.path.dirname(__file__)
THUMB_TEMPLATE = os.path.join(BASE_DIR, "template", "thumbnail", "thumb_project.png")


# --- CollapsibleSection để nhóm theo loại asset ---
class CollapsibleSection(QWidget):
    """
    Widget bao gồm một header (QToolButton) và một content widget có thể ẩn/hiện.
    Khi header được nhấn, content.expand() hoặc content.collapse().
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title, checkable=True, checked=True)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.toggled.connect(self.on_toggled)

        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(16, 4, 0, 4)
        self.content_layout.setSpacing(4)
        self.content_area.setLayout(self.content_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

    def on_toggled(self, checked: bool):
        if checked:
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_area.setVisible(True)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_area.setVisible(False)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


class AssetItemWidget(CustomItemWidget):
    """
    Mở rộng CustomItemWidget để hiển thị Asset dưới dạng List View.
    Khi click trái, emit signal asset_selected; khi click phải, hiện menu.
    """

    def __init__(self, title: str, image_path: str, asset_path: str, parent_tab=None):
        super().__init__(title, image_path, text1="", text2="", text3="", parent_tab=parent_tab)
        self.asset_path = asset_path

        # Chuyển sang List View
        self.switch_view("list")
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Lấy widget List View (index=1 trong stack)
        list_widget = self.stack.widget(1)
        if list_widget:
            list_widget.setFixedHeight(60)
            layout = list_widget.layout()
            if layout:
                layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # QLabel đầu tiên là icon
            icon_label = list_widget.findChildren(QLabel)[0]
            # Đặt khung cố định 80×64, căn giữa
            icon_label.setFixedSize(70, 48)
            icon_label.setAlignment(Qt.AlignCenter)

            # Nếu pixmap cũ tồn tại, scale giữ tỉ lệ vừa khung 80×64
            orig_pix = icon_label.pixmap()
            if orig_pix and not orig_pix.isNull():
                scaled = orig_pix.scaled(
                    icon_label.width(),
                    icon_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                icon_label.setPixmap(scaled)

            # Label tiêu đề: căn trái, giữ nguyên bố cục
            self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.title_label.setFont(QFont("Roboto", 9, QFont.Bold))

        for lbl in getattr(self, "sub2_labels", []):
            lbl.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_tab:
            self.parent_tab.clear_selection()
            self.set_selected(True)
            self.parent_tab._write_latest_asset(self.asset_path)
            self.parent_tab.asset_selected.emit(self.asset_path)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        event.ignore()

    def mouseDoubleClickEvent(self, event):
        event.ignore()

    def contextMenuEvent(self, event):
        if self.parent_tab:
            self.parent_tab.clear_selection()
        self.set_selected(True)

        menu = QMenu(self)
        menu.addAction("Open in Explorer", self.open_folder)
        menu.addAction("Copy File Path", self.copy_path)
        menu.addAction("Create Thumbnail", self.create_thumbnail)
        menu.addAction("Delete", self.delete_folder)
        menu.exec_(event.globalPos())

    def open_folder(self):
        if os.path.exists(self.asset_path):
            os.startfile(self.asset_path)

    def copy_path(self):
        QApplication.clipboard().setText(self.asset_path)

    def delete_folder(self):
        if not os.path.exists(self.asset_path):
            return

        confirm = QMessageBox.question(
            self, "Xác nhận xoá",
            f"Bạn có chắc muốn xoá asset này không?\n{self.asset_path}",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        shutil.rmtree(self.asset_path)
        if self.parent_tab and self in self.parent_tab.cards:
            self.parent_tab.cards.remove(self)
            self.parent_tab.container_layout.removeWidget(self)
        self.setParent(None)
        self.deleteLater()

    def create_thumbnail(self):
        clipboard = QApplication.clipboard()
        timeout = time.time() + 30
        img = clipboard.image()

        if img.isNull():
            QMessageBox.warning(self, "Warning", "Không lấy được ảnh từ Clipboard. Vui lòng thử lại.")
            return

        thumb_path = os.path.join(self.asset_path, "thumbnail.png")
        if not img.save(thumb_path, "PNG"):
            QMessageBox.warning(self, "Warning", "Không thể lưu ảnh thumbnail.")
            return

        list_widget = self.stack.widget(1)
        icon_label = list_widget.findChildren(QLabel)[0]
        pix = QPixmap(thumb_path)
        pix = pix.scaled(80, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pix)


class AddAssetDialog(QDialog):
    """
    Dialog nhập tên Asset và chọn loại Asset.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thêm Asset Mới")
        self.asset_name = None
        self.asset_type = None

        layout = QFormLayout()
        self.name_input = QLineEdit()
        layout.addRow("Tên Asset:", self.name_input)

        self.type_input = QComboBox()
        self.type_input.addItems(["character", "prop", "vfx"])
        layout.addRow("Loại Asset:", self.type_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def accept(self):
        self.asset_name = self.name_input.text().strip()
        self.asset_type = self.type_input.currentText()
        if not self.asset_name:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên Asset.")
            return
        super().accept()


class AssetTab(QWidget):
    """
    Widget quản lý Asset:
    - Hiển thị danh sách Asset và nút "Thêm Asset"
    - Mỗi lần select hoặc tạo Asset, ghi latest_asset.json vào <project_root>/00_Pipeline/data/
    - Emit signal asset_selected(asset_path) để MasterUI load tab
    """

    asset_selected = pyqtSignal(str)

    def __init__(self, project_root=None, username=None):
        super().__init__()
        # Trong asset.py (AssetTab.__init__)


        self.project_root = project_root
        self.username = username
        self.cards = []
        self.view_mode = "list"

        self.setFocusPolicy(Qt.StrongFocus)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self._create_thumbnail_selected)

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        main_layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container.setLayout(self.container_layout)
        self.scroll.setWidget(self.container)

        self.add_button = QPushButton("Thêm Asset")
        self.add_button.clicked.connect(self.add_asset)
        main_layout.addWidget(self.add_button)

        self._last_asset_path = None
        self._load_latest_asset()

        if self.project_root and os.path.isdir(os.path.join(self.project_root, "03_Production", "assets")):
            self.load_assets()

    def get_asset_root(self):
        return os.path.join(self.project_root, "03_Production", "assets")

    def _get_pipeline_data_dir(self):
        data_dir = os.path.join(self.project_root, "00_Pipeline", "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def _write_latest_asset(self, asset_path: str):
        data_dir = self._get_pipeline_data_dir()
        latest_file = os.path.join(data_dir, "latest_asset.json")
        if self._last_asset_path == asset_path:
            return
        try:
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump({"asset_path": asset_path}, f, ensure_ascii=False, indent=2)
            self._last_asset_path = asset_path
        except Exception:
            pass

    def _load_latest_asset(self):
        data_dir = self._get_pipeline_data_dir()
        latest_file = os.path.join(data_dir, "latest_asset.json")
        if os.path.exists(latest_file):
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                asset_path = data.get("asset_path", "")
                if asset_path and os.path.isdir(asset_path):
                    self._last_asset_path = asset_path
                else:
                    self._last_asset_path = None
            except Exception:
                self._last_asset_path = None
        else:
            self._last_asset_path = None

    def load_assets(self):
        self.clear_layout(self.container_layout)
        self.cards.clear()

        asset_root = self.get_asset_root()
        if not os.path.isdir(asset_root):
            return

        for asset_type in sorted(os.listdir(asset_root)):
            type_dir = os.path.join(asset_root, asset_type)
            if not os.path.isdir(type_dir):
                continue

            section = CollapsibleSection(asset_type.capitalize())
            self.container_layout.addWidget(section)

            for asset_name in sorted(os.listdir(type_dir)):
                asset_dir = os.path.join(type_dir, asset_name)
                if not os.path.isdir(asset_dir):
                    continue

                thumb_path = THUMB_TEMPLATE
                # Nếu có thumbnail đã lưu, dùng nó
                custom_thumb = os.path.join(asset_dir, "thumbnail.png")
                if os.path.exists(custom_thumb):
                    thumb_path = custom_thumb

                card = AssetItemWidget(asset_name, thumb_path, asset_dir, parent_tab=self)
                section.add_widget(card)
                self.cards.append(card)

            if section.content_layout.count() == 0:
                section.toggle_button.setEnabled(False)
                section.toggle_button.setArrowType(Qt.RightArrow)
                section.content_area.setVisible(False)

        if self._last_asset_path:
            for c in self.cards:
                if c.asset_path == self._last_asset_path:
                    c.set_selected(True)
                    self.asset_selected.emit(self._last_asset_path)
                    sec_widget = c.parent().parent()
                    if isinstance(sec_widget, CollapsibleSection):
                        sec_widget.toggle_button.setChecked(True)
                    break

    def add_asset(self):
        dialog = AddAssetDialog()
        if dialog.exec_():
            asset_name = dialog.asset_name
            asset_type = dialog.asset_type

            asset_path = os.path.join(self.project_root, "03_Production", "assets", asset_type, asset_name)
            os.makedirs(asset_path, exist_ok=True)
            for sub in ["scenefiles", "outputs", "textures"]:
                os.makedirs(os.path.join(asset_path, sub), exist_ok=True)

            # Lấy user từ latest_user.json
            user_name = ""
            if self.project_root:
                latest_user_file = os.path.join(BASE_DIR, "data", "latest_user.json")
                if os.path.exists(latest_user_file):
                    try:
                        with open(latest_user_file, "r", encoding="utf-8") as uf:
                            udata = json.load(uf)
                        user_name = udata.get("last_user", "")
                    except Exception:
                        user_name = ""

            # Tạo JSON metadata cho asset chung
            data = {
                "name":    asset_name,
                "type":    asset_type,
                "user":    user_name,
                "version": 1,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            json_path = os.path.join(asset_path, f"{asset_name}.json")
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Không thể tạo file JSON metadata:\n{e}")

            # Tạo file .blend mặc định cho stage "Modeling"
            latest_proj_file = os.path.join(os.path.dirname(__file__), "data", "latest_project.json")
            project_short = ""
            if os.path.exists(latest_proj_file):
                try:
                    with open(latest_proj_file, "r", encoding="utf-8") as f:
                        proj_data = json.load(f)
                    project_short = proj_data.get("short", "")
                except Exception:
                    project_short = ""
            if project_short:
                template_blend = os.path.join(BASE_DIR, "template", "app", "blender_template.blend")
                if os.path.exists(template_blend):
                    new_blend = f"{project_short}_{asset_name}_modeling.blend"
                    blender_dest = os.path.join(asset_path, "scenefiles", new_blend)
                    shutil.copy(template_blend, blender_dest)

                    # Tạo JSON metadata riêng cho file .blend này
                    name_no_ext = os.path.splitext(new_blend)[0]
                    json_per_file = os.path.join(asset_path, "scenefiles", f"{name_no_ext}.json")

                    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M")
                    version_str = "001"
                    metadata = {
                        "name":    asset_name,
                        "type":    asset_type,
                        "stage":   "Modeling",
                        "user":    user_name,
                        "version": version_str,
                        "created": timestamp
                    }
                    try:
                        with open(json_per_file, "w", encoding="utf-8") as jf:
                            json.dump(metadata, jf, ensure_ascii=False, indent=4)
                    except Exception as e:
                        QMessageBox.warning(self, "Warning", f"Không thể tạo JSON cho file .blend:\n{e}")

                else:
                    QMessageBox.warning(self, "Warning", f"Không tìm thấy blender_template.blend tại:\n{template_blend}")

            # Reload lại danh sách asset và tự động chọn asset mới
            self.load_assets()
            new_card = next((c for c in self.cards if c.asset_path == asset_path), None)
            if new_card:
                self.clear_selection()
                new_card.set_selected(True)
                self._write_latest_asset(asset_path)
                self.asset_selected.emit(asset_path)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def clear_selection(self):
        for c in self.cards:
            c.set_selected(False)

    def get_selected_widget(self):
        for c in self.cards:
            if c._selected:
                return c
        return None

    def _open_selected(self):
        w = self.get_selected_widget()
        if w:
            w.open_folder()

    def _copy_selected(self):
        w = self.get_selected_widget()
        if w:
            w.copy_path()

    def _delete_selected(self):
        w = self.get_selected_widget()
        if w:
            w.delete_folder()

    def _create_thumbnail_selected(self):
        w = self.get_selected_widget()
        if w:
            w.create_thumbnail()