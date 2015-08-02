Schildergenerator
=================

A web page to quickly create and print signs using a common design.
Especially useful for events.

Dependencies
------------

  * python-flask python-genshi 
  * python-pythonmagick + graphicsmagick
  * pdflatex latex-beamer
  * libapache2-mod-wsgi for production use (or [anything capable of running WSGI apps](http://wsgi.readthedocs.org/en/latest/servers.html) really…)


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

