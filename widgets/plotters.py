#    plotters.py
#    plotting classes

#    Copyright (C) 2004 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###############################################################################

# $Id$

import qt
import itertools
import numarray as N

import widget
import widgetfactory
import graph
import setting

import utils

def _trim(x, x1, x2):
    """Truncate x in range x1->x2."""
    if x < x1: return x1
    if x > x2: return x2
    return x

class GenericPlotter(widget.Widget):
    """Generic plotter."""

    typename='genericplotter'
    allowedparenttypes=[graph.Graph]

    def __init__(self, parent, name=None):
        """Initialise object, setting axes."""
        widget.Widget.__init__(self, parent, name=name)

        s = self.settings
        s.add( setting.Str('key', '',
                           descr = 'Description of the plotted data') )
        s.add( setting.Str('xAxis', 'x',
                           descr = 'Name of X-axis to use') )
        s.add( setting.Str('yAxis', 'y',
                           descr = 'Name of Y-axis to use') )

    def getAxesNames(self):
        """Returns names of axes used."""
        s = self.settings
        return [s.xAxis, s.yAxis]

    def drawKeySymbol(self, painter, x, y, width, height):
        """Draw the plot symbol and/or line at (x,y) in a box width*height.

        This is used to plot a key
        """
        pass

########################################################################
        
class FunctionPlotter(GenericPlotter):
    """Function plotting class."""

    typename='function'
    allowusercreation=True
    description='Plot a function'
    
    def __init__(self, parent, name=None):
        """Initialise plotter with axes."""

        GenericPlotter.__init__(self, parent, name=name)

        # define environment to evaluate functions
        self.fnenviron = globals()
        exec 'from numarray import *' in self.fnenviron

        s = self.settings
        s.add( setting.Int('steps', 50,
                           descr = 'Number of steps to evaluate the function'
                           ' over'), 0 )
        s.add( setting.Choice('variable', ['x', 'y'], 'x',
                              descr='Variable the function is a function of'),
               0 )
        s.add( setting.Str('function', 'x',
                           descr='Function expression'), 0 )

        s.add( setting.Line('Line',
                            descr = 'Function line settings') )

        if type(self) == FunctionPlotter:
            self.readDefaults()
        
    def _getUserDescription(self):
        """User-friendly description."""
        return "%s = %s" % ( self.settings.variable,
                             self.settings.function )
    userdescription = property(_getUserDescription)

    def _plotLine(self, painter, xpts, ypts, bounds):
        """ Plot the points in xpts, ypts."""
        x1, y1, x2, y2 = bounds

        # idea is to collect points until we go out of the bounds
        # or reach the end, then plot them
        pts = []
        lastx = lasty = -65536
        for x, y in itertools.izip(xpts, ypts):

            # ignore point if it outside sensible bounds
            if x < -32767 or y < -32767 or x > 32767 or y > 32767:
                if len(pts) >= 4:
                    painter.drawPolyline( qt.QPointArray(pts) )
                    pts = []
            else:
                dx = abs(x-lastx)
                dy = abs(y-lasty)

                # if the jump wasn't too large, add the point to the points
                if dx < (x2-x1)*3/4 and dy < (y2-y1)*3/4:
                    pts.append(x)
                    pts.append(y)
                else:
                    # draw what we have until now, and start a new line
                    if len(pts) >= 4:
                        painter.drawPolyline( qt.QPointArray(pts) )
                    pts = [x, y]

            lastx = x
            lasty = y

        # draw remaining points
        if len(pts) >= 4:
            painter.drawPolyline( qt.QPointArray(pts) )

    def drawKeySymbol(self, painter, x, y, width, height):
        """Draw the plot symbol and/or line."""

        s = self.settings
        yp = y + height/2

        # draw line
        if not s.Line.hide:
            painter.setBrush( qt.QBrush() )
            painter.setPen( s.Line.makeQPen(painter) )
            painter.drawLine(x, yp, x+width, yp)

    def getKeySymbolWidth(self, height):
        """Get preferred width of key symbol of height."""

        if not self.settings.Line.hide:
            return 3*height
        else:
            return height

    def initEnviron(self):
        """Initialise function evaluation environment each time."""
        return self.fnenviron.copy()

    def draw(self, parentposn, painter, outerbounds = None):
        """Draw the function."""

        posn = GenericPlotter.draw(self, parentposn, painter,
                                   outerbounds = outerbounds)
        x1, y1, x2, y2 = posn
        s = self.settings

        # get axes widgets
        axes = self.parent.getAxes( (s.xAxis, s.yAxis) )

        # return if there's no proper axes
        if ( None in axes or
             axes[0].settings.direction != 'horizontal' or
             axes[1].settings.direction != 'vertical' ):
            return

        env = self.initEnviron()
        if s.variable == 'x':
            # x function
            delta = (x2 - x1) / float(s.steps)
            pxpts = N.arange(x1, x2+delta, delta).astype(N.Int32)
            env['x'] = axes[0].plotterToGraphCoords(posn, pxpts)
            try:
                y = eval( s.function + ' + 0*x', env )
                bad = False
            except:
                bad = True
            else:
                pypts = axes[1].graphToPlotterCoords(posn, y)

        else:
            # y function
            delta = (y2 - y1) / float(s.steps)
            pypts = N.arange(y1, y2+delta, delta).astype(N.Int32)
            env['y'] = axes[1].plotterToGraphCoords(posn, pypts)
            try:
                x = eval( s.function + ' + 0*y', env )
                bad = False
            except:
                bad = True
            else:
                pxpts = axes[0].graphToPlotterCoords(posn, x)

        # clip data within bounds of plotter
        painter.save()
        painter.setClipRect( qt.QRect(x1, y1, x2-x1, y2-y1) )

        # draw the function line
        if not s.Line.hide and not bad:
            painter.setBrush( qt.QBrush() )
            painter.setPen( s.Line.makeQPen(painter) )
            self._plotLine(painter, pxpts, pypts, posn)

        if bad:
            # not sure how to deal with errors here
            painter.setPen( qt.QColor('red') )
            f = qt.QFont()
            f.setPointSize(20)
            painter.setFont(f)
            painter.drawText( qt.QRect(x1, y1, x2-x1, y2-y1),
                              qt.Qt.AlignCenter,
                              "Cannot evaluate '%s'" % s.function )

        painter.restore()

##     def _fillYFn(self, painter, xpts, ypts, bounds, leftfill):
##         """ Take the xpts and ypts, and fill above or below the line."""
##         if len(xpts) == 0:
##             return

##         x1, y1, x2, y2 = bounds

##         if leftfill:
##             pts = [x1, y1]
##         else:
##             pts = [x2, y1]

##         for x,y in zip(xpts, ypts):
##             pts.append( _trim(x, x1, x2) )
##             pts.append(y)

##         if leftfill:
##             pts.append(x2)
##         else:
##             pts.append(x1)
##         pts.append(y2)

##         painter.drawPolygon( qt.QPointArray(pts) )

##     def _fillXFn(self, painter, xpts, ypts, bounds, belowfill):
##         """ Take the xpts and ypts, and fill to left or right of the line."""
##         if len(ypts) == 0:
##             return

##         x1, y1, x2, y2 = bounds

##         if belowfill:
##             pts = [x1, y2]
##         else:
##             pts = [x1, y1]

##         for x,y in zip(xpts, ypts):
##             pts.append(x)
##             pts.append( _trim(y, y1, y2) )

##         pts.append( x2 )
##         if belowfill:
##             pts.append( y2 )
##         else:
##             pts.append( y1 )

##         painter.drawPolygon( qt.QPointArray(pts) )

##     def draw(self, parentposn, painter):
##         """Plot the function."""

##         posn = GenericPlotter.draw(self, parentposn, painter)

##         # the algorithm is to work out the fn for each pixel on the plot
##         # need to convert pixels -> graph coord -> calc fn -> pixels

##         x1, y1, x2, y2 = posn

##         ax1 = self.getAxisVar( self.axes[0] )
##         ax2 = self.getAxisVar( self.axes[1] )

##         if self.xfunc:
##             xplotter = numarray.arange(x1, x2+1, self.iter)
##             self.fnenviron['x'] = ax1.plotterToGraphCoords(posn, xplotter)
##             # HACK for constants
##             y = eval( self.function + " + (0*x)", self.fnenviron )
##             yplotter = ax2.graphToPlotterCoords(posn, y)
##         else:
##             yplotter = numarray.arange(y1, y2+1, self.iter)
##             self.fnenviron['y'] = ax2.plotterToGraphCoords(posn, yplotter)
##             # HACK for constants
##             x = eval( self.function + " + (0*y)", self.fnenviron )
##             xplotter = ax1.graphToPlotterCoords(posn, x)

##         # here we go through the generated points, and plot those that
##         # are in the plot (we can clip fairly easily).
##         # each time there is a section we can plot, we plot it
        
##         painter.save()
##         painter.setPen( qt.QPen( qt.QColor(), 0, qt.Qt.NoPen ) )

##         painter.setBrush( qt.QBrush(qt.QColor("darkcyan"),
##                                     qt.Qt.Dense6Pattern) )
##         self._fillXFn(painter, xplotter, yplotter, posn, 1)
        
##         painter.setBrush( qt.QBrush() )
##         painter.setPen( self.Line.makeQPen(painter) )
##         self._plotLine(painter, xplotter, yplotter, posn)

##         painter.restore()

# allow the factory to instantiate an function plotter
widgetfactory.thefactory.register( FunctionPlotter )

###############################################################################
        
class PointPlotter(GenericPlotter):
    """A class for plotting points and their errors."""

    typename='xy'
    allowusercreation=True
    description='Plot points with lines and errorbars'
    
    def __init__(self, parent, name=None):
        """Initialise XY plotter plotting (xdata, ydata).

        xdata and ydata are strings specifying the data in the document"""
        
        GenericPlotter.__init__(self, parent, name=name)
        s = self.settings

        s.add( setting.Distance('markerSize', '3pt'), 0 )
        s.add( setting.Choice('marker', utils.MarkerCodes, 'circle'), 0 )
        s.add( setting.Str('yData', 'y',
                           descr = 'Variable containing y data'), 0 )
        s.add( setting.Str('xData', 'x',
                           descr = 'Variable containing x data'), 0 )
        s.add( setting.Choice('errorStyle',
                              ['bar', 'box', 'diamond', 'curve',
                               'barbox', 'bardiamond', 'barcurve'], 'bar',
                              descr='Style of error bars to plot') )

        s.add( setting.XYPlotLine('PlotLine',
                                  descr = 'Plot line settings') )
        s.add( setting.Line('MarkerLine',
                            descr = 'Line around the marker settings') )
        s.add( setting.Brush('MarkerFill',
                             descr = 'Marker fill settings') )
        s.add( setting.Line('ErrorBarLine',
                            descr = 'Error bar line settings') )

        if type(self) == PointPlotter:
            self.readDefaults()

    def _getUserDescription(self):
        """User-friendly description."""

        s = self.settings
        return "x='%s', y='%s', marker='%s'" % (s.xData, s.yData,
                                                s.marker)
    userdescription = property(_getUserDescription)

    def _plotErrors(self, posn, painter, xplotter, yplotter,
                    axes):
        """Plot error bars (horizontal and vertical)."""

        # get the data
        s = self.settings
        xdata = self.document.getData(s.xData)

        # draw horizontal error bars
        if xdata.hasErrors():
            xmin, xmax = xdata.getPointRanges()
                    
            # convert xmin and xmax to graph coordinates
            xmin = axes[0].graphToPlotterCoords(posn, xmin)
            xmax = axes[0].graphToPlotterCoords(posn, xmax)

            # clip... (avoids problems with INFs, etc)
            xmin = N.clip(xmin, posn[0]-1, posn[2]+1)
            xmax = N.clip(xmax, posn[0]-1, posn[2]+1)

            # draw lines between each of the points
        else:
            xmin = xmax = None

        # draw vertical error bars
        # get data
        ydata = self.document.getData(s.yData)
        if ydata.hasErrors():
            ymin, ymax = ydata.getPointRanges()

            # convert ymin and ymax to graph coordinates
            ymin = axes[1].graphToPlotterCoords(posn, ymin)
            ymax = axes[1].graphToPlotterCoords(posn, ymax)

            # clip...
            ymin = N.clip(ymin, posn[1]-1, posn[3]+1)
            ymax = N.clip(ymax, posn[1]-1, posn[3]+1)

            # draw lines between each of the points
        else:
            ymin = ymax = None

        # draw normal error bars
        style = s.errorStyle
        if style in {'bar':True, 'bardiamond':True,
                     'barcurve':True, 'barbox': True}:
            # list of output lines
            pts = []

            # vertical error bars
            if ymin != None and ymax != None:
                for i in itertools.izip(xplotter, ymin, xplotter,
                                        ymax):
                    pts += i
            # horizontal error bars
            if xmin != None and xmax != None:
                for i in itertools.izip(xmin, yplotter, xmax,
                                        yplotter):
                    pts += i

            if len(pts) != 0:
                painter.drawLineSegments( qt.QPointArray(pts) )

        # special error bars (only works with proper x and y errors)
        if ( ymin != None and ymax != None and xmin != None and
             xmax != None ):

            # draw boxes
            if style in {'box':True, 'barbox':True}:

                # non-filling brush
                painter.setBrush( qt.QBrush() )

                for xmn, ymn, xmx, ymx in (
                    itertools.izip(xmin, ymin, xmax, ymax)):

                    painter.drawPolygon(
                        qt.QPointArray([xmn, ymn, xmx, ymn, xmx, ymx,
                                        xmn, ymx]) )

            # draw diamonds
            elif style in {'diamond':True, 'bardiamond':True}:

                # non-filling brush
                painter.setBrush( qt.QBrush() )

                for xp, yp, xmn, ymn, xmx, ymx in itertools.izip(
                    xplotter, yplotter, xmin, ymin, xmax, ymax):

                    painter.drawPolygon(
                        qt.QPointArray([xmn, yp, xp, ymx, xmx, yp, xp, ymn]) )

            # draw curved errors
            elif style in {'curve':True, 'barcurve': True}:

                # non-filling brush
                painter.setBrush( qt.QBrush() )

                for xp, yp, xmn, ymn, xmx, ymx in itertools.izip(
                    xplotter, yplotter, xmin, ymin, xmax, ymax):

                    # break up curve into four arcs (for asym error bars)
                    # qt geometry means we have to calculate lots
                    painter.drawArc(xp - (xmx-xp), yp - (yp-ymx),
                                    (xmx-xp)*2+1, (yp-ymx)*2+1,
                                    0, 1440)
                    painter.drawArc(xp - (xp-xmn), yp - (yp-ymx),
                                    (xp-xmn)*2+1, (yp-ymx)*2+1,
                                    1440, 1440)
                    painter.drawArc(xp - (xp-xmn), yp - (ymn-yp),
                                    (xp-xmn)*2+1, (ymn-yp)*2+1,
                                    2880, 1440)
                    painter.drawArc(xp - (xmx-xp), yp - (ymn-yp),
                                    (xmx-xp)*2+1, (ymn-yp)*2+1,
                                    4320, 1440)

    def _autoAxis(self, dataname, bounds):
        """Determine range of data."""
        if self.document.hasData(dataname):
            range = self.document.getData(dataname).getRange()
            bounds[0] = min( bounds[0], range[0] )
            bounds[1] = max( bounds[1], range[1] )

    def autoAxis(self, name, bounds):
        """Automatically determine the ranges of variable on the axes."""

        s = self.settings
        if name == s.xAxis:
            self._autoAxis( s.xData, bounds )
        elif name == s.yAxis:
            self._autoAxis( s.yData, bounds )

    def _drawPlotLine( self, painter, xvals, yvals, posn ):
        """Draw the line connecting the points."""

        pts = []

        s = self.settings
        steps = s.PlotLine.steps

        # simple continuous line
        if steps == 'off':
            for xpt, ypt in itertools.izip(xvals, yvals):
                pts.append(xpt)
                pts.append(ypt)

        # stepped line, with points on left
        elif steps == 'left':
            for x1, x2, y1, y2 in itertools.izip(xvals[:-1], xvals[1:],
                                                 yvals[:-1], yvals[1:]):
                pts += [x1, y1, x2, y1, x2, y2]

        # stepped line, with points on right
        elif steps == 'right':
            for x1, x2, y1, y2 in itertools.izip(xvals[:-1], xvals[1:],
                                                 yvals[:-1], yvals[1:]):
                pts += [x1, y1, x1, y2, x2, y2]
            
        # stepped line, with points in centre
        # this is complex as we can't use the mean of the plotter coords,
        #  as the axis could be log
        elif steps == 'centre':
            xv = self.document.getData(s.xData)
            axes = self.parent.getAxes( (s.xAxis, s.yAxis) )
            xcen = axes[0].graphToPlotterCoords(posn,
                                                0.5*(xv.data[:-1]+xv.data[1:]))

            for x1, x2, xc, y1, y2 in itertools.izip(xvals[:-1], xvals[1:],
                                                     xcen,
                                                     yvals[:-1], yvals[1:]):
                pts += [x1, y1, xc, y1, xc, y2, x2, y2]

        else:
            assert 0

        painter.drawPolyline( qt.QPointArray(pts) )

    def drawKeySymbol(self, painter, x, y, width, height):
        """Draw the plot symbol and/or line."""

        s = self.settings
        yp = y + height/2

        # draw line
        if not s.PlotLine.hide:
            painter.setPen( s.PlotLine.makeQPen(painter) )
            painter.drawLine(x, yp, x+width, yp)

        # draw marker
        if not s.MarkerLine.hide or not s.MarkerFill.hide:
            size = int( utils.cnvtDist(s.markerSize, painter) )

            if not s.MarkerFill.hide:
                painter.setBrush( s.MarkerFill.makeQBrush() )

            if not s.MarkerLine.hide:
                painter.setPen( s.MarkerLine.makeQPen(painter) )
            else:
                painter.setPen( qt.QPen( qt.Qt.NoPen ) )
                
            utils.plotMarker(painter, x+width/2, yp, s.marker, size)

    def getKeySymbolWidth(self, height):
        """Get preferred width of key symbol of height."""

        if not self.settings.PlotLine.hide:
            return 3*height
        else:
            return height

    def draw(self, parentposn, painter, outerbounds=None):
        """Plot the data on a plotter."""

        posn = GenericPlotter.draw(self, parentposn, painter,
                                   outerbounds=outerbounds)
        x1, y1, x2, y2 = posn

        # skip if there's no data
        d = self.document
        s = self.settings
        if not d.hasData(s.xData) or not d.hasData(s.yData):
            return
        
        # get axes widgets
        axes = self.parent.getAxes( (s.xAxis, s.yAxis) )

        # return if there's no proper axes
        if ( None in axes or
             axes[0].settings.direction != 'horizontal' or
             axes[1].settings.direction != 'vertical' ):
            return

        xvals = d.getData(s.xData)
        yvals = d.getData(s.yData)

        # no points to plot
        if xvals.empty() or yvals.empty():
            return

        # clip data within bounds of plotter
        painter.save()
        painter.setClipRect( qt.QRect(x1, y1, x2-x1, y2-y1) )

        # calc plotter coords of x and y points
        xplotter = axes[0].graphToPlotterCoords(posn, xvals.data)
        yplotter = axes[1].graphToPlotterCoords(posn, yvals.data)

        # plot data line
        if not s.PlotLine.hide:
            painter.setPen( s.PlotLine.makeQPen(painter) )
            self._drawPlotLine( painter, xplotter, yplotter, posn )

        # plot errors bars
        if not s.ErrorBarLine.hide:
            painter.setPen( s.ErrorBarLine.makeQPen(painter) )
            self._plotErrors(posn, painter, xplotter, yplotter,
                             axes)

        # plot the points (we do this last so they are on top)
        if not s.MarkerLine.hide or not s.MarkerFill.hide:
            size = int( utils.cnvtDist(s.markerSize, painter) )

            if not s.MarkerFill.hide:
                painter.setBrush( s.MarkerFill.makeQBrush() )

            if not s.MarkerLine.hide:
                painter.setPen( s.MarkerLine.makeQPen(painter) )
            else:
                painter.setPen( qt.QPen( qt.Qt.NoPen ) )
                
            utils.plotMarkers(painter, xplotter, yplotter, s.marker,
                              size)

        painter.restore()

# allow the factory to instantiate an x,y plotter
widgetfactory.thefactory.register( PointPlotter )

###############################################################################

class TextLabel(GenericPlotter):

    """Add a text label to a graph."""

    typename = 'label'
    description = "Text label"
    allowedparenttypes = [graph.Graph]
    allowusercreation = True

    def __init__(self, parent, name=None):
        GenericPlotter.__init__(self, parent, name=name)
        s = self.settings

        # text labels don't need key symbols
        s.remove('key')

        s.add( setting.Str('label', '',
                           descr='Text to show'), 0 )
        s.add( setting.Float('xPos', 0.5,
                             descr='x coordinate of the text'), 1 )
        s.add( setting.Float('yPos', 0.5,
                             descr='y coordinate of the text'), 2 )
        s.add( setting.Choice('positioning',
                              ['axes', 'relative'], 'relative',
                              descr='Use axes or fractional position to '
                              'place label'), 3)

        s.add( setting.Choice('alignHorz',
                              ['left', 'centre', 'right'], 'left',
                              descr="Horizontal alignment of label"), 4)
        s.add( setting.Choice('alignVert',
                              ['top', 'centre', 'bottom'], 'bottom',
                              descr='Vertical alignment of label'), 5)

        s.add( setting.Float('angle', 0.,
                             descr='Angle of the label in degrees'), 6 )

        s.add( setting.Text('Text',
                            descr = 'Text settings') )

        if type(self) == TextLabel:
            self.readDefaults()

    # convert text to alignments used by Renderer
    cnvtalignhorz = { 'left': -1, 'centre': 0, 'right': 1 }
    cnvtalignvert = { 'top': 1, 'centre': 0, 'bottom': -1 }

    def draw(self, parentposn, painter, outerbounds = None):
        """Draw the text label."""

        posn = GenericPlotter.draw(self, parentposn, painter,
                                   outerbounds=outerbounds)

        s = self.settings
        if s.positioning == 'axes':
            # translate xPos and yPos to plotter coordinates

            axes = self.parent.getAxes( (s.xAxis, s.yAxis) )
            xp = axes[0].graphToPlotterCoords(posn, N.array( [s.xPos] ))[0]
            yp = axes[1].graphToPlotterCoords(posn, N.array( [s.yPos] ))[0]
        else:
            # work out fractions inside pos
            xp = posn[0] + (posn[2]-posn[0])*s.xPos
            yp = posn[3] + (posn[1]-posn[3])*s.yPos

        if not s.Text.hide:
            textpen = s.get('Text').makeQPen()
            painter.setPen(textpen)
            font = s.get('Text').makeQFont(painter)

            utils.Renderer( painter, font, xp, yp,
                            s.label,
                            TextLabel.cnvtalignhorz[s.alignHorz],
                            TextLabel.cnvtalignvert[s.alignVert],
                            s.angle ).render()

# allow the factory to instantiate a text label
widgetfactory.thefactory.register( TextLabel )
