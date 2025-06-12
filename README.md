# PCL (Python-C Linked) Minimal Compiler/Runner

`pcl` is a minimal proof-of-concept compiler and runner for PCL files, which combine embedded C and Python code into a single source file. It extracts, compiles C code into shared libraries, generates Python `ctypes` wrappers, and runs the combined Python code seamlessly.

---

## Features

- Extracts embedded C and Python code blocks from `.pcl` source files.
- Compiles C code blocks into shared objects (`.so` files) using `gcc`.
- Automatically generates Python `ctypes` wrappers for C functions, globals, and callbacks.
- Stitches together Python code blocks and runs the result.
- Supports commands to build, run, clean, and package into a `.pyz` archive.

---

##  Online Playground

You can try out PCL directly in your browser using the **PCL Playground**:

[https://hejhdiss.github.io/pcl-playground/](https://hejhdiss.github.io/pcl-playground/)

The playground allows you to write `.pcl` files (which combine Python and C code), execute them remotely, and instantly see the results — no installation required.

### How It Works

- When you click **Run**, your `.pcl` code is sent to a remote backend.
- The backend:
  - Creates a **temporary `.pcl` file and project folder** on the server.
  - Extracts the C and Python code blocks.
  - Compiles the C part using `gcc`.
  - Generates `ctypes` wrappers and links everything.
  - Runs the resulting Python code and sends the output back.

### Use Case: Experiments

The playground is great for:

- Quickly experimenting with Python–C integration.
- Prototyping and testing `.pcl` code without setting up a local toolchain.

> ⚠️ **Note:** Code is stored and processed temporarily on the backend. Do not use the playground for storing important data or sensitive code.

---

## Installation on Linux (.deb based distros)

### Step 1: Import the public key

Download and import the PGP public key to verify packages:

```bash
wget https://keys.openpgp.org/vks/v1/by-fingerprint/63DDA53D7262972ABCFEDC6ADCD23CA69DC67339 -O publickey.asc
gpg --import publickey.asc
```

### Step 2: Install dependencies

Make sure you have the following installed:

- `python3` (3.7+ recommended)
- `gcc` compiler
- `gpg` (for key management)

You can install them using your package manager:

```bash
sudo apt update
sudo apt install python3 gcc gpg
```

### Step 3: Install PCL

Download the .deb file from [Releases](https://github.com/hejhdiss/pcl/releases) page.  
Open a terminal in the same directory where the .deb file is located, then run:

```bash
sudo dpkg -i pcl_1.0_all.deb
```

## Usage

Run commands as:

```bash
pcl run  /path_to_pcl_file
```

Run — Extract C and Python blocks, build C shared libs, generate wrappers, then execute the Python main script.

```bash
pcl build  /path_to_pcl_file 
```

build — Extract and build only (no execution). Outputs are placed in build/ and dist/ folders adjacent to your .pcl file.

```bash
pcl clean  /path_top_pcl_file 
```

clean — Deletes generated build/ and dist/ directories for the specified .pcl file.

### Optional Flags

--onefile — Creates a .pyz archive (zipapp) of the built project in the dist/ folder for easier distribution.

```bash
pcl build --onefile /path_to_pcl_file
```

---

## File Structure After Build

For a source file hello.pcl, you will get:

```bash
hello/
├── build/
│   ├── manifest.json
│   ├── mathmod.c
│   ├── mathmod.so
│   ├── mathmod_wrapper.py
│   └── __pcl_main__.py
├── dist/
│   └── hello_onefile.pyz  # if --onefile used
└── hello.pcl
```

---

## [Example .pcl Block Syntax](hello.pcl)

```bash
%c name=mathmod export=add,g_counter
#include <stdio.h>

int g_counter = 0;

int add(int a, int b) {
    return a + b;
}
%endc

%py requires=mathmod
print("Sum 3 + 4 =", add(3, 4))
print("Counter before increment:", g_counter.value)
g_counter.value += 1
print("Counter after increment:", g_counter.value)
%endpy
```

---

## Development Notes: PCL (Python-C Linked) Compiler/Runner

### Overview

- **PCL** allows embedding **C** and **Python** code blocks in a single `.pcl` file.
- The tool **extracts** C and Python blocks, compiles the C code into shared libraries (`.so`), and runs the combined Python code.
- Python code can import and use C modules through generated `ctypes` wrappers.

### Double File Usage: Python & C

- `.pcl` source contains interleaved **C** and **Python** code blocks, each marked by `%c ... %endc` and `%py ... %endpy`.
- C blocks are extracted into `.c` files and compiled into `.so` shared objects.
- Python blocks are combined into a single Python script (`__pcl_main__.py`) that imports generated wrappers for C modules.
- Generated wrappers expose C functions, globals, callbacks, structs, and enums to Python via `ctypes`.

### Key Features

- Auto-detection of exported symbols via metadata (`export` key).
- Optional symbol visibility control (e.g., hide symbols with `-fvisibility=hidden`).
- Simple error-checking wrappers that convert C error codes to Python exceptions.
- Only uses python standard libraries.
- Supports callback functions through `CFUNCTYPE`.
- Combines all Python code into one executable Python script.
- Optionally creates a `.pyz` archive (one-file executable).

### Limitations and Notes

- **Structs and enums:** Only minimal placeholder support; complex definitions require manual extension.
- **Global variables:** Only basic support assuming naming conventions (e.g., starting with `g_`).
- **Callbacks:** Assumes specific function signatures (e.g., `int callback(int)`), manual adjustment may be needed.
- **Error handling:** Requires explicit metadata flags or naming conventions for attaching error checks.
- **No advanced C parsing:** The compiler does not parse full C syntax or semantics; it relies on user metadata.
- **Build environment:** Requires `gcc` and Python 3.7+; `ctypes` is used for interfacing.
- **No symbol hiding by default:** Unless `hide=yes` is set, symbols remain visible in the `.so`.
- **Single process:** Python runs in the same process that loads compiled C modules.
- **Temporary directories:** Build and dist directories are created beside the `.pcl` file.
- **No cross-compilation:** Assumes native build environment.

### Tested Environment

- **Operating System:** Xubuntu 24.04.2 LTS
- **Virtualization Platform:** VMware Workstation 17
- **Notes:** The project has been tested and confirmed working in this environment. Compatibility with other Linux distributions or setups may vary.

---

## Further Development

The current PCL tool is a minimal proof-of-concept with several limitations and areas for improvement. Future development goals include:

- **Full C Language Parsing:** Implement a proper C parser to fully understand structs, enums, typedefs, macros, and complex declarations for accurate wrapper generation.
- **Advanced Type Support:** Automatically generate complete `ctypes` structures, unions, enums, and function pointer types from C definitions.
- **Improved Global Variable Handling:** Support arbitrary global variable types with correct memory management and type inference.
- **Flexible Callback Signatures:** Allow user-defined callback function signatures instead of hardcoded assumptions.
- **Enhanced Error Handling:** Provide comprehensive and customizable error checking and exception translation for all exported functions.
- **Symbol Visibility and Namespacing:** Enable fine-grained control over symbol export, hiding, and versioning to avoid conflicts.
- **Cross-Platform Support:** Extend compilation support beyond Linux/GCC to Windows (MSVC) and macOS (Clang).
- **Incremental Build System:** Implement caching and dependency tracking to avoid unnecessary recompilation.
- **Onefile Optimization:** Optimize `.pyz` packaging for faster startup and smaller size.
- **Performance Improvements:** Optimize compilation flags, caching, and wrapper overhead for maximum runtime efficiency.
- **IDE and Debugging Support:** Add features for debugging and interactive development, including better error messages and source mapping.
- **User-Friendly Metadata Syntax:** Develop richer, more intuitive metadata specification for exports, imports, and build options.
- **Security and Sandboxing:** Incorporate measures to sandbox and securely load compiled modules.
- **Multiple Python File Support:** Add support for multiple Python blocks/files within a single `.pcl` source, enabling modular Python code organization.
- **Documentation and Examples:** Expand official docs, tutorials, and example projects to facilitate adoption.

Our aim is to evolve PCL into a robust, flexible, and high-performance tool that seamlessly bridges Python and C with minimal boilerplate, no loss of type safety or performance, and maximum developer productivity.

---

## License

MIT License.

---

## Collaboration and Contribution

This project is a minimal proof-of-concept implementation of the Python-C Linked (PCL) compiler/runner. To evolve it beyond its current limitations and maximize its potential, collaboration from experienced open source developers and the community is highly welcomed.

If you have expertise in compiler design, ctypes integration, C/Python interoperability, or related fields, your contributions will be invaluable in:

- Removing existing limitations  
- Adding support for multiple Python files and complex C constructs  
- Optimizing build and runtime performance  
- Enhancing error handling and memory management  
- Expanding documentation and test coverage

Please reach out via email (hejhdiss@gmail.com) or submit pull requests on the repository. Together, we can build a robust and versatile PCL toolchain.

---

## Support and Contact

For questions, support, or feedback, please contact:

**[Submit Feedback or Support the Project]**(https://hejhdiss.github.io/pcl-support/)  
**Email:** hejhdiss@gmail.com  
**Author:** Muhammed Shafin P

