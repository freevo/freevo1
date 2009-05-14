#include <Python.h>
#include <SDL.h>
#include <pygame.h>
#include <goom_core.h>

#include <config.h>
#include <unistd.h>

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


/* Local Vars */
typedef struct 
{
  int nch;
  int bs;
  unsigned long long count;
} data_t;

//SDL_Surface* surf =  NULL;
PySurfaceObject *pysurf = NULL;
data_t*   mmap_area;
int16_t   data[ 2 ][ 512 ];
uint32_t  *render_data = NULL;
unsigned long long counter = 0;

int FXMODE = -1;
int init = 0;
int width = 100;
int height = 100;
int cinema = 0;
int fd = 0;
char* sharedfile = NULL;
char* message = NULL;
char* songtitle = NULL;

/* ***** Method Declarations ***************************************************/
int data_import_init();
void data_import_clean();

static PyObject* pympav_set_exportfile(PyObject *self, PyObject *args);
static PyObject* pympav_set_resolution(PyObject *self, PyObject *args);
static PyObject* pympav_set_visual(PyObject *self, PyObject *args);
static PyObject* pympav_set_message(PyObject *self, PyObject *args);
static PyObject* pympav_set_title(PyObject *self, PyObject *args);
static PyObject* pympav_get_exportfile();
static PyObject* pympav_cleanup();
static PyObject* pympav_process();

/* ***** Python Declarations ***************************************************/
// methods defined by the module
static PyMethodDef pympavMethods[] = {

 {"set_exportfile", pympav_set_exportfile, METH_VARARGS, "Set the export file used by MPlayer"},
 {"set_visual",     pympav_set_visual,     METH_VARARGS, "Set the export file used by MPlayer"},
 {"set_resolution", pympav_set_resolution, METH_VARARGS, "Get the export file used bu MPlayer"},
 {"set_message",    pympav_set_message,    METH_VARARGS, "Get the export file used bu MPlayer"},
 {"set_title",      pympav_set_title,      METH_VARARGS, "Get the export file used bu MPlayer"},
 {"get_exportfile", pympav_get_exportfile, 0,            "Get the export file used bu MPlayer"},
 {"get_surface",    pympav_process,        0,			 "Get the export file used bu MPlayer"},
 {"quit",           pympav_cleanup,        0,            "Get the export file used bu MPlayer"},


 { NULL, NULL, 0, NULL }
};



