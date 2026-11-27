#ifndef EVENT_TYPES_H_
#define EVENT_TYPES_H_

#include <stdint.h>

// Max payload size for a data packet (MAX_FULL_PACKET_SIZE from c-mesh-api)
#define EVENT_DATA_MAX_PAYLOAD 1500

/*
 * Note: Data types here match the ones used by sd-bus for the MessageReceived
 * signal. num_bytes is uint16_t to save space.
 */
_Static_assert(UINT16_MAX >= EVENT_DATA_MAX_PAYLOAD, "");
typedef struct
{
    uint64_t timestamp_ms;
    uint32_t src_addr;
    uint32_t dst_addr;
    uint32_t travel_time;
    uint16_t num_bytes;
    uint8_t qos;
    uint8_t src_ep;
    uint8_t dst_ep;
    uint8_t hop_count;
    uint8_t payload[EVENT_DATA_MAX_PAYLOAD];
} event_data_received_t;

typedef struct
{
    uint8_t status;
} event_stack_status_t;

typedef enum
{
    EVENT_TYPE_DATA_RECEIVED,
    EVENT_TYPE_STACK_STATUS,
} event_type_e;

typedef struct
{
    event_type_e type;
    union
    {
        event_data_received_t data_received;
        event_stack_status_t stack_status;
    } event;
} event_t;

#endif // EVENT_TYPES_H_

