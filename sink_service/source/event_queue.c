#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <string.h>
#include <sys/eventfd.h>
#include <time.h>
#include <unistd.h>

#include "event_queue.h"

#define LOG_MODULE_NAME "EventQueue"
#define MAX_LOG_LEVEL INFO_LOG_LEVEL
#include "logger.h"

// Number selected to be larger than the indication queue size in c-mesh-api
#define EVENT_QUEUE_CAPACITY 64

// Number of times to retry when the queue is full
static const int PUSH_MAX_RETRIES = 3;

// How long to wait for space on each retry (nanoseconds)
static const unsigned int PUSH_RETRY_WAIT_NS = 10000000;

static event_t m_buffer[EVENT_QUEUE_CAPACITY];
static size_t m_write_idx;
static size_t m_read_idx;

static pthread_mutex_t m_lock;
static pthread_cond_t m_not_full_cond;

static int m_event_fd = -1;

static size_t get_next_write_idx_locked()
{
    return (m_write_idx + 1) % EVENT_QUEUE_CAPACITY;
}

static bool is_buffer_full_locked()
{
    return m_read_idx == get_next_write_idx_locked();
}

/**
 * \brief   Wait until queue is not full
 * \return  true on successful wait (including timeout),
 *          false on error.
 */
static bool wait_for_not_full_cond_locked()
{
    struct timespec ts;
    if (0 != clock_gettime(CLOCK_MONOTONIC, &ts))
    {
        LOGE("Could not get current time when waiting: %s\n", strerror(errno));
        return false;
    }

    static const unsigned long NS_PER_SEC = 1000000000L;
    _Static_assert(ULONG_MAX >= (NS_PER_SEC + PUSH_RETRY_WAIT_NS), "");

    unsigned long nsec = ts.tv_nsec + PUSH_RETRY_WAIT_NS;
    ts.tv_sec += nsec / NS_PER_SEC;
    ts.tv_nsec = nsec % NS_PER_SEC;

    const int ret = pthread_cond_timedwait(&m_not_full_cond, &m_lock, &ts);
    if (ret != 0 && ret != ETIMEDOUT)
    {
        LOGE("Error when waiting for not full condition: %s\n", strerror(ret));
        return false;
    }
    return true;
}

static void add_to_buffer_locked(const event_t *const event)
{
    m_buffer[m_write_idx] = *event;
    m_write_idx = get_next_write_idx_locked();
}

static void wake_eventfd()
{
    if (0 != eventfd_write(m_event_fd, 1))
    {
        LOGE("Failed to write to eventfd: %s\n", strerror(errno));
    }
}

static bool init_condition_variable()
{
    bool success = false;
    int ret;
    pthread_condattr_t attr;

    ret = pthread_condattr_init(&attr);
    if (ret != 0)
    {
        LOGE("Failed to init condattr: %s\n", strerror(ret));
        return false;
    }

    ret = pthread_condattr_setclock(&attr, CLOCK_MONOTONIC);
    if (ret != 0)
    {
        LOGE("Could not set clock type for condattr: %s\n", strerror(ret));
        success = false;
        goto destroy_condattr_and_return;
    }

    ret = pthread_cond_init(&m_not_full_cond, &attr);
    if (ret != 0)
    {
        LOGE("pthread_cond_init failed: %s\n", strerror(ret));
        success = false;
        goto destroy_condattr_and_return;
    }

    success = true;

destroy_condattr_and_return:
    ret = pthread_condattr_destroy(&attr);
    if (ret != 0)
    {
        LOGE("Could not destroy condattr: %s\n", strerror(ret));
    }

    return success;
}

static bool init_mutex()
{
    bool success = false;
    int ret;
    pthread_mutexattr_t attr;

    ret = pthread_mutexattr_init(&attr);
    if (ret != 0)
    {
        LOGE("Failed to init mutexattr: %s\n", strerror(ret));
        return false;
    }

    ret = pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK);
    if (ret != 0)
    {
        LOGE("Failed to set mutexattr: %s\n", strerror(ret));
        success = false;
        goto destroy_mutexattr_and_return;
    }

    ret = pthread_mutex_init(&m_lock, &attr);
    if (ret != 0)
    {
        LOGE("pthread_mutex_init failed: %s\n", strerror(ret));
        success = false;
        goto destroy_mutexattr_and_return;
    }

    success = true;

destroy_mutexattr_and_return:
    ret = pthread_mutexattr_destroy(&attr);
    if (ret != 0)
    {
        LOGE("Could not destroy mutexattr: %s\n", strerror(ret));
    }

    return success;
}

bool EventQueue_Init(void)
{
    if (!init_mutex())
    {
        LOGE("Failed to init mutex\n");
        return false;
    }

    if (!init_condition_variable())
    {
        LOGE("Failed to init condition variable\n");
        goto error1;
    }

    m_event_fd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
    if (m_event_fd < 0)
    {
        LOGE("Failed to create eventfd: %s\n", strerror(errno));
        goto error2;
    }

    m_write_idx = 0;
    m_read_idx = 0;

    return true;

error2:
    pthread_cond_destroy(&m_not_full_cond);
error1:
    pthread_mutex_destroy(&m_lock);
    return false;
}

void EventQueue_Close(void)
{
    if (m_read_idx != m_write_idx)
    {
        LOGW("Queue is not empty when closing\n");
    }

    if (m_event_fd >= 0)
    {
        if (0 != close(m_event_fd))
        {
            LOGE("Failed to close eventfd: %s\n", strerror(errno));
        }
        m_event_fd = -1;
    }

    int ret = pthread_cond_destroy(&m_not_full_cond);
    if (ret != 0)
    {
        LOGE("Failed to destroy condvar: %s\n", strerror(ret));
    }
    ret = pthread_mutex_destroy(&m_lock);
    if (ret != 0)
    {
        LOGE("Failed to destroy mutex: %s\n", strerror(ret));
    }
}

int EventQueue_get_fd(void)
{
    return m_event_fd;
}

bool EventQueue_Push(const event_t *const event)
{
    if (!event)
    {
        LOGE("Cannot add null event to the queue\n");
        return false;
    }

    int ret = pthread_mutex_lock(&m_lock);
    if (ret != 0)
    {
        LOGE("Could not lock mutex when pushing: %s\n", strerror(ret));
        return false;
    }

    for (int attempt = 0; attempt < PUSH_MAX_RETRIES; attempt++)
    {
        if (is_buffer_full_locked())
        {
            if (!wait_for_not_full_cond_locked())
            {
                // Error when waiting; unlock mutex and return.
                break;
            }
        }
        else
        {
            add_to_buffer_locked(event);
            ret = pthread_mutex_unlock(&m_lock);
            if (ret != 0)
            {
                LOGE("Could not unlock mutex after adding to buffer: %s\n", strerror(ret));
            }
            LOGD("Added event with type: %d\n", event->type);

            // Return true even if writing to eventfd fails because event was
            // added to the queue.
            wake_eventfd();
            return true;
        }
    }

    ret = pthread_mutex_unlock(&m_lock);
    if (ret != 0)
    {
        LOGE("Could not unlock mutex after pushing failed: %s\n", strerror(ret));
    }
    LOGE("Event queue full after %d retries, dropping event (type=%d)\n",
         PUSH_MAX_RETRIES, event->type);
    return false;
}

bool EventQueue_Pop(event_t *const event)
{
    if (!event)
    {
        return false;
    }

    int ret = pthread_mutex_lock(&m_lock);
    if (ret != 0)
    {
        LOGE("Could not lock mutex when popping: %s\n", strerror(ret));
        return false;
    }

    const bool is_buffer_empty = (m_read_idx == m_write_idx);
    if (!is_buffer_empty)
    {
        *event = m_buffer[m_read_idx];
        m_read_idx = (m_read_idx + 1) % EVENT_QUEUE_CAPACITY;
        LOGD("Popped event with type: %d\n", event->type);

        ret = pthread_cond_signal(&m_not_full_cond);
        if (ret != 0)
        {
            LOGE("Could not send condition signal after popping: %s\n", strerror(ret));
        }
    }

    ret = pthread_mutex_unlock(&m_lock);
    if (ret != 0)
    {
        LOGE("Could not unlock mutex after popping: %s\n", strerror(ret));
    }

    return !is_buffer_empty;
}

