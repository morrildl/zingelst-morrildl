#include <stdio.h>
#include <sys/types.h>

struct _datagram {
    u_int8_t type;
    u_int8_t f1;
} __attribute__((packed));

typedef struct _datagram datagram;

int main(int argc, char** argv) {
    datagram gram;
    FILE* file = NULL;
    char* path = NULL;

    gram.type = 1;
    gram.f1 = 7;

    if (argc < 2)
	path = "./testdump.dat";
    else
	path = argv[1];

    file = fopen(path, "w");

    fwrite(&gram, sizeof(gram), 1, file);

    return 0;
}
