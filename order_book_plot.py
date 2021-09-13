from bokeh.plotting import figure, curdoc
from bokeh.driving import linear
import numpy as np

import random

p = figure(plot_width=1000, plot_height=600)
r1 = p.line([], [], color="firebrick", line_width=2)
r2 = p.line([], [], color="limegreen", line_width=2)
r3 = p.line([], [], color="limegreen", line_width=2)

ds1 = r1.data_source
ds2 = r2.data_source
ds3 = r3.data_source

@linear()
def update(step):
    x = np.random.rand()
    y = np.random.rand()
    z = np.random.rand()
    ds1.data['x'].append(step)
    ds2.data['x'].append(step)
    ds3.data['x'].append(step)
    ds1.data['y'].append(x)
    ds2.data['y'].append(y)
    ds3.data['y'].append(z)
    ds1.trigger('data', ds1.data, ds1.data)
    ds2.trigger('data', ds2.data, ds2.data)
    ds3.trigger('data', ds3.data, ds3.data)

curdoc().add_root(p)

# Add a periodic callback to be run every 500 milliseconds
curdoc().add_periodic_callback(update, 500)