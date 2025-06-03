# shot.py

import os
import time
import json
import shutil
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QScrollArea,
    QLabel, QShortcut, QMessageBox, QMenu, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPixmap, QFont

from tab_presets import CustomItemWidget

BASE_DIR         = os.path.dirname(__file__)
THUMB_TEMPLATE   = os.path.join(BASE_DIR, "template", "thumbnail", "thumb_project.png")
BLENDER_TEMPLATE = os.path.join(BASE_DIR, "template", "app", "blender_template.blend")


class ShotItemWidget(CustomItemWidget):
    """
    Mở rộng CustomItemWidget để hiển thị mỗi Shot dưới dạng List View.
    - Khi click trái: chọn và emit signal shot_selected.
    - Khi click phải: hiện context menu với Open, Copy Path, Create Thumbnail, Delete shot.
    """

    def __init__(self, title: str, image_path: str, shot_path: str, parent_tab=None):
        super().__init__(title, image_path, text1="", text2="", text3="", parent_tab=parent_tab)
        self.shot_path = shot_path

        # Chuyển sang List View và tùy chỉnh kích thước/căn lề icon
        self.switch_view("list")
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        list_widget = self.stack.widget(1)  # widget List View
        if list_widget:
            list_widget.setFixedHeight(60)
            layout = list_widget.layout()
            if layout:
                layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            icon_label = list_widget.findChildren(QLabel)[0]
            icon_label.setFixedSize(70, 48)
            icon_label.setAlignment(Qt.AlignCenter)

            orig_pix = icon_label.pixmap()
            if orig_pix and not orig_pix.isNull():
                scaled = orig_pix.scaled(
                    icon_label.width(),
                    icon_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                icon_label.setPixmap(scaled)

            self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.title_label.setFont(QFont("Roboto", 9, QFont.Bold))

        for lbl in getattr(self, "sub2_labels", []):
            lbl.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_tab:
            self.parent_tab.clear_selection()
            self.set_selected(True)
            self.parent_tab._write_latest_shot(self.shot_path)
            self.parent_tab.shot_selected.emit(self.shot_path)
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
        if os.path.exists(self.shot_path):
            os.startfile(self.shot_path)

    def copy_path(self):
        QApplication.clipboard().setText(self.shot_path)

    def delete_folder(self):
        if not os.path.exists(self.shot_path):
            return

        confirm = QMessageBox.question(
            self, "Xác nhận xoá",
            f"Bạn có chắc muốn xoá shot này không?\n{self.shot_path}",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        shutil.rmtree(self.shot_path)
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

        thumb_path = os.path.join(self.shot_path, "thumbnail.png")
        if not img.save(thumb_path, "PNG"):
            QMessageBox.warning(self, "Warning", "Không thể lưu ảnh thumbnail.")
            return

        list_widget = self.stack.widget(1)
        icon_label = list_widget.findChildren(QLabel)[0]
        pix = QPixmap(thumb_path)
        pix = pix.scaled(100, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pix)


class ShotTab(QWidget):
    """
    Tab quản lý Shot:
    - Lưu trữ tất cả shot trong <project_root>/03_Production/sequencer
    - Nút "Thêm Shot": tự động tăng dần số thứ tự (001, 002, …), tạo subfolders: scenefiles, outputs, playblast, textures.
    - Khi tạo shot mới:
        • Tạo <shot_folder>/<shot_name>.json metadata chung.
        • Copy template .blend vào <shot_folder>/scenefiles/<PROJECT_SHORT>_<SHOT_NAME>_animation.blend.
        • Tạo kèm file JSON metadata riêng cho file .blend vừa tạo.
    - Mỗi lần chọn hoặc tạo mới, ghi latest_shot.json trong <project_root>/00_Pipeline/data.
    """

    shot_selected = pyqtSignal(str)

    def __init__(self, project_root=None, username=None):
        super().__init__()
        self.project_root = project_root
        self.username     = username
        self.cards        = []
        self.view_mode    = "list"

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

        self.add_button = QPushButton("Thêm Shot")
        self.add_button.clicked.connect(self.add_shot)
        main_layout.addWidget(self.add_button)

        # Thiết lập phím tắt
        self.sc_open   = QShortcut(QKeySequence("Ctrl+E"), self)
        self.sc_copy   = QShortcut(QKeySequence("Ctrl+C"), self)
        self.sc_delete = QShortcut(QKeySequence("Ctrl+X"), self)
        self.sc_open  .setContext(Qt.ApplicationShortcut)
        self.sc_copy  .setContext(Qt.ApplicationShortcut)
        self.sc_delete.setContext(Qt.ApplicationShortcut)
        self.sc_open  .activated.connect(self._open_selected)
        self.sc_copy  .activated.connect(self._copy_selected)
        self.sc_delete.activated.connect(self._delete_selected)

        self._last_shot_path = None
        self._load_latest_shot()

        if self.project_root:
            self.load_shots()

    def get_shot_root(self) -> str:
        """
        Trả về thư mục chung chứa các shot: <project_root>/03_Production/sequencer.
        """
        seq_folder = os.path.join(self.project_root, "03_Production", "sequencer")
        os.makedirs(seq_folder, exist_ok=True)
        return seq_folder

    def _get_pipeline_data_dir(self) -> str:
        """
        Trả về thư mục lưu trữ file latest_shot.json: <project_root>/00_Pipeline/data.
        """
        data_dir = os.path.join(self.project_root, "00_Pipeline", "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def _write_latest_shot(self, shot_path: str):
        """
        Ghi đường dẫn shot hiện tại vào latest_shot.json (nếu khác với lần trước).
        """
        data_dir   = self._get_pipeline_data_dir()
        latest_file = os.path.join(data_dir, "latest_shot.json")

        if self._last_shot_path == shot_path:
            return

        try:
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump({"shot_path": shot_path}, f, ensure_ascii=False, indent=2)
            self._last_shot_path = shot_path
        except Exception:
            pass

    def _load_latest_shot(self):
        """
        Đọc latest_shot.json (nếu có) để nhớ lần chọn shot gần nhất.
        """
        data_dir   = self._get_pipeline_data_dir()
        latest_file = os.path.join(data_dir, "latest_shot.json")
        if os.path.exists(latest_file):
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                shot_path = data.get("shot_path", "")
                if shot_path and os.path.isdir(shot_path):
                    self._last_shot_path = shot_path
                else:
                    self._last_shot_path = None
            except Exception:
                self._last_shot_path = None
        else:
            self._last_shot_path = None

    def load_shots(self):
        """
        Load tất cả folder shot (tên là số) trong sequencer, mỗi folder tạo 1 ShotItemWidget.
        Nếu có latest_shot, chọn luôn.
        """
        # Xóa layout cũ
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.cards.clear()

        shot_root = self.get_shot_root()
        shot_list = []
        for name in os.listdir(shot_root):
            full = os.path.join(shot_root, name)
            if os.path.isdir(full) and name.isdigit():
                shot_list.append((name, full))
        shot_list.sort(key=lambda x: int(x[0]))

        for shot_name, shot_folder in shot_list:
            self._add_card(shot_name, shot_folder)

        if self._last_shot_path:
            for c in self.cards:
                if c.shot_path == self._last_shot_path:
                    c.set_selected(True)
                    self.shot_selected.emit(self._last_shot_path)
                    break

    def add_shot(self):
        """
        Tạo shot mới với tên tự động (tiếp theo 001,002,…):
        - Tạo folder <shot_root>/<shot_name> và subfolders: scenefiles, outputs, playblast, textures.
        - Tạo file JSON metadata chung: <shot_name>.json.
        - Copy template .blend vào <shot_folder>/scenefiles/<PROJECT_SHORT>_<SHOT_NAME>_animation.blend và tạo kèm file JSON riêng.
        - Thêm card vào UI, chọn mặc định, ghi latest_shot.json và emit signal.
        """
        shot_root = self.get_shot_root()
        existing = [int(n) for n in os.listdir(shot_root) if n.isdigit()]
        next_num = max(existing) + 1 if existing else 1

        shot_name  = f"{next_num:03d}"
        new_folder = os.path.join(shot_root, shot_name)
        try:
            os.makedirs(new_folder, exist_ok=False)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo folder shot mới:\n{e}")
            return

        # Tạo subfolders
        for sub in ["scenefiles", "outputs", "playblast", "textures"]:
            try:
                os.makedirs(os.path.join(new_folder, sub), exist_ok=True)
            except Exception:
                pass

        # 1) Tạo JSON metadata chung cho shot
        data = {
            "name":    shot_name,
            "user":    self.username or "",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        json_path = os.path.join(new_folder, f"{shot_name}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

        # 2) Copy template .blend vào scenefiles và tạo JSON kèm theo
        #    Lấy project_short từ latest_project.json
        project_short = ""
        latest_proj_file = os.path.join(os.path.dirname(__file__), "data", "latest_project.json")
        if os.path.exists(latest_proj_file):
            try:
                with open(latest_proj_file, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                project_short = proj_data.get("short", "")
            except Exception:
                project_short = ""

        if project_short and os.path.exists(BLENDER_TEMPLATE):
            new_blend_name = f"{project_short}_{shot_name}_animation.blend"
            dest_blend = os.path.join(new_folder, "scenefiles", new_blend_name)
            try:
                shutil.copy(BLENDER_TEMPLATE, dest_blend)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Không thể copy template .blend:\n{e}")
            else:
                # Tạo JSON metadata riêng cho file .blend vừa tạo
                name_no_ext = os.path.splitext(new_blend_name)[0]
                json_per_file = os.path.join(new_folder, "scenefiles", f"{name_no_ext}.json")

                # Lấy last_user từ latest_user.json
                user_name = ""
                if self.project_root:
                    latest_user_file = os.path.join(
                        self.project_root, "00_Pipeline", "data", "latest_user.json"
                    )
                    if os.path.exists(latest_user_file):
                        try:
                            with open(latest_user_file, "r", encoding="utf-8") as uf:
                                udata = json.load(uf)
                            user_name = udata.get("last_user", "")
                        except Exception:
                            user_name = ""

                timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M")
                version_str = "001"

                metadata = {
                    "name":    shot_name,
                    "stage":   "Animation",
                    "user":    user_name,
                    "version": version_str,
                    "created": timestamp
                }
                try:
                    with open(json_per_file, "w", encoding="utf-8") as jf:
                        json.dump(metadata, jf, ensure_ascii=False, indent=4)
                except Exception as e:
                    QMessageBox.warning(self, "Warning", f"Không thể tạo JSON cho file .blend:\n{e}")

        # 3) Thêm card mới vào UI và chọn nó
        card = self._add_card(shot_name, new_folder)
        self.clear_selection()
        card.set_selected(True)

        # 4) Ghi lại latest_shot và emit signal
        self._write_latest_shot(new_folder)
        self.shot_selected.emit(new_folder)

    def _add_card(self, shot_name: str, shot_folder: str):
        """
        Tạo ShotItemWidget và thêm vào container_layout, lưu vào self.cards.
        """
        thumb = THUMB_TEMPLATE if os.path.exists(THUMB_TEMPLATE) else ""
        card = ShotItemWidget(shot_name, thumb, shot_folder, parent_tab=self)
        self.container_layout.addWidget(card)
        self.cards.append(card)
        return card

    def clear_layout(self, layout):
        """
        Xóa toàn bộ widgets trong layout.
        """
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def clear_selection(self):
        """
        Bỏ chọn toàn bộ ShotItemWidget hiện tại.
        """
        for c in self.cards:
            c.set_selected(False)

    def get_selected_widget(self):
        """
        Trả về widget đang được chọn (nếu có), ngược lại None.
        """
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
            # Khi xóa một shot, toàn bộ folder shot including JSON per-file đã được dựng sẵn xóa cùng
            w.delete_folder()
    def _create_thumbnail_selected(self):
        w = self.get_selected_widget()
        if w:
            w.create_thumbnail()