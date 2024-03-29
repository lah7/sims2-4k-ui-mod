#!/usr/bin/python3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2022-2023 Luke Horwell <code@horwell.me>
#
"""
This script takes files from an extracted ui.package (via SimPE),
upscales the fonts & graphics and produces a new package file.

While graphic rules can be defined to allow The Sims 2 to run at 4K,
the user interface elements are extremely tiny.  This modification
upscales the user interface by doubling the density of the graphics and fonts.

See the README for instructions on using this script.
"""
import argparse
import glob
import os
import shutil
import signal
import tempfile

import dbpf


class Properties():
    # The number to multiply the UI dialog geometry and graphics
    # -- TODO: Test decimal
    UI_ZOOM_FACTOR: int = 2

    # How many points to increase the font size in addition to the UI_ZOOM_FACTOR
    FONT_INCREASE_PT: int = 0

    # What quality to upscale images: point, linear, cubic
    UPSCALE_FILTER: str = "point"

    # Paths
    INPUT_DIR: str = os.path.join(os.path.dirname(__file__), "input")
    TEMP = tempfile.TemporaryDirectory()
    TEMP_DIR: str = os.path.join(TEMP.name, "sims2-4k-ui-mod")
    OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "output")

PROPS = Properties()


def filter_files_by_type(files) -> dict:
    """
    The files extracted by SimPE are not actually JPGs. Most are Targa (TGA),
    bu could also be PNGs, Bitmap (.bmp) and JPEGs.

    This function checks for first few bytes of each file and returns a
    dictionary filtered by each known type.
    """
    print(f"\nAnalyzing {len(files)} files...")
    tga = []
    bmp = []
    jpg = []
    png = []
    unknown = []

    for path in files:
        with open(path, "rb") as f:
            # Check the first 4 bytes
            start = f.read()[:4]

            if start[:3] in [b'\x00\x00\x02', b'\x00\x00\n']:
                tga.append(path)
            elif start[:2] == b'BM':
                bmp.append(path)
            elif start[:3] == b'\xff\xd8\xff':
                jpg.append(path)
            elif start[:4] == b'\x89PNG':
                png.append(path)
            else:
                unknown.append(path)

    return {
        "bmp": bmp,
        "jpg": jpg,
        "png": png,
        "tga": tga,
        "unknown": unknown,
    }


def upscale_fontstyle_ini():
    """
    Parses FontStyle.ini from the input/Fonts folder and writes a new one
    with font sizes increased by the FONT_INCREASE_PT factor.
    """
    in_path = os.path.join(PROPS.INPUT_DIR, "FontStyle.ini")
    out_path = os.path.join(PROPS.OUTPUT_DIR, "FontStyle.ini")

    if not os.path.exists(in_path):
        print("Skipping FontStyle.ini as not present in 'input' folder")
        return

    with open(in_path, "r") as f:
        lines = f.readlines()

    output = []
    for line in lines:
        parts = line.split('"')
        if len(parts) < 6:
            output.append(line)
            continue

        old_size = parts[3]
        new_size = (int(parts[3]) * PROPS.UI_ZOOM_FACTOR) + PROPS.FONT_INCREASE_PT
        parts[3] = str(new_size)
        output.append('"'.join(parts))

    with open(out_path, "w") as f:
        f.writelines(output)

    print("\nWritten new FontStyle.ini")


def upscale_uiscripts():
    """
    Parses *.uiScript (modified XML) files; multiplies the attribute's
    value (consisting of comma separated values) by UI_ZOOM_FACTOR and
    returns the new data.
    """
    print("\nProcessing .uiScript files...")
    file_list = glob.glob(PROPS.INPUT_DIR + "/**/*.uiScript", recursive=True)
    current = 0
    total = len(file_list)
    print(".", end="")

    for path in file_list:
        current += 1
        print(f"\r[{current}/{total}, {int(current/total * 100)}%] Writing: {path.split('/')[-1]}    ", end="")
        output_path = path.replace(PROPS.INPUT_DIR, PROPS.TEMP_DIR)

        try:
            with open(path, "r") as f:
                data = f.read()
        except UnicodeDecodeError:
            # Encountered a binary .uiScript files, copy them as-is.
            shutil.copy(path, output_path)
            continue

        def _replace_coord_attribute(data, name):
            output = []
            parts = data.split(name + "=")
            for part in parts:
                if not part.startswith("("):
                    output.append(part)
                    continue

                new_values = []
                values = part.split("(")[1].split(")")[0]
                for number in values.split(","):
                    new_values.append(str(int(number) * PROPS.UI_ZOOM_FACTOR))
                part = f"{name}={part.replace(values, ','.join(new_values))}"
                output.append(part)
            return "".join(output)

        data = _replace_coord_attribute(data, "area")
        data = _replace_coord_attribute(data, "gutters")

        with open(output_path, "w") as f:
            f.writelines(data)


def upscale_graphics():
    """
    Upscales the specified graphic using Imagemagick ('convert' command)
    with the UPSCALE_FILTER for quality.
    """
    file_list = glob.glob(PROPS.INPUT_DIR + "/**/*.jpg", recursive=True)
    file_types = filter_files_by_type(file_list)
    print("\nProcessing graphics...")
    print("    TGA:", len(file_types["tga"]))
    print("    JPG:", len(file_types["jpg"]))
    print("    PNG:", len(file_types["png"]))
    print("    BMP:", len(file_types["bmp"]))
    print("     ? :", len(file_types["unknown"]))

    # Copy unknown files as-is
    for path in file_types["unknown"]:
        shutil.copy(path, path.replace(PROPS.INPUT_DIR, PROPS.TEMP_DIR))
    del(file_types["unknown"])

    current = 0
    total = len(file_types["tga"]) + len(file_types["jpg"]) + len(file_types["png"]) + len(file_types["bmp"])
    print(".", end="")
    for ext in file_types.keys():
        for path in file_types[ext]:
            current += 1
            print(f"\r[{current}/{total}, {int(current/total * 100)}%] Converting {ext.upper()}: {path.split('/')[-1].split('.')[0]}    ", end="")

            # Create temporary file so input directory remains untouched
            tempin = path.replace(PROPS.INPUT_DIR, PROPS.TEMP_DIR).replace(".jpg", f".tmp.{ext}")
            shutil.copy(path, tempin)

            # Imagemagick needs to know the real file extension to convert
            tempout = tempin.replace(f".tmp.{ext}", f".{ext}")
            os.system(f"convert '{tempin}' -filter {PROPS.UPSCALE_FILTER} -resize {PROPS.UI_ZOOM_FACTOR * 100}% '{tempout}'")
            os.remove(tempin)

            # Rename the file back to 'JPG'
            output = tempout.replace(f".{ext}", ".jpg")
            os.rename(tempout, output)

    print("\n")


def create_dirs():
    """
    Replicate the input subdirectories and copy the XML files (which SimPE
    created and we need to reference later)
    """
    def ignore_files(dir, files):
        ignored = []
        for name in files:
            if os.path.isfile(os.path.join(dir, name)) and not name.endswith(".xml") and not name.endswith(".simpe"):
                ignored.append(name)
        return ignored

    shutil.copytree(PROPS.INPUT_DIR, PROPS.TEMP_DIR, ignore=ignore_files)

    if not os.path.exists(PROPS.OUTPUT_DIR):
        os.makedirs(PROPS.OUTPUT_DIR)


def check_input_files(check_name, ext):
    """
    Perform a prelimitary check that we have everything required for processing.
    """
    if len(glob.glob(PROPS.INPUT_DIR + "/**/*." + ext, recursive=True)) > 0:
        print("     OK |", check_name)
        return True
    print("MISSING |", check_name)
    return False


def create_dbpf_package():
    """
    Use the custom DBPF library written specifically for this project to create
    a new .package file.

    Because the extraction is incomplete (due to compressed files), SimPE's XML
    files will be used to determine the correct IDs when packing a new file.
    """
    print("\nCreating DBPF package...")
    output_path = os.path.join(PROPS.OUTPUT_DIR, "ui.package")

    if os.path.exists(output_path):
        os.remove(output_path)
    open(output_path, "wb").close()

    package = dbpf.DBPF(output_path)
    xml_files = glob.glob(PROPS.TEMP_DIR + "/**/*.xml", recursive=True)
    uuids = []

    def _get_xml_attribute(xml_path: str, attrib: str):
        """
        Scrape the XML file and returns the value for the attribute.
        A library would be better, but this is quicker with less overhead for now.
        """
        with open(xml_path, "r") as f:
            for line in f.readlines():
                if line.strip().startswith(f"<{attrib}>"):
                    return int(line.split(f"<{attrib}>")[1].split(f"</{attrib}>")[0].strip())
        return 0

    for xml_path in xml_files:
        if xml_path.endswith("package.xml"):
            continue

        file_path: str = xml_path.replace(".xml", "")
        type_id: int = _get_xml_attribute(xml_path, "number")
        group_id: int = _get_xml_attribute(xml_path, "group")
        instance_id: int = _get_xml_attribute(xml_path, "instance")

        # Skip duplicate group/instance ID combos
        # This may happen if multiple extracted ui.package files are processed
        uuid = str(group_id) + "_" + str(instance_id)
        if uuid in uuids:
            print(f"Skipping duplicate group ID {hex(group_id)} with instance ID {hex(instance_id)}")
            continue
        uuids.append(uuid)

        # Add file into DBPF package
        package.add_file_from_path(type_id, group_id, instance_id, file_path)

    package.save(output_path)
    print("\nPackage successfully saved to output/" + os.path.basename(output_path), "\n")


def process_parameters():
    """
    Processes optional parameters passed by the user.
    """
    parser = argparse.ArgumentParser()
    #parser._optionals.title = "Optional arguments"
    parser.add_argument("--zoom-factor", help="Pixel density to multiply by (e.g. 2)", action="store")
    parser.add_argument("--filter", help="Filter to use when upscaling, (e.g. pointer, linear, cubic)", action="store")
    parser.add_argument("--input-dir", help="Path to extracted, original package files", action="store")
    parser.add_argument("--temp-dir", help="Path to temporarily store files. It won't be deleted afterwards", action="store")
    parser.add_argument("--output-dir", help="Path to save the modified package/files", action="store")

    args = parser.parse_args()

    if args.zoom_factor:
        PROPS.UI_ZOOM_FACTOR = int(args.zoom_factor)
    if args.filter:
        PROPS.UPSCALE_FILTER = args.filter
    if args.input_dir:
        PROPS.INPUT_DIR = os.path.realpath(args.input_dir)
    if args.temp_dir:
        PROPS.TEMP_DIR = os.path.realpath(args.temp_dir)
    if args.output_dir:
        PROPS.OUTPUT_DIR = os.path.realpath(args.output_dir)


if __name__ == "__main__":
    # Allow CTRL+C to abort script
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    process_parameters()

    # Check files are found
    print("Performing preliminary checks...")
    checks = [
        check_input_files("UI Data (UI)", "uiScript"),
        check_input_files("jpg/tga/png Image (IMG)", "jpg"),
        check_input_files("Accelerator Key Definitions", "simpe"),
    ]
    if False in checks:
        exit(1)

    # Write directories for output
    create_dirs()

    # 1. Adjust geometry in *.uiScript files
    upscale_uiscripts()

    # 2. Adjust font size in FontStyle.ini (base game)
    upscale_fontstyle_ini()

    # 3. Enlarge UI graphics (requires 'imagemagick' to be installed)
    upscale_graphics()

    # 4. Create a new DBPF compatible package
    create_dbpf_package()

    # Clean up
    PROPS.TEMP.cleanup()
