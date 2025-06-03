import os
import time
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QGridLayout, QScrollArea, QMenu, QAction, QActionGroup,
    QApplication, QShortcut, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont, QFontMetrics, QKeySequence, QDrag
from PyQt5.QtCore import Qt, QEvent, QPoint, QMimeData, QUrl
from flowlayout import FlowLayout

BASE_DIR = os.path.dirname(__file__)
PRODUCTS_FOLDER = os.path.join(BASE_DIR, "Products")

class CustomItemWidget(QWidget):
    def __init__(self,
                 title: str,
                 image_path: str,
                 text1: str = "",
                 text2: str = "",
                 text3: str = "",
                 parent_tab=None):
        super().__init__()

        self.title = title
        self.text1 = text1
        self.text2 = text2
        self.text3 = text3
        self.extra_lines = [t for t in (text1, text2, text3) if t]
        self.parent_tab = parent_tab
        self._hovered = False
        self._selected = False
        self.file_path = image_path

        self.stack = QStackedWidget(self)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        thumb = QWidget()
        thumb.setObjectName("card")
        t_layout = QVBoxLayout(thumb)
        t_layout.setContentsMargins(6, 6, 6, 6)
        t_layout.setSpacing(4)

        pix = QPixmap(image_path)
        img = QLabel()
        img.setFixedSize(160, 160)
        img.setAlignment(Qt.AlignCenter)
        if not pix.isNull():
            img.setPixmap(pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        t_layout.addWidget(img)

        self.title_lbl = QLabel(title)
        self.title_lbl.setFont(QFont("Roboto", 14, QFont.Bold))
        self.title_lbl.setMinimumWidth(100)
        self.title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.title_lbl.setToolTip(title)
        fm = QFontMetrics(self.title_lbl.font())
        self.title_lbl.setText(fm.elidedText(title, Qt.ElideRight, self.title_lbl.width()))
        t_layout.addWidget(self.title_lbl)

        text_layout = QHBoxLayout()
        text_layout.setSpacing(8)
        self.sub_labels = []
        for txt in self.extra_lines:
            label = QLabel(txt)
            label.setFont(QFont("Roboto", 10))
            label.setWordWrap(True)
            text_layout.addWidget(label)
            self.sub_labels.append(label)

        t_layout.addLayout(text_layout)
        self.stack.addWidget(thumb)

        lst = QWidget()
        lst.setObjectName("card")
        lst.setFixedHeight(80)
        lst.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        l_layout = QHBoxLayout(lst)
        l_layout.setContentsMargins(6, 6, 6, 6)
        l_layout.setSpacing(10)

        icon = QLabel()
        icon.setFixedSize(64, 64)
        icon.setAlignment(Qt.AlignCenter)
        if not pix.isNull():
            icon.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        l_layout.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Roboto", 12, QFont.Bold))
        self.title_label.setToolTip(self.title)
        fm2 = QFontMetrics(self.title_label.font())
        self.title_label.setText(fm2.elidedText(self.title, Qt.ElideRight, 400))
        info.addWidget(self.title_label)

        text_row = QHBoxLayout()
        text_row.setSpacing(8)
        self.sub2_labels = []
        for line in self.extra_lines:
            label = QLabel(str(line))
            label.setFont(QFont("Roboto", 9))
            label.setWordWrap(True)
            text_row.addWidget(label)
            self.sub2_labels.append(label)

        info.addLayout(text_row)
        l_layout.addLayout(info)
        self.stack.addWidget(lst)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)

        self.switch_view("thumbnail")
        self.setAttribute(Qt.WA_Hover)
        self.installEventFilter(self)

    def switch_view(self, mode: str):
        idx = 0 if mode == "thumbnail" else 1
        self.stack.setCurrentIndex(idx)

        if mode == "thumbnail":
            self.setFixedSize(180, 220)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            self.setFixedHeight(80)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.setMaximumWidth(16777215)  # max width tự động giãn
            self.setMinimumWidth(0)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.view_mode = mode
        self.update_style()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Enter, QEvent.Leave):
            self._hovered = (ev.type()==QEvent.Enter)
            self.update_style()
        return super().eventFilter(obj, ev)

    def set_selected(self, sel: bool):
        self._selected = sel
        self.update_style()

    def update_style(self):
        bg, bd = "transparent", "1px solid #1d3557"
        color = "#1D1D1D"  # Màu chữ mặc định

        if self._selected:
            bg, bd = "#1d3557", "2px solid #1d3557"
            color = "#ffffff"
        elif self._hovered:
            bg, bd = "#e63946", "0px solid #457b9d"
            color = "#000000"

        style = f"""
            #card {{
                background-color: {bg};
                border: {bd};
                border-radius: 10px;
            }}
        """
        self.stack.widget(0).setStyleSheet(style)
        self.stack.widget(1).setStyleSheet(style)
        self.title_label.setStyleSheet(f"color: {color};")
        self.title_lbl.setStyleSheet(f"color: {color};")
        for lbl in self.sub_labels:
            lbl.setStyleSheet(f"color: {color};")
        for lbl in self.sub2_labels:
            lbl.setStyleSheet(f"color: {color};")


    def contextMenuEvent(self, event):
        if self.parent_tab:
            self.parent_tab.clear_selection()
        self.set_selected(True)
        menu = QMenu(self)
        menu.addAction("Open in Explorer", self.open_in_explorer)
        menu.addAction("Copy File Path", self.copy_file_path)
        menu.addAction("Delete", self.delete_file)
        menu.exec_(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.file_path:
            global_pos = self.mapToGlobal(event.pos())
            widget_rect = self.mapToGlobal(self.rect().topLeft()), self.mapToGlobal(self.rect().bottomRight())

            # Nếu con trỏ vẫn nằm trong widget → KHÔNG khởi động drag
            x_in = widget_rect[0].x() <= global_pos.x() <= widget_rect[1].x()
            y_in = widget_rect[0].y() <= global_pos.y() <= widget_rect[1].y()
            if x_in and y_in:
                return

            # Con trỏ đã rời khỏi vùng widget → bắt đầu kéo thả
            mime_data = QMimeData()
            url = QUrl.fromLocalFile(self.file_path)
            mime_data.setUrls([url])

            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)

    def open_in_explorer(self):
        if os.path.exists(self.file_path):
            os.startfile(os.path.dirname(self.file_path))

    def copy_file_path(self):
        QApplication.clipboard().setText(self.file_path)

    def delete_file(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        self.setParent(None)
        self.deleteLater()
        if self.parent_tab:
            self.parent_tab.cards.remove(self)
            if self.parent_tab.view_mode == "list":
                self.parent_tab.relayout_list()
            else:
                self.parent_tab.relayout()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_tab:
            self.parent_tab.clear_selection()
            self.set_selected(True)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and os.path.exists(self.file_path):
            os.startfile(self.file_path)


class BaseCardTab(QWidget):
    def __init__(self, data_list):
        super().__init__()
        self.scroll_list = QScrollArea() 
        self.cards = []
        self.view_mode = "thumbnail"

        self.setFocusPolicy(Qt.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setAcceptDrops(True)
        self.folder_path = PRODUCTS_FOLDER

        # stacked widget
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.stack, 1)

        # --- Thumbnail Page ---
        thumb_page = QWidget()
        t_layout = QVBoxLayout(thumb_page)
        t_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_thumb = QScrollArea()
        self.scroll_thumb.setWidgetResizable(True)
        self.scroll_thumb.viewport().setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll_thumb.viewport().customContextMenuRequested.connect(self.show_background_menu)
        self.scroll_thumb.viewport().installEventFilter(self)
        t_layout.addWidget(self.scroll_thumb)

        self.thumb_container = QWidget()
        self.grid = FlowLayout(self.thumb_container, margin=0, spacing=20)
        self.grid.setAlignment(Qt.AlignTop)
        self.grid.setSpacing(20)
        self.scroll_thumb.setWidget(self.thumb_container)

        self.stack.addWidget(thumb_page)

        # --- List Page ---
        list_page = QWidget()
        l_layout = QVBoxLayout(list_page)
        l_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_list = QScrollArea()
        self.scroll_list.setWidgetResizable(True)
        self.scroll_list.viewport().installEventFilter(self)
        l_layout.addWidget(self.scroll_list)

        self.list_container = QWidget()
        self.list_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.scroll_list.setWidget(self.list_container)

        self.stack.addWidget(list_page)

        # tạo card
        for title, img, t1, t2, t3 in data_list:
            card = CustomItemWidget(title, img, t1, t2, t3, parent_tab=self)
            self.cards.append(card)

        self.relayout()

        # Phím tắt
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.toggle_view_mode)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._short_open)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self._short_copy)
        QShortcut(QKeySequence("Ctrl+X"), self, activated=self._short_delete)

    def extract_metadata(self, filepath):
        """
        Mặc định chỉ trả về tên file làm title. Các tab con có thể override.
        """
        title = os.path.splitext(os.path.basename(filepath))[0]
        return title, "", "", ""


    def show_background_menu(self, pos: QPoint):
        global_pos = self.scroll_thumb.viewport().mapToGlobal(pos)
        menu = QMenu(self)
        grp = QActionGroup(menu)
        grp.setExclusive(True)

        a_thumb = QAction("Thumbnail View", grp)
        a_thumb.setCheckable(True)
        a_thumb.setChecked(self.view_mode == "thumbnail")
        a_thumb.triggered.connect(lambda: self.set_view_mode("thumbnail"))

        a_list = QAction("List View", grp)
        a_list.setCheckable(True)
        a_list.setChecked(self.view_mode == "list")
        a_list.triggered.connect(lambda: self.set_view_mode("list"))

        menu.addActions([a_thumb, a_list])
        menu.exec_(global_pos)

    def toggle_view_mode(self):
        self.set_view_mode("list" if self.view_mode == "thumbnail" else "thumbnail")

    def set_view_mode(self, mode: str):
        self.view_mode = mode
        self.stack.setCurrentIndex(0 if mode == "thumbnail" else 1)
        if mode == "thumbnail":
            self.relayout()
        else:
            self.relayout_list()

    def relayout(self):
        for card in self.cards:
            card.switch_view("thumbnail")
            if self.grid.indexOf(card) == -1:
                self.grid.addWidget(card)
        self.grid.invalidate()

    def relayout_list(self):
        while self.list_layout.count():
            it = self.list_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)

        for card in self.cards:
            card.switch_view("list")
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def clear_selection(self):
        for c in self.cards:
            c.set_selected(False)

    def eventFilter(self, obj, event):
        # 1) Thumbnail View: nếu click ra ngoài thumbnail, bỏ chọn
        if obj is self.scroll_thumb.viewport() and self.view_mode == "thumbnail":
            if event.type() == QEvent.Resize:
                self.relayout()
                return False
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                w = self.scroll_thumb.viewport().childAt(event.pos())
                # Nếu không click trúng một CustomItemWidget, bỏ chọn tất cả
                if not w or not isinstance(w.parent(), CustomItemWidget):
                    self.clear_selection()
                    return True

        # 2) List View: nếu click ra ngoài list, bỏ chọn
        if obj is self.scroll_list.viewport() and self.view_mode == "list":
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                w = self.scroll_list.viewport().childAt(event.pos())
                # Nếu click không trúng một CustomItemWidget, bỏ chọn tất cả
                if not w or not isinstance(w.parent(), CustomItemWidget):
                    self.clear_selection()
                    return True

        return super().eventFilter(obj, event)

    def get_selected_widget(self):
        return next((c for c in self.cards if c._selected), None)

    def _short_open(self):
        w = self.get_selected_widget()
        if w: w.open_in_explorer()

    def _short_copy(self):
        w = self.get_selected_widget()
        if w: w.copy_file_path()

    def _short_delete(self):
        w = self.get_selected_widget()
        if w: w.delete_file()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.source() is not None:
            cursor_pos = self.mapToGlobal(event.pos())
            if self.window().geometry().contains(cursor_pos):
                return

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                source_path = url.toLocalFile()
                if not os.path.isfile(source_path):
                    continue

                ext = os.path.splitext(source_path)[1].lower()
                if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                    continue

                base_name = os.path.basename(source_path)
                name, ext = os.path.splitext(base_name)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                new_filename = f"{name}_{timestamp}{ext}"
                new_path = os.path.join(self.folder_path, new_filename)

                with open(source_path, 'rb') as src_file:
                    data = src_file.read()
                with open(new_path, 'wb') as dst_file:
                    dst_file.write(data)

                for card in self.cards:
                    card.set_selected(False)

                title, text1, text2, text3 = self.extract_metadata(new_path)
                new_card = CustomItemWidget(title, new_path, text1, text2, text3, parent_tab=self)
                new_card.set_selected(True)
                self.cards.append(new_card)

                if self.view_mode == "list":
                    new_card.switch_view("list")
                    self.list_layout.insertWidget(self.list_layout.count() - 1, new_card)
                else:
                    new_card.switch_view("thumbnail")
                    self.grid.addWidget(new_card)
                    self.relayout()

            event.acceptProposedAction()

    def import_dropped_file(self, source_path):
        # Tạo thư mục nếu chưa có
        if not os.path.exists(PRODUCTS_FOLDER):
            os.makedirs(PRODUCTS_FOLDER)

        filename = os.path.basename(source_path)
        target_path = os.path.join(PRODUCTS_FOLDER, filename)

        # Tránh ghi đè
        base, ext = os.path.splitext(filename)
        count = 1
        while os.path.exists(target_path):
            target_path = os.path.join(PRODUCTS_FOLDER, f"{base}_{count}{ext}")
            count += 1

        # Copy file
        import shutil
        shutil.copy2(source_path, target_path)

        # Tạo và hiển thị card mới
        title, text1, text2, text3 = self.extract_metadata(target_path)
        card = CustomItemWidget(title, target_path, text1, text2, text3, parent_tab=self)

        self.cards.append(card)

        if self.view_mode == "list":
            card.switch_view("list")
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
        else:
            card.switch_view("thumbnail")
            self.grid.addWidget(card)  # ✅ CẦN CÓ để hiển thị
            self.relayout()

        card.set_selected(True)

