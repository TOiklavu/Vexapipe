import sys, os, json
from PyQt5.QtWidgets import QApplication, QDialog
from login import LoginDialog
from project import ProjectSelectionDialog
from master_ui import MasterUI

BASE_DIR = os.path.dirname(__file__)
LATEST_USER_FILE = os.path.join(BASE_DIR, "data", "latest_user.json")
LATEST_PROJECT_FILE = os.path.join(BASE_DIR, "data", "latest_project.json")

def main():
    app = QApplication(sys.argv)
    # Đọc latest_user.json
    user = None
    if os.path.exists(LATEST_USER_FILE):
        try:
            with open(LATEST_USER_FILE, "r", encoding="utf-8") as f:
                data_u = json.load(f)
            user = data_u.get("last_user")
        except Exception:
            user = None

    # Đọc latest_project.json
    project = None
    if os.path.exists(LATEST_PROJECT_FILE):
        try:
            with open(LATEST_PROJECT_FILE, "r", encoding="utf-8") as f:
                data_p = json.load(f)
            if isinstance(data_p, dict) and all(k in data_p for k in ("name","path")):
                project = data_p
        except Exception:
            project = None

    if not user or not project:
        # a) Login
        dlg_login = LoginDialog()
        if dlg_login.exec_() != QDialog.Accepted:
            sys.exit(0)
        user = dlg_login.user_edit.text().strip()

        # b) Chọn project
        dlg_proj = ProjectSelectionDialog()
        if dlg_proj.exec_() != QDialog.Accepted:
            sys.exit(0)
        project = dlg_proj.get_selected()

        # Ghi lại latest_project.json (dùng biến toàn cục)
        os.makedirs(os.path.dirname(LATEST_PROJECT_FILE), exist_ok=True)
        with open(LATEST_PROJECT_FILE, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)

    # 2) Mở giao diện chính
    window = MasterUI(user, project)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
