#include <pympav.h>

// module init function
PyMODINIT_FUNC initpympav(void) {
	import_pygame_surface();
   (void) Py_InitModule("pympav", pympavMethods);
}

/* ***** Methods *************************************************************/

// Set the export file for mplayer
static PyObject* pympav_set_exportfile(PyObject *self, PyObject *args) {
	if (!PyArg_ParseTuple(args, "s", &sharedfile))
		return (PyObject*) NULL;
	RETURN_NONE;
}

// Get the export file for mplayer
static PyObject* pympav_get_exportfile() {
	if(!sharedfile) {
		RETURN_NONE;
	}
	return Py_BuildValue("s", sharedfile);
}

// Set screenresolution
static PyObject* pympav_set_resolution(PyObject *self, PyObject *args) {

	if (!PyArg_ParseTuple(args, "iii", &width, &height, &cinema))
		return (PyObject*)NULL;

	if(init == 1) {
		goom_set_resolution(width, height, cinema);
	}

	// See http://sdldoc.csn.ul.ie/sdlcreatergbsurface.php
	SDL_Surface* s = SDL_CreateRGBSurface(0, width, height, 32, 0, 0, 0, 0);

	if (s) {
		// deallocate if there is one already
		if (pysurf) {
			Py_XDECREF(pysurf);
		}

		pysurf = (PySurfaceObject*) PySurface_New(s);
		Py_XINCREF(pysurf);
		
		if (pysurf) {
			RETURN_NONE;
		} 
		else {
			RAISE(PyExc_ValueError, "Error creating pygame surface");
		}
	}
	RAISE(PyExc_ValueError, "Error creating sdl surface");
}

// Change visualization
static PyObject* pympav_set_visual(PyObject *self, PyObject *args) {
	/* from goom/filters.h:
	#define NORMAL_MODE 0
	#define WAVE_MODE 1
	#define CRYSTAL_BALL_MODE 2
	#define SCRUNCH_MODE 3
	#define AMULETTE_MODE 4
	#define WATER_MODE 5
	#define HYPERCOS1_MODE 6
	#define HYPERCOS2_MODE 7
	*/
	int val;
	if (!PyArg_ParseTuple(args, "i", &val))
		return (PyObject*) NULL;

	// not sure about these, should perhaps 
	// take -1 as well
	if(val>8 || val<1) {
		PyErr_SetString(PyExc_ValueError, "Use values between 1 and 8");
		return (PyObject*) NULL;
	}
	else {
		FXMODE = val;
	}

	RETURN_NONE;
}

static PyObject* pympav_set_title(PyObject *self, PyObject *args) {
	if (!PyArg_ParseTuple(args, "s", &songtitle))
		return (PyObject*) NULL;

	RETURN_NONE;
}

static PyObject* pympav_set_message(PyObject *self, PyObject *args) {
	if (!PyArg_ParseTuple(args, "s", &message))
		return (PyObject*) NULL;

	RETURN_NONE;
}


// our main method for processing images
// should  return a surface no matter what in the future
static PyObject* pympav_process() {
	if(!sharedfile) {
		RAISE(PyExc_ValueError, "Export file not set");
	}
	
	if (init == 0) {
		if (data_import_init() == 0) {
			goom_init(width, height, cinema);
			goom_setAsmUse(1);
			init = 1;
		}
		else {
			data_import_clean();
			RAISE(PyExc_ValueError, "Error initializing mmap");
		}
	}

	// This probably needs to be cleaned up
	if(mmap_area->count > counter) {
		
		//printf("Missed %i sound updates", mmap_area->count-counter);
		counter = mmap_area->count;
		memcpy( data, ((void *)mmap_area) + sizeof( data_t ), 2048 );
		render_data = goom_update( data, 0, FXMODE, NULL, NULL);

		if(!render_data) {
			data_import_clean();
			RAISE(PyExc_ValueError, "Goom didn't give any result!");
		}
	}
	if(pysurf) {
		memcpy( pysurf->surf->pixels, render_data, width * height * sizeof(uint32_t) );
		return (PySurfaceObject*)pysurf;
	}
	RETURN_NONE;
}


// cleanups
static PyObject* pympav_cleanup() {
	data_import_clean();
	RETURN_NONE;
}


void data_import_clean() {

	if (init == 1) {
		goom_close();
		counter = 0;
		init = 0;
	}
	Py_XDECREF(pysurf);
}


// imports the datafile
int data_import_init() {
	fd = open(sharedfile, O_RDONLY);
	if (fd < 0) {
		return -1;
	}

	mmap_area = mmap(0, sizeof(data_t), PROT_READ, MAP_SHARED, fd, 0 );
	if (mmap_area == MAP_FAILED) {
		return -2;
	}
	mmap_area = mremap( mmap_area, sizeof( data_t ), sizeof( data_t ) + mmap_area->bs, 0 );
	return(0);
}
