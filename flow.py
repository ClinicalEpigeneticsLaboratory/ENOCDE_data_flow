from urllib.request import urlretrieve
from subprocess import call
from os.path import join, exists
from os import makedirs
import requests

import pandas as pd
from glob import glob
from prefect import task, flow
from pathlib import Path

from typing import Union
from src.utils import show_progress
from src.exceptions import WrongGenomeAssembly, WrongSignalType, DataNotFound


@task
def extract_files_from_experiments(
    experiments: Union[list, tuple], signal_type: str, genome_assembly: str
) -> pd.DataFrame:
    extracted_data = []

    for experiment in experiments:
        print(f"Parsing data from {experiment}.")
        endpoint = f"https://www.encodeproject.org/experiment/{experiment}/?format=json"
        response = requests.get(endpoint).json()
        
        summary = response["biosample_summary"]
        target = response["target"]["name"]
        
        assay_type = response["assay_term_name"]
        cell_classification = response["biosample_ontology"]["classification"]
        term_name = response["biosample_ontology"]["term_name"]

        files = [
            file
            for file in response["files"]
            if (file["file_format"] == "bigWig")
            and (file["status"] == "released")
            and (file["assembly"] == genome_assembly)
            and (file["output_type"] == signal_type)
            and (file["no_file_available"] is False)
        ]

        for file in files:
            record = {
                "Experiment": experiment,
                "Summary": summary,
                "Target": target,
                "Assay": assay_type,
                "Cell classification": cell_classification,
                "Term_name": term_name,
                "File": file["accession"],
                "Donor": file["donors"],
                "Signal": file["output_type"],
                "Link": file["href"],
            }

            extracted_data.append(record)

    return pd.DataFrame(extracted_data)


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def download_bigwig(file: str, link: str, output: str) -> None:
    print(f"Downloadig file: {file} to {output} directory.")

    endpoint = "https://www.encodeproject.org" + link
    output = join(output, f"{file}.bigWig")
    
    if exists(output):
        print(f"File {file} already in {output} directory, skipping.")
    else:
        urlretrieve(endpoint, output, show_progress)
        print("File downloaded successfully.")


@flow(log_prints=True)
def start_integration(
    exmperiments_to_integrate: Union[list, tuple],
    output: str,
    signal_type: str = "signal p-value",
    genome_assembly: str = "GRCh38",
) -> None:
    if signal_type not in ["signal p-value", "fold change over control"]:
        raise WrongSignalType

    if genome_assembly not in ["GRCh38", "hg19"]:
        raise WrongGenomeAssembly

    if not exists(output):
        makedirs(join(output, "data"), exist_ok=True)
        print("Created output directory.")

    sample_sheet = extract_files_from_experiments(
        exmperiments_to_integrate, signal_type, genome_assembly
    )
    sample_sheet.to_csv(join(output, "sample_sheet.csv"), index=False)

    print(f"Sample sheet saved in {output} directory.")
    print(f"Extracted {sample_sheet.shape[0]} files.")

    for file_id, file_link in zip(sample_sheet["File"], sample_sheet["Link"]):
        download_bigwig(file_id, file_link, join(output, "data"))

@task(log_prints=True)
def build_summary_matrix(bigwig_files: Union[list, tuple], bed_files: Union[list, tuple], output: str, workers: int) -> None:
    output_matrix = join(output, "summary.npz")
    output_summary = join(output, "summary.tsv")
    
    bigwig_files = " ".join(bigwig_files)
    bed_files = " ".join(bed_files)
        
    command = f"multiBigwigSummary BED-file -p {workers} -b {bigwig_files} --BED {bed_files} -o {output_matrix} --smartLabels --outRawCounts {output_summary}"
    
    print(f"Running: {command}")
    call(command, shell=True)

@task(log_prints=True)
def compute_matrix(sample_sheet: pd.DataFrame, bigwig_files: Union[list, tuple], bed_files: Union[list, tuple], window: int, output: str, workers: int) -> None:
    files_ids = [Path(file).name.split(".")[0] for file in bigwig_files]
    labels = sample_sheet[sample_sheet.File.isin(files_ids)]["Target"].tolist()
    labels = " ".join(labels)
    
    output = join(output, "matrix")
    
    if exists(output):
        print(f"Attention! Matrix already exists in this directory. Aborting to prevent overwriting!")
        return ""
    
    bigwig_files = " ".join(bigwig_files)
    bed_files = " ".join(bed_files)
    command = f"computeMatrix reference-point -p {workers} -S {bigwig_files} -R {bed_files} -a {window} -b {window} -o {output} --samplesLabel {labels}"
    
    print(f"Running: {command}")
    call(command, shell=True)
    
@task(log_prints=True)
def plot_heatmap(matrix: str, output: str, bed_files: Union[list, tuple]) -> None:
    labels = [Path(file).name.split(".")[0] for file in bed_files]
    labels = " ".join(labels)
    command = f"plotHeatmap -m {matrix} --regionsLabel {labels} --refPointLabel CpG --dpi 500 --perGroup -o {output}"
    
    print(f"Running: {command}")
    call(command, shell=True)

@flow(log_prints=True)
def start_analysis(bed_files: Union[list, tuple], encode_data_directory: str, window: int, output: str, workers: int) -> None:
    bigwig_files = glob(join(encode_data_directory, "data", "*.bigWig"))
    if not bigwig_files:
        raise DataNotFound(f"Not found bigWig files in data/ in {encode_data_directory} directory!")
    
    sample_sheet = join(encode_data_directory, "sample_sheet.csv")
    if not exists:
        raise DataNotFound(f"Samplesheet not found in {encode_data_directory} directory!")
    
    if not exists(output):
        print(f"Created {output} directory.")
        makedirs(output, exist_ok=True)
    
    for file in bed_files:
        if not exists(file):
            raise DataNotFound(f"Not found {file} directory!")
    
    print("Seems to be ok.")
    sample_sheet = pd.read_csv(sample_sheet)
    
    compute_matrix(sample_sheet, bigwig_files, bed_files, window, output, workers)
    plot_heatmap(join(output, "matrix"), join(output, "heatmap.png"), bed_files)
    build_summary_matrix(bigwig_files, bed_files, output, workers)