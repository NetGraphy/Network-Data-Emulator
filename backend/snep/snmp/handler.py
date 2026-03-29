"""SNMP packet handler — decodes requests and encodes responses.

Uses pysnmp for ASN.1 encoding/decoding of SNMP PDUs.
"""

import logging

from pysnmp.proto import api as snmp_api
from pysnmp.proto import rfc1902, rfc1905
from pyasn1.codec.ber import decoder as ber_decoder
from pyasn1.codec.ber import encoder as ber_encoder
from pyasn1.type import univ

from snep.snmp.oid_tree import build_oid_tree, find_exact_oid, find_next_oid

logger = logging.getLogger(__name__)


def handle_snmp_packet(data: bytes, device_info: dict) -> bytes | None:
    """Process an incoming SNMP packet and return a response.

    Supports SNMPv2c GET, GETNEXT, and GETBULK.
    """
    try:
        # Decode the SNMP message
        msg, _ = ber_decoder.decode(data, asn1Spec=univ.Sequence())
        if not msg:
            return None

        # Extract version
        version = int(msg[0])

        if version == 1:  # SNMPv2c (version value 1 = v2c)
            return _handle_v2c(msg, device_info)
        elif version == 0:  # SNMPv1
            return _handle_v2c(msg, device_info)  # treat similarly for basic ops
        else:
            logger.debug(f"Unsupported SNMP version: {version}")
            return None

    except Exception as e:
        logger.error(f"Error handling SNMP packet: {e}")
        return None


def _handle_v2c(msg, device_info: dict) -> bytes | None:
    """Handle SNMPv2c request."""
    try:
        community = str(msg[1])
        pdu = msg[2]

        # Validate community string
        expected_community = (device_info.get("snmp_profile") or {}).get("v2_community", "public")
        if community != expected_community:
            return None  # Silent drop per spec

        # Build OID tree from current state
        tree = build_oid_tree(
            device=device_info,
            interfaces=device_info.get("interfaces", []),
            snmp_profile=device_info.get("snmp_profile"),
        )

        # Determine PDU type from tag
        pdu_tag = pdu.tagSet

        # Extract request-id and var-binds
        request_id = int(pdu[0])
        # pdu[1] = error-status, pdu[2] = error-index
        var_binds = pdu[3]

        response_bindings = []

        # Check if this is a GETBULK (tag context-specific, constructed, 5)
        is_getbulk = pdu_tag == univ.Sequence.tagSet.clone(tagClass=0x80, tagId=5) if hasattr(pdu_tag, 'clone') else False

        # Simple approach: check the raw tag byte
        raw_tag = data_tag_from_pdu(pdu)

        if raw_tag == 0xA0:  # GET
            for vb in var_binds:
                oid = str(vb[0])
                result = find_exact_oid(tree, oid)
                if result:
                    response_bindings.append(_make_varbind(result[0], result[1], result[2]))
                else:
                    response_bindings.append(_make_no_such_instance(oid))

        elif raw_tag == 0xA1:  # GETNEXT
            for vb in var_binds:
                oid = str(vb[0])
                result = find_next_oid(tree, oid)
                if result:
                    response_bindings.append(_make_varbind(result[0], result[1], result[2]))
                else:
                    response_bindings.append(_make_end_of_mib(oid))

        elif raw_tag == 0xA5:  # GETBULK
            non_repeaters = int(pdu[1])
            max_repetitions = min(int(pdu[2]), 100)

            # Non-repeater var-binds: treat as GETNEXT
            for i in range(min(non_repeaters, len(var_binds))):
                oid = str(var_binds[i][0])
                result = find_next_oid(tree, oid)
                if result:
                    response_bindings.append(_make_varbind(result[0], result[1], result[2]))
                else:
                    response_bindings.append(_make_end_of_mib(oid))

            # Repeater var-binds
            for i in range(non_repeaters, len(var_binds)):
                current_oid = str(var_binds[i][0])
                for _ in range(max_repetitions):
                    result = find_next_oid(tree, current_oid)
                    if result:
                        response_bindings.append(_make_varbind(result[0], result[1], result[2]))
                        current_oid = result[0]
                    else:
                        response_bindings.append(_make_end_of_mib(current_oid))
                        break
        else:
            logger.debug(f"Unknown PDU tag: 0x{raw_tag:02x}")
            return None

        # Build response
        return _build_response(int(msg[0]), community, request_id, response_bindings)

    except Exception as e:
        logger.error(f"Error processing SNMPv2c: {e}")
        return None


def data_tag_from_pdu(pdu) -> int:
    """Extract the raw ASN.1 tag from a PDU object."""
    try:
        encoded = ber_encoder.encode(pdu)
        return encoded[0] if encoded else 0
    except Exception:
        return 0


def _make_varbind(oid: str, asn1_type: str, value) -> tuple:
    return (oid, asn1_type, value)


def _make_no_such_instance(oid: str) -> tuple:
    return (oid, "noSuchInstance", None)


def _make_end_of_mib(oid: str) -> tuple:
    return (oid, "endOfMibView", None)


def _build_response(version: int, community: str, request_id: int, bindings: list) -> bytes:
    """Build an SNMP response packet manually using BER encoding."""
    # Encode var-bind list
    varbind_encodings = []
    for oid_str, typ, val in bindings:
        oid_encoded = _encode_oid(oid_str)
        val_encoded = _encode_value(typ, val)
        varbind = _encode_sequence(oid_encoded + val_encoded)
        varbind_encodings.append(varbind)

    varbind_list = _encode_sequence(b"".join(varbind_encodings))

    # Response PDU (tag 0xA2)
    pdu_content = (
        _encode_integer(request_id) +  # request-id
        _encode_integer(0) +           # error-status: noError
        _encode_integer(0) +           # error-index
        varbind_list
    )
    response_pdu = _encode_tagged(0xA2, pdu_content)

    # Full message
    message = (
        _encode_integer(version) +
        _encode_octet_string(community.encode()) +
        response_pdu
    )

    return _encode_sequence(message)


def _encode_integer(value: int) -> bytes:
    """BER encode an INTEGER."""
    if value == 0:
        payload = b"\x00"
    else:
        # Handle negative and positive
        length = (value.bit_length() + 8) // 8
        payload = value.to_bytes(length, "big", signed=True)
    return b"\x02" + _encode_length(len(payload)) + payload


def _encode_octet_string(value: bytes) -> bytes:
    return b"\x04" + _encode_length(len(value)) + value


def _encode_oid(oid_str: str) -> bytes:
    """BER encode an OID."""
    parts = [int(x) for x in oid_str.split(".") if x]
    if len(parts) < 2:
        parts = parts + [0] * (2 - len(parts))

    encoded = bytes([40 * parts[0] + parts[1]])
    for part in parts[2:]:
        if part < 128:
            encoded += bytes([part])
        else:
            # Multi-byte encoding
            chunks = []
            while part > 0:
                chunks.append(part & 0x7F)
                part >>= 7
            chunks.reverse()
            for i, c in enumerate(chunks):
                if i < len(chunks) - 1:
                    encoded += bytes([c | 0x80])
                else:
                    encoded += bytes([c])

    return b"\x06" + _encode_length(len(encoded)) + encoded


def _encode_value(asn1_type: str, value) -> bytes:
    """Encode a value based on its ASN.1 type."""
    if asn1_type == "Integer32":
        return _encode_integer(int(value))
    elif asn1_type == "OctetString":
        return _encode_octet_string(str(value).encode())
    elif asn1_type == "ObjectIdentifier":
        return _encode_oid(str(value))
    elif asn1_type == "Counter32":
        val = int(value) & 0xFFFFFFFF
        payload = val.to_bytes(4, "big") if val > 0 else b"\x00"
        # Strip leading zeros but keep at least one byte
        payload = payload.lstrip(b"\x00") or b"\x00"
        # Add leading zero if high bit set (would be negative)
        if payload[0] & 0x80:
            payload = b"\x00" + payload
        return b"\x41" + _encode_length(len(payload)) + payload
    elif asn1_type == "Counter64":
        val = int(value) & 0xFFFFFFFFFFFFFFFF
        payload = val.to_bytes(8, "big")
        payload = payload.lstrip(b"\x00") or b"\x00"
        if payload[0] & 0x80:
            payload = b"\x00" + payload
        return b"\x46" + _encode_length(len(payload)) + payload
    elif asn1_type == "Gauge32":
        val = int(value) & 0xFFFFFFFF
        payload = val.to_bytes(4, "big")
        payload = payload.lstrip(b"\x00") or b"\x00"
        if payload[0] & 0x80:
            payload = b"\x00" + payload
        return b"\x42" + _encode_length(len(payload)) + payload
    elif asn1_type == "TimeTicks":
        val = int(value) & 0xFFFFFFFF
        payload = val.to_bytes(4, "big")
        payload = payload.lstrip(b"\x00") or b"\x00"
        if payload[0] & 0x80:
            payload = b"\x00" + payload
        return b"\x43" + _encode_length(len(payload)) + payload
    elif asn1_type == "noSuchInstance":
        return b"\x81\x00"
    elif asn1_type == "endOfMibView":
        return b"\x82\x00"
    else:
        return _encode_octet_string(str(value).encode())


def _encode_sequence(content: bytes) -> bytes:
    return b"\x30" + _encode_length(len(content)) + content


def _encode_tagged(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(content)) + content


def _encode_length(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    elif length < 256:
        return b"\x81" + bytes([length])
    elif length < 65536:
        return b"\x82" + length.to_bytes(2, "big")
    else:
        return b"\x83" + length.to_bytes(3, "big")
