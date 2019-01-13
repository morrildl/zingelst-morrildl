#include "gl-mockup.h"

typedef struct rot_vector {
	GLfloat x, y, z;
	GLfloat angle;
} rot_vector_t;

GLfloat radius = 20.0;
GLdouble campos[16];
GLdouble debpos[16];
GLubyte test_image[128][128][4];

#define DEBRIS_LIGHT GL_LIGHT1

ProjectX74Mockup app;
CL_ResourceManager* res = NULL;
CL_Texture* tex = NULL;

CollisionModel3D* colShip = NULL;
CollisionModel3D* colDebris = NULL;

char *ProjectX74Mockup::get_title() {
	return "ProjectX74 Primitive Mock-up";
}

int ProjectX74Mockup::main(int argc, char** argv)
{
	// Create a console window for text-output if not available
	CL_ConsoleWindow console("Console");
	console.redirect_stdio();

	colShip = new CollisionModel3D();
	colDebris = new CollisionModel3D();

	try {
		CL_SetupCore::init();
		CL_SetupGL::init();
		CL_SetupDisplay::init();

		init();
		run();

		CL_SetupDisplay::deinit();
		CL_SetupGL::deinit();
		CL_SetupCore::deinit();
	} catch (CL_Error err) {
		cout << "Exception caught: " << err.message.c_str() << endl;
		// Display console close message and wait for a key
		console.display_close_message();
	}

	return 0;
}

void ProjectX74Mockup::init() {
	init_display();
	init_gl();
	init_textures();
	init_display_lists();

	glPushMatrix();
	glLoadIdentity();
	glGetDoublev(GL_MODELVIEW_MATRIX, campos);
	glPopMatrix();

	glPushMatrix();
	glLoadIdentity();
	glGetDoublev(GL_MODELVIEW_MATRIX, debpos);
	glPopMatrix();
}

void ProjectX74Mockup::init_display() {
	CL_Display::set_videomode(WIDTH, HEIGHT, 32, false);
	CL_Display::clear_display();
	CL_Display::flip_display();	

	glViewport (0, 0, (GLsizei)WIDTH, (GLsizei)HEIGHT);
	glMatrixMode (GL_PROJECTION);
	glLoadIdentity ();
	gluPerspective(90, (GLfloat)WIDTH/(GLfloat)HEIGHT, 1.0, 1000.0);
	glMatrixMode (GL_MODELVIEW);
}
GLuint texes[1];
void ProjectX74Mockup::init_textures() {
    // load the Resource Manager, and use it to load the texture
    res = new CL_ResourceManager("gl-mockup.scr", false);
    tex = CL_Texture::load("Textures/space_tex", res);
    
    /* Generally all this is handled by the CL_Texture class. Here for
     * reference.  Yes, this works.

    // this bit loads a checkerboard texture; came from Red Book
    for (int i = 0; i < 128; ++i) {
	GLubyte c = 0;
	for (int j = 0; j < 128; ++j) {
	    c = (((i&0x8)==0)^((j&0x8)==0))*255;
	    test_image[i][j][0] = (GLubyte)c;
	    test_image[i][j][1] = (GLubyte)c;
	    test_image[i][j][2] = (GLubyte)c;
	    test_image[i][j][3] = (GLubyte)255;
	}
    }
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1); // data is byte-aligned
    glGenTextures(1, texes); // texes is array of 1 element
    glBindTexture(GL_TEXTURE_2D, texes[0]); // sets tex affected by next lines
    // linear texture scaling
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    // repeat texture across surface, vs. smearing it
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
    // blend texture w/ color of polygon, vs. "overriding" poly color
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_BLEND);

    // stuff the image data into the texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 128, 128, 0, GL_RGBA,
		 GL_UNSIGNED_BYTE, test_image);
    */

    glEnable(GL_TEXTURE_2D);
}

void ProjectX74Mockup::init_gl() {
	const GLfloat light_parms[] = { 0.1, 0.1, 0.1, 1.0 };
	
	glClearColor(0, 0, 0, 0);

	glShadeModel(GL_SMOOTH);

	glPointSize(2);
	glLineWidth(2);

	glEnable(GL_CULL_FACE);
	glCullFace(GL_BACK);

	glEnable(GL_DEPTH_TEST);

	glEnable(GL_LIGHTING);

	glEnable(GL_COLOR_MATERIAL);
	glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE);

	glEnable(DEBRIS_LIGHT);

//	glLightModelfv(GL_LIGHT_MODEL_AMBIENT, light_parms);

	glBlendFunc(GL_SRC_ALPHA,GL_ONE);						// Set The Blending Function For Translucency
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);						// This Will Clear The Background Color To Black
	glClearDepth(1.0);								// Enables Clearing Of The Depth Buffer
	glDepthFunc(GL_LESS);								// The Type Of Depth Test To Do
	glEnable(GL_DEPTH_TEST);							// Enables Depth Testing
	glShadeModel(GL_SMOOTH);							// Enables Smooth Color Shading
	glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST);

}

void ProjectX74Mockup::init_display_lists() {
	GLUquadric* quad = gluNewQuadric();
	GLUquadric* dquad = gluNewQuadric();

	// Wormhole
	_wormhole = glGenLists(3);
	glNewList(_wormhole, GL_COMPILE);
		glColor3f(1.0, 0.0, 0.0);
		gluSphere(quad, 5.0, 25, 25);
	glEndList();

	// Debris
	_debris = _wormhole + 1;
	glNewList(_debris, GL_COMPILE);
		glColor3f(1.0, 1.0, 1.0);
		gluSphere(dquad, 1.0, 15, 15);
	glEndList();

	// Background Starfield
	_zone = _wormhole + 2;

	glNewList(_zone, GL_COMPILE);
		tex->bind(); // tell ClanLib to bind the texture we loaded

	       	// this cube was wound so that it faces out: make it face in
		glFrontFace(GL_CW);

		glColor3f(0.4, 0.4, 0.4); // backgrounds should be dark

		// here we go. Note that the texture has to be wound
		// IN THE SAME DIRECTION as the surface polygon. I think.
		// Anyway this didn't work before but it works now, and I
		// think that's why.
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
		       	glVertex3f(-300.0, -300.0, -300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f(-300.0, 300.0, -300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f( 300.0, 300.0, -300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f( 300.0, -300.0, -300.0);
		glEnd();
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
			glVertex3f( 300.0, -300.0, 300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f( 300.0, 300.0, 300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f(-300.0, 300.0, 300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f(-300.0, -300.0, 300.0);
		glEnd();
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
			glVertex3f(-300.0, 300.0, -300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f(-300.0, -300.0, -300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f(-300.0, -300.0, 300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f(-300.0, 300.0, 300.0);
		glEnd();
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
			glVertex3f(300.0, 300.0, 300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f(300.0, -300.0, 300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f(300.0, -300.0, -300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f(300.0, 300.0, -300.0);
		glEnd();
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
			glVertex3f(300.0, -300.0, -300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f(300.0, -300.0, 300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f(-300.0, -300.0, 300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f(-300.0, -300.0, -300.0);
		glEnd();
		glBegin(GL_QUADS);
			glTexCoord2f(0.0, 1.0);
			glVertex3f(-300.0, 300.0, 300.0);
			glTexCoord2f(1.0, 1.0);
			glVertex3f(300.0, 300.0, 300.0);
			glTexCoord2f(1.0, 0.0);
			glVertex3f(300.0, 300.0, -300.0);
			glTexCoord2f(0.0, 0.0);
			glVertex3f(-300.0, 300.0, -300.0);
		glEnd();
		glFrontFace(GL_CCW);

		// texture of "0" means unbind textures altogether; w/o this
		// ALL subsequent glVertex3f()s get assigned the last
		// glTexCoord specified, which is BAD
		glBindTexture(GL_TEXTURE_2D, 0);
	glEndList();

	// Axes for origin
	_axes = _wormhole + 3;
	glNewList(_axes, GL_COMPILE);
		glBegin(GL_LINES);
	    		glColor3f(1.0, 1.0, 1.0);
	    		glVertex3f(0,0,0);
	    		glVertex3f(0, 10, 0);
	    		glVertex3f(0,0,0);
	    		glVertex3f(10, 0, 0);
	    		glVertex3f(0,0,0);
	    		glVertex3f(0, 0, 10);
		glEnd();
	glEndList();
}

void ProjectX74Mockup::draw() {
	GLfloat mat[4];

	// reset world
	glLoadIdentity();

	// Clear framebuffer to black
	glClear(GL_DEPTH_BUFFER_BIT|GL_COLOR_BUFFER_BIT);

	// set camera position
	glTranslatef(0.0, 0.0, -radius);
	glMultMatrixd(campos);
	
	// draw space
	glCallList(_zone);

	// Draw the wormhole at the origin
	glCallList(_wormhole);
//	glCallList(_stars);

	// Draws axis lines
	glCallList(_axes);

	// Draw some debris around the wormhole; debris glows
	glMultMatrixd(debpos);
	glTranslatef(0.0, 0.0, 20.0);

	// move this stuff into display list?
	mat[0] = 0.0f;
	mat[1] = 0.0f;
	mat[2] = 0.0f;
	mat[3] = 1.0f;
	glLightfv(DEBRIS_LIGHT, GL_POSITION, mat); // set light position
	mat[0] = 0.2f;
	mat[1] = 0.2f;
	mat[2] = 0.2f;
	mat[3] = 1.0f;
	glLightfv(DEBRIS_LIGHT, GL_AMBIENT, mat); // dim ambient component
	mat[0] = 0.9f;
	mat[1] = 0.9f;
	mat[2] = 0.0f;
	mat[3] = 1.0f;
	glLightfv(DEBRIS_LIGHT, GL_DIFFUSE, mat); // bright yellow diffuse 
	glLightfv(DEBRIS_LIGHT, GL_SPECULAR, mat); // same for specular
	glMaterialfv(GL_FRONT, GL_EMISSION, mat); // make debris "emit" too
	glCallList(_debris); // draw the debris
	mat[0] = 0.0f;
	mat[1] = 0.0f;
	mat[2] = 0.0f;
	mat[3] = 1.0f;
	glMaterialfv(GL_FRONT, GL_EMISSION, mat); // disable emission
}


void ProjectX74Mockup::run() {
	bool quit;

	do {
		CL_System::sleep(20);
		draw();

		glPushMatrix();
		glLoadIdentity();
		glRotated((1.0/20.0)*(180.0/M_PI), 1.0, 0.0, 0.0);
		glMultMatrixd(debpos);
		glGetDoublev(GL_MODELVIEW_MATRIX, debpos);
		glPopMatrix();


		CL_Display::flip_display();
		CL_System::keep_alive();

		if(CL_Keyboard::get_keycode(CL_KEY_PAGEUP)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(180/M_PI/10, 0.0, 0.0, 1.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		} 
		
		if(CL_Keyboard::get_keycode(CL_KEY_PAGEDOWN)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(-180/M_PI/10, 0.0, 0.0, 1.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		} 

		if(CL_Keyboard::get_keycode(CL_KEY_RIGHT)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(-1/radius*180/M_PI, 0.0, 1.0, 0.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		}

		if(CL_Keyboard::get_keycode(CL_KEY_LEFT)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(1/radius*180/M_PI, 0.0, 1.0, 0.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		}

		if(CL_Keyboard::get_keycode(CL_KEY_UP)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(1/radius*180/M_PI, 1.0, 0.0, 0.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		}

		if(CL_Keyboard::get_keycode(CL_KEY_DOWN)) {
			glPushMatrix();
			glLoadIdentity();
			glRotated(-1/radius*180/M_PI, 1.0, 0.0, 0.0);
			glMultMatrixd(campos);
			glGetDoublev(GL_MODELVIEW_MATRIX, campos);
			glPopMatrix();
		}

		if(CL_Keyboard::get_keycode(CL_KEY_A)) {
			radius += 1.0;
			if (radius > 150.0) radius = 150.0;
		}
		if(CL_Keyboard::get_keycode(CL_KEY_Z)) {
			radius -= 1.0;
			if(radius < 2.0) radius = 2.0;
		}

		quit = CL_Keyboard::get_keycode(CL_KEY_ESCAPE);
	} while(quit == false);
}
