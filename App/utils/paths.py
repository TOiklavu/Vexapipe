# utils/paths.py
import os

def get_projects_data_path():
    project_data_dir = "D:/OneDrive/Desktop/Projects/Vexapipe/App/Resources/ProjectData"
    return os.path.join(project_data_dir, "projects.json")

def get_project_data_path(project_path):
    project_name = os.path.basename(project_path)
    project_data_dir = "D:/OneDrive/Desktop/Projects/Vexapipe/App/Resources/ProjectData"
    return os.path.join(project_data_dir, project_name, "data.json")