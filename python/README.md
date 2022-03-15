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
- Python 3.6 or later

### Directory Structure
  - `python/` - Python source files
    - `bin/` - Application files
      - [p1_display.py](examples/p1_display.py) - Generate HTML plots of vehicle trajectory, etc. (see also
        `analyzer.py` below)
      - [separate_mixed_log.py](examples/separate_mixed_log.py) - Extract FusionEngine message contents from a binary 
        file containing mixed data (e.g., interleaved RTCM and FusionEngine messages) 
    - `examples/` - Python example applications
      - [analyze_data.py](examples/analyze_data.py) - Generate HTML plots of vehicle trajectory, INS filter state, etc.
      - [encode_data.py](examples/encode_data.py) - Construct and serialize FusionEngine messages, and save them in a
        `*.p1log` file that can be used with the other example utilities
      - [extract_imu_data.py](examples/extract_imu_data.py) - Generate a CSV file containing recorded IMU measurements
      - [extract_position_data.py](examples/extract_position_data.py) - Generate CSV and KML files detailing the vehicle
        position over time
        - This script also includes an example of time-aligning multiple message types
      - [extract_satellite_info.py](examples/extract_satellite_info.py) - Generate a CSV file containing satellite 
        azimuth/elevation and C/N0 information over time
      - [message_decode.py](examples/message_decode.py) - Read a `.p1log` binary file and decode the contents
      - [raw_tcp_client.py](examples/raw_tcp_client.py) - Connect to a device over TCP and decode/display messages in
        real time (decoding messages manually, without the using the `FusionEngineDecoder` helper class)
      - [tcp_client.py](examples/tcp_client.py) - Connect to a device over TCP and decode messages in real time to be
        displayed and/or logged to disk using the `FusionEngineDecoder` helper class
      - [udp_client.py](examples/udp_client.py) - Connect to a device over UDP and decode/display messages in real time
    - `fusion_engine_client` - Top Python package directory
      - `analysis`
        - [analyzer.py](analysis/analyzer.py) - `Analyzer` class, used to plot data from a recorded file of FusionEngine
          messages (vehicle trajectory map, navigation engine state information, etc.)
          - This class is used by the `bin/p1_display.py` application
        - [file_reader.py](analysis/file_reader.py) - `FileReader` class, capable of loading and time-aligning
          FusionEngine data captured in a `*.p1log` file
      - `messages` - Python message definitions
      - `parsers` - Message encoding and decoding support
        - [decoder.py](parsers/decoder.py) - `FusionEngineDecoder` class, used to frame and parse incoming streaming
          data (e.g., received over TCP or serial)
        - [encoder.py](parsers/encoder.py) - `FusionEngineEncoder` class, used when serializing messages to be sent to a
          connected device
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

## Examples

### Analyzing A Recorded Log And Plotting Results

> Note: In order to generate a map, you must provide a Mapbox access token using the `--mapbox-token` argument, or by
> setting either the `MAPBOX_ACCESS_TOKEN` or `MapboxAccessToken` environment variables.

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

### Record Data Over TCP

The [examples/tcp_client.py]() script can be used to record data to a `.p1log` file for post-processing by specifying
the `--output` argument. Note that we are also setting `--no-display` here, since we only want to record the data and
are not interested in printing the contents to the console.

```bash
> python3 examples/tcp_client.py --no-display --output my_data.p1log 192.168.1.2
```

### Reading Messages From A `*.p1log` File

```python
from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *

reader = FileReader(input_path)
result = reader.read(message_types=[PoseMessage])
for message in result[PoseMessage.MESSAGE_TYPE].messages:
    print("LLA: %.6f, %.6f, %.3f" % message.lla_deg)
```

### Time-Aligning Multiple Message Types

The `FileReader` class has built-in support for aligning multiple message types based on their P1 timestamps. When
`INSERT` mode is enabled, the `FileReader` will create messages automatically for any times when they are not present
(dropped due to invalid CRC, etc.). The created message objects will be set to their default values.

```python
from fusion_engine_client.analysis.file_reader import FileReader, TimeAlignmentMode
from fusion_engine_client.messages.core import *

reader = FileReader(input_path)
result = reader.read(message_types=[PoseMessage, GNSSSatelliteMessage], time_align=TimeAlignmentMode.INSERT)
for pose, gnss in zip(result[PoseMessage.MESSAGE_TYPE].messages, result[GNSSSatelliteMessage.MESSAGE_TYPE].messages):
    print("LLA: %.6f, %.6f, %.3f, # satellites: %d" % (pose.lla_deg, len(gnss.svs)))
```

> Note that some message types are not synchronous. For example, raw sensor measurements (IMU data, etc.) are not
guaranteed to occur at the same time as the generated position solutions. Attempting to time-align asynchronous message
types may result in unexpected behavior.

See [extract_position_data.py](examples/extract_position_data.py) for an example of time-aligning multiple message
types.

### Framing And Decoding Incoming Messages

```python
from fusion_engine_client.messages.core import *
from fusion_engine_client.parsers import FusionEngineDecoder

decoder = FusionEngineDecoder()
results = decoder.on_data(received_bytes)
for (header, message) in results:
    if isinstance(message, PoseMessage):
        print("LLA: %.6f, %.6f, %.3f" % message.lla_deg)
```

See [examples/tcp_client.py]() for an example use of the decoder class.

### Serializing Outgoing Messages

```python
from fusion_engine_client.messages.core import *
from fusion_engine_client.parsers import FusionEngineEncoder

encoder = FusionEngineEncoder()

message = PoseMessage()
message.p1_time = Timestamp(1.0)
message.solution_type = SolutionType.DGPS
message.lla_deg = np.array([37.776417, -122.417711, 0.0])
message.ypr_deg = np.array([45.0, 0.0, 0.0])
data = encoder.encode_message(message)
```

### Generate A CSV File Containing Position And Solution Type Information

```bash
> python3 examples/extract_position_data.py /path/to/c25445f4e60d441dbf4af8a3571352fa
```

This will produce the file `/path/to/c25445f4e60d441dbf4af8a3571352fa/position.csv`.

### Generate A CSV File Containing Satellite Information

_Requires `GNSSSatelliteMessage` to be enabled on the device._

```bash
> python3 examples/extract_position_data.py /path/to/c25445f4e60d441dbf4af8a3571352fa
```

This will produce the file `/path/to/c25445f4e60d441dbf4af8a3571352fa/position.csv`.

See [examples/encode_data.py]() for an example of data serialization.

## Using A Python Virtual Environment

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
