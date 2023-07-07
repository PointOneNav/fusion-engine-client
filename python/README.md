# Point One FusionEngine Python Client

This directory includes Python support for the Point One FusionEngine message protocol, along with analysis tools,
data extraction utilities, and example usage scripts.

See https://github.com/PointOneNav/fusion-engine-client for full details. See
[Point One FusionEngine Message Specification](http://pointonenav.com/files/fusion-engine-message-spec) for the latest
FusionEngine message specification.

* [Requirements](#requirements)
* [Directory Structure](#directory-structure)
* [Usage Instructions](#usage-instructions)
* [Examples](#examples)
* [Using A Python Virtual Environment](#using-a-python-virtual-environment)

### Requirements
- Python 3.6 or later

### Directory Structure
  - `python/` - Python source files
    - `bin/` - Analysis and processing tools
      - [p1_display](bin/p1_display) - Generate HTML plots of vehicle trajectory, etc. (see also
        `analyzer.py` below)
      - [p1_extract](bin/p1_extract) - Extract FusionEngine message contents from a binary file containing mixed data
        (e.g., interleaved RTCM and FusionEngine messages)
      - [p1_print](bin/p1_print) - Print the contents of FusionEngine messages found in a binary file to the
        console
    - `examples/` - Python example applications
      - [analyze_data.py](examples/analyze_data.py) - Generate HTML plots of vehicle trajectory, INS filter state, etc.
      - [binary_message_decode.py](examples/binary_message_decode.py) - Decode and print FusionEngine messages contained
        in a hex byte string
      - [encode_data.py](examples/encode_data.py) - Construct and serialize FusionEngine messages, and save them in a
        `*.p1log` file that can be used with the other example utilities
      - [encode_message.py](examples/encode_message.py) - Construct and serialize a single FusionEngine message, and
        print the result to the console as a hex byte string
      - [extract_imu_data.py](examples/extract_imu_data.py) - Generate a CSV file containing recorded IMU measurements
      - [extract_position_data.py](examples/extract_position_data.py) - Generate CSV and KML files detailing the vehicle
        position over time
        - This script also includes an example of time-aligning multiple message types
      - [extract_satellite_info.py](examples/extract_satellite_info.py) - Generate a CSV file containing satellite 
        azimuth/elevation and C/N0 information over time
      - [manual_message_decode.py](examples/manual_message_decode.py) - Read a `.p1log` binary file and decode the
        message headers and payloads explicitly (without the using the `FusionEngineDecoder` helper class)
      - [manual_tcp_client.py](examples/manual_tcp_client.py) - Connect to a device over TCP and decode/display messages
        in real time, decoding message headers and payloads manually (without the using the `FusionEngineDecoder` helper
        class)
      - [message_decode.py](examples/message_decode.py) - Read a `.p1log` binary file containing FusionEngine messages,
        optionally mixed with other binary data, and decode the contents using the `FusionEngineDecoder` helper class
      - [send_command.py](examples/send_command.py) - Send a command to a device over serial or TCP, and wait for a
        response
      - [serial_client.py](examples/serial_client.py) - Connect to a device over a local serial port and decode messages
        in real time to be displayed and/or logged to disk using the `FusionEngineDecoder` helper class
      - [tcp_client.py](examples/tcp_client.py) - Connect to a device over TCP and decode messages in real time to be
        displayed and/or logged to disk using the `FusionEngineDecoder` helper class
      - [udp_client.py](examples/udp_client.py) - Connect to a device over UDP and decode/display messages in real time
        - Unlike [tcp_client.py](examples/tcp_client.py), currently assumes all incoming UDP packets contain
          FusionEngine messages and does not use the `FusionEngineDecoder` helper class
    - `fusion_engine_client` - Top Python package directory
      - `analysis`
        - [analyzer.py](analysis/analyzer.py) - `Analyzer` class, used to plot data from a recorded file of FusionEngine
          messages (vehicle trajectory map, navigation engine state information, etc.)
          - This class is used by the `bin/p1_display` application
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

#### Install From PyPI

1. Install Python (3.6 or later) and pip.
2. Install the `fusione-engine-client` module, including all analysis and data processing tools:
   ```bash
   python3 -m pip install fusion-engine-client[all]
   ```
   - Note: If you wish to only install data parsing support, and do not want to install plotting and other requirements
     used by the analysis tools in `bin/`, you may omit `[all]` and run `python3 -m pip install fusion-engine-client`
3. Run any of the applications in `bin/`. For example, to plot results from a `*.p1log` file from a Point One device:
   ```bash
   p1_display /path/to/log/file_or_directory
   ```

#### Install From Source (Use In Another Python Project)

1. Install Python (3.6 or later) and pip.
2. Clone a copy of this repository:
   ```bash
   git clone https://github.com/PointOneNav/fusion-engine-client.git
   ```
3. Install the `fusione-engine-client` module, including all analysis and data processing tools:
   ```bash
   python3 -m pip install -e /path/to/fusion-engine-client[all]
   ```
   - Note the additional `-e` argument (optional), which tells `pip` to install `fusion-engine-client` as editable.
     This means that it will reference the local directory instead of copying the source code. That way, if you update
     the code (`git pull`), your Python installation will automatically use the new version.
4. Run any of the applications in `bin/`. For example, to plot results from a `*.p1log` file from a Point One device:
   ```bash
   p1_display /path/to/log/file_or_directory
   ```

#### Install From Source (Development)

1. Install Python (3.6 or later) and pip.
2. Clone a copy of this repository:
   ```bash
   git clone https://github.com/PointOneNav/fusion-engine-client.git
   ```
3. Install the Python requirements:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
4. Run any of the applications in `bin/` or the example code in `examples/`. For example, to plot results from a
   `*.p1log` file from a Point One device:
   ```bash
   python3 bin/p1_display /path/to/log/file_or_directory
   ```

Whenever possible, we strongly encourage the use of a Python [virtual environment](#using-a-python-virtual-environment).

## Examples

### Analyzing A Recorded Log And Plotting Results

> Note: `p1_display` will generate a map showing the vehicle trajectory. By default, the map will be displayed using
> freely available Open Street Map street data. In order to display satellite imagery, please request a free access
> token from https://account.mapbox.com/access-tokens, then provide that token by specifying the `--mapbox-token`
> argument, or by setting either the `MAPBOX_ACCESS_TOKEN` or `MapboxAccessToken` environment variables.

The following will generate plots for a log with ID `c25445f4e60d441dbf4af8a3571352fa`.

```bash
> python3 bin/p1_display --mapbox-token MY_MAPBOX_TOKEN /path/to/c25445f4e60d441dbf4af8a3571352fa
```

Alternatively, you can search for a log by entering the first few characters of the ID. By default, logs are assumed to
be stored in the directory `/logs`.

```bash
> python3 bin/p1_display c2544
```

Use the `--logs-base-dir` argument to search a directory other than `/logs`:

```bash
> python3 bin/p1_display --logs-base-dir /my/log/directory c2544
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
   python3 bin/p1_display /path/to/log/directory
   ```
