#!/usr/bin/env python3

""" Generates a single HTML page showing all module visualistions from multiple
antiSMASH results
"""

import argparse
import glob
import json
import os
import shutil
import sys

VISUALISER_ROOT = "antismash.outputs.html.visualisers"

HTML_TOP = """
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Collected modules from antiSMASH results</title>
  <link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
"""
HTML_BOTTOM = """
  <script src="custom_antismash.js"></script>
  <script src="data.js"></script>
  <script src="jquery.js"></script>
  <script>
    $(document).ready(function() {
        for (record of data) {
            for (area of record.areas) {
                console.log(area.anchor, area.bubbles);
                viewer["actualDrawDomainBubbleData"](area.anchor, area.bubbles);
            }
        }
    })
  </script>
</body>
</html>
"""


class InputError(Exception):
    """ A subclass just to be able to communicate to the command line that the
        error is directly related to the inputs
    """


def get_areas(handle):
    """ Loads JSON from the given file handle to antiSMASH results, then gathers
        all the areas from it.

        Returns:
            a dictionary mapping typical antiSMASH anchors (e.g. "r1c5") to the
            area dictionary from the results, also including the record identifier
    """
    full_results = json.load(handle)
    schema = full_results.get("schema", 0)
    if not 2 <= schema <= 3:
        raise InputError(f"incompatible antiSMASH results file schema version: {schema}")
    areas = {}
    for r_index, record in enumerate(full_results["records"]):
        for c_index, area in enumerate(record["areas"]):
            areas[f"r{r_index + 1}c{c_index + 1}"] = {
                "name": record["id"],
                "start": area["start"],
                "end": area["end"],
                "products": area["products"],
            }
    return areas


def extract_bubble_data(handle):
    """ Extracts the bubble/module visualisation data from a handle to the "region.js"
        output file from antiSMASH. Takes the first (i.e. largest) candidate cluster
        from each region instead of showing options.

        Returns:
            the existing JSON data, as a dictionary
    """
    lines = handle.readlines()
    relevant_section = []
    i = 0
    # skip to the relevant section
    while i < len(lines) and not lines[i].startswith("var resultsData ="):
        i += 1
    if i >= len(lines):
        raise ValueError("Javascript data does not contain relevant results")
    # remove the non-JSON assignment
    lines[i] = lines[i].replace("var resultsData = ", "")
    while i < len(lines) and not lines[i].startswith("var "):
        relevant_section.append(lines[i])
        i += 1
    # the remainder of the file can be skipped

    # rebuild from JSON, remembering to remove any trailing semicolons from the javascript
    results_data = json.loads(" ".join(relevant_section).rstrip().rstrip(";"))

    bubble_data = {}
    for anchor, data in results_data.items():
        bubble_data[anchor] = data.get(f"{VISUALISER_ROOT}.bubble_view")
    return bubble_data


def gather_from_files(input_dir: str):
    """ Gathers all relevant data from the given antiSMASH results directory.
        If a single record does not contain any relevant data, it will not be
        included in the results.

        Returns:
            a dictionary mapping each record name to another dictionary with:
                - the record's areas, as pulled from the antiSMASH results JSON
                - the record's module visualisation data from the antiSMASH 'regions.js' output file
    """
    full_result_file = glob.glob(os.path.join(input_dir, "*.json"))
    if not full_result_file:
        raise InputError(f"No results file ('*.json') in result directory: {input_dir}")
    with open(full_result_file[0], encoding="utf-8") as handle:
        areas = get_areas(handle)

    with open(os.path.join(input_dir, "regions.js"), encoding="utf-8") as handle:
        bubble_data = extract_bubble_data(handle)

    record_names = {area["name"] for area in areas.values()}
    records = {name: {"name": name, "areas": []} for name in record_names}
    for anchor, area in areas.items():
        name = area.pop("name")
        bubbles = bubble_data.get(anchor)
        if not bubbles:
            continue
        area["bubbles"] = list(bubbles.values())[0]
        records[name]["areas"].append(area)

    # remove records any that don't have any relevant parts at all
    records = {key: value for key, value in records.items() if value["areas"]}
    return list(records.values())


def process_all_results(input_dirs):
    """ Gathers all relevant data from the given antiSMASH results directories.

        Returns:
            a dictionary mapping record name to another dictionary with:
                - the record's areas, as pulled from the antiSMASH results JSON
                - the record's module visualisation data from the antiSMASH 'regions.js' output file
    """
    if not input_dirs:
        raise ValueError("No result directories provided")
    return [record for input_dir in input_dirs for record in gather_from_files(input_dir)]


def generate_page(inputs, output_dir) -> None:
    """ Generates a webpage in the given output directory, using all of the antiSMASH
        results directories given as inputs.
    """
    all_results = process_all_results(inputs)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as handle:
        handle.write(HTML_TOP)
        for record in all_results:
            for area in record["areas"]:
                area["anchor"] = f'{record["name"].replace(".", "-")}-{area["start"]}'
                anchor = f"{area['anchor']}-domain-bubble-svg-container"
                style = "font-weight:bold; margin-bottom: -2em; margin-top: 2em;"
                location = f'{area["start"]}-{area["end"]}'
                products = ", ".join(area["products"])
                handle.write(f'  <div style="{style}">{record["name"]}: {location}: {products}</div>')
                handle.write(f'  <div id={anchor}></div>')
        handle.write(HTML_BOTTOM)
    with open(os.path.join(output_dir, "data.js"), "w", encoding="utf-8") as handle:
        handle.write("var data = ")
        json.dump(all_results, handle, indent=1)
        handle.write(";")
    for dep in glob.glob(os.path.join(os.path.dirname(__file__), "dependencies", "*")):
        shutil.copy(dep, os.path.join(output_dir, os.path.basename(dep)))


def _main(input_dir, output_dir) -> int:
    """ Simple checking and processing of basic command line arguments """
    if not os.path.isdir(input_dir):
        print("Input is not a directory:", input_dir, file=sys.stderr)
        return 1
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.isdir(output_dir):
        print("Input is not a directory:", input_dir, file=sys.stderr)
        return 1
    result_files = glob.glob(os.path.join(input_dir, "*"))
    try:
        generate_page(result_files, output_dir)
    except (OSError, InputError) as err:
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=str,
                        help="The path to a directory containing antiSMASH output directories",
                        metavar="PATH")
    parser.add_argument("output", type=str,
                        help="The output location, will be created if it does not exist",
                        metavar="PATH")
    args = parser.parse_args()
    sys.exit(_main(args.inputs, args.output))
