#!/usr/bin/python
# -*- encoding: utf8 -*-

from flask import Flask, flash, session, redirect, url_for, escape, request, Response, Markup
import sys, os, os.path, glob
from genshi.template import TemplateLoader
from genshi.template.text import NewTextTemplate
from flaskext.genshi import Genshi, render_response
from werkzeug.utils import secure_filename
from collections import defaultdict
import warnings
import shutil
import subprocess
from subprocess import CalledProcessError, STDOUT
import PythonMagick
import json
import tempfile
import config

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.uploaddir
app.config['PROPAGATE_EXCEPTIONS'] = True
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

@app.route('/')
def index(**kwargs):
  data = defaultdict(str)
  data.update(**kwargs)
  filelist = glob.glob(config.datadir + '/*.schild')
  data['files'] = [ unicode(os.path.basename(f)) for f in sorted(filelist) ]
  return render_response('index.html', data)

@app.route('/edit')
def edit(**kwargs):
  data = defaultdict(str)
  data.update(**kwargs)
  imagelist = glob.glob(config.imagedir + '/*.png')
  data['images'] = [ os.path.basename(f) for f in imagelist ]
  templatelist = glob.glob(config.textemplatedir + '/*.tex')
  data['templates'] = [ unicode(os.path.basename(f)) for f in sorted(templatelist) ]
  return render_response('edit.html', data)

@app.route('/edit/<filename>')
def edit_one(filename):
  with open(os.path.join(config.datadir, filename), 'r') as infile:
    formdata = json.load(infile)
    return edit(form=formdata)

def run_pdflatex(context, outputfilename):
  if not context.has_key('textemplate'):
    context['textemplate'] = "text-image-quer.tex"
  genshitex = TemplateLoader([config.textemplatedir])
  template = genshitex.load(context['textemplate'], cls=NewTextTemplate, encoding='utf8')
  tmpdir = tempfile.mkdtemp(dir=config.tmpdir)
  if context.has_key('img') and context['img'] and context['img'] != '__none':
    try:
      shutil.copy(os.path.join(config.imagedir, context['img']), os.path.join(tmpdir, context['img']))
    except:
      raise IOError("COULD NOT COPY")
  else:
    #print "MEH No image"
    pass
  tmptexfile = os.path.join(tmpdir, 'output.tex')
  tmppdffile = os.path.join(tmpdir, 'output.pdf')
  with open(tmptexfile, 'w') as texfile:
    texfile.write(template.generate(form = context).render(encoding='utf8'))
  cwd = os.getcwd()
  os.chdir(tmpdir)
  os.symlink(config.texsupportdir, os.path.join(tmpdir, 'support'))
  try:
    texlog = check_output(['pdflatex', '--halt-on-error', tmptexfile], stderr=STDOUT)
  except CalledProcessError as e:
    flash(Markup("<p>PDFLaTeX Output:</p><pre>%s</pre>" % e.output), 'log')
    raise SyntaxWarning("PDFLaTeX bailed out")
  finally:
    os.chdir(cwd)
  flash(Markup("<p>PDFLaTeX Output:</p><pre>%s</pre>" % texlog), 'log')
  shutil.copy(tmppdffile, outputfilename)
  shutil.rmtree(tmpdir)

def save_and_convert_image_upload(inputname):
  file = request.files[inputname]
  if file:
    if not allowed_file(file.filename):
      raise UserWarning("Uploaded image is not in the list of allowed file types.")
    filename = os.path.join(config.uploaddir, secure_filename(file.filename))
    file.save(filename)
    img = PythonMagick.Image(filename)
    imgname = os.path.splitext(secure_filename(file.filename))[0].replace('.', '_') + '.png'
    savedfilename = os.path.join(config.imagedir, imgname)
    img.write(savedfilename)
    os.remove(filename)
    return imgname
  return None

@app.route('/create', methods=['POST'])
def create():
  if request.method == 'POST':
    formdata = request.form.to_dict(flat=True)
    for a in ('headline', 'text'):
      formdata[a] = unicode(formdata[a])
    try:
      imgpath = save_and_convert_image_upload('imgupload')
      if imgpath is not None:
        formdata['img'] = imgpath
      outfilename = secure_filename(formdata['headline'][:16])+str(hash(formdata['headline']+formdata['text']+os.path.splitext(formdata['textemplate'])[0]))+'.schild'
      outpdfname = outfilename + '.pdf'
      formdata['pdfname'] = outpdfname
      run_pdflatex(formdata, os.path.join(config.pdfdir, outpdfname))
      with open(os.path.join(config.datadir, outfilename), 'w') as outfile:
        json.dump(formdata, outfile)
      flash(Markup(u"""PDF created and data saved. You might create another one. Here's a preview. Click to print.<br/>
          <a href="%s"><img src="%s"/></a>""" %
          (url_for('schild', filename=outfilename), url_for('pdfthumbnail', pdfname=outpdfname, maxgeometry=200))
        ))
    except Exception as e:
      flash(u"Could not create pdf or save data: %s" % str(e), 'error')

    data = {'form': formdata }
    imagelist = glob.glob(config.imagedir + '/*.png')
    data['images'] = [ os.path.basename(f) for f in imagelist ]
    templatelist = glob.glob(config.textemplatedir + '/*.tex')
    data['templates'] = [ os.path.basename(f) for f in sorted(templatelist) ]
    return render_response('edit.html', data)
  flash("No POST data. You've been redirected to the edit page.", 'warning')
  return redirect(url_for('edit'))

@app.route('/schild/<filename>')
def schild(filename):
  return render_response('schild.html', {'filename':filename, 'printer':[ unicode(f) for f in sorted(config.printers.keys()) ]})

@app.route('/printout', methods=['POST'])
def printout():
  filename = os.path.join(config.pdfdir, secure_filename(request.form['filename']))
  printer = config.printers[request.form['printer']]
  copies = int(request.form['copies']) or 0
  if copies > 0 and copies <= 6:
    try:
      lprout = check_output(['lpr', '-H', str(config.printserver), '-P', str(printer), '-#', str(copies)] + config.lproptions + [filename], stderr=STDOUT)
      flash(u'Schild wurde zum Drucker geschickt!')
    except CalledProcessError as e:
      flash(Markup("<p>Could not print:</p><pre>%s</pre>" % e.output), 'error')
  else:
    flash(u'Ungültige Anzahl Kopien!')
  return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete():
  filename = secure_filename(request.form['filename'])
  try:
    os.unlink(os.path.join(config.datadir, filename))
    for f in glob.glob(os.path.join(config.pdfdir, filename + '.pdf*')):
      os.unlink(f)
    flash(u"Schild %s wurde gelöscht" % filename)
    return redirect(url_for('index'))
  except:
    flash(u"Schild %s konnte nicht gelöscht werden." % filename, 'error')
    return redirect(url_for('schild', filename=filename))

@app.route('/image/<imgname>')
def image(imgname):
  imgpath = os.path.join(config.imagedir, secure_filename(imgname))
  #print(imgpath)
  if os.path.exists(imgpath):
    with open(imgpath, 'r') as imgfile:
      return Response(imgfile.read(), mimetype="image/png")
  else:
    return "Meh" #redirect(url_for('index'))

def make_thumb(filename, maxgeometry):
  thumbpath = filename + '.' + str(maxgeometry)
  if not os.path.exists(thumbpath) or os.path.getmtime(filename) > os.path.getmtime(thumbpath):
    img = PythonMagick.Image(str(filename))
    img.transform("%sx%s" % (maxgeometry,maxgeometry))
    img.quality(90)
    img.write(str("png:%s" % thumbpath))
  return thumbpath

@app.route('/thumbnail/<imgname>/<int:maxgeometry>')
def thumbnail(imgname, maxgeometry):
  imgpath = os.path.join(config.imagedir, secure_filename(imgname))
  thumbpath = make_thumb(imgpath, maxgeometry)
  with open(thumbpath, 'r') as imgfile:
    return Response(imgfile.read(), mimetype="image/png")

@app.route('/pdfthumb/<pdfname>/<int:maxgeometry>')
def pdfthumbnail(pdfname, maxgeometry):
  pdfpath = os.path.join(config.pdfdir, secure_filename(pdfname))
  thumbpath = make_thumb(pdfpath, maxgeometry)
  with open(thumbpath, 'r') as imgfile:
    return Response(imgfile.read(), mimetype="image/png")

@app.route('/pdfdownload/<pdfname>')
def pdfdownload(pdfname):
  pdfpath = os.path.join(config.pdfdir, secure_filename(pdfname))
  with open(pdfpath, 'r') as pdffile:
    return Response(pdffile.read(), mimetype="application/pdf")

if __name__ == '__main__':
  app.debug = True
  app.run(host=config.listen, port=config.port)
