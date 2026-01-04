import os
import uuid
import asyncio
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.models.exam_paper_model import ExamPaper
from app.core.config import settings

# Setup Jinja2 environment
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

class PDFService:
    @staticmethod
    def generate_exam_paper_pdf(exam_paper: ExamPaper) -> str:
        """
        Generates a PDF for the given exam paper and returns the path to the temporary file.
        """
        template = env.get_template("exam_paper_template.html")
        
        # Prepare context
        # Ensure we pass all necessary data. Relationships should be eager loaded by the caller.
        html_content = template.render(exam=exam_paper)
        
        # Create temporary file path
        # Using /tmp or a specific temp dir. 
        temp_dir = "/tmp/exam_papers"
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"exam_paper_{exam_paper.id}_{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(temp_dir, filename)
        
        # specific write_pdf options can be added here (e.g., zoom, stylesheets)
        HTML(string=html_content).write_pdf(file_path)
        
        return file_path

    @staticmethod
    async def remove_file_after_delay(path: str, delay: int = 1800):
        """
        Waits for a specified delay (in seconds) and then removes the file.
        Default delay is 30 minutes (1800 seconds).
        """
        try:
            await asyncio.sleep(delay)
            if os.path.exists(path):
                os.remove(path)
                print(f"INFO: Removed temporary PDF file: {path}")
        except Exception as e:
            print(f"ERROR: Failed to remove temporary PDF file {path}: {e}")
