#include <Python.h>
#include <SDL.h>
#include <pygame.h>
#include <goom/goom.h>

#include "config.h"
#include "fastmemcpy.h"
#include "cpudetect.h"

#include <getopt.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>


// a couple of handy macros
#define RAISE(x,y) (PyErr_SetString((x), (y)), (PyObject*)NULL)
#define RETURN_NONE return (Py_INCREF(Py_None), Py_None);

#define INC(x) { Py_XDECREF(x); }
#define DEC(x) { Py_XINCREF(x); }


/* Local Vars */
typedef struct 
{
  int nch;
  int bs;
  unsigned long long count;
} data_t;

SDL_Surface *surf = NULL;
data_t *mmap_area;
int16_t data[2][512];
uint32_t *render_data = NULL;
unsigned long long counter = 0;

PluginInfo *goomInfo = NULL;

int FXMODE = -1;
int init = 0;
int width = 100;
int height = 100;
int fd = 0;
float fps = 0;
char *sharedfile = 0;
char *message = 0;
char *songtitle = 0;

/* ***** Method Declarations ***************************************************/
int data_import_init(void);
void data_import_clean(void);
int set_resolution(void);

static PyObject *pygoom_set_exportfile(PyObject *self, PyObject *args);
static PyObject *pygoom_get_exportfile(PyObject *self, PyObject *args);
static PyObject *pygoom_set_resolution(PyObject *self, PyObject *args);
static PyObject *pygoom_get_resolution(PyObject *self, PyObject *args);
static PyObject *pygoom_set_visual(PyObject *self, PyObject *args);
static PyObject *pygoom_get_visual(PyObject *self, PyObject *args);
static PyObject *pygoom_set_message(PyObject *self, PyObject *args);
static PyObject *pygoom_get_message(PyObject *self, PyObject *args);
static PyObject *pygoom_set_title(PyObject *self, PyObject *args);
static PyObject *pygoom_get_title(PyObject *self, PyObject *args);
static PyObject *pygoom_set_fps(PyObject *self, PyObject *args);
static PyObject *pygoom_get_fps(PyObject *self, PyObject *args);
static PyObject *pygoom_process(PyObject *self, PyObject *args);
static PyObject *pygoom_cleanup(PyObject *self, PyObject *args);

/* ***** Python Declarations ***************************************************/
// methods defined by the module
static PyMethodDef pygoomMethods[] = {

 {"set_exportfile", pygoom_set_exportfile, METH_VARARGS, "Set the export file used by MPlayer"},
 {"get_exportfile", pygoom_get_exportfile, METH_NOARGS,  "Get the export file used by MPlayer"},
 {"set_resolution", pygoom_set_resolution, METH_VARARGS, "Set the resolution, width and height"},
 {"get_resolution", pygoom_get_resolution, METH_NOARGS,  "Get the resolution, width and height"},
 {"set_visual",     pygoom_set_visual,     METH_VARARGS, "Set the visualization effect"},
 {"get_visual",     pygoom_get_visual,     METH_NOARGS,  "Get the visualization effect"},
 {"set_message",    pygoom_set_message,    METH_VARARGS, "Set the message text"},
 {"get_message",    pygoom_get_message,    METH_NOARGS,  "Get the message text"},
 {"set_fps",        pygoom_set_fps,        METH_VARARGS, "Set the frames per second"},
 {"get_fps",        pygoom_get_fps,        METH_NOARGS,  "Get the frames per second"},
 {"set_title",      pygoom_set_title,      METH_VARARGS, "Set the song title"},
 {"get_title",      pygoom_get_title,      METH_NOARGS,  "Set the song title"},
 {"get_surface",    pygoom_process,        METH_NOARGS,  "Process main loop, get the surface"},
 {"quit",           pygoom_cleanup,        METH_NOARGS,  "Clean up and quit"},
 { NULL, NULL, 0, NULL }
};



