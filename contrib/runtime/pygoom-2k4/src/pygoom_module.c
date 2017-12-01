/*
 * -----------------------------------------------------------------------
 * This is a module binding goom-2k4 to Python
 * -----------------------------------------------------------------------
 * $Id$
 * -----------------------------------------------------------------------
 * Freevo - A Home Theater PC framework
 * Copyright (C) 2002 Krister Lagerstrom, et al.
 * Please see the file freevo/Docs/CREDITS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * -----------------------------------------------------------------------
 */

/* PyGoom objects */

#include <Python.h>
#include <structmember.h>

#include <SDL.h>
#include <pygame.h>
#include <goom/goom.h>

#include "config.h"
//#include "fastmemcpy.h"
//#include "cpudetect.h"

#include <getopt.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>

#define HEXVERSION 0x000201f0L
#define VERSION "0.2.1"

static PyObject *ErrorObject;
static int debug = 0;

typedef struct data_t {
	int nch;
	int bs;
	unsigned long long count;
} data_t;

typedef struct PyGoomObject {
	PyObject_HEAD
	PyObject *exportfile;
	PyObject *songtitle;
	PyObject *message;
	int fxmode;
	int init;
	int width;
	int height;
	double fps;

	PluginInfo *goominfo;

	SDL_Surface *surface;
	uint32_t *render_data;

	int16_t data[2][512];
	int mmap_fd;
	data_t *mmap_area;
	unsigned long long mmap_area_count;

} PyGoomObject;

static PyTypeObject PyGoomType;

#define PyGoomObject_Check(v)   (Py_TYPE(v) == &PyGoomType)

/* PyGoom methods */

PyDoc_STRVAR(pygoom_resolution_doc, "resolution(width, height) -> None\n"
			 "set the resolution to width and height");

static PyObject *
PyGoom_resolution(PyGoomObject *self, PyObject *args)
{
	if (!PyArg_ParseTuple(args, "ii:resolution", &self->width, &self->height)) {
		return NULL;
	}
    if (self->surface) {
		SDL_FreeSurface(self->surface);
    }
    goom_set_resolution(self->goominfo, self->width, self->height);
    self->surface = SDL_CreateRGBSurface(0, self->width, self->height, 32, 0, 0, 0, 0);
    if (! self->surface) {
        return RAISE(PyExc_ValueError, "Cannot create surface");
    }

	Py_INCREF(Py_None);
	return Py_None;
}

PyDoc_STRVAR(pygoom_process_doc, "process() -> None\n"
			 "process a frame");

static PyObject *
PyGoom_process(PyGoomObject *self, PyObject *args)
{
    int i, j;
    gint16 data[2][512];
    char *songtitle, *message;

    if (debug >= 4) {
        printf("*"); fflush(stdout);
    }
	if (!PyArg_ParseTuple(args, ":process")) {
		return NULL;
	}

    if (!self->surface) {
        return RAISE(PyExc_ValueError, "Surface not initialized");
    }

    if (self->mmap_area) {
        if (self->mmap_area->count != self->mmap_area_count) {
            if (debug >= 4) {
                printf("mmap_area->count=%llu, self->mmap_area_count=%llu\n", 
                    self->mmap_area->count, self->mmap_area_count);
            }
            if (debug >= 3) {
                printf("memcpy(data=%p, self->mmap_area=%p + sizeof(data_t)=%u, sizeof(gint16)=%u * 2 * 512)\n",
                    data, self->mmap_area, (unsigned)sizeof(data_t), (unsigned)sizeof(gint16));
            }
            self->mmap_area_count = self->mmap_area->count;
            //memcpy(data, self->mmap_area + sizeof(data_t), sizeof(gint16) * 2 * 512);
            memcpy(data, self->mmap_area + sizeof(data_t), sizeof(gint16) * 1 * 512);
        }
    }
    else {
        // generate some random data if export file is NULL
        for (i = 0; i < 2; i++) {
            for (j = 0; j < 512; j++) {
                data[i][j] = (gint16)rand();
            }
        }
    }

    songtitle = PyString_AsString(self->songtitle);
    if (songtitle && strcmp(songtitle, "") == 0) {
        songtitle = 0;
    } 
    message = PyString_AsString(self->message);
    if (message && strcmp(message, "") == 0) {
        message = 0;
    }
    if (songtitle || message) {
        if (debug >= 1) {
            printf ("songtitle=%s, message=%s\n", songtitle, message);
        }
    }
    
    self->render_data = goom_update(self->goominfo, data, self->fxmode, self->fps, songtitle, message);

    self->songtitle = PyString_FromString("");
    self->message = PyString_FromString("");

    if (!self->render_data) {
        return RAISE(PyExc_ValueError, "Goom didn't give any result!");
    }

    memcpy(self->surface->pixels, self->render_data, self->width * self->height * sizeof(uint32_t));
    // fast memcpy make very little differenc so lets not use it
    //fast_memcpy(self->surface->pixels, self->render_data, self->width * self->height * sizeof(uint32_t));

    return Py_BuildValue("O", PySurface_New(self->surface));
}

static PyMethodDef PyGoom_methods[] = {
	{ "resolution", (PyCFunction)PyGoom_resolution, METH_VARARGS, pygoom_resolution_doc },
	{ "process",    (PyCFunction)PyGoom_process,    METH_VARARGS, pygoom_process_doc    },
	{ NULL,         NULL }                      /* sentinel */
};

static PyMemberDef PyGoom_members[] = {
	{ NULL }  /* Sentinel */
};

static PyObject *
PyGoom_getexport(PyGoomObject *self, void *closure)
{
    if (debug >= 3) {
        printf("PyGoom_getexport()\n"); fflush(stdout);
    }
	Py_INCREF(self->exportfile);
	return self->exportfile;
}

static PyObject *
PyGoom_getsurface(PyGoomObject *self, void *closure)
{
    if (debug >= 3) {
        printf("PyGoom_getsurface()\n"); fflush(stdout);
    }
    return Py_BuildValue("O", PySurface_New(self->surface));
}

static PyObject *
PyGoom_getsongtitle(PyGoomObject *self, void *closure)
{
    if (debug >= 3) {
        printf("PyGoom_getsongtitle()\n"); fflush(stdout);
    }
	Py_INCREF(self->songtitle);
	return self->songtitle;
}

PyDoc_STRVAR(PyGoom_songtitle_doc, "Set the song title\n"
			 "The song title is displayed in the middle of the surface");

static int
PyGoom_setsongtitle(PyGoomObject *self, PyObject *value, void *closure)
{
    if (debug >= 1) {
        printf("PyGoom_setsongtitle(value=%p)\n", value); fflush(stdout);
    }
	if (!PyString_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The title attribute value must be a string");
		return -1;
	}

	Py_DECREF(self->songtitle);
	Py_INCREF(value);
	self->songtitle = value;
    if (debug >= 2) {
        printf("self->songtitle=%s\n", PyString_AsString(self->songtitle));
    }

	return 0;
}

static PyObject *
PyGoom_getmessage(PyGoomObject *self, void *closure)
{
    if (debug >= 3) {
        printf("PyGoom_getmessage()\n"); fflush(stdout);
    }
	Py_INCREF(self->message);
	return self->message;
}

PyDoc_STRVAR(PyGoom_message_doc, "Set the message text\n"
			 "The message scrolls up from the bottom for about 370 frames");

static int
PyGoom_setmessage(PyGoomObject *self, PyObject *value, void *closure)
{
    if (debug >= 1) {
        printf("PyGoom_setmessage(value=%p)\n", value); fflush(stdout);
    }
	if (value == NULL) {
		PyErr_SetString(PyExc_TypeError, "Cannot delete the message attribute");
		return -1;
	}

	if (!PyString_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The message attribute value must be a string");
		return -1;
	}

	Py_DECREF(self->message);
	Py_INCREF(value);
	self->message = value;
    if (debug >= 2) {
        printf("self->message=%s\n", PyString_AsString(self->message));
    }

	return 0;
}

PyDoc_STRVAR(PyGoom_fxmode_doc, "Set the effects mode\n"
			 "An integer in the range -1 to 9");

static PyObject *
PyGoom_getfxmode(PyGoomObject *self, void *closure)
{
    if (debug >= 3) {
        printf("PyGoom_getfxmode()\n"); fflush(stdout);
    }
	return PyInt_FromLong(self->fxmode);
}

static int
PyGoom_setfxmode(PyGoomObject *self, PyObject *value, void *closure)
{
    if (debug >= 1) {
        printf("PyGoom_setfxmode(value=%p)\n", value); fflush(stdout);
    }
	if (!PyNumber_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The fxmode attribute value must be a number");
		return -1;
	}

	self->fxmode = PyInt_AsLong(value);

	return 0;
}

PyDoc_STRVAR(PyGoom_fps_doc, "display frames per second\n"
			 "This is called once per process loop");

static PyObject *
PyGoom_getfps(PyGoomObject *self, void *closure)
{
	return PyFloat_FromDouble(self->fps);
}

static int
PyGoom_setfps(PyGoomObject *self, PyObject *value, void *closure)
{
	if (!PyNumber_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The fps attribute value must be a number");
		return -1;
	}

	self->fps = PyFloat_AsDouble(value);

	return 0;
}

static PyGetSetDef PyGoom_getseters[] = {
	{ "exportfile",(getter)PyGoom_getexport,    NULL,                        "export file name",   NULL },
	{ "surface",   (getter)PyGoom_getsurface,   NULL,                        "surface",            NULL },
	{ "songtitle", (getter)PyGoom_getsongtitle, (setter)PyGoom_setsongtitle, PyGoom_songtitle_doc, NULL },
	{ "message",   (getter)PyGoom_getmessage,   (setter)PyGoom_setmessage,   PyGoom_message_doc,   NULL },
	{ "fxmode",    (getter)PyGoom_getfxmode,    (setter)PyGoom_setfxmode,    PyGoom_fxmode_doc,    NULL },
	{ "fps",       (getter)PyGoom_getfps,       (setter)PyGoom_setfps,       PyGoom_fps_doc,       NULL },
	{ NULL }  /* Sentinel */
};

static PyObject *
PyGoom_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	PyGoomObject *self;

    if (debug >= 1) {
        printf("PyGoom_new\n"); fflush(stdout);
    }
	self = (PyGoomObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->exportfile = PyString_FromString("");
		self->songtitle = PyString_FromString("");
		self->message = PyString_FromString("");
		self->width = 0;
		self->height = 0;
		self->fxmode = 0;
		self->fps = -1;
        self->mmap_fd = -1;
        self->mmap_area = 0;
        self->mmap_area_count = 0;
        self->render_data = 0;
	}

	return (PyObject *)self;
}


static int
PyGoom_init(PyGoomObject *self, PyObject *args, PyObject *kwds)
{
	PyObject    *exportfile = NULL, *songtitle = NULL, *tmp;
    char *mmapfile = NULL;

	static char *kwlist[] = { "width", "height", "export", "songtitle", "fxmode", NULL };

    if (debug >= 1) {
        printf("PyGoom_init\n"); fflush(stdout);
    }
	if (!PyArg_ParseTupleAndKeywords(args, kwds, "iiO|Si", kwlist,
	      &self->width, &self->height, &exportfile, &songtitle, &self->fxmode)) {
		return -1;
	}

	if (exportfile) {
		tmp = self->exportfile;
		Py_INCREF(exportfile);
		self->exportfile = exportfile;
		Py_XDECREF(tmp);
	}

	if (songtitle) {
		tmp = self->songtitle;
		Py_INCREF(songtitle);
		self->songtitle = songtitle;
		Py_XDECREF(tmp);
	}

	self->goominfo = goom_init(self->width, self->height);
    self->surface = SDL_CreateRGBSurface(0, self->width, self->height, 32, 0, 0, 0, 0);
    if (! self->surface) {
        PyErr_SetString(PyExc_ValueError, "Cannot create surface");
        return -1;
    }
    mmapfile = PyString_AsString(self->exportfile);
    if (strcmp(mmapfile, "") != 0) {
        self->mmap_fd = open(mmapfile, O_RDONLY);
        if (self->mmap_fd < 0) {
            PyErr_Format(PyExc_IOError, "export file '%s' not found", mmapfile);
            return -1;
        }
        self->mmap_area = mmap(0, sizeof(data_t), PROT_READ, MAP_SHARED, self->mmap_fd, 0);
        if (self->mmap_area == MAP_FAILED) {
            PyErr_Format(PyExc_IOError, "export file '%s' cannot be mapped", mmapfile);
            return -1;
        }
        if (debug >= 1) {
            printf("sizeof(data_t)=%u sizeof(gint16)=%u\n", (unsigned)sizeof(data_t), (unsigned)sizeof(gint16));
            printf("nch=%d, bs=%d, count=%llu\n", self->mmap_area->nch, self->mmap_area->bs, self->mmap_area->count);
        }
        self->mmap_area = mremap(self->mmap_area, sizeof(data_t), sizeof(data_t) + self->mmap_area->bs, 0);
        if (! self->mmap_area) {
            PyErr_Format(PyExc_IOError, "export file '%s' cannot be re-mapped", mmapfile);
            return -1;
        }
    }
	return 0;
}

static void
PyGoom_dealloc(PyGoomObject *self)
{
    if (debug >= 1) {
        printf("PyGoom_dealloc\n"); fflush(stdout);
    }
	Py_XDECREF(self->exportfile);
	Py_XDECREF(self->songtitle);
	Py_XDECREF(self->message);

	if (self->mmap_area) {
		munmap(self->mmap_area, sizeof(data_t));
	}
    if (self->mmap_fd >= 0) {
        close(self->mmap_fd);
    }
	if (self->surface) {
		SDL_FreeSurface(self->surface);
	}
    if (self->goominfo) {
        goom_close(self->goominfo);
    }

	PyObject_Del(self);
}

static PyTypeObject PyGoomType = {
	/* The ob_type field must be initialized in the module init function
	 * to be portable to Windows without using C++. */
	PyObject_HEAD_INIT(NULL)
	0,                                                  /*ob_size*/
	"pygoom.PyGoom",                                    /*tp_name*/
	sizeof(PyGoomObject),                               /*tp_basicsize*/
	0,                                                  /*tp_itemsize*/
	/* methods */
	(destructor)PyGoom_dealloc,                         /*tp_dealloc*/
	0,                                                  /*tp_print*/
	0,                                                  /*tp_getattr*/
	0,                                                  /*tp_setattr*/
	0,                                                  /*tp_compare*/
	0,                                                  /*tp_repr*/
	0,                                                  /*tp_as_number*/
	0,                                                  /*tp_as_sequence*/
	0,                                                  /*tp_as_mapping*/
	0,                                                  /*tp_hash*/
	0,                                                  /*tp_call*/
	0,                                                  /*tp_str*/
	0,                                                  /*tp_getattro*/
	0,                                                  /*tp_setattro*/
	0,                                                  /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,                                 /*tp_flags*/
	0,                                                  /*tp_doc*/
	0,                                                  /*tp_traverse*/
	0,                                                  /*tp_clear*/
	0,                                                  /*tp_richcompare*/
	0,                                                  /*tp_weaklistoffset*/
	0,                                                  /*tp_iter*/
	0,                                                  /*tp_iternext*/
	PyGoom_methods,                                     /*tp_methods*/
	PyGoom_members,                                     /*tp_members*/
	PyGoom_getseters,                                   /*tp_getset*/
	0,                                                  /*tp_base*/
	0,                                                  /*tp_dict*/
	0,                                                  /*tp_descr_get*/
	0,                                                  /*tp_descr_set*/
	0,                                                  /*tp_dictoffset*/
	(initproc)PyGoom_init,                              /*tp_init*/
	0,                                                  /*tp_alloc*/
	PyGoom_new,                                         /*tp_new*/
	0,                                                  /*tp_free*/
	0,                                                  /*tp_is_gc*/
};
/* --------------------------------------------------------------------- */

/* Function of no arguments returning new PyGoom object */

/* List of functions defined in the module */
static PyObject *
pygoom_debug(PyObject *self, PyObject *args)
{
	if (!PyArg_ParseTuple(args, "i:debug", &debug)) {
		return NULL;
	}
    printf("debugging set to %d\n", debug);

	Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef pygoom_methods[] = {
	{ "debug", pygoom_debug, METH_VARARGS, PyDoc_STR("debug(n) -> None") },
	{ NULL,  NULL }                             /* sentinel */
};

PyDoc_STRVAR(module_doc, "This is a Python interface to goom-2k4");

static void updateModuleDict(PyObject *module)
{
	PyObject *dict;

	dict = PyModule_GetDict(module);
	PyDict_SetItemString(dict, "VERSION", PyString_FromString(VERSION));
	PyDict_SetItemString(dict, "HEXVERSION", PyInt_FromLong(HEXVERSION));
}

/* Initialization function for the module (*must* be called initpygoom) */

PyMODINIT_FUNC
initpygoom(void)
{
	PyObject *m;

    import_pygame_surface();
	/* Due to cross platform compiler issues the slots must be filled
	 * here. It's required for portability to Windows without requiring
	 * C++. */

	/* Finalize the type object including setting type of the new type
	 * object; doing it here is required for portability, too. */
	if (PyType_Ready(&PyGoomType) < 0) {
		return;
	}

	/* Create the module and add the functions */
	m = Py_InitModule3("pygoom", pygoom_methods, module_doc);
	if (m == NULL) {
		return;
	}

	updateModuleDict(m);

	Py_INCREF((PyObject *)&PyGoomType);
	PyModule_AddObject(m, "PyGoom", (PyObject *)&PyGoomType);


	/* Add some symbolic constants to the module */
	if (ErrorObject == NULL) {
		ErrorObject = PyErr_NewException("pygoom.error", NULL, NULL);
		if (ErrorObject == NULL) {
			return;
		}
	}
	Py_INCREF(ErrorObject);
	PyModule_AddObject(m, "error", ErrorObject);
}
