import argparse
import logging
from pathlib import Path
import shutil
import sys
import wave

WAVE_FMT_DATA_HEADER = bytes.fromhex(
    "666D7420120000000100020044AC000010B1020004001000000064617461"
)
ID31 = bytes.fromhex("696433200a080000")
ID32 = bytes.fromhex("49443303000000001000")

# Function to determine if wave is corrupt
def is_corrupt(file):
    try:
        wave_file = wave.open(str(file), "rb")
    except RuntimeError:
        return True

    try:
        params = wave_file.getparams()
    except RuntimeError:
        return True

    return False


def get_new_path(source: Path, source_root: Path, destination_root: Path):
    relative_source = source.relative_to(source_root)
    return destination_root / relative_source


def setup_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def clean_wave(source, source_root, destination_root):
    infile = open(source, "rb")
    outfile_path = get_new_path(source, source_root, destination_root)
    outfile_dir = outfile_path.parent
    outfile_dir.mkdir(parents=True, exist_ok=True)
    outfile = open(outfile_path, "wb")

    # Jump to 16, where the list length is
    infile.seek(16)

    # Get length of info header
    info_length_bytes = infile.read(4)
    info_length = int.from_bytes(info_length_bytes, byteorder="little")

    # Store info_header to write later
    info_header = infile.read(info_length)

    # Skip id3 nonsense. Make sure id3 tags start here, if not, bail on this file
    id31 = infile.read(8)
    if id31 != ID31:
        print(f"ERROR: {source} - ID3 tags not found where expected")
        return

    id32 = infile.read(10)
    if id32 != ID32:
        print(f"ERROR: {source} - ID3 tags not found where expected")
        return

    # Iterate over ID3 frames
    id3_frames = []

    while True:
        id3_next_char = infile.read(1)
        # Back up the char you just read so we can save it
        infile.seek(-1, 1)

        if not id3_next_char.isalnum():
            break

        # Frame ID: 4 char capital
        frame_id = infile.read(4)
        id3_frames.append(frame_id)

        # Frame length 4 bytes
        frame_length_bytes = infile.read(4)
        id3_frames.append(frame_length_bytes)
        frame_length = int.from_bytes(frame_length_bytes, byteorder="big")

        # Frame flags 4 bytes
        frame_flags = infile.read(2)
        id3_frames.append(frame_flags)

        # Frame content length from above
        frame_content = infile.read(frame_length)
        id3_frames.append(frame_content)

    # Calculate remaining size
    cur_pos = infile.tell()
    infile.seek(0, 2)
    last_pos = infile.tell()
    data_length = last_pos - cur_pos
    infile.seek(cur_pos)

    # 16 RIFF Header
    # 4 RIFF total length
    # info_length has info header length
    # WAVE_FMT_DATA_HEADER is the header (so get it's length)
    # 4 data length

    riff_length = 16 + 4 + info_length + len(WAVE_FMT_DATA_HEADER) + 4 + data_length

    outfile.write(b"RIFF")
    outfile.write(riff_length.to_bytes(4, byteorder="little", signed=True))
    outfile.write(b"WAVELIST")
    outfile.write(info_length_bytes)
    outfile.write(info_header)
    outfile.write(WAVE_FMT_DATA_HEADER)

    # Handle odd data length, wav must be even
    if data_length % 2 == 1:
        outfile.write(bytes.fromhex("00"))
        data_length += 1
    outfile.write(data_length.to_bytes(4, byteorder="little", signed=True))

    # Write the remainder of data
    outfile.write(infile.read())

    infile.close()
    outfile.close()


### Main method
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="fixwav",
        description="Copy a directory to a new directory and clean corrupt wav files in it.",
    )
    parser.add_argument("-s", "--source", required=True)
    parser.add_argument("-d", "--destination", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", "--all", action="store_true")
    group.add_argument("-c", "--corrupt", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    destination = Path(args.destination)
    copy_all = args.all

    # Set up loggers
    corrupt = setup_logger("corrupt", "corrupt.log")
    clean = setup_logger("clean", "clean.log")

    # Destination should not exist
    if Path.exists(destination):
        print(f"Destination path should not exist")
        sys.exit(1)

    destination.mkdir(parents=True)

    # TODO: Might need generator if too many files
    # If so, don't sort!
    files = [x for x in sorted(Path(source).rglob("*")) if x.is_file()]
    for path in files:
        print(path)

        # Copy wav files
        if path.suffix == ".wav":
            if is_corrupt(path):
                corrupt.info(path)
                clean_wave(path, source, destination)
            else:
                if copy_all:
                    clean.info(path)
                    outfile_path = get_new_path(path, source, destination)
                    outfile_dir = outfile_path.parent
                    outfile_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy(path, outfile_path)

        # Copy non wav files
        else:
            if copy_all:
                clean.info(path)
                outfile_path = get_new_path(path, source, destination)
                outfile_dir = outfile_path.parent
                outfile_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(path, outfile_path)
