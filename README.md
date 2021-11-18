# fixwav
## Description
A tool I created to "clean" corrupted wav files.

This tool won't work on just any corrupt wav file. The corruption was
very specific and consistent in what it did. The corruption was
part of an upgrade from Windows 7 to Windows 10, and some process
evidently tried to do some id3 tagging of the .wav files, but just
left them in an unplayable state.

This tool will take a source and destination parameters and clean
all corrupted wav files in the source and copy them to the corresponding
location in the destination. While it might be able to help a few people
with the same problem, it more likely is a good resource to look and see
how a python file can go about parsing wav (and id3) headers.

Tested with Python 3.8.11 on MacOS.

## Usage
```bash
python fixwav.py -s SOURCE_DIR -d DESTINATION_DIR -a
```

__-s__ Source dir to analyze

__-d__ Destination dir to copy to

__-a / -c__ Mutually exclusive flags. Can either copy all other files (-a) to preserve
folder structure, or you can choose to copy/clean the corrup files (-c)
