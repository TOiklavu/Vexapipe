import os

# Định nghĩa các đường dẫn cơ bản
BASE_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/App"
RESOURCES_DIR = os.path.join(BASE_DIR, "Resources")
PROJECTS_DIR = "D:/OneDrive/Desktop/Projects/Vexapipe/Projects"
PROJECT_DATA_DIR = os.path.join(RESOURCES_DIR, "ProjectData")

def get_projects_data_path():
    """
    Trả về đường dẫn đến file projects.json trong thư mục ProjectData.
    """
    return os.path.join(PROJECT_DATA_DIR, "projects.json")

def get_project_data_path(project_path):
    """
    Trả về đường dẫn đến file data.json của một dự án cụ thể.
    """
    project_name = os.path.basename(project_path)
    return os.path.join(PROJECT_DATA_DIR, project_name, "data.json")

def resource_path(relative_path):
    """
    Trả về đường dẫn tuyệt đối đến tài nguyên.
    
    Nếu relative_path bắt đầu bằng 'Projects', trả về đường dẫn từ PROJECTS_DIR.
    Ngược lại, trả về đường dẫn từ BASE_DIR (thư mục gốc của ứng dụng).
    
    Args:
        relative_path (str): Đường dẫn tương đối (ví dụ: "Projects", "last_project.json", "icons/default_project_icon.png").
    
    Returns:
        str: Đường dẫn tuyệt đối đến tài nguyên.
    """
    if relative_path.startswith("Projects"):
        # Nếu đường dẫn liên quan đến thư mục Projects
        sub_path = relative_path[len("Projects") + 1:] if len(relative_path) > len("Projects") else ""
        return os.path.join(PROJECTS_DIR, sub_path)
    else:
        # Các đường dẫn khác (như last_project.json, icons,...) nằm trong BASE_DIR
        return os.path.join(BASE_DIR, relative_path)