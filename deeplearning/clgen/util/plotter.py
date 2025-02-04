"""
In-house plotter module that plots data.
Based on plotly module
"""
import typing
import pathlib
import numpy as np
from plotly import graph_objs as go

def SingleScatterLine(x: np.array,
                      y: np.array,
                      title : str,
                      x_name: str,
                      y_name: str,
                      plot_name: str,
                      path: pathlib.Path,
                      ) -> None:
  """Plot a single line, with scatter points at datapoints."""
  layout = go.Layout(
    title = title,
    xaxis = dict(title = x_name),
    yaxis = dict(title = y_name),
  )
  fig = go.Figure(layout = layout)
  fig.add_trace(
    go.Scatter(
      x = x, y = y,
      mode = 'lines+markers',
      name = plot_name,
      showlegend = False,
      marker_color = "#00b3b3",
      opacity = 0.75
    )
  )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return

def GroupScatterPlot(groups: typing.Dict[str, typing.Dict[str, list]],
                     title: str,
                     x_name: str,
                     y_name: str,
                     plot_name: str,
                     path: pathlib.Path,
                     ) -> None:
  """
  Plots groupped scatter plot of points in two-dimensional space.
  """
  layout = go.Layout(
    title = title,
    # xaxis = dict(title = x_name),
    # yaxis = dict(title = y_name),
  )
  fig = go.Figure(layout = layout)
  for group, values in groups.items():
    feats = np.array(values['data'])
    names = values['names']
    fig.add_trace(
      go.Scatter(
        x = feats[:,0], y = feats[:,1],
        name = group,
        mode = 'markers',
        showlegend = True,
        opacity    = 0.75,
        text       = names,
      )
    )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return

def FrequencyBars(x: np.array,
                  y: np.array,
                  title    : str,
                  x_name   : str,
                  plot_name: str,
                  path: pathlib.Path
                  ) -> None:
  """Plot frequency bars based on key."""
  layout = go.Layout(
    title = title,
    xaxis = dict(title = x_name),
    yaxis = dict(title = "# of Occurences"),
  )
  fig = go.Figure(layout = layout)
  fig.add_trace(
    go.Bar(
      x = x,
      y = y,
      showlegend = False,
      marker_color = '#ac3939',
      opacity = 0.75,
    )
  )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return

def LogitsStepsDistrib(x              : typing.List[np.array],
                       atoms          : typing.List[str],
                       sample_indices : typing.List[str],
                       title          : str,
                       x_name         : str,
                       # plot_name: str,
                       # path: pathlib.Path
                       ) -> None:
  """
  Categorical group-bar plotting.
  vocab_size number of groups. Groups are as many as prediction steps.
  Used to plot the probability distribution of BERT's token selection. 
  """
  layout = go.Layout(
    title = title,
    xaxis = dict(title = x_name),
    # yaxis = dict(title = ""),
  )
  fig = go.Figure(layout = layout)

  for pred, name in zip(x, sample_indices):
    fig.add_trace(
      go.Bar(
        name = name,
        x = atoms,
        y = pred,
      )
    )
  fig.show()
  return

def CumulativeHistogram(x: np.array,
                        y: np.array,
                        title    : str,
                        x_name   : str,
                        plot_name: str,
                        path: pathlib.Path
                        ) -> None:
  """Plot percent cumulative histogram."""
  layout = go.Layout(
    title = title,
    xaxis = dict(title = x_name),
    yaxis = dict(title = "% of Probability Density"),
  )
  fig = go.Figure(layout = layout)
  fig.add_trace(
    go.Histogram(
      x = x,
      y = y,
      xbins = dict(size = 8),
      cumulative_enabled = True,
      histfunc = 'sum',
      histnorm = 'percent',
      showlegend = False,
      marker_color = '#1d99a3',
      opacity = 0.65,
    )
  )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return

def NormalizedRadar(r         : np.array,
                    theta     : typing.List[str],
                    title     : str,
                    plot_name : str,
                    path      : pathlib.Path,
                    ) -> None:
  """Radar chart for feature plotting"""
  layout = go.Layout(
    title = title,
  )
  fig = go.Figure(layout = layout)
  fig.add_trace(
    go.Scatterpolar(
      r = r,
      theta = theta,
      fill = 'toself',
      marker_color = "#cbef0e",
    )
  )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return

def CategoricalViolin(x: np.array,
                      y: typing.List[np.array],
                      title    : str,
                      x_name   : str,
                      plot_name: str,
                      path: pathlib.Path
                      ) -> None:
  """Plot percent cumulative histogram."""
  layout = go.Layout(
    title = title,
    violingap = 0,
    violinmode = 'overlay',
    xaxis = dict(title = x_name),
    yaxis = dict(title = "Distribution / category"),
  )
  fig = go.Figure(layout = layout)
  for xel, yel in zip(x, y):
    fig.add_trace(
      go.Violin(
        x = [xel]*len(yel),
        y = yel,
        name = xel,
        # side = 'positive',
        meanline_visible = True,
        box_visible = True,
        showlegend = False,
        opacity = 0.65,
      )
    )
  outf = lambda ext: str(path / "{}.{}".format(plot_name, ext))
  fig.write_html (outf("html"))
  fig.write_image(outf("png"), scale = 2.0)
  return