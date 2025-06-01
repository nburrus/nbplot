![image](https://img.shields.io/github/workflow/status/nburrus/nbplot/nbplot%20package)

# nbplot 

Command-line utility to quickly plot files in a Jupyter notebook.

Tools like pandas+matplotlib are very powerful, but it takes some time to plot a file from scratch: run a Jupyter notebook instance, create a notebook, import the modules, go grab the path of the file, remember how to call `read_csv` properly, create the matplotlib figure, etc. The goal of `nbplot` is to remove that friction and make this as easy as launching a dedicated tool like `gnuplot`.

# Demo

![nbplot_demo](https://user-images.githubusercontent.com/541507/113471006-d155e680-9459-11eb-8333-ada4cb6e45fe.png)

# Installation

Tested on Python 3.8 to 3.12, but it likely works on more versions.

```
pip install nbplot
```

# Features

* Can be fully configured via templates. A template is just a notebook with some special variables that will get replaced.

* Ships with a default template for numpy+matplotlib and one for pandas+matplotlib.

* Can guess the column delimiter of text files.

* Data can be directly read from stdin, and the string will be embedded in the generated notebook.

* Will try to reuse an existing instance of notebook server (inspired by [nbopen](https://github.com/takluyver/nbopen)).

# Examples 

## Plots

```
$ cat mydata.txt
1 1
2 4
3 9
4 16

$ nbplot mydata.txt
```

* Generates a notebook `~/nbplot/{{date}}-mydata.ipynb` with the code to load `mydata.txt` with `pandas.read_csv` and the guessed space delimiter.

* Opens the notebook in the browser, reusing existing instances of Jupyter if possible, starting a new one otherwise.

---

```
$ nbplot -t numpy mydata.txt
```

* Generates the notebook with the `numpy` template, using `numpy.genfromtxt` to load the file.

---

```
$ nbplot mydata1.txt mydata2.txt [...]
```

* Generates a notebook that loads all the input files in the same plot.

---

```
$ for i in `seq -10 10`; do echo $i $((i*i)); done | nbplot -
```

* Reads the data to plot from stdin and generates a notebook to plot it, with the data embedded as a string.

![nbplot_stdin](https://user-images.githubusercontent.com/541507/113489773-452dd880-94c6-11eb-8ba5-eaceb39bd4e3.png)

# Images

```
$ nbplot -t imshow image1.png image2.jpg
```

* Uses the `imshow` template to generate a notebook that loads and displays the 2 images with matplotlib `imshow` and `PIL.Image`.

---

```
$ nbplot -t imshow paste-image
```

* Use the special `paste-image` filename to directly plot an image from the clipboard. It will get embedded into the notebook via a base64 string.

![nbplot_images_clipboard](https://user-images.githubusercontent.com/541507/113489588-5d512800-94c5-11eb-94e1-e84f7f359f2d.png)

---

```
$ nbplot -t daltonize Ishihara_9_from_wikipedia.png
```

* The `daltonize` template generates a notebook with the same image rendered with various color filters that can either help color-blind people to better see the contrasts, or designers to simulate different kinds of color blindness. Powered by the [daltonize](https://github.com/joergdietrich/daltonize) module.

![nbplot_daltonize](https://user-images.githubusercontent.com/541507/113513842-d4d99280-956b-11eb-90aa-94484e8128d9.png)

## Empty notebook, no input files

```
$ nbplot -t empty -o empty.ipynb
```

* Creates an empty notebook in the current folder with the name `empty.ipynb` and opens it.

# Creating a custom template

Templates are just regular `.ipynb` notebooks, with special variables like the filenames to plot that will get replaced when generating the output notebook.

The easiest way to create a custom template is to copy and adapt an existing one from the `templates/` folder of the repository, and put it in your `~/.nbplot/` folder, next to the configuration file. The name of the template is defined in `metadata` dictionary defined in the special cell that stars with a `# [[nbplot]] template` line.

The search for template files is recursive, so it is possible to manage custom templates in e.g. an external repository and git clone it in a subfolder under `~/.nbplot`.
# Configuring the default behavior

When first launched, `nbplot` generates a configuration file in `~/.nbplot/config.ipynb`. It is also a notebook, and the config dictionary will be read after evaluating the cell. The main options are the default template, the folder from which to start the notebook instance, and the folder where the generated plots will be saved.

# ChangeLog

## v0.3 (April 6th, 2021)

- Add an empty template and accept to run without input files
- Fix the recursive globbing of user templates to follow symlinks
- Fix the image type conversion in the daltonize template

## v0.2 (April 4th, 2021)

New features:

- Add an `imshow` template to show images with `matplotlib.imshow`.
- Add a `daltonize` template to show images enhanced for colorblind people.
- Glob templates recursively in `~/.nbplot`. This makes it possible to manage private templates via a git cloned subfolder.
- Add the `paste-image` special filename to grab an image from the clipboard and embed its content in the notebook.


Fixes:

- Fix the metadata to automatically load a Python kernel.
- Don't fail when trying to determine the delimiter on binary files.
- `pandas`: handle files with multiple spaces / tabs between columns.
## v0.1 (April 1st, 2021)

Initial release.
