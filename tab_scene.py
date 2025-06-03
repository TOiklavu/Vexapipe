# tab_scene.py

import os
import time
import json
import shutil

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QMessageBox
from tab_presets import BaseCardTab, CustomItemWidget

BASE_DIR            = os.path.dirname(__file__)
BLENDER_ICON        = os.path.join(BASE_DIR, "template", "logo", "logo_blender.jpg")
BLENDER_TEMPLATE    = os.path.join(BASE_DIR, "template", "app", "blender_template.blend")
LATEST_PROJECT_FILE = os.path.join(BASE_DIR, "data", "latest_project.json")


class SceneTab(BaseCardTab):
    """
    Tab Scene hiển thị tất cả file .blend trong <asset_or_shot>/scenefiles> ở chế độ List View.
    - Dùng eventFilter để bắt QEvent.ContextMenu (right-click).
    - Nếu nhấn phải lên một CustomItemWidget (card), bỏ qua (card có menu riêng).
    - Nếu nhấn phải lên vùng trống, hiện menu các stage tương ứng:
        + Asset: Modeling, Texturing, Rigging, Groom
        + Shot:  Animation, Blocking, Lighting, Vfx
      Những stage đã tồn tại file .blend sẽ bị ẩn.
    - Khi tạo file .blend mới (dù từ asset mới hoặc context-menu), luôn tạo kèm file JSON có cùng tên:
      {
        "name": "<tên asset/shot>",
        "type": "<chỉ Asset mới có: ví dụ \"character\">",
        "stage": "<Modeling/Texturing/... hoặc Animation/...>",
        "user": "<username lấy từ latest_user.json>",
        "version": "001",
        "created": "YYYY-MM-DD HH:MM"
      }
    - Khi load danh sách, mỗi item lấy thông tin từ file JSON tương ứng để hiển thị:
        * title  = stage (viết hoa)
        * text1  = "v" + version  (ví dụ "v001")
        * text2  = created
        * text3  = user
    - Mỗi khi bấm “Delete” trên một card, ngoài việc xoá file .blend, cũng sẽ xoá luôn file .json đi kèm.
    """

    def __init__(self):
        super().__init__([])
        self.setAcceptDrops(True)
        self.current_folder = None

        # --- Khởi tạo project_root (đường dẫn tới thư mục dự án) từ latest_project.json ---
        self.project_root = ""
        try:
            with open(LATEST_PROJECT_FILE, "r", encoding="utf-8") as f:
                proj_data = json.load(f)
            # latest_project.json phải có trường "path": "<project_root>"
            self.project_root = proj_data.get("path", "")
        except Exception:
            self.project_root = ""
        # ------------------------------------------------------------------------------

        # Mặc định hiển thị List View
        self.set_view_mode("list")

        # Cài eventFilter để bắt QEvent.ContextMenu trên scroll_list.viewport()
        self.scroll_list.viewport().installEventFilter(self)

    def load_from(self, folder_path):
        """
        folder_path: ví dụ "<asset_or_shot>/scenefiles"
        - Xóa hết nội dung cũ, rồi load tất cả .blend.
        - Mỗi item đọc file JSON cùng tên (nếu có) để lấy version, created, user.
        - Sau khi tạo card, override phương thức delete_file để xoá luôn .json kèm theo.
        """
        self.current_folder = folder_path

        # 1) Xóa hết card cũ
        self.cards.clear()
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # 2) Nếu folder không tồn tại hoặc không phải thư mục → hiển thị trống
        if not folder_path or not os.path.isdir(folder_path):
            self.set_view_mode("list")
            self.relayout_list()
            return

        # 3) Xác định mode ("asset" hoặc "shot") và entity_name, category (nếu asset)
        mode = None
        entity_name = ""
        category = ""
        p = folder_path
        while True:
            p = os.path.dirname(p)
            if not p:
                break
            base = os.path.basename(p).lower()
            if base == "assets":  # Asset mode
                mode = "asset"
                entity_name = os.path.basename(os.path.dirname(folder_path))
                # category = thư mục cha của entity
                category = os.path.basename(os.path.dirname(os.path.dirname(folder_path)))
                break
            if base == "sequencer":  # Shot mode
                mode = "shot"
                entity_name = os.path.basename(os.path.dirname(folder_path))
                break
            if os.path.dirname(p) == p:
                break

        # 4) Đường dẫn file JSON metadata toàn entity (nằm cùng cấp với folder_path/../<entity>.json)
        if mode in ("asset", "shot"):
            json_entity = os.path.join(os.path.dirname(folder_path), f"{entity_name}.json")
        else:
            json_entity = None

        # 5) Nếu JSON metadata toàn entity tồn tại, load để lấy base_version, entity_created, entity_user
        metadata_entity = {}
        if json_entity and os.path.exists(json_entity):
            try:
                with open(json_entity, "r", encoding="utf-8") as jf:
                    metadata_entity = json.load(jf)
            except Exception:
                metadata_entity = {}

        base_version   = metadata_entity.get("version", 1)
        entity_created = metadata_entity.get("created", "")
        entity_user    = metadata_entity.get("user", "")

        # 6) Xây danh sách all_stages để dò tìm stage từ tên file
        if mode == "asset":
            all_stages = ["Modeling", "Texturing", "Rigging", "Groom"]
        elif mode == "shot":
            all_stages = ["Animation", "Blocking", "Lighting", "Vfx"]
        else:
            all_stages = []

        # 7) Duyệt từng file .blend trong folder, sorted để giữ thứ tự
        exts = {'.blend'}
        for fname in sorted(os.listdir(folder_path)):
            full = os.path.join(folder_path, fname)
            if not os.path.isfile(full):
                continue
            if os.path.splitext(fname)[1].lower() not in exts:
                continue

            # Tách stage từ filename
            name_no_ext = os.path.splitext(fname)[0]
            stage_matched = ""
            lower_name = name_no_ext.lower()
            for st in all_stages:
                if lower_name.endswith(st.lower()):
                    stage_matched = st
                    break
            if not stage_matched:
                parts = name_no_ext.split("_")
                stage_matched = parts[-1] if parts else ""

            # title = stage (viết hoa)
            title = stage_matched

            # Đọc file JSON riêng cho file .blend này (nếu có)
            json_per_file = os.path.join(folder_path, name_no_ext + ".json")
            if os.path.exists(json_per_file):
                try:
                    with open(json_per_file, "r", encoding="utf-8") as jf:
                        info = json.load(jf)
                except Exception:
                    info = {}
            else:
                info = {}

            version = info.get("version", base_version)
            created = info.get("created", entity_created)
            user    = info.get("user", entity_user)

            # text1 = "v" + version (đảm bảo 3 chữ số)
            ver_str = str(version).zfill(3)
            text1 = f"v{ver_str}"

            # text2 = created
            text2 = created

            # text3 = user
            text3 = user

            # Thumbnail: nếu có BLENDER_ICON thì dùng, ngược lại để trống
            thumb = BLENDER_ICON if os.path.exists(BLENDER_ICON) else ""

            # Tạo card
            card = CustomItemWidget(title, thumb, text1, text2, text3, parent_tab=self)
            card.file_path = full

            # Vô hiệu hóa drag trên Scene Tab
            card.setAcceptDrops(False)
            card.mouseMoveEvent = lambda e: None

            # --- GHI ĐÈ phương thức delete_file để khi xóa .blend cũng xóa luôn .json ---
            def make_delete_func(blend_path, parent_tab):
                def delete_with_json():
                    # 1) Xóa file .blend
                    try:
                        os.remove(blend_path)
                    except Exception:
                        pass

                    # 2) Xóa thêm file JSON cùng tên (đổi .blend -> .json)
                    json_path = os.path.splitext(blend_path)[0] + ".json"
                    if os.path.exists(json_path):
                        try:
                            os.remove(json_path)
                        except Exception:
                            pass

                    # 3) Reload lại list
                    parent_tab.load_from(parent_tab.current_folder)
                return delete_with_json

            # Gán lại delete_file cho mỗi card
            card.delete_file = make_delete_func(card.file_path, self)
            # --------------------------------------------------------------------

            self.cards.append(card)
            self.list_layout.addWidget(card)

        # 8) Chuyển view và relayout
        self.set_view_mode("list")
        self.relayout_list()

    def clear_selection(self):
        """
        Bỏ chọn hết tất cả các card (CustomItemWidget) hiện tại.
        """
        for c in self.cards:
            c.set_selected(False)

    def eventFilter(self, obj, evt):
        """
        Bắt QEvent.ContextMenu (right-click) trên scroll_list.viewport().
        Nếu click phải lên một CustomItemWidget (card), bỏ qua;
        nếu click phải lên vùng trống, show menu tạo stage.
        """
        if obj is self.scroll_list.viewport() and self.view_mode == "list":
            if evt.type() == QEvent.ContextMenu:
                pos = evt.pos()

                # Nếu current_folder chưa set hoặc không tồn tại → bỏ qua
                if not self.current_folder or not os.path.isdir(self.current_folder):
                    return False

                # Kiểm tra widget dưới pointer
                widget_under = self.scroll_list.viewport().childAt(pos)
                w = widget_under
                while w:
                    if isinstance(w, CustomItemWidget):
                        # Click phải trên card → bỏ qua (card có menu riêng)
                        return False
                    w = w.parent()

                # Click phải trên vùng trống → show menu
                self.show_stage_menu(pos)
                return True

        return super().eventFilter(obj, evt)

    def show_stage_menu(self, pos: QPoint):
        """
        Hiển thị context menu với danh sách stage (Asset hoặc Shot) tại vị trí `pos`.
        - Ẩn các stage đã tồn tại file .blend.
        - Khi chọn, tạo file .blend và file .json metadata (cùng tên với .blend).
        """
        # 1) Xác định mode, entity_name, category nếu asset
        folder       = self.current_folder
        mode         = None
        entity_name  = ""
        category     = ""

        p = folder
        while True:
            p = os.path.dirname(p)
            if not p:
                break
            base = os.path.basename(p).lower()
            if base == "assets":
                mode = "asset"
                entity_name = os.path.basename(os.path.dirname(folder))
                category = os.path.basename(os.path.dirname(os.path.dirname(folder)))
                break
            if base == "sequencer":
                mode = "shot"
                entity_name = os.path.basename(os.path.dirname(folder))
                break
            if os.path.dirname(p) == p:
                break

        if mode is None or not entity_name:
            return

        # 2) Lấy project_short
        project_short = ""
        if os.path.exists(LATEST_PROJECT_FILE):
            try:
                with open(LATEST_PROJECT_FILE, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                project_short = proj_data.get("short", "")
            except Exception:
                project_short = ""
        if not project_short:
            QMessageBox.warning(
                self, "Warning",
                "Không tìm thấy project_short trong latest_project.json.\n"
                "Không thể tạo file .blend mới."
            )
            return

        # 3) Xây danh sách all_stages
        if mode == "asset":
            all_stages = ["Modeling", "Texturing", "Rigging", "Groom"]
        else:
            all_stages = ["Animation", "Blocking", "Lighting", "Vfx"]

        # 4) Tìm các stage đã tồn tại (từ những file .blend hiện có)
        existing_files = []
        for fname in os.listdir(self.current_folder):
            if fname.lower().endswith(".blend"):
                name_no_ext = os.path.splitext(fname)[0]
                parts = name_no_ext.split("_")
                stage_lower = parts[-1].lower() if parts else ""
                existing_files.append(stage_lower)

        # 5) Tạo context menu chỉ chứa những stage chưa có file
        menu = QMenu(self)
        for st in all_stages:
            if st.lower() not in existing_files:
                menu.addAction(QAction(st, menu))
        if menu.isEmpty():
            return

        # 6) Hiển thị menu tại vị trí toàn cục
        global_pos = self.scroll_list.viewport().mapToGlobal(pos)
        selected_action = menu.exec_(global_pos)
        if not selected_action:
            return

        selected_stage = selected_action.text()
        stage_lower    = selected_stage.lower()

        # 7) Tạo file .blend mới
        new_filename = f"{project_short}_{entity_name}_{stage_lower}.blend"
        dest_path    = os.path.join(self.current_folder, new_filename)

        if not os.path.exists(BLENDER_TEMPLATE):
            QMessageBox.critical(
                self, "Lỗi",
                f"Không tìm thấy blender_template.blend:\n{BLENDER_TEMPLATE}"
            )
            return

        try:
            shutil.copy(BLENDER_TEMPLATE, dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo file .blend:\n{e}")
            return

        # 8) Tạo file JSON metadata cùng tên với .blend
        name_no_ext = os.path.splitext(new_filename)[0]
        json_path   = os.path.join(self.current_folder, f"{name_no_ext}.json")

        # Lấy user_name từ latest_user.json (nằm trong <project_root>/00_Pipeline/data/latest_user.json)
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

        # Lấy timestamp hiện tại
        timestamp   = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        version_str = "001"

        metadata = {
            "name":    entity_name,
            "stage":   selected_stage,
            "user":    user_name,
            "version": version_str,
            "created": timestamp
        }
        if mode == "asset":
            metadata["type"] = category

        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(metadata, jf, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Không thể tạo file JSON metadata:\n{e}")

        # 9) Reload folder để hiển thị ngay file mới
        self.load_from(self.current_folder)
        
        # 10) Bỏ chọn các card cũ, rồi chọn riêng card mới vừa tạo
        self.clear_selection()
        for card in self.cards:
            if card.file_path == dest_path:
                card.set_selected(True)
                break

def create_scene_tab():
    return SceneTab()
