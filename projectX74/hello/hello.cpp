#include <ClanLib/core.h>
#include <ClanLib/application.h>
#include <ClanLib/display.h>
#include <ClanLib/ttf.h>

#define WIDTH	640
#define HEIGHT	480

class Hello : public CL_ClanApplication {
    public:
	virtual char* get_title() { return "Hello, ClanLib!"; }

	virtual int main(int argc, char** argv) {
	    CL_ConsoleWindow* console = NULL;
	    int xpos1 = 0, xpos2 = 0, ypos1 = 0, ypos2 = 0;
	    int xdir1 = 1, xdir2 = 1, ydir1 = 1, ydir2 = 1;
	    float r = 0.3, g = 0.3, b = 0.3;

	    try {
		console = new CL_ConsoleWindow("Console");
		console->redirect_stdio();

		CL_SetupCore::init();
		CL_SetupDisplay::init();
		CL_SetupTTF::init();
		CL_Display::set_videomode(WIDTH, HEIGHT, 16, false);
		CL_ResourceManager* resources =
		    new CL_ResourceManager("fonts.scr", false);
		CL_Font* font = CL_Font::load("Fonts/foo_bar", resources);

		std::cout << "Hello, ClanLib!" << std::endl;

		font->change_size(30);
		font->change_colour(0, 0, 0, 0xFF);

		srand(time(NULL));
		xpos1 = (int)((double)rand()*WIDTH/(double)RAND_MAX);
		xpos2 = (int)((double)rand()*WIDTH/(double)RAND_MAX);
		ypos1 = (int)((double)rand()*HEIGHT/(double)RAND_MAX);
		ypos2 = (int)((double)rand()*HEIGHT/(double)RAND_MAX);

		std::cout << xpos1 << std::endl;
		std::cout << xpos2 << std::endl;
		std::cout << ypos1 << std::endl;
		std::cout << ypos2 << std::endl;
		std::cout << rand() << std::endl;
		

		while (CL_Keyboard::get_keycode(CL_KEY_ESCAPE) == false) {
		    CL_Display::clear_display();

		    xpos1 = xpos1 + xdir1;
		    ypos1 = ypos1 + ydir1;

		    if ((ypos1 >= HEIGHT) || (ypos1 <= 0)) {
			ydir1 *= -1;
		    }
		    if ((xpos1 >= HEIGHT) || (xpos1 <= 0)) {
			xdir1 *= -1;
		    }

		    xpos2 = xpos2 + xdir2;
		    ypos2 = ypos2 + ydir2;

		    if ((ypos2 >= HEIGHT) || (ypos2 <= 0)) {
			ydir2 *= -1;
		    }
		    if ((xpos2 >= HEIGHT) || (xpos2 <= 0)) {
			xdir2 *= -1;
		    }

		    /*1
		    r = r + 0.1;
		    b = b + 0.1;
		    g = g + 0.1;

		    r = (r > 1.0) ? 0.3 : r;
		    g = (g > 1.0) ? 0.3 : g;
		    b = (b > 1.0) ? 0.3 : b;
		    */

		    CL_Display::draw_line(xpos1, ypos1, xpos2, ypos2,
				    	  r, g, b, 1.0);

		    CL_Display::flip_display();

		    //CL_System::sleep(50);
		    CL_System::keep_alive();
		}

		delete console;
		delete font;
		delete resources;

		CL_SetupTTF::deinit();
		CL_SetupDisplay::deinit();
		CL_SetupCore::deinit();
	    } catch(CL_Error err) {
		std::cout << "Error: " << err.message.c_str() << std::endl;
		console->display_close_message();
	    }

	    return 0;
	}
} foo;
