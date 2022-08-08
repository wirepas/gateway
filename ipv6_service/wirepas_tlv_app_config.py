# Copied from wirepas_mqtt_library/wirepas_tlv_app_config_helper.py
import logging

class WirepasTLVAppConfig:
    wirepas_tlv_header = b'\xF6\x7E'

    def __init__(self, entries=None):
        if entries == None:
            entries = dict()
        self.entries = entries

    def add_entry(self, entry_type, entry_value):
        # Adding an entry for a type already existing, will remove
        # previous one
        try:
            if self.entries[entry_type] == entry_value:
                # Same value already
                return False
        except KeyError:
            # Key doesn't exist
            pass
        
        self.entries[entry_type] = entry_value
        return True

    def remove_entry(self, entry_type):
        try:
            del self.entries[entry_type]
            return True
        except KeyError:
            logging.warning("Trying to remove a key that doesn't exist")
            return False

    def _generate_app_config(entries):
        """ Generate app config from a dic of type -> value
        """
        # Create the app_config holder with correct header
        app_config = bytearray(WirepasTLVAppConfig.wirepas_tlv_header)

        # Add number of TLV entries
        app_config.append(entries.__len__())
        
        # Add one by one the entries
        for t, v in entries.items():
            l = v.__len__()
            logging.debug("Adding: t = 0x%x, l = %d" % (t, l))
            
            if (t > 0xffff):
                raise ValueError("Type must be feat on 2 bytes: 0x%x", t)

            # Add Type LSByte
            app_config.append(t & 0xff)
            if (t >= 256):
                # Long type, set MSBit of length to 1
                app_config.append(l | 0x80)
                app_config.append(t >> 8 & 0xff)
            else:
                app_config.append(l)

            # Add the value
            app_config += v

        logging.debug("Gen app_config is %s" % app_config.hex())
        return app_config

    def _parse_app_config(app_config):
        # Check that it starts with right key
        if app_config[0:2] != WirepasTLVAppConfig.wirepas_tlv_header:
            # It is not an app config following Wirepas TLV format
            logging.debug("Not a Wirepas TLV app config")
            return None

        # Check number of TLV entries
        tlv_entries = app_config[2]
        logging.debug("Number of tlv entries: %d" % tlv_entries)

        app_config = app_config[3:]

        entries={} 
        # Iterate the different entries
        while (tlv_entries > 0):
            value_offset = 2
            # Check type first
            t = app_config[0]
            if app_config[1] >= 0x80:
                # We have a long type
                t += app_config[2] * 256
                value_offset += 1
            
            l = app_config[1] & ~0x80
            logging.debug("t = 0x%x, l = %d," % (t, l))
            entries[t] = app_config[value_offset:value_offset+l]
            
            app_config = app_config[value_offset+l:]
            tlv_entries-=1

        return entries

    @classmethod
    def from_value(cls, app_config):
        d = WirepasTLVAppConfig._parse_app_config(app_config)
        if d == None:
            raise ValueError("Not a Wirepas TLV app_config format")
        return cls(d)

    @property
    def value(self):
        return WirepasTLVAppConfig._generate_app_config(self.entries)

    def __str__(self):
        str = "{"
        for t, v in self.entries.items():
            if str.__len__() > 2:
                str+=", "
            str+= "0x%x:%s" % (t, v.hex())

        str += "}"
        return str

