Schildergenerator
=================

A web service to quickly create and print signs using a common design.
Especially useful for events.

You might find it useful in the following scenarios:
  
  * You need to set up an event where visitors need signs to point them around.
  * You often need to change some signs in your organization.
  * You're bored in the Fachschaftsbüro.

What you need:

  * A printer on premise.
  * Some kind of server, preferrably running a flavor of Linux, capable of printing
    on said printer via lpd. A RaspberryPi would suffice, even if it's slow.
  * Web clients of any type being able to connect to said server.
  * The knowledge to modify a LaTeX template to fit your organizations design.

After you put in the initial work of setting this up, you'll have a service 
where everyone on your team can quickly create a new sign as soon as they see a
need for it (provided they've got a mobile web client) just by typing a headline
and some text, selecting or uploading an image -- and by the time they arrive at
the printer, the sign is already printed and ready to be posted on the wall. All
while heeding the event's design.

> This script frees the event organisators of the responsibility to pre-think
> all the details of sign-making. Instead, this part can simply be delegated to 
> the helpers who are setting up the event by showing them the web frontend of
> this tool.


Dependencies
------------

  * python-flask, python-genshi 
  * python-pythonmagick, graphicsmagick
  * pdflatex, latex-beamer
  * libapache2-mod-wsgi for production use 
    (or [anything capable of running WSGI apps](http://wsgi.readthedocs.org/en/latest/servers.html) really…)


Download
--------

       $ git clone https://github.com/kif-ev/schildergenerator.git


Config
------

  * for all uses: copy config.py.example to config.py and edit it to your needs.
  * for production use: copy schildergen.wsgi.example to schildergen.wsgi and edit it.


Running in test/debug mode
--------------------------

You need to have the config done. Then you could just start the server in debug mode:

       $ python schilder.py


Webserver Deployment
--------------------

See http://flask.pocoo.org/docs/0.10/deploying/ for all deployment options.

Example config for the Apache Webserver, following http://flask.pocoo.org/docs/deploying/mod_wsgi/:

        LoadModule wsgi_module /usr/lib/apache2/modules/mod_wsgi.so
        WSGIRestrictStdout Off

        <VirtualHost *:443>
                ServerAdmin admin@server.test
                DocumentRoot /path/to/schildergen
                ServerName server.name.org
                AddDefaultCharset utf-8
                ErrorLog /path/to/log
                CustomLog /path/to/log
                
                SSLEngine on
                SSLCertificateFile /path/to/www.example.com.cert
                SSLCertificateKeyFile /path/to/www.example.com.key

                WSGIDaemonProcess schildergen user=www-data group=www-data threads=2
                WSGIScriptAlias / /path/to/schildergen.wsgi

                <Directory /path/to/schildergen.wsgi>
                        AllowOverride All
                        WSGIProcessGroup schildergen
                        WSGIApplicationGroup %{GLOBAL}
                        WSGIScriptReloading On
                        Order deny,allow
                        Allow from all
                </Directory>
        </VirtualHost>

Contributors
============

  * Dave Kliczbor <dave@fsinfo.cs.tu-dortmund.de>
  * Lars Beckers <larsb@fsmpi.rwth-aachen.de>
  * Moritz Holtz <moritz@fsmpi.rwth-aachen.de>
  * Konstantin Kotenko <konstantin@fsmpi.rwth-aachen.de>

Image Sources
-------------

  * USNPS pictograms taken from the Open Icon Library: http://sourceforge.net/projects/openiconlibrary/

