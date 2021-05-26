--------------------------------------------------------------------------------
-- @brief Point One FusionEngine Protocol Wireshark packet dissector.
--
-- To use, install in `~/.local/lib/wireshark/plugins/`, then reload the
-- Wireshark plugins (Analyze -> Reload Lua Plugins) or restart Wireshark. We
-- recommend using a symlink so that the plugin stays up to date with new
-- changes. For example:
-- ```
-- > mkdir -p ~/.local/lib/wireshark/plugins
-- > ln -s /path/to/p1_fusion_engine_dissector.lua ~/.local/lib/wireshark/plugins/
-- ```
--------------------------------------------------------------------------------

-- Protocol definition.
local fe_proto = Proto("FusionEngine", "Point One FusionEngine Protocol")

-- MessageType
local message_type_to_name = {}
message_type_to_name[0] = "Invalid"

message_type_to_name[10000] = "PoseMessage"
message_type_to_name[10001] = "GNSSInfoMessage"
message_type_to_name[10002] = "GNSSSatelliteMessage"
message_type_to_name[10003] = "PoseAuxMessage"

message_type_to_name[11000] = "IMUMeasurement"

message_type_to_name[12000] = "ros::PoseMessage"
message_type_to_name[12010] = "ros::GPSFixMessage"
message_type_to_name[12011] = "ros::IMUMessage"

-- MessageHeader
local SYNC0 = 0x2E -- '.'
local SYNC1 = 0x31 -- '1'

local MESSAGE_HEADER_SIZE = 24
local PAYLOAD_SIZE_OFFSET = 16

local pf_header = ProtoField.new("Header", "fusionengine.header", ftypes.NONE)
local pf_preamble = ProtoField.new("Preamble", "fusionengine.header.preamble", ftypes.STRING)
local pf_crc = ProtoField.new("CRC", "fusionengine.header.event_id", ftypes.UINT32, nil, base.HEX)
local pf_version = ProtoField.new("Protocol Version", "fusionengine.header.version", ftypes.UINT8)
local pf_message_type = ProtoField.new("Message Type", "fusionengine.header.message_type", ftypes.UINT16)
local pf_message_name = ProtoField.new("Message Name", "fusionengine.header.message_name", ftypes.STRING)
local pf_sequence_num = ProtoField.new("Sequence Number", "fusionengine.header.sequence_num", ftypes.UINT32)
local pf_payload_size = ProtoField.new("Payload Size", "fusionengine.header.payload_size", ftypes.UINT32)
local pf_source_id = ProtoField.new("Source ID", "fusionengine.header.source_id", ftypes.UINT32)

-- Generic message payload byte array.
local pf_payload = ProtoField.new("Payload", "fusionengine.payload", ftypes.BYTES)

-- Add all field definitions to the protocol.
fe_proto.fields = {
   -- MessageHeader
   pf_header,
   pf_preamble,
   pf_crc,
   pf_version,
   pf_message_type,
   pf_message_name,
   pf_sequence_num,
   pf_payload_size,
   pf_source_id,
   pf_payload,
}

-- Define extractable fields to be used in dissect functions.
local message_type_field = Field.new("fusionengine.header.message_type")
local payload_size_field = Field.new("fusionengine.header.payload_size")

--------------------------------------------------------------------------------
-- @brief Helper function for extracting the value of a specified field.
--------------------------------------------------------------------------------
local function getValue(field, index)
   local tbl = { field() }
   return tbl[#tbl]()
end

--------------------------------------------------------------------------------
-- @brief Dissect the message header.
--
-- @return The offset into the data buffer at which the contents end.
-- @return The message name (or message type value if unknown).
--------------------------------------------------------------------------------
dissectHeader = function(tvbuf, pktinfo, tree, offset, message_index)
   local header = tree:add(pf_header, tvbuf:range(offset, MESSAGE_HEADER_SIZE))

   -- Preamble
   header:add(pf_preamble, tvbuf:range(offset, 2))
   offset = offset + 2

   -- Reserved
   offset = offset + 2

   -- CRC
   header:add_le(pf_crc, tvbuf:range(offset, 4))
   offset = offset + 4

   -- Version
   header:add_le(pf_version, tvbuf:range(offset, 1))
   offset = offset + 1

   -- Reserved
   offset = offset + 1

   -- Message type
   header:add_le(pf_message_type, tvbuf:range(offset, 2))
   offset = offset + 2

   local message_type = getValue(message_type_field, message_index)
   local message_name = message_type_to_name[message_type]

   if message_name ~= nil then
      header:add(pf_message_name, tvbuf:range(offset - 2, 2), message_name)
   else
      header:add(pf_message_name, tvbuf:range(offset - 2, 2), "<unknown>")
      message_name = string.format("%d", message_type)
   end

   -- Sequence number
   header:add_le(pf_sequence_num, tvbuf:range(offset, 4))
   offset = offset + 4

   -- Payload size
   header:add_le(pf_payload_size, tvbuf:range(offset, 4))
   offset = offset + 4

   -- Source ID
   header:add_le(pf_source_id, tvbuf:range(offset, 4))
   offset = offset + 4

   -- Set packet display info.
   pktinfo.cols.protocol:set("P1 FusionEngine")
   tree:append_text(string.format(" (%s) [%u bytes]", message_name, MESSAGE_HEADER_SIZE + payload_size))

   return offset, message_name
end

--------------------------------------------------------------------------------
-- @brief Check for a complete message.
--
-- @return The message size (in bytes), or -N where N is the number of bytes
--         needed to complete the message.
-- @return The payload size (in bytes).
--------------------------------------------------------------------------------
checkMessageSize = function(tvbuf, offset)
   -- Get the total (non-consumed) packet length.
   local bytes_available = tvbuf:len() - offset

   -- If the packet was cutoff due to Wireshark a size limit, we can't use it.
   if bytes_available ~= tvbuf:reported_length_remaining(offset) then
      return 0, nil
   end

   -- Do we have enough data to decode the header?
   if bytes_available < MESSAGE_HEADER_SIZE then
      return -DESEGMENT_ONE_MORE_SEGMENT, nil
   end

   -- Do we have enough data to decode the payload?
   payload_size_range = tvbuf:range(offset + 16, 4)
   local payload_size = payload_size_range:le_uint()
   local message_size = MESSAGE_HEADER_SIZE + payload_size

   if bytes_available < message_size then
      return -(message_size - bytes_available), nil
   end

   return message_size, payload_size
end

--------------------------------------------------------------------------------
-- @brief Dissect a single FusionEngine message.
--
-- @return The offset into the data buffer at which the contents end, or -N if
--         more bytes are needed to complete the message, where N is the number
--         of required bytes.
-- @return The message name (or message type value if unknown).
--------------------------------------------------------------------------------
dissectMessage = function(tvbuf, pktinfo, root, offset, message_index)
   -- See if we have a complete message. If the message is incomplete (<0),
   -- return the number of bytes to finish it.
   message_size, payload_size = checkMessageSize(tvbuf, offset)
   if message_size < 0 then
      return message_size, nil
   end

   -- Add an entry for a single message and dissect the header and payload.
   local tree = root:add(fe_proto, tvbuf:range(offset, message_size))

   -- Dissect the header.
   payload_offset, message_name = dissectHeader(tvbuf, pktinfo, tree, offset, message_index)

   if message_name == "PoseMessage" then
      -- dissectPoseMessage(tvbuf, pktinfo, tree, payload_offset, message_index)
      -- TODO
      tree:add(pf_payload, tvbuf:range(payload_offset, payload_size))
   else
      -- Unhandled message - display the payload as a byte array.
      tree:add(pf_payload, tvbuf:range(payload_offset, payload_size))
   end

   return offset + message_size, message_name
end

--------------------------------------------------------------------------------
-- @brief Dissect incoming TCP data.
--
-- A TCP data buffer may contain one or more FusionEngine messages.
--
-- @return The offset into the data buffer at which the contents end.
--------------------------------------------------------------------------------
function fe_proto.dissector(tvbuf, pktinfo, root)
    -- Process all complete messages in the TCP data.
    local packet_length = tvbuf:len()
    local bytes_consumed = 0
    local total_messages = 0
    local message_count = {}
    while bytes_consumed < packet_length do
        local message_length = 0
        local start_offset = bytes_consumed

        -- Try to dissect a complete message. If this returns >0, we found a
        -- message. If it returns <0, we need more data to complete the message.
        end_offset, message_name = dissectMessage(tvbuf, pktinfo, root, start_offset, total_messages)
        if end_offset > 0 then
           bytes_consumed = (end_offset - start_offset)
           start_offset = end_offset

           total_messages = total_messages + 1

           if(message_count[message_name] == nil) then
              message_count[message_name] = 0
           end
           message_count[message_name] = message_count[message_name] + 1
        elseif end_offset == 0 then
           -- This shouldn't happen normally. Return 0 to indicate a protocol
           -- error/this packet isn't for us.
           return 0
        else
           -- Set the offset to the start of the incomplete message, and the
           -- length to the number of bytes required to complete it.
           pktinfo.desegment_offset = start_offset
           pktinfo.desegment_len = -end_offset
           bytes_consumed = packet_length
           break
        end

    end

    if(total_messages > 0) then
       local s = ""
       if(total_messages > 1) then
	  s = "s"
       end

       pktinfo.cols.info:append(string.format(" %d message%s: [", total_messages, s))
       local count_string = ""
       for key, value in pairs(message_count) do
	  if(count_string ~= "") then
	     count_string = count_string .. ", "
	  end
	  count_string = count_string .. string.format("%d %s", value, key)
       end
       pktinfo.cols.info:append(count_string .. "]")
    end

    return bytes_consumed
end

DissectorTable.get("tcp.port"):add(30201, fe_proto)
