![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)
![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)

# Data flow from ENCODE - dfENCODE

Project created to interrogate CHIP-seq data (bigWig) deposited in the [ENCODE](https://www.encodeproject.org/).

### To start 
        git clone https://github.com/ClinicalEpigeneticsLaboratory/dfENCODE.git
        pip install poetry
        poetry install

### To run
Firstly, user has to define experiments of interest for example: **ENCSR073ORI**, **ENCSR829ZLX**, **ENCSR641ZFV**.   
Then to integrate these datasets:

        poetry run python -i flow.py
        start_integration(exmperiments_to_integrate=["ENCSR073ORI", "ENCSR829ZLX", "ENCSR641ZFV"], output="example")

This code will create `example/` directory and will download selected files to `example/data` sub-directory.
Please note that user may also specify `signal_type (default="signal p-value")` as well as `genome_assembly (default="GRCh38")`.

To create heatmaps and bigWig summary file for specified BED file(s) and downloaded experiment(s):

        start_analysis(encode_data_directory="example", output="results/", bed_files=["BED1.bed", "BED2.bed"], window=5000, workers=10)

This code will create `results/` directory with elements generated using [deepTools](https://deeptools.readthedocs.io/en/develop/) based on specified `BED files` and `bigWig files` integrated in previous step.
**INFO** add `plot_heatmap="group"` argument to create grouped heatmap.
