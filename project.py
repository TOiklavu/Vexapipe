# project.py

import os
import json
import shutil
import datetime

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QScrollArea,
    QGridLayout,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

from tab_presets import CustomItemWidget

BASE_DIR = os.path.dirname(__file__)
TEMPLATE_THUMB = os.path.join(BASE_DIR, "template", "thumbnail", "thumb_project.png")
LATEST_PROJECT_FILE = os.path.join(BASE_DIR, "data", "latest_project.json")
LATEST_PROJECTS_ROOT = os.path.join(BASE_DIR, "data", "latest_projects_root.json")


def create_project_folders(base_path: str, name: str, short: str) -> str:
    """
    Tạo cấu trúc thư mục cho một dự án mới:
      base_path: Ví dụ "F:/Projects" (thư mục chứa tất cả dự án)
      name:      Tên hiển thị của dự án (ví dụ "MyProject")
      short:     Tên viết tắt (ví dụ "MP")
    Kết quả:
      - Tạo folder "<base_path>/<YYYY>_<name>"
      - Bên trong có subfolders:
          00_Pipeline
          01_Management
          02_Designs
          03_Production
          04_Resources
      - Copy thumbnail mẫu (nếu có) vào "<proj_folder>/thumbnail.png"
      - Tạo JSON file "<proj_folder>/00_Pipeline/project.json" chứa:
          { "name": ..., "short": ..., "path": ... }
      Trả về đường dẫn tuyệt đối đến proj_folder.
    """
    year = str(datetime.datetime.now().year)
    folder_name = f"{year}_{name.strip()}"
    proj_folder = os.path.join(base_path, folder_name)

    # 1) Tạo cấu trúc thư mục
    subfolders = [
        "00_Pipeline",
        "01_Management",
        "02_Designs",
        "03_Production",
        "04_Resources"
    ]
    for sub in subfolders:
        os.makedirs(os.path.join(proj_folder, sub), exist_ok=True)

    # 2) Copy thumbnail mẫu (nếu có)
    thumb_src = TEMPLATE_THUMB
    thumb_dst = os.path.join(proj_folder, "thumbnail.png")
    if os.path.exists(thumb_src):
        try:
            shutil.copy(thumb_src, thumb_dst)
        except Exception:
            pass

    # 3) Tạo project.json riêng trong "00_Pipeline"
    pipeline_folder = os.path.join(proj_folder, "00_Pipeline")
    project_json_path = os.path.join(pipeline_folder, "project.json")
    proj_data = {
        "name": name.strip(),
        "short": short.strip(),
        "path": os.path.abspath(proj_folder)
    }
    try:
        with open(project_json_path, "w", encoding="utf-8") as f:
            json.dump(proj_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise RuntimeError(f"Không thể ghi project.json tại {project_json_path}:\n{e}")

    return os.path.abspath(proj_folder)


class AddProjectDialog(QDialog):
    """
    Dialog cho phép user nhập:
      - Tên dự án
      - Tên viết tắt (short)
      - Thư mục gốc để chứa dự án (projects_root)
    Khi nhấn OK, trả về dict: {"name":..., "short":..., "base_path": ...}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm Dự án Mới")
        self.resize(400, 220)

        self.name_edit = QLineEdit()
        self.short_edit = QLineEdit()
        self.base_edit = QLineEdit()
        self.base_edit.setReadOnly(True)

        btn_browse = QPushButton("Chọn...")
        btn_browse.clicked.connect(self.on_browse)

        h_base = QHBoxLayout()
        h_base.addWidget(self.base_edit)
        h_base.addWidget(btn_browse)

        form = QFormLayout()
        form.addRow("Tên dự án:", self.name_edit)
        form.addRow("Tên viết tắt:", self.short_edit)
        form.addRow("Thư mục chứa:", h_base)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        v = QVBoxLayout(self)
        v.addLayout(form)
        v.addWidget(buttons)

    def on_browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa tất cả dự án")
        if directory:
            self.base_edit.setText(directory)

    def accept(self):
        name = self.name_edit.text().strip()
        short = self.short_edit.text().strip()
        base = self.base_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên dự án.")
            return
        if not short:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên viết tắt.")
            return
        if not base or not os.path.isdir(base):
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn thư mục chứa dự án hợp lệ.")
            return

        self.project_data = {
            "name": name,
            "short": short,
            "base_path": base
        }
        super().accept()

    def get_data(self):
        """
        Sau khi exec_() trả về:
          self.project_data = {"name":..., "short":..., "base_path":...}
        """
        return getattr(self, "project_data", None)


class ProjectSelectionDialog(QDialog):
    """
    Dialog để chọn dự án. 
    - Bấm 'Chọn thư mục chứa dự án' để chọn projects_root (ví dụ "F:/Projects").
    - Hệ thống scan subfolder trong projects_root; mỗi folder con có "00_Pipeline/project.json" sẽ được load.
    - Hiển thị các CustomItemWidget cho từng dự án tìm được.
    - Có nút 'Thêm dự án' để tạo mới dự án bên trong projects_root hiện tại.
    - Khi double-click vào một project, return dữ liệu project đó.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn Dự án")
        self.resize(800, 600)

        # Nếu trước đó user đã chọn một thư mục chứa dự án, load đường dẫn đó
        self.projects_root = ""
        if os.path.exists(LATEST_PROJECTS_ROOT):
            try:
                with open(LATEST_PROJECTS_ROOT, "r", encoding="utf-8") as f:
                    data = json.load(f)
                candidate = data.get("projects_root", "")
                if candidate and os.path.isdir(candidate):
                    self.projects_root = candidate
                else:
                    self.projects_root = ""
            except Exception:
                self.projects_root = ""
        else:
            self.projects_root = ""

        self.projects = []         # Danh sách dict {"name","short","path"}

        # --- Layout chính ---
        main_layout = QVBoxLayout(self)

        # Nút chọn thư mục chứa dự án
        h_top = QHBoxLayout()
        self.btn_choose_root = QPushButton("Chọn thư mục chứa dự án")
        self.btn_choose_root.clicked.connect(self.on_choose_root)
        h_top.addWidget(self.btn_choose_root)

        # Nút "Thêm dự án" (chỉ enable nếu đã chọn root)
        self.btn_add = QPushButton("Thêm dự án")
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self.on_add)
        h_top.addWidget(self.btn_add)

        main_layout.addLayout(h_top)

        # ScrollArea chứa grid các project item
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setAlignment(Qt.AlignTop)
        self.grid.setSpacing(20)
        self.scroll.setWidget(container)
        main_layout.addWidget(self.scroll)

        self.selected_project = None

        # Nếu đã có projects_root hợp lệ, bật nút "Thêm dự án" và populate ngay
        if self.projects_root:
            self.btn_add.setEnabled(True)
            self.populate()

    def on_choose_root(self):
        """
        Mở dialog để chọn thư mục gốc chứa các dự án.
        Sau đó scan và populate danh sách project, đồng thời ghi lại đường dẫn này vào LATEST_PROJECTS_ROOT.
        """
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục gốc chứa dự án")
        if not directory:
            return

        self.projects_root = directory
        self.btn_add.setEnabled(True)

        # Ghi lại vào latest_projects_root.json để nhớ lần sau
        try:
            data = { "projects_root": self.projects_root }
            os.makedirs(os.path.dirname(LATEST_PROJECTS_ROOT), exist_ok=True)
            with open(LATEST_PROJECTS_ROOT, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Sau đó scan và hiển thị danh sách các project tìm được
        self.populate()

    def populate(self):
        """
        Scan tất cả thư mục con của self.projects_root.
        Với mỗi folder con, kiểm tra file:
            <folder_con>/00_Pipeline/project.json
        Nếu tồn tại, đọc vào và thêm vào self.projects, rồi hiển thị.
        """
        # Xóa grid cũ
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.projects.clear()
        if not self.projects_root or not os.path.isdir(self.projects_root):
            return

        # Duyệt thư mục con
        for name in sorted(os.listdir(self.projects_root)):
            proj_dir = os.path.join(self.projects_root, name)
            if not os.path.isdir(proj_dir):
                continue

            pipeline_json = os.path.join(proj_dir, "00_Pipeline", "project.json")
            if not os.path.exists(pipeline_json):
                continue

            # Đọc nội dung project.json
            try:
                with open(pipeline_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Kiểm tra các key cần thiết
                if all(k in data for k in ("name", "short", "path")):
                    self.projects.append(data)
                else:
                    continue
            except Exception:
                continue

        # Hiển thị mỗi project bằng CustomItemWidget
        cols = 3
        for idx, proj in enumerate(self.projects):
            thumb_path = os.path.join(proj["path"], "thumbnail.png")
            if not os.path.exists(thumb_path):
                thumb_path = TEMPLATE_THUMB

            item = CustomItemWidget(
                proj["name"],
                thumb_path,
                "",  # text1
                "",  # text2
                "",  # text3
                parent_tab=self
            )
            item.setAcceptDrops(False)
            item.setContextMenuPolicy(Qt.NoContextMenu)
            item.mouseMoveEvent = lambda e: None

            # Single-click: chọn item
            def make_click(it):
                def on_click(ev):
                    if ev.button() == Qt.LeftButton:
                        for c in self.findChildren(CustomItemWidget):
                            c.set_selected(False)
                        it.set_selected(True)
                    else:
                        QWidget.mousePressEvent(it, ev)
                return on_click

            item.mousePressEvent = make_click(item)

            # Double-click: chọn project và đóng dialog
            def make_dblclick(p):
                def on_dbl(ev):
                    if ev.button() == Qt.LeftButton:
                        # Ghi ngay latest_project.json để MasterUI khởi chạy lần sau
                        os.makedirs(os.path.dirname(LATEST_PROJECT_FILE), exist_ok=True)
                        try:
                            with open(LATEST_PROJECT_FILE, "w", encoding="utf-8") as f:
                                json.dump(p, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                        self.selected_project = p
                        self.accept()
                return on_dbl

            item.mouseDoubleClickEvent = make_dblclick(proj)

            r, c = divmod(idx, cols)
            self.grid.addWidget(item, r, c)

    def on_add(self):
        """
        Khi nút 'Thêm dự án' được nhấn:
        - Mở AddProjectDialog để nhập name, short, base_path = self.projects_root
        - Sau khi OK, gọi create_project_folders(self.projects_root, name, short)
        - Thêm project mới vào grid lập tức
        - Ghi latest_project.json (để MasterUI load ban đầu)
        """
        if not self.projects_root:
            return

        dlg = AddProjectDialog(self)
        # Pre-fill base_path với self.projects_root
        dlg.base_edit.setText(self.projects_root)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            name = data["name"]
            short = data["short"]
            base = data["base_path"]

            try:
                new_path = create_project_folders(base, name, short)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Tạo dự án không thành công:\n{e}")
                return

            # Sau khi tạo, đọc lại project.json từ 00_Pipeline
            proj_json = os.path.join(new_path, "00_Pipeline", "project.json")
            if os.path.exists(proj_json):
                try:
                    with open(proj_json, "r", encoding="utf-8") as f:
                        new_proj_data = json.load(f)
                    self.projects.append(new_proj_data)
                except Exception:
                    pass

            # Reload grid để thấy project mới
            self.populate()

            # Ghi latest_project.json để MasterUI khởi chạy lần đầu
            os.makedirs(os.path.dirname(LATEST_PROJECT_FILE), exist_ok=True)
            try:
                with open(LATEST_PROJECT_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_proj_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def get_selected(self):
        """
        Sau khi dialog accept, trả về dict của project đã chọn:
        { "name":..., "short":..., "path":... }
        """
        return self.selected_project
