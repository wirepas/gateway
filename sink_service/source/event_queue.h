#ifndef EVENT_QUEUE_H_
#define EVENT_QUEUE_H_

#include <stdbool.h>
#include "event_types.h"

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

