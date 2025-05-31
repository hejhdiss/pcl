# Changelog

## Version 1.0 – Initial Release

- Minimal proof-of-concept compiler/runner for PCL (Python-C Linked) files.
- Supports embedding multiple C and Python blocks in a single `.pcl` file.
- Extraction of C and Python code blocks with metadata parsing.
- Automatic compilation of C blocks into shared objects (`.so`).
- Generation of Python `ctypes` wrappers for calling C functions and accessing global variables.
- Stitching multiple Python blocks into a single runnable Python script.
- CLI support for `run`, `build`, and `clean` commands.
- Option to create a single-file `.pyz` archive for easy distribution.
- Basic error handling and memory ownership helpers in wrappers.
- Support for exporting functions, global variables, callback types, and placeholders for structs/enums.
- Designed as a minimal proof-of-concept to demonstrate core ideas.
