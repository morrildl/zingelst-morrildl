#include <ClanLib/core.h>
#include <ClanLib/application.h>
#include <ClanLib/display.h>
#include <ClanLib/gl.h>

#define WIDTH 640
#define HEIGHT 480

class ProjectX74Mockup: public CL_ClanApplication {
public:
    virtual char *get_title();
    virtual int main(int argc, char** argv);

private:
    void init();
    void init_display();
    void init_gl();
    void init_display_lists();
    void init_textures();
    void run();
    void draw();
    void check_timers();

private:
    GLuint _wormhole, _debris, _zone, _axes;

    GLint timer;
    GLint startTime, endTime;
    GLboolean useTimer;
    GLfloat _curRotX, _curRotY, _curRotZ;
};
