# nbplot

Command-line utility to quickly plot files in a Jupyter notebook.

Tools like pandas+matplotlib are very powerful, but it takes some time to plot a file from scratch: run a Jupyter notebook instance, create a notebook, import the modules, go grab the path of the file, remember how to call `read_csv` properly, create the matplotlib figure, etc. The goal of `nbplot` is to remove that friction and make this as easy as launching a dedicated tool like `gnuplot`.

# Demo

![nbplot_demo](https://user-images.githubusercontent.com/541507/113471006-d155e680-9459-11eb-8333-ada4cb6e45fe.png)

# Installation

Python 3.7 or higher required.

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

# Creating a custom template

Templates are just regular `.ipynb` notebooks, with special variables like the filenames to plot that will get replaced when generating the output notebook.

The easiest way to create a custom template is to copy and adapt an existing one from the `templates/` folder of the repository, and put it in your `~/.nbplot/` folder, next to the configuration file. The name of the template is defined in `metadata` dictionary defined in the special cell that stars with a `# [[nbplot]] template` line.

# Configuring the default behavior

When first launched, `nbplot` generates a configuration file in `~/.nbplot/config.ipynb`. It is also a notebook, and the config dictionary will be read after evaluating the cell. The main options are the default template, the folder from which to start the notebook instance, and the folder where the generated plots will be saved.
