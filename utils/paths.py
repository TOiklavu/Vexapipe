# utils/paths.py
import os

def get_projects_data_path():
    """
    Trả về đường dẫn đến file projects.json (danh sách các dự án).
    """
    projects_dir = os.path.join(os.path.dirname(__file__), "..", "projects")
    os.makedirs(projects_dir, exist_ok=True)  # Tạo thư mục projects nếu chưa có
    return os.path.join(projects_dir, "projects.json")

def get_project_data_path(project_path):
    """
    Trả về đường dẫn đến file data.json của một dự án cụ thể.
    """
    return os.path.join(project_path, "data.json")