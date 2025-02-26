import subprocess

def compile_latex_with_xelatex(latex_file):
    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory=.",
        latex_file
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ PDF đã tạo thành công!")
    else:
        print("❌ Lỗi khi biên dịch LaTeX. Kiểm tra lỗi bên dưới:")
        print(result.stderr)

compile_latex_with_xelatex("sample.tex")
