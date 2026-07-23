#ifndef EVENT_QUEUE_H_
#define EVENT_QUEUE_H_

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <wpc.h>

// Max payload size for a data packet (MAX_FULL_PACKET_SIZE from c-mesh-api)
#define EVENT_DATA_MAX_PAYLOAD 1500

typedef enum
{
    EVENT_TYPE_DATA_RECEIVED,
    EVENT_TYPE_STACK_STATUS,
} event_type_e;

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

typedef struct
{
    event_type_e type;
    union
    {
        event_data_received_t data_received;
        event_stack_status_t stack_status;
    } event;
} event_t;

/**
 * \brief   Initialize the event queue
 * \return  true on success, false on error
 */
bool EventQueue_Init(void);

/**
 * \brief   Close and clean up the event queue
 */
void EventQueue_Close(void);

/**
 * \brief   Get the eventfd which is written when events are queued.
 *
 *          The main loop should poll this file descriptor and drain the queue
 *          by calling EventQueue_Pop when readable. The eventfd should not be
 *          read directly, it is done in EventQueue_Pop.
 * \return  The eventfd file descriptor, or -1 if not initialized.
 */
int EventQueue_get_fd(void);

/**
 * \brief   Add an event to the queue
 *
 *          If the queue is full, retries a few times with short waits.
 * \param   event
 *          The event to enqueue
 * \return  true if the event was enqueued, false if dropped.
 */
bool EventQueue_Push(const event_t *const event);

/**
 * \brief       Pop an event from the queue.
 *
 *              If the queue is empty after the operation, drains the eventfd
 *              (see EventQueue_get_fd).
 * \param[out]  event
 *              The dequeued event
 * \return      true if an event was dequeued,
 *              false otherwise (error or queue was empty)
 */
bool EventQueue_Pop(event_t *event);

#endif // EVENT_QUEUE_H_

