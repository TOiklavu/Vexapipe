import os
import shutil
import json
import datetime
from PyQt5.QtWidgets import (
    QDialog, QMessageBox, QFileDialog, QGridLayout, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from tab_presets import CustomItemWidget

# Đường dẫn lưu trạng thái
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LATEST_DRIVE_FILE   = os.path.join(DATA_DIR, "latest_drive.json")
LATEST_LOCAL_FILE   = os.path.join(DATA_DIR, "latest_local.json")
LATEST_PROJECT_FILE = os.path.join(DATA_DIR, "latest_project.json")
TEMPLATE_THUMB = os.path.join(BASE_DIR, "template", "thumbnail.png")


def create_project_folders(base_path: str, name: str, short: str) -> str:
    year = str(datetime.datetime.now().year)
    folder_name = f"{year}_{name.strip()}"
    proj_folder = os.path.join(base_path, folder_name)
    os.makedirs(proj_folder, exist_ok=True)

    subfolders = [
        "00_Pipeline", "01_Management", "02_Designs",
        "03_Production", "04_Resources"
    ]
    for sub in subfolders:
        os.makedirs(os.path.join(proj_folder, sub), exist_ok=True)

    # Copy thumbnail mẫu
    if os.path.exists(TEMPLATE_THUMB):
        shutil.copy(TEMPLATE_THUMB, os.path.join(proj_folder, "thumbnail.png"))

    # Ghi metadata
    proj_data = {
        "name": name.strip(),
        "short": short.strip(),
        "path": os.path.abspath(proj_folder)
    }
    with open(os.path.join(proj_folder, "project.json"), "w", encoding="utf-8") as f:
        json.dump(proj_data, f, ensure_ascii=False, indent=2)

    return os.path.abspath(proj_folder)


class AddProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm dự án")
        self.name_label  = QLabel("Name:")
        self.name_edit   = QLineEdit()
        self.short_label = QLabel("Short:")
        self.short_edit  = QLineEdit()

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.name_label)
        form_layout.addWidget(self.name_edit)
        form_layout.addWidget(self.short_label)
        form_layout.addWidget(self.short_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn     = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        self.project_data = None

    def accept(self):
        name  = self.name_edit.text().strip()
        short = self.short_edit.text().strip()
        if not name or not short:
            QMessageBox.warning(self, "Thiếu thông tin", "Phải nhập Name và Short.")
            return
        self.project_data = {"name": name, "short": short}
        super().accept()

    def get_data(self):
        return self.project_data


class ProjectSelectionDialog(QDialog):
    project_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn dự án")

        # Nút chọn Drive, Local, Thêm dự án
        self.choose_drive_btn = QPushButton("Chọn Drive...")
        self.choose_local_btn = QPushButton("Chọn Local...")
        self.add_btn          = QPushButton("Thêm dự án")
        self.add_btn.setEnabled(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Drive:"))
        top_layout.addWidget(self.choose_drive_btn)
        top_layout.addWidget(QLabel("Local:"))
        top_layout.addWidget(self.choose_local_btn)
        top_layout.addWidget(self.add_btn)

        # Grid hiển thị project
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.grid_widget)

        # Kết nối
        self.choose_drive_btn.clicked.connect(self.on_choose_drive)
        self.choose_local_btn.clicked.connect(self.on_choose_local)
        self.add_btn.clicked.connect(self.on_add)

        # Load trạng thái gần nhất
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.isfile(LATEST_DRIVE_FILE):
            d = json.load(open(LATEST_DRIVE_FILE, 'r', encoding='utf-8')).get('path', '')
            if os.path.isdir(d):
                self.drive_root = d
                self.choose_drive_btn.setText(d)
        if os.path.isfile(LATEST_LOCAL_FILE):
            l = json.load(open(LATEST_LOCAL_FILE, 'r', encoding='utf-8')).get('path', '')
            if os.path.isdir(l):
                self.local_root = l
                self.choose_local_btn.setText(l)

        if hasattr(self, 'drive_root') and hasattr(self, 'local_root'):
            self.add_btn.setEnabled(True)
            self.load_projects()

    def on_choose_drive(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn Drive folder", "")
        if path:
            self.drive_root = path
            self.choose_drive_btn.setText(path)
            json.dump({'path': path}, open(LATEST_DRIVE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            if hasattr(self, 'local_root'):
                self.add_btn.setEnabled(True)
            self.load_projects()

    def on_choose_local(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn Local folder", "")
        if path:
            self.local_root = path
            self.choose_local_btn.setText(path)
            json.dump({'path': path}, open(LATEST_LOCAL_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            if hasattr(self, 'drive_root'):
                self.add_btn.setEnabled(True)
            self.load_projects()

    def make_dblclick(self, proj_data):
        def on_dbl(ev):
            if ev.button() == Qt.LeftButton:
                os.makedirs(os.path.dirname(LATEST_PROJECT_FILE), exist_ok=True)
                try:
                    with open(LATEST_PROJECT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(proj_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                self.project_selected.emit(proj_data)
                self.accept()
            else:
                super(ProjectSelectionDialog, self).mouseDoubleClickEvent(ev)
        return on_dbl

    def load_projects(self):
        # Clear cũ
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        if not hasattr(self, 'drive_root'):
            return
        folders = sorted(os.listdir(self.drive_root))
        cols = 3
        idx = 0
        for nm in folders:
            pd = os.path.join(self.drive_root, nm)
            pj = os.path.join(pd, 'project.json')
            if not os.path.isfile(pj):
                continue
            meta = json.load(open(pj, 'r', encoding='utf-8'))
            proj_data = {
                'name': meta.get('name', nm),
                'short': meta.get('short', ''),
                'path': pd,
                'local_path': os.path.join(self.local_root, nm)
            }
            thumb = os.path.join(pd, 'thumbnail.png')
            item = CustomItemWidget(proj_data['name'], thumb, parent_tab=self)
            item.drive_path = pd
            item.local_path = proj_data['local_path']
            # Download button only
            if os.path.isdir(item.local_path):
                item.download_btn.hide()
            else:
                item.download_btn.clicked.connect(lambda _, it=item: self.download(it))
            # Double click only write JSON and accept
            item.mouseDoubleClickEvent = self.make_dblclick(proj_data)

            row = idx // cols
            col = idx % cols
            self.grid.addWidget(item, row, col)
            idx += 1

    def download(self, item):
        try:
            shutil.copytree(item.drive_path, item.local_path)
            item.download_btn.hide()
        except Exception as e:
            QMessageBox.critical(self, 'Lỗi tải dự án', f'Không thể tải dự án:\n{e}')

    def on_add(self):
        dlg = AddProjectDialog(self)
        if dlg.exec_():
            pd = dlg.get_data()
            drive_proj = create_project_folders(self.drive_root, pd['name'], pd['short'])
            local_proj = os.path.join(self.local_root, os.path.basename(drive_proj))
            shutil.copytree(drive_proj, local_proj)
            # Hiển thị mới ngay
            proj_data = {'name': pd['name'], 'short': pd['short'], 'path': drive_proj, 'local_path': local_proj}
            thumb = os.path.join(drive_proj, 'thumbnail.png')
            item = CustomItemWidget(proj_data['name'], thumb, parent_tab=self)
            item.drive_path = drive_proj
            item.local_path = local_proj
            item.download_btn.hide()
            # attach double click
            item.mouseDoubleClickEvent = self.make_dblclick(proj_data)
            idx = self.grid.count()
            row = idx // 3
            col = idx % 3
            self.grid.addWidget(item, row, col)

    def get_selected(self):
        try:
            return json.load(open(LATEST_PROJECT_FILE, 'r', encoding='utf-8'))
        except:
            return None

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = ProjectSelectionDialog()
    dlg.exec_()
    print('Chọn dự án:', dlg.get_selected())
