# Use an custom pdflatex as parent
FROM pdflatex

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

#install latex, python and pythonmagick
RUN apt-get update && apt-get install -y \
#texlive texlive-lang-english texlive-lang-german \
#texlive-latex-base texlive-latex-recommended texlive-latex-extra \
python python-pip python-pythonmagick 


# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 5432 available to the world outside this container
EXPOSE 5432

# Define environment variable for PythonMagick
ENV PYTHONPATH ".:/usr/lib/python2.7/dist-packages:${PYTHONPATH}"

# Run app.py when the container launches
CMD ["python2", "schilder.py"]
