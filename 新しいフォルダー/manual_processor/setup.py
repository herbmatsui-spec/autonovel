from setuptools import setup, find_packages

setup(
    name="manual_processor",
    version="1.0.0",
    description="Handwritten Manual Processor for Windows with Google Cloud AI",
    author="Developer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "google-generativeai>=0.8.0",
        "google-cloud-vision>=3.7.0",
        "PyMuPDF>=1.24.0",
        "python-docx==1.1.0",
        "fpdf2>=2.7.0",
        "python-dotenv>=1.0.0",
        "pillow>=10.0.0"
    ],
    entry_points={
        'console_scripts': [
            'manual-processor=manual_processor.main:main'
        ]
    },
    python_requires=">=3.8"
)