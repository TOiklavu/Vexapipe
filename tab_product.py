import os
from PyQt5.QtGui import QPixmap
from tab_presets import BaseCardTab, CustomItemWidget

BASE_DIR    = os.path.dirname(__file__)
LOGO_FOLDER = os.path.join(BASE_DIR, "template", "logo")

LOGO_MAP = {
    "abc":  os.path.join(LOGO_FOLDER, "logo_abc.png"),
    "fbx":  os.path.join(LOGO_FOLDER, "logo_fbx.png"),
    "usd":  os.path.join(LOGO_FOLDER, "logo_usd.png"),
    "usda": os.path.join(LOGO_FOLDER, "logo_usd.png"),
    "usdc": os.path.join(LOGO_FOLDER, "logo_usd.png"),
}


class ProductTab(BaseCardTab):
    def __init__(self):
        # Khởi tạo với data_list rỗng; sau đó load động qua load_from()
        super().__init__([])
        self.setAcceptDrops(True)
        self.current_folder = None
        # Mặc định hiển thị Thumbnail View
        self.set_view_mode("thumbnail")

    def load_from(self, folder_path):
        """
        folder_path: ví dụ "<asset_path>"
        Thực chất, nội dung lấy từ "<asset_path>/outputs"
        Sau khi thu thập hết data, thêm vào self.cards rồi gọi self.relayout()
        để BaseCardTab tự sắp xếp thumbnail grid.
        """
        # 1) Xác định đúng thư mục con "outputs"
        self.current_folder = folder_path
        self.folder_path = folder_path

        # 2) Xoá sạch cards cũ và xóa layout thumb + list
        self.cards.clear()

        # Xóa các widget cũ trong thumb_container
        while self.thumb_container.layout().count():
            item = self.thumb_container.layout().takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # Xóa các widget cũ trong list_layout (nếu có)
        while self.list_layout.count():
            it = self.list_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        # 3) Nếu folder không tồn tại, để tab trống (self.cards rỗng và tương ứng relayout)
        if not folder_path or not os.path.isdir(folder_path):
            # Gọi relayout() để chắc chắn hiển thị rỗng
            self.relayout()
            return

        # 4) Duyệt file trong outputs, lọc các extension có trong LOGO_MAP
        for fname in sorted(os.listdir(folder_path)):
            full = os.path.join(folder_path, fname)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(fname)[1].lower().lstrip('.')
            if ext not in LOGO_MAP:
                continue

            # Thiết lập thông tin để hiển thị trên card
            title = os.path.splitext(fname)[0]
            text1 = ext
            text2 = ""
            size_kb = os.path.getsize(full) / 1024
            if size_kb < 1024:
                text3 = f"{size_kb:.1f} KB"
            else:
                text3 = f"{(size_kb/1024):.1f} MB"
            thumb = LOGO_MAP.get(ext, "")

            # Tạo card và thêm vào self.cards
            card = CustomItemWidget(title, thumb, text1, text2, text3, parent_tab=self)
            card.file_path = full
            self.cards.append(card)

        # 5) Cuối cùng gọi relayout() để BaseCardTab tự sắp các card vào thumbnail grid
        self.relayout()


def create_product_tab():
    return ProductTab()
