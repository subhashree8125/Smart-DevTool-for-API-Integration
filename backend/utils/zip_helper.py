import zipfile
import os

def create_project_zip(source_dir: str, output_zip_path: str) -> None:
    """
    Creates a ZIP archive containing all files from the source_dir.
    The paths within the ZIP will be relative to source_dir.
    """
    # Ensure target parent directory exists
    parent_dir = os.path.dirname(output_zip_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
        
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Write file with path relative to the root generator folder
                archive_name = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, archive_name)
