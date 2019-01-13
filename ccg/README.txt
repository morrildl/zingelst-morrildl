You need the Apache FOP JARs. They are not in CVS, so copy them into the
lib directory:
    lib/fop.jar
    lib/avalon.jar
    lib/batik.jar

Yeah yeah, I know, local JARs. But it was either that, or try and munge the
build.xml file in such a way that the paths work both on Unix and NT, and on
different systems.  This was easier.
