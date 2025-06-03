# tab_library.py

import os
from PyQt5.QtGui import QPixmap, QImageReader, QPixmapCache
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QLabel
from tab_presets import BaseCardTab, CustomItemWidget

class LibraryTab(BaseCardTab):
    def __init__(self):
        super().__init__([])
        self.setAcceptDrops(True)
        self.current_folder = None

        # Mặc định hiển thị Thumbnail View
        self.set_view_mode("thumbnail")

        # Không gian tối đa dành cho mỗi thumbnail (width × height)
        self.thumb_size = QSize(160, 160)

    def load_from(self, folder_path):
        """
        folder_path: đường dẫn trực tiếp tới thư mục textures.
        Ví dụ, MasterUI gọi:
            self.library_tab.load_from(os.path.join(asset_path, "textures"))
        Chúng ta sẽ:
         1. Xóa toàn bộ cards cũ và widget cũ trong thumb_container + list_layout
         2. Duyệt qua từng file ảnh trong folder_path
         3. Với mỗi file, tạo thumbnail giữ tỉ lệ, canh giữa trong QPixmap 180×180
            bằng QImageReader + tính toán tỉ lệ, hoặc lấy từ QPixmapCache nếu đã có
         4. Tạo CustomItemWidget và gán thumbnail vào QLabel nằm giữa item
         5. Cuối cùng gọi self.relayout() để BaseCardTab tự sắp xếp grid Thumbnail
        """

        full_folder = folder_path
        self.current_folder = full_folder
        self.folder_path = full_folder

        # 1) Xóa cards cũ và gỡ toàn bộ widget cũ trong thumb_container lẫn list_layout
        self.cards.clear()
        # thumb_container là QWidget chứa FlowLayout cho thumbnail
        grid_layout = self.thumb_container.layout()
        while grid_layout and grid_layout.count():
            it = grid_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        # list_layout là QVBoxLayout dùng cho chế độ list view
        list_layout = self.list_layout
        while list_layout.count():
            it = list_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        # 2) Nếu folder không tồn tại hoặc không phải thư mục, để thumbnail grid trống
        if not full_folder or not os.path.isdir(full_folder):
            self.relayout()
            return

        # 3) Duyệt tất cả file ảnh trong thư mục
        exts = {'.png', '.jpg', '.jpeg', '.bmp'}
        for fname in sorted(os.listdir(full_folder)):
            full = os.path.join(full_folder, fname)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in exts:
                continue

            # 3.1) Lấy metadata để hiển thị
            title = os.path.splitext(fname)[0]
            text1 = ext.lstrip('.')  # ví dụ "png"
            # Đọc kích thước gốc của ảnh (chỉ header)
            reader_info = QImageReader(full)
            reader_info.setAutoTransform(True)
            size = reader_info.size()
            if size.isValid():
                text2 = f"{size.width()}×{size.height()}"
            else:
                text2 = ""
            size_kb = os.path.getsize(full) / 1024
            if size_kb < 1024:
                text3 = f"{size_kb:.1f} KB"
            else:
                text3 = f"{(size_kb/1024):.1f} MB"

            # 3.2) Tạo hoặc lấy thumbnail từ QPixmapCache
            cache_key = f"thumb::{full}"
            pix = QPixmapCache.find(cache_key)
            if pix is None or pix.isNull():
                # Đọc ảnh gốc, tính tỉ lệ để scale sao cho tối đa bằng thumb_size
                reader = QImageReader(full)
                reader.setAutoTransform(True)

                orig_size = reader.size()
                if orig_size.isValid() and (orig_size.width() > 0 and orig_size.height() > 0):
                    ow, oh = orig_size.width(), orig_size.height()
                    tw, th = self.thumb_size.width(), self.thumb_size.height()

                    if ow > oh:
                        # Chiều ngang gốc lớn hơn, scale theo chiều ngang
                        new_w = tw
                        new_h = int(oh * (tw / ow))
                    else:
                        # Chiều dọc gốc >= chiều ngang, scale theo chiều dọc
                        new_h = th
                        new_w = int(ow * (th / oh))

                    # Đảm bảo không vượt quá thumb_size
                    new_w = min(new_w, tw)
                    new_h = min(new_h, th)
                    reader.setScaledSize(QSize(new_w, new_h))
                else:
                    # Nếu không đọc được size gốc hoặc kích thước không hợp lệ, scale mặc định
                    reader.setScaledSize(self.thumb_size)

                image = reader.read()
                if not image.isNull():
                    pix = QPixmap.fromImage(image)
                else:
                    pix = QPixmap()

                # Lưu vào cache (nếu pix không rỗng)
                if not pix.isNull():
                    QPixmapCache.insert(cache_key, pix)

            # 3.3) Tạo CustomItemWidget (thumbnail mode) nhưng ban đầu để image_path = ""
            card = CustomItemWidget(title, "", text1, text2, text3, parent_tab=self)
            card.file_path = full

            # 3.4) Thay thế QLabel 'img' trong stacked widget index 0
            #     Đảm bảo label canh giữa và chỉ hiển thị pix (với KeepAspectRatio)
            thumb_widget = card.stack.widget(0)
            img_labels = thumb_widget.findChildren(QLabel)
            if img_labels:
                img_label = img_labels[0]
                img_label.setFixedSize(self.thumb_size)   # giữ nguyên vùng 180×180
                img_label.setAlignment(Qt.AlignCenter)    # canh giữa
                if not pix.isNull():
                    img_label.setPixmap(pix)
                else:
                    img_label.clear()

            # Thêm vào danh sách self.cards
            self.cards.append(card)

        # 4) Cuối cùng gọi relayout() để BaseCardTab tự sắp thumbnail grid
        self.relayout()


def create_library_tab():
    return LibraryTab()
