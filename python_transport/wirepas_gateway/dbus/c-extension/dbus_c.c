/* Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
 *
 * See file LICENSE for full license details.
 *
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <systemd/sd-bus.h>

/** \brief  Dbus bus instance*/
static sd_bus * m_bus = NULL;

/** \brief  Callback set by Python code to be called on message reception */
static PyObject * m_message_callback = NULL;

/** \brief  Callback called when a packet is received from bus */
static int on_packet_received(sd_bus_message * m, void * userdata, sd_bus_error * ret_error)
{
    PyGILState_STATE gstate;

    int r;
    uint32_t src_addr, dst_addr, travel_time;
    uint8_t qos, src_ep, dst_ep, hop_count;
    uint64_t timestamp_ms;
    size_t size;
    const void * bytes_arr;

    /* Load all parameters */
    // clang-format off
    r = sd_bus_message_read(m,
                            "tuuyyuyy",
                            &timestamp_ms,
                            &src_addr,
                            &dst_addr,
                            &src_ep,
                            &dst_ep,
                            &travel_time,
                            &qos,
                            &hop_count);
    // clang-format on
    if (r < 0)
    {
        printf("C_extension: Cannot read parameters\n");
        return r;
    }

    r = sd_bus_message_read_array(m, 'y', &bytes_arr, &size);
    if (r < 0)
    {
        printf("C_extension: Cannot read message array\n");
        return r;
    }

    /* Call registered callback */
    if (m_message_callback != NULL)
    {
        /* Get the GIL. It is needed as wa are dealing with Python objects */
        gstate = PyGILState_Ensure();

        PyObject * arglist;
        PyObject * result;

        arglist = Py_BuildValue("(sLIIBBIBBy#)",
                                sd_bus_message_get_sender(m),
                                timestamp_ms,
                                src_addr,
                                dst_addr,
                                src_ep,
                                dst_ep,
                                travel_time,
                                qos,
                                hop_count,
                                (const char *) bytes_arr,
                                size);

        if (arglist == NULL)
        {
            PyErr_Print();
            PyGILState_Release(gstate);
            return -1;
        }

        result = PyEval_CallObject(m_message_callback, arglist);
        if (result == NULL)
        {
            PyErr_Print();
            Py_DECREF(arglist);
            PyGILState_Release(gstate);
            return -1;
        }

        Py_DECREF(arglist);
        Py_DECREF(result);

        PyGILState_Release(gstate);
    }

    return 0;
}

/**
* \brief Function to be called from Python to serve Dbus signals
*/
static PyObject * infiniteEventsLoop(PyObject * self, PyObject * args)
{
    int r;
    /* Release the GIL. It will be acquire by the callback
     * It make this thread totally independant from python code
     */
    // clang-format off
    Py_BEGIN_ALLOW_THREADS
    for (;;)
    {
        /* Process requests */
        r = sd_bus_process(m_bus, NULL);
        if (r < 0)
        {
            printf("C_extension: Cannot process request %d\n", r);
            return Py_None;
        }

        /* we processed a request, try to process another one, right-away */
        if (r > 0)
            continue;

        /* Wait for the next request to process */
        r = sd_bus_wait(m_bus, (uint64_t) -1);
        if (r < 0)
        {
            printf("C_extension: Cannot wait %d\n", r);
            return Py_None;
        }
    }
    /* Should never be called */
    Py_END_ALLOW_THREADS
    // clang-format on
}

/**
 * \brief   Function to set a callback from python
 */
static PyObject * setCallback(PyObject * self, PyObject * args)
{
    PyObject * result = NULL;
    PyObject * temp;
    int r;

    if (PyArg_ParseTuple(args, "O:set_callback", &temp))
    {
        if (!PyCallable_Check(temp))
        {
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return NULL;
        }

        Py_XINCREF(temp);               /* Add a reference to new callback */
        Py_XDECREF(m_message_callback); /* Dispose of previous callback */
        m_message_callback = temp;      /* Save new callback */

        Py_INCREF(Py_None);
        result = Py_None;
    }

    /* Create the matching rule to get all MessageReceived signals */
    char match_rule[] = "type='signal', \
                         interface='com.wirepas.sink.data1', \
                         member='MessageReceived'";

    /* Listen for message signals */
    r = sd_bus_add_match(m_bus, NULL, match_rule, on_packet_received, NULL);

    if (r < 0)
    {
        return Py_None;
    }

    return result;
}

/**
 * \brief   Interface of our C module
 */
static PyMethodDef myMethods[] = {
    {"setCallback", setCallback, METH_VARARGS, "Initialize the callback"},
    {"infiniteEventLoop", infiniteEventsLoop, METH_NOARGS, "Infinite Event loop"},
    {NULL, NULL, 0, NULL}};

/**
 * \brief   Definition of our module
 */
static struct PyModuleDef dbusCExtension = {PyModuleDef_HEAD_INIT,
                                            "transportOptimizationC",
                                            "Optimization for dbus signal "
                                            "handling",
                                            -1,
                                            myMethods,
                                            NULL,
                                            NULL,
                                            NULL,
                                            NULL};

/**
 * \brief   Initialization function of our module
 */
PyMODINIT_FUNC PyInit_dbusCExtension(void)
{
    if (!PyEval_ThreadsInitialized())
    {
        PyEval_InitThreads();
    }

    int r;
    r = sd_bus_open_system(&m_bus);
    if (r < 0)
    {
        return Py_None;
    }

    return PyModule_Create(&dbusCExtension);
}
