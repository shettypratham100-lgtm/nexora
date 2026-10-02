"""
converter.py

This module is responsible for converting Office documents
(DOC, DOCX, PPT, PPTX, etc.) into PDF using LibreOffice.

The generated PDF is later displayed using PDF.js.
"""

import subprocess
from pathlib import Path

from django.conf import settings

def convert_to_pdf(input_file_path, output_directory):
    """
    Convert an Office document (DOC, DOCX, PPT, PPTX, etc.)
    into a PDF using LibreOffice.

    Parameters
    ----------
    input_file_path : str or Path
        Full path of the uploaded Office document.

    output_directory : str or Path
        Folder where the converted PDF will be saved.

    Returns
    -------
    Path
        Path to the generated PDF.
    """

    # -------------------------------------------------------------
    # Convert the input file path into a Path object.
    #
    # Example:
    # "media/resources/java.docx"
    #
    # becomes:
    #
    # Path("media/resources/java.docx")
    #
    # Path objects make file operations much easier than strings.
    # -------------------------------------------------------------
    input_file_path = Path(input_file_path)


    # -------------------------------------------------------------
    # Convert the output directory into a Path object.
    #
    # Example:
    # "media/temp"
    #
    # becomes:
    #
    # Path("media/temp")
    # -------------------------------------------------------------
    output_directory = Path(output_directory)


    # -------------------------------------------------------------
    # Create the output folder if it doesn't already exist.
    #
    # parents=True
    #     Creates parent folders if necessary.
    #
    # exist_ok=True
    #     Prevents an error if the folder already exists.
    #
    # Example:
    #
    # media/
    #     temp/
    #
    # If "temp" is missing, Python creates it automatically.
    # -------------------------------------------------------------
    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )


    # -------------------------------------------------------------
    # Decide the name of the generated PDF.
    #
    # input_file_path.stem returns the filename
    # WITHOUT its extension.
    #
    # Example:
    #
    # Java Notes.docx
    #
    # becomes:
    #
    # Java Notes
    #
    # Then we add ".pdf".
    #
    # Final result:
    #
    # media/temp/Java Notes.pdf
    # -------------------------------------------------------------
    output_pdf = (
        output_directory /
        f"{input_file_path.stem}.pdf"
    )


    # -------------------------------------------------------------
    # Build the LibreOffice command.
    #
    # This is exactly the command you would type
    # manually into Command Prompt.
    #
    # Example:
    #
    # "C:\Program Files\LibreOffice\program\soffice.exe"
    #     --headless
    #     --convert-to pdf
    #     --outdir media/temp
    #     media/resources/Java Notes.docx
    #
    # Python stores each argument separately inside a list.
    # subprocess.run() will execute this command.
    # -------------------------------------------------------------
    command = [

        # Path of LibreOffice executable
        settings.LIBREOFFICE_PATH,

        # Run without opening the LibreOffice window
        "--headless",

        # Convert the document into PDF
        "--convert-to",
        "pdf",

        # Folder where the generated PDF will be saved
        "--outdir",
        str(output_directory),

        # Path of the Office document to convert
        str(input_file_path),

    ]


    # -------------------------------------------------------------
    # Execute the LibreOffice command.
    #
    # subprocess.run() starts another program
    # (LibreOffice) from Python.
    #
    # capture_output=True
    #     Stores LibreOffice's output for debugging.
    #
    # text=True
    #     Returns output as normal strings
    #     instead of raw bytes.
    #
    # check=True
    #     Raises an exception automatically if
    #     LibreOffice fails to convert the document.
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # Execute the LibreOffice command.
    #
    # If conversion fails, subprocess.run() will raise
    # CalledProcessError because we set check=True.
    # -------------------------------------------------------------
    try:

        subprocess.run(

            command,

            capture_output=True,

            text=True,

            check=True

        )

    except subprocess.CalledProcessError as error:

        # ---------------------------------------------------------
        # LibreOffice returned an error.
        #
        # stderr contains the actual error message produced by
        # LibreOffice.
        #
        # We raise a new exception with a cleaner message so
        # Django can display or log it.
        # ---------------------------------------------------------
        raise Exception(
            f"LibreOffice conversion failed:\n{error.stderr}"
        )

    # -------------------------------------------------------------
    # Verify that LibreOffice actually generated the PDF.
    #
    # Even if LibreOffice exits successfully, we double-check
    # that the output file exists.
    # -------------------------------------------------------------
    if not output_pdf.exists():

        raise FileNotFoundError(

            f"Generated PDF not found:\n{output_pdf}"

        )
    # -------------------------------------------------------------
    # Conversion completed successfully.
    #
    # Return the path of the generated PDF so other parts
    # of the application can use it.
    # -------------------------------------------------------------
    return output_pdf

    