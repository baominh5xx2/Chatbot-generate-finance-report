import subprocess
import os
import shutil

def compile_latex_to_pdf(latex_file, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(latex_file)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get filename without path and extension
    base_filename = os.path.basename(latex_file)
    filename_no_ext = os.path.splitext(base_filename)[0]
    
    # Working directory and command
    working_dir = os.path.dirname(latex_file)
    
    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        latex_file
    ]

    try:
        # Run xelatex twice for proper cross-references and TOC
        for _ in range(2):
            result = subprocess.run(command, 
                                   capture_output=True, 
                                   text=True,
                                   cwd=working_dir)
            
            # Check if compilation was successful
            if result.returncode != 0:
                return False, f"Lỗi biên dịch LaTeX:\n{result.stderr[:500]}..."
        
        # PDF file path
        pdf_path = os.path.join(output_dir, f"{filename_no_ext}.pdf")
        
        # Check if PDF was created
        if os.path.exists(pdf_path):
            print(f"✅ PDF đã tạo thành công tại: {pdf_path}")
            return True, pdf_path
        else:
            return False, "PDF không được tạo ra mặc dù không có lỗi biên dịch"
            
    except Exception as e:
        return False, f"Lỗi khi biên dịch: {str(e)}"

def clean_latex_auxiliary_files(output_dir, filename_no_ext):
    """Remove auxiliary files created during LaTeX compilation"""
    extensions = ['.aux', '.log', '.out', '.toc', '.lof', '.lot', '.bbl', '.blg']
    for ext in extensions:
        aux_file = os.path.join(output_dir, f"{filename_no_ext}{ext}")
        if os.path.exists(aux_file):
            try:
                os.remove(aux_file)
            except:
                pass  # Ignore errors in cleanup
