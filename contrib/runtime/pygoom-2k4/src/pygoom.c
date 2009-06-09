#include <pygoom.h>

// module init function
PyMODINIT_FUNC initpygoom(void)
{
    import_pygame_surface();
    Py_InitModule("pygoom", pygoomMethods);
#ifdef VERBOSE
    CpuCaps caps;
    GetCpuCaps(&caps);
    printf ("cpuType = %d\n", caps.cpuType);
    printf ("cpuModel = %d\n", caps.cpuModel);
    printf ("cpuStepping = %d\n", caps.cpuStepping);
    printf ("hasMMX = %d\n", caps.hasMMX);
    printf ("hasMMX2 = %d\n", caps.hasMMX2);
    printf ("has3DNow = %d\n", caps.has3DNow);
    printf ("has3DNowExt = %d\n", caps.has3DNowExt);
    printf ("hasSSE = %d\n", caps.hasSSE);
    printf ("hasSSE2 = %d\n", caps.hasSSE2);
    printf ("isX86 = %d\n", caps.isX86);
    printf ("cl_size = %u\n", caps.cl_size); /* size of cache line */
    printf ("hasAltiVec = %d\n", caps.hasAltiVec);
    printf ("hasTSC = %d\n", caps.hasTSC);
#endif
}

/* ***** Methods *************************************************************/

// Set the export file for mplayer
static PyObject* pygoom_set_exportfile(PyObject *self, PyObject *args)
{
    const char *value;

    if (sharedfile) {
        free(sharedfile);
        sharedfile = 0;
    }
    if (!PyArg_ParseTuple(args, "s", &value)) {
        return (PyObject*)NULL;
    }
    if (value) {
        sharedfile = strdup(value);
    }
    RETURN_NONE;
}

// Get the export file for mplayer
static PyObject* pygoom_get_exportfile(PyObject *self, PyObject *args)
{
    return Py_BuildValue("s", sharedfile);
}

// Set screenresolution
static PyObject* pygoom_set_resolution(PyObject *self, PyObject *args)
{
    int cinema = 0;

    if (!PyArg_ParseTuple(args, "iii", &width, &height, &cinema)) {
        return NULL;
    }

    if (init == 1) {
        goom_set_resolution(goomInfo, width, height);
        surf = SDL_CreateRGBSurface(0, width, height, 32, 0, 0, 0, 0);
        if (!surf) {
            return RAISE(PyExc_ValueError, "Surface error");
        }
    }
    RETURN_NONE;
}

// Get the screen resolution
static PyObject* pygoom_get_resolution(PyObject *self, PyObject *args)
{
    return Py_BuildValue("(ii)", width, height);
}

// Change visualization
static PyObject* pygoom_set_visual(PyObject *self, PyObject *args)
{
    int val;

    if (!PyArg_ParseTuple(args, "i", &val)) {
        return NULL;
    }

    /* from src/goom_filters.h
    NORMAL_MODE 0
    WAVE_MODE 1
    CRYSTAL_BALL_MODE 2
    SCRUNCH_MODE 3
    AMULETTE_MODE 4
    WATER_MODE 5
    HYPERCOS1_MODE 6
    HYPERCOS2_MODE 7
    YONLY_MODE 8
    SPEEDWAY_MODE 9
    */

    if (val < -1 || val > 9) {
        PyErr_SetString(PyExc_ValueError, "Use values between -1 and 9");
        return NULL;
    }
    else {
        FXMODE = val;
    }

    RETURN_NONE;
}

// Get the visualization mode
static PyObject* pygoom_get_visual(PyObject *self, PyObject *args)
{
    return Py_BuildValue("i", FXMODE);
}

// Get the song title
static PyObject* pygoom_set_title(PyObject *self, PyObject *args)
{
    const char *value;

    if (songtitle) {
        free(songtitle);
        songtitle = 0;
    }
    if (!PyArg_ParseTuple(args, "z", &value)) {
        return (PyObject*)NULL;
    }
    if (value) {
        songtitle = strdup(value);
    }
    RETURN_NONE;
}

// Get the song title
static PyObject* pygoom_get_title(PyObject *self, PyObject *args)
{
    return Py_BuildValue("z", songtitle);
}

// Set the message
static PyObject* pygoom_set_message(PyObject *self, PyObject *args)
{
    const char *value;

    if (message) {
        free(message);
        message = 0;
    }
    if (!PyArg_ParseTuple(args, "z", &value)) {
        return (PyObject*)NULL;
    }
    if (value) {
        message = strdup(value);
    }
    RETURN_NONE;
}

// Get the message
static PyObject* pygoom_get_message(PyObject *self, PyObject *args)
{
    return Py_BuildValue("z", message);
}

// Set the frames per second
static PyObject* pygoom_set_fps(PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "f", &fps)) {
        return NULL;
    }

    RETURN_NONE;
}

// Get the frames per second
static PyObject* pygoom_get_fps(PyObject *self, PyObject *args)
{
    return Py_BuildValue("f", fps);
}

// our main method for processing images
// should  return a surface no matter what in the future
static PyObject* pygoom_process(PyObject *self, PyObject *args)
{
    if (init == 0) {
        if (data_import_init() == 0) {
            goomInfo = goom_init(width, height);
            init     = 1;
        }
        else {
            data_import_clean();
            return RAISE(PyExc_ValueError, "Error initializing mmap");
        }
    }

    if (mmap_area->count > counter || mmap_area->count < counter) {
        counter = mmap_area->count;

#ifdef USE_FASTMEMCPY
        fast_memcpy(data, mmap_area + sizeof(data_t), 2048);
#else
        memcpy(data, mmap_area + sizeof(data_t), 2048);
#endif
#ifdef VERBOSE
        printf ("goomInfo=%p, data=%p, FXMODE=%d, fps=%.1f, songtitle=%s, message=%s\n", 
            goomInfo, data, FXMODE, fps, songtitle, message);
#endif
        render_data = goom_update(goomInfo, data, FXMODE, fps, songtitle, message);

        if (!render_data) {
            data_import_clean();
            return RAISE(PyExc_ValueError, "Goom didn't give any result!");
        }

        if (!surf) {
            return RAISE(PyExc_ValueError, "Resolution not set");
        }

#ifdef USE_FASTMEMCPY
        fast_memcpy(surf->pixels, render_data, width * height * sizeof(uint32_t));
#else
        memcpy(surf->pixels, render_data, width * height * sizeof(uint32_t));
#endif
    }
    return Py_BuildValue("O", PySurface_New(surf));
}

// cleanups
static PyObject* pygoom_cleanup(PyObject *self, PyObject *args)
{
    if (sharedfile) {
        free(sharedfile);
        sharedfile = 0;
    }
    if (songtitle) {
        free(songtitle);
        songtitle = 0;
    }
    if (message) {
        free(message);
        message = 0;
    }
    data_import_clean();
    RETURN_NONE;
}

/**
 * $(fclass)
 *
 * 
 */
void data_import_clean()
{
    if (init == 1) {
        goom_close(goomInfo);
        counter = 0;
        init    = 0;
    }
}

// imports the datafile
int data_import_init()
{
    fd = open(sharedfile, O_RDONLY);

    if (fd < 0) {
        return -1;
    }

    mmap_area = mmap(0, sizeof(data_t), PROT_READ, MAP_SHARED, fd, 0);
    if (!mmap_area) {
        return -2;
    }
    mmap_area = mremap(mmap_area, sizeof(data_t), sizeof(data_t) + mmap_area->bs, 0);
    surf      = SDL_CreateRGBSurface(0, width, height, 32, 0, 0, 0, 0);

    if (surf) {
        return 0;
    }

    return -3;
}

