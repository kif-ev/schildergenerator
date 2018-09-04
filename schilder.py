#!/usr/bin/env python2
# -*- encoding: utf8 -*-

from flask import Flask, flash, session, redirect, url_for, escape, request, Response, Markup
import sys
import os
import os.path
import glob
from genshi.template import TemplateLoader
from genshi.template.text import NewTextTemplate
from flaskext.genshi import Genshi, render_response
from werkzeug.utils import secure_filename
from collections import defaultdict
from docutils.core import publish_parts
import warnings
import shutil
import subprocess
from subprocess import CalledProcessError, STDOUT
import PythonMagick
import json
import tempfile
import config

app = Flask(__name__)
app.config.update(
    UPLOAD_FOLDER = config.uploaddir,
    PROPAGATE_EXCEPTIONS = True,
    MAX_CONTENT_LENGTH = 8388608L
)
app.secret_key = config.app_secret
genshi = Genshi(app)
genshi.extensions['html'] = 'html5'


def check_output(*popenargs, **kwargs):
    # Copied from py2.7s subprocess module
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode != 0:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=output)
        #raise Exception(output)
    return output

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in config.allowed_extensions

def load_data(filename):
    with open(os.path.join(config.datadir, filename), 'r') as infile:
        formdata = defaultdict(str, json.load(infile))
        formdata['filename'] = filename
        if len(formdata['markup']) < 1:
            formdata['markup'] = 'latex'
        return formdata
        
def save_data(formdata, outfilename):
    with open(os.path.join(config.datadir, outfilename), 'w') as outfile:
        json.dump(formdata, outfile)
    
def run_pdflatex(context, outputfilename, overwrite=True):
    if not context.has_key('textemplate'):
        context['textemplate'] = "text-image-quer.tex"
    genshitex = TemplateLoader([config.textemplatedir])
    template = genshitex.load(
        context['textemplate'], cls=NewTextTemplate, encoding='utf8')
    if not overwrite and os.path.isfile(outputfilename) and os.path.getmtime(template.filepath) < os.path.getmtime(outputfilename):
        return
    if context['markup'] == 'rst':
        context['text'] = publish_parts(context['text'], writer_name='latex')['body']
        #context['headline'] = publish_parts(context['headline'], writer_name='latex')['body']
    tmpdir = tempfile.mkdtemp(dir=config.tmpdir)
    
    #image
    if context.has_key('img') and context['img'] and context['img'] != '__none':
        try:
            source = os.path.join(config.imagedir, context['img'])
            
            filename = os.path.split(context['img'])[1]
            context['img'] = filename
            
            #create destinationfolder if not exist
            dest =  os.path.join(tmpdir,filename )

            shutil.copy(source, dest)
            
            
        except:
            raise IOError("COULD NOT COPY IMAGE")
    else:
        # print "MEH No image"
        pass
    
    #logo   
    if context.has_key('logo') and context['logo'] and context['logo'] != '__none':
        try:
            source = os.path.join(config.logodir, context['logo'])
            
            filename = os.path.split(context['logo'])[1]
            context['logo'] = filename
            
            #create destinationfolder if not exist
            dest =  os.path.join(tmpdir,filename )

            shutil.copy(source, dest)
            
            
        except:
            raise IOError("COULD NOT COPY LOGO")
    else:
        # print "MEH No logo"
        pass
    
    
    tmptexfile = os.path.join(tmpdir, 'output.tex')
    tmppdffile = os.path.join(tmpdir, 'output.pdf')
    with open(tmptexfile, 'w') as texfile:
        texfile.write(template.generate(form=context).render(encoding='utf8'))
    cwd = os.getcwd()
    os.chdir(tmpdir)
    os.symlink(config.texsupportdir, os.path.join(tmpdir, 'support'))
    try:
        texlog = check_output(
            ['pdflatex', '--halt-on-error', tmptexfile], stderr=STDOUT)
    except CalledProcessError as e:
        if overwrite:
            try:
                flash(Markup("<p>PDFLaTeX Output:</p><pre>%s</pre>" % e.output), 'log')
            except:
                print(e.output)
        raise SyntaxWarning("PDFLaTeX bailed out")
    finally:
        os.chdir(cwd)
    if overwrite:
        try:
            flash(Markup("<p>PDFLaTeX Output:</p><pre>%s</pre>" % texlog), 'log')
        except:
            print(texlog)
    shutil.copy(tmppdffile, outputfilename)
    shutil.rmtree(tmpdir)

def save_and_convert_image_upload(inputname,folder):
    imgfile = request.files[inputname]
    if imgfile:
        print 'debug#1'
        if not allowed_file(imgfile.filename):
            raise UserWarning(
                "Uploaded image is not in the list of allowed file types.")
        
        filename = os.path.join(
            config.uploaddir, secure_filename(imgfile.filename))
        imgfile.save(filename)
        img = PythonMagick.Image(filename)
        imgname = os.path.splitext(secure_filename(imgfile.filename))[
            0].replace('.', '_') + '.png'
        savedfilename = os.path.join(folder, imgname)
        print 'debug#end-2'
        print savedfilename
        print folder
        img.write(str(savedfilename))
        print 'debug#end-1'
        os.remove(filename)
        print 'debug#end'
        return imgname
    print "no file"
    return None



def make_thumb(filename, maxgeometry):

    thumbpath = filename + '.' + str(maxgeometry)
    if not os.path.exists(thumbpath) or os.path.getmtime(filename) > os.path.getmtime(thumbpath):
        img = PythonMagick.Image(str(filename))
        img.transform("%sx%s" % (maxgeometry, maxgeometry))
        img.quality(90)
        img.write(str("png:%s" % thumbpath))
    print filename , " #2 "
    return thumbpath



@app.route('/')
def index(**kwargs):
    data = defaultdict(str)
    data.update(**kwargs)
    filelist = glob.glob(config.datadir + '/*.schild')
    data['files'] = [unicode(os.path.basename(f)) for f in sorted(filelist)]
    return render_response('index.html', data)


@app.route('/edit')
def edit(**kwargs):
    data = defaultdict(str)
    data.update(**kwargs)
    #imagelist = sorted(glob.glob(config.imagedir + '/*.png')) #TODO
    #data['images'] = [os.path.basename(f) for f in imagelist] #TODO
    data['images'] = generateImagelist()
    data['logos'] = generateImagelist(config.logodir)
    data['standartLogo'] = config.standartLogo
    data['standartFooter'] = config.standartFooter
    templatelist = glob.glob(config.textemplatedir + '/*.tex')
    data['templates'] = [unicode(os.path.basename(f))
                         for f in sorted(templatelist)]
    data['imageextensions'] = config.allowed_extensions
    return render_response('edit.html', data)


@app.route('/edit/<filename>')
def edit_one(filename):
    return edit(form=load_data(filename))


@app.route('/create', methods=['POST'])
def create():
    if request.method == 'POST':
        formdata = defaultdict(str, request.form.to_dict(flat=True))
        for a in ('headline', 'text'):
            formdata[a] = unicode(formdata[a])
        try:
            
            #Bild upload
            imagedir = config.imagedir
            category = formdata['img--cat'] 
            if not category:
                category = 'none'
                
            #benuterdefinierte /neue kategorie
            if(category == "__user"):
                category = formdata['usercat']
                if not category:
                    category = 'none'

                
            
             #kategorie/ordner festlegen
            if(category != 'none'):
                category = category.replace(' ','_').replace('/','_')
                imagedir = os.path.join(imagedir , category)
                if not os.path.exists(imagedir):
                    os.makedirs(imagedir)
           
            imgpath = save_and_convert_image_upload('imgupload',imagedir)
            if imgpath is not None:
                if(category != 'none'):
                    formdata['img'] =  os.path.join(category,imgpath)
                else:
                    formdata['img'] =  imgpath
            
        
            #logo upload
            logopath = save_and_convert_image_upload('logoupload',config.logodir)
            if logopath is not None:
                formdata['logo'] = logopath
            
            outfilename = secure_filename(formdata['headline'][:16]) + str(hash(formdata['headline'] + formdata[
                'text'] + os.path.splitext(formdata['textemplate'])[0] + os.path.splitext(formdata['img'])[0] + formdata['footer']) )+ '.schild'
            if formdata['reusefilename']:
                outfilename = secure_filename(formdata['filename'])
            outpdfname = outfilename + '.pdf'
            formdata['filename'] = outfilename
            formdata['pdfname'] = outpdfname
            save_data(formdata, outfilename)
            run_pdflatex(formdata, os.path.join(config.pdfdir, outpdfname))
            try:
                flash(Markup(u"""PDF created and data saved. You might create another one. Here's a preview. Click to print.<br/>
                                <a href="%s"><img src="%s"/></a>""" %
                         (url_for('schild', filename=outfilename), url_for(
                             'pdfthumbnail', pdfname=outpdfname, maxgeometry=200))
                         ))
            except:
                print("%s created" % outpdfname)
        except Exception as e:
            try:
                flash(u"Could not create pdf or save data: %s" % str(e), 'error')
            except:
                print("Could not create pdf or save data: %s" % str(e))

        data = {'form': formdata}
       # imagelist = glob.glob(config.imagedir + '/*.png')  #TODO unterordner hinzufügen
       # data['images'] = [os.path.basename(f) for f in imagelist] #TODO nach unterordnern kategorieisieren
        data['images'] = generateImagelist()
        templatelist = glob.glob(config.textemplatedir + '/*.tex')
        data['templates'] = [os.path.basename(f) for f in sorted(templatelist)]
        try:
            return redirect(url_for('edit_one', filename=outfilename))
        except:
            pass
    try:
        flash("No POST data. You've been redirected to the edit page.", 'warning')
        return redirect(url_for('edit'))
    except:
        pass


@app.route('/schild/<filename>')
def schild(filename):
    return render_response('schild.html', {'filename': filename, 'printer': [unicode(f) for f in sorted(config.printers.keys())]})


@app.route('/printout', methods=['POST'])
def printout():
    filename = os.path.join(
        config.pdfdir, secure_filename(request.form['filename']))
    printer = config.printers[request.form['printer']]
    copies = int(request.form['copies']) or 0
    if copies > 0 and copies <= 6:
        try:
            lprout = check_output(['lpr', '-H', str(config.printserver), '-P', str(
                printer), '-#', str(copies)] + config.lproptions + [filename], stderr=STDOUT)
            flash(u'Schild wurde zum Drucker geschickt!')
        except CalledProcessError as e:
            flash(Markup("<p>Could not print:</p><pre>%s</pre>" % e.output), 'error')
    else:
        flash(u'Ungültige Anzahl Kopien!')
    return redirect(url_for('index'))

def delete_file(filename):
    try:
        os.unlink(os.path.join(config.datadir, filename))
        for f in glob.glob(os.path.join(config.pdfdir, filename + '.pdf*')):
            os.unlink(f)
        flash(u"Schild %s wurde gelöscht" % filename)
        return redirect(url_for('index'))
    except:
        flash(u"Schild %s konnte nicht gelöscht werden." % filename, 'error')
        return redirect(url_for('schild', filename=filename))


@app.route('/delete', methods=['POST'])
def delete():
    return delete_file(secure_filename(request.form['filename']))

@app.route('/deletelist', methods=['POST'])
def deletelist():
    for filename in request.form.getlist('filenames'):
        delete_file(secure_filename(filename))
    return redirect(url_for('index'))

@app.route('/image/<imgname>')
def image(imgname):
    imgpath = os.path.join(config.imagedir, secure_filename(imgname))
    if os.path.exists(imgpath):
        with open(imgpath, 'r') as imgfile:
            return Response(imgfile.read(), mimetype="image/png")
    else:
        return "Meh"  # redirect(url_for('index'))


@app.route('/thumbnail/<category>/<imgname>/<int:maxgeometry>')
def thumbnail(imgname,category, maxgeometry):
    if category == 'none':
         imgpath = os.path.join(config.imagedir, secure_filename( imgname))
    else:
        imgpath = os.path.join(config.imagedir, category ,secure_filename( imgname))
    thumbpath = make_thumb(imgpath, maxgeometry)
    with open(thumbpath, 'r') as imgfile:
        return Response(imgfile.read(), mimetype="image/png")

@app.route('/logothumbnail/<category>/<imgname>/<int:maxgeometry>')
def logothumbnail(imgname,category, maxgeometry):
    if category == 'none':
         imgpath = os.path.join(config.logodir, secure_filename( imgname))
    else:
        imgpath = os.path.join(config.logodir, category + '/' +secure_filename( imgname))
    thumbpath = make_thumb(imgpath, maxgeometry)
    with open(thumbpath, 'r') as imgfile:
        return Response(imgfile.read(), mimetype="image/png")




@app.route('/pdfthumb/<pdfname>/<int:maxgeometry>')
def pdfthumbnail(pdfname, maxgeometry):
    pdfpath = os.path.join(config.pdfdir, secure_filename(pdfname))
    thumbpath = make_thumb(pdfpath, maxgeometry)
    with open(thumbpath, 'r') as imgfile:
        return Response(imgfile.read(), mimetype="image/png")


@app.route('/tplthumb/<tplname>/<int:maxgeometry>')
def tplthumbnail(tplname, maxgeometry):
    pdfpath = os.path.join(config.cachedir, secure_filename(tplname) + '.pdf')
    try:
        run_pdflatex(
            {'textemplate': secure_filename(tplname),
             'img': 'pictograms-nps-misc-camera.png',
             'headline': u'Überschrift',
             'text': u'Dies ist der Text, der in der UI als Text bezeichnet ist.',
             'markup': 'latex',
             'footer': u'Das hier ist der Footer',
             'logo': config.standartLogo,
             }, pdfpath, overwrite=False
        )
    except Exception as e:
        return str(e)
    else:
        thumbpath = make_thumb(pdfpath, maxgeometry)
        with open(thumbpath, 'r') as imgfile:
            return Response(imgfile.read(), mimetype="image/png")


@app.route('/pdfdownload/<pdfname>')
def pdfdownload(pdfname):
    pdfpath = os.path.join(config.pdfdir, secure_filename(pdfname))
    with open(pdfpath, 'r') as pdffile:
        return Response(pdffile.read(), mimetype="application/pdf")


def generateImagelist(path = None):
    #imagelist = sorted(glob.glob(config.imagedir + '/*.png'))
    #standart bilder pfad
    if(path == None): 
        path = config.imagedir + '/'
	
    imagelist = {}
    imagelist['none'] = []
	
    files = os.walk(path)
    for root,dirs,files in os.walk(path):
        for f in files:
            if f.endswith('.png'):
                filename = os.path.basename(f)
                category = root.replace(path,'')
                if(category == ""):
                	imagelist['none'].append(filename)
                else:
                    if category not in imagelist.keys():
                        imagelist[category] = []
                    imagelist[category].append(filename)
                
    return imagelist

def recreate_cache():
    for filename in (glob.glob(os.path.join(config.pdfdir, '*.pdf*')) +
             glob.glob(os.path.join(config.cachedir, '*.pdf*')) +
             glob.glob(os.path.join(config.imagedir, '*.png.*'))):
        try:
            os.unlink(filename)
            print("Deleted %s" % filename)
        except Exception as e:
            print("Could not delete %s: %s" % (filename, str(e)))
    for filename in glob.glob(os.path.join(config.datadir, '*.schild')):
        data = load_data(filename)
        pdfname = os.path.join(config.pdfdir, data['pdfname'])
        print("Recreating %s" % pdfname)
        run_pdflatex(data, pdfname)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--recreate-cache':
        recreate_cache()
    else:
        app.debug = True
        app.run(host=config.listen, port=config.port)
