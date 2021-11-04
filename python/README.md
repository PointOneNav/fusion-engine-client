# Point One FusionEngine Python Client

This directory includes Python support for the Point One FusionEngine message protocol, along with analysis tools,
data extraction utilities, and example usage scripts.

See https://github.com/PointOneNav/fusion-engine-client for full details. See http://docs.pointonenav.com/fusion-engine/
for the latest API documentation.

* [Requirements](#requirements)
* [Directory Structure](#directory-structure)
* [Usage Instructions](#usage-instructions)
* [Examples](#examples)
* [Using A Python Virtual Environment](#using-a-python-virtual-environment)

### Requirements
- Python 3.4 or later

### Directory Structure
  - `python/` - Python source files
    - `bin/` - Application files
      - [p1_display.py](examples/p1_display.py) - Generate HTML plots of vehicle trajectory, etc. (see also
        `analyzer.py` below)
    - `examples/` - Python example applications
      - [analyze_data.py](examples/analyze_data.py) - Generate HTML plots of vehicle trajectory, INS filter state, etc.
      - [extract_imu_data.py](examples/extract_imu_data.py) - Generate a CSV file containing recorded IMU measurements
      - [extract_position_data.py](examples/extract_position_data.py) - Generate CSV and KML files detailing the vehicle
        position over time
        - This script also includes an example of time-aligning multiple message types
      - [extract_satellite_info.py](examples/extract_satellite_info.py) - Generate a CSV file containing satellite 
        azimuth/elevation and C/N0 information over time
      - [message_decode.py](examples/message_decode.py) - Read a `.p1log` binary file and decode the contents
      - [tcp_client.py](examples/tcp_client.py) - Connect to a device over TCP and decode/display messages in real time
      - [udp_client.py](examples/udp_client.py) - Connect to a device over UDP and decode/display messages in real time
    - `fusion_engine_client` - Top Python package directory
      - `analysis`
        - [analyzer.py](analysis/analyzer.py) - `Analyzer` class, used to plot data from a recorded file of FusionEngine
          messages (vehicle trajectory map, navigation engine state information, etc.)
          - This class is used by the `bin/p1_display.py` application
        - [file_reader.py](analysis/file_reader.py) - `FileReader` class, capable of loading and time-aligning
          FusionEngine data captured in a `*.p1log` file
      - `messages` - Python message definitions
      - `utils` - Various utility functions used by the other files (e.g., log search support)
    
### Usage Instructions

To use the Python library:

1. Install Python 3.4 (or later) and pip.
2. Install the Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run any of the applications in `python/bin/` or the example code in `python/examples/`. For example, to plot results
   from a `*.p1log` file or recorded in an Atlas log:
   ```bash
   python3 bin/p1_display.py /path/to/log/directory
   ```

Whenever possible, we strongly encourage the use of a Python [virtual environment](#using-a-python-virtual-environment).

### Examples

#### Analyzing A Recorded Log

The following will generate plots for a log with ID `c25445f4e60d441dbf4af8a3571352fa`.

```bash
> python3 bin/p1_display.py /path/to/c25445f4e60d441dbf4af8a3571352fa
```

Alternatively, you can search for a log by entering the first few characters of the ID. By default, logs are assumed to
be stored in the directory `/logs`.

```bash
> python3 bin/p1_display.py c2544
```

Use the `--logs-base-dir` argument to search a directory other than `/logs`:

```bash
> python3 bin/p1_display.py --logs-base-dir /my/log/directory c2544
```

#### Generate A CSV File Containing Position And Solution Type Information

```bash
> python3 examples/extract_position_data.py /path/to/c25445f4e60d441dbf4af8a3571352fa
```

This will produce the file `/path/to/c25445f4e60d441dbf4af8a3571352fa/position.csv`.

#### Generate A CSV File Containing Satellite Information

_Requires `GNSSSatelliteMessage` to be enabled._

```bash
> python3 examples/extract_position_data.py /path/to/c25445f4e60d441dbf4af8a3571352fa
```

This will produce the file `/path/to/c25445f4e60d441dbf4af8a3571352fa/position.csv`.

### Using A Python Virtual Environment

Whenever possible, we strongly encourage the use of a
[Python virtual environment](https://docs.python.org/3/tutorial/venv.html). To use the FusionEngine client within a
virtual  environment:

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
   or in Windows:
   ```bash
   venv\Scripts\activate.bat
   ```
3. Install the pip requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Run any of the FusionEngine applications/scripts normally:
   ```bash
   python3 bin/p1_display.py /path/to/log/directory
   ```
