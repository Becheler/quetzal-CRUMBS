#!/usr/bin/python
from optparse import OptionParser
import io
import rasterio.plot
from rasterio.plot import show_hist

import imageio
from tqdm import tqdm
import numpy

def summary(dataset):
    print(" - no data value: \t", dataset.nodata )
    print(" - crs:\t", dataset.crs)
    print(" - ", dataset.bounds)
    pxsz, pysz = dataset.res
    print(" - pixel size X: \t", pxsz, "unit:", dataset.crs.linear_units)
    print(" - pixel size Y: \t", pysz, "unit:", dataset.crs.linear_units)
    print(" - width: \t", dataset.width)
    print(" - height: \t", dataset.height)
    return

def get_band(Z, i):
    """ Return the ith band of the (possibly masked) Z 3D array: if masked, fills masked values with nan.
    """
    z = Z[i].astype(float)
    if isinstance(z, numpy.ma.MaskedArray):
        z = z.filled(numpy.nan)  # Set masked values to nan
    return z

from mayavi import mlab

def get_points(shapefile):
    from shapely.geometry import shape
    import fiona
    lons, lats, years = ([] for i in range(3))
    with fiona.open(shapefile, mode='r') as source:
        print(source.crs)
        for feature in source:
            try:
                g = feature["geometry"]
                assert g["type"] == "Point"
                lon, lat = g["coordinates"]
                year = feature['properties']['Year']
                lons.append(float(lon))
                lats.append(float(lat))
                years.append(int(year))
            except IOError:
                logging.exception("Error processing feature %s:", feature["id"])
    return lons, lats, years

def make_X_Y_Z(raster_src):
    Z = raster_src.read(masked=True); Z=Z.filled(-1.0)
    nrows, ncols = Z[0].shape
    # the value returned by bounds is a tuple: (lower left x, lower left y, upper right x, upper right y)
    x = numpy.linspace(raster_src.bounds[0], raster_src.bounds[2], ncols)
    y = numpy.linspace(raster_src.bounds[1], raster_src.bounds[3], nrows)
    X, Y = numpy.meshgrid(x, y)
    return X, Y, Z

def plot_axes():
    import numpy as np
    xx = yy = zz = np.arange(start = 0.0, stop = 1300, step = 1)
    xy = xz = yx = yz = zx = zy = np.zeros_like(xx)
    lensoffset = 0
    mlab.plot3d(yx, yy + lensoffset, yz, line_width=10, tube_radius=10)
    mlab.plot3d(zx, zy + lensoffset, zz, line_width=10, tube_radius=10)
    mlab.plot3d(xx, xy + lensoffset, xz, line_width=10, tube_radius=10)

def decorate(surface, vmin, vmax):
    # Custom axes because mayavi defaults suck
    plot_axes()
    # Vertical colorbar
    mlab.colorbar(orientation='vertical')
    # Sets nan pixels to white
    surface.module_manager.scalar_lut_manager.lut.nan_color = 0, 0, 0, 0
    # Fix colorbar to global max/min
    surface.module_manager.scalar_lut_manager.use_default_range = False
    surface.module_manager.scalar_lut_manager.data_range = numpy.array([vmin, vmax])
    surface.update_pipeline()

@mlab.animate(delay=10, ui=False)
def update_animation(Z, surface, writer, DDD=False):

    figure = mlab.gcf()
    t = 2.0

    increment = 0.1 if DDD is True else 1.0

    sequence = numpy.arange(t, float(Z.shape[0]), increment)

    for i in tqdm(range(len(sequence))):

        if(DDD is True):
            figure.scene.camera.azimuth(1)
            figure.scene.render()

        t += increment
        surface.mlab_source.scalars = get_band(Z, int(t)-1)
        writer.append_data(mlab.screenshot())
        yield

def feature_scaling(x, xmin, xmax):
    return (x - xmin) / (xmax -xmin)

@mlab.animate(delay=10, ui=False)
def update_gbif_animation(output, xs, ys, zs, years, vmin, vmax, warp_scale):

    sorted_years = sorted(set(years))
    zipped = zip(xs, ys, zs, years)
    sorted_tuples = sorted(zipped, key=lambda x: x[3])

    figure = mlab.gcf()
    title = mlab.title(str(sorted_years[0]), color=(0,0,0), line_width=1, size=0.5)
    azimuth = 0.0
    tubes_dict = dict.fromkeys(sorted_years, [])

    with imageio.get_writer(output, mode='I') as writer:

        for year in tqdm(sorted_years):

            # Update title
            title.remove()
            title = mlab.title(str(year), color=(0,0,0), line_width=1, size= 0.5)

            # Fade others tubes a bit more
            for time, tubes in tubes_dict.items():
                for tube in tubes:
                    tube.actor.property.opacity = max(0, tube.actor.property.opacity - 0.1)

            # Plot the occurrences while rotating
            for i in sorted_tuples:

                if i[3] == year:

                    xx = [i[0], i[0]]
                    yy = [i[1], i[1]]
                    zz = [vmin, vmax*warp_scale]

                    # Update current year observations with max opacity
                    new_tube = mlab.plot3d(xx, yy, zz, line_width=5, tube_radius=5, opacity=1)
                    tubes_dict[year].append(new_tube)

                    # rotate the figure for each new tube
                    figure.scene.camera.azimuth(1)
                    azimuth += 1.0
                    figure.scene.render()
                    writer.append_data(mlab.screenshot())
                    yield

        while azimuth < 360.0:
            # continue rotating
            figure.scene.camera.azimuth(1)
            azimuth += 1.0
            figure.scene.render()
            writer.append_data(mlab.screenshot())
            yield

def animate_gbif(demRaster, gbif_occurrences, output=None, warp_scale=1.0):
    """Peforms a Delaunay 2D triangulation of the elevation surface before to plot the points for each year recorded.
    """
    import numpy
    import rasterio
    output = 'animation_occurrence.gif' if output is None else output

    with rasterio.open(demRaster) as source:
        print("- Elevation source dataset:", demRaster)
        summary(source)
        # Elevation surface
        X, Y, Z = make_X_Y_Z(source)

        vmax = numpy.amax(Z)
        vmin = numpy.amin(Z)
        extent = [0, Z.shape[2] - 1, 0, Z.shape[1] - 1, vmin, vmax]

        # initialize the figure
        fig = mlab.figure(1, bgcolor=(1, 1, 1))
        # initialize data source
        array_2d = get_band(Z, 0)

        # Retrieve GBIF occurrences to plot
        lons, lats, years = get_points(gbif_occurrences)
        points_ys, points_xs = rasterio.transform.rowcol(transform=source.transform, xs=lons, ys=lats)
        points_zs = [ array_2d[points_ys[i], points_xs[i]] for i in range(len(points_xs)) ]

        # initialize data source
        data = mlab.pipeline.array2d_source(array_2d)
        # Use a greedy_terrain_decimation to created a decimated mesh
        terrain = mlab.pipeline.greedy_terrain_decimation(data)
        terrain.filter.error_measure = 'number_of_triangles'
        terrain.filter.number_of_triangles = 10000
        terrain.filter.compute_normals = True
        # Plot it black the lines of the mesh
        lines = mlab.pipeline.surface(terrain, color=(0, 0, 0), representation='wireframe', extent=extent)
        # The terrain decimator has done the warping. We control the warping scale via the actor's scale.
        lines.actor.actor.scale = [1, 1, warp_scale]
        # Display the surface itself.
        surface = mlab.pipeline.surface(terrain, colormap='viridis', extent=extent)
        surface.actor.actor.scale = [1, 1, warp_scale]

        # Get current_scene
        s = mlab.get_engine().current_scene
        # Set the scene to an isometrwarp_scaleic view.
        s.scene.isometric_view()
        a = update_gbif_animation(output, points_xs, points_ys, points_zs, years, vmin, vmax, warp_scale)
        mlab.show()

def animate(inputRaster, vmin=None, vmax=None, output=None, gbif_occurrences=None, DDD=False, warp_scale=1.0):
    output = 'animation.gif' if output is None else output

    if gbif_occurrences is not None:
        animate_gbif(demRaster = inputRaster, gbif_occurrences = gbif_occurrences, output = output, warp_scale = warp_scale)

    else :
        with rasterio.open(inputRaster) as source:
            print("- Source dataset:", inputRaster)
            summary(source)

            # Elevation surface
            X, Y, Z = make_X_Y_Z(source)

            # Fix value extent across time dimension
            if vmax is None: vmax = numpy.amax(Z)
            if vmin is None: vmin = numpy.amin(Z)

            lons, lats, years = get_points(gbif_occurrences)
            points_ys, points_xs = rasterio.transform.rowcol(transform=source.transform, xs=lons, ys=lats)

            extent = [0, Z.shape[2] - 1, 0, Z.shape[1] - 1, vmin, vmax]

            writer = imageio.get_writer(output, mode='I')

            fig = mlab.figure(1, bgcolor=(1, 1, 1))

            array_2d = get_band(Z, 0)
            data = mlab.pipeline.array2d_source(array_2d)
            # Use a greedy_terrain_decimation to created a decimated mesh
            terrain = mlab.pipeline.greedy_terrain_decimation(data)
            terrain.filter.error_measure = 'number_of_triangles'
            terrain.filter.number_of_triangles = 10000
            terrain.filter.compute_normals = True
            # Plot it black the lines of the mesh
            lines = mlab.pipeline.surface(terrain, color=(0, 0, 0), representation='wireframe', extent=extent)
            # The terrain decimator has done the warping. We control the warping scale via the actor's scale.
            lines.actor.actor.scale = [1, 1, warp_scale]
            # Display the surface itself.
            surf = mlab.pipeline.surface(terrain, colormap='viridis', extent=extent)
            surf.actor.actor.scale = [1, 1, warp_scale]
            # Plot the occurrences
            print(surf.mlab_source)
            points_zs = [ array_2d[points_ys[i], points_xs[i]] for i in range(len(points_xs)) ]
            #points = mlab.points3d(points_xs, points_ys, points_zs, extent=extent)
            for i in range(len(points_zs)):
                xx = [points_xs[i], points_xs[i]]
                yy = [points_ys[i], points_ys[i]]
                zz = [vmin, vmax*warp_scale]
                mlab.plot3d(xx, yy, zz, line_width=5, tube_radius=5)
            # Get current_scene
            s = mlab.get_engine().current_scene
            # Set the scene to an isometrwarp_scaleic view.
            s.scene.isometric_view()
            #writer.append_data(mlab.screenshot())
            mlab.show()
            # if DDD is True:
            #     surface = mlab.surf(get_band(Z, 0), colormap='viridis', extent = extent)
            #     points_zs = [ Z[Z.shape[0]-1, points_ys[i], points_xs[i]]/warp_scale for i in range(len(points_xs)) ]
            # else:
            #     surface = mlab.imshow(get_band(Z, 0), colormap='viridis', extent = extent)
            #     # Observational points have no elevation
            #     points_zs = [0] * len(points_xs)
            #     # view surface along z axis (2D)
            #     mlab.view(0,0)

            # points = [points_xs, points_ys, points_zs]
            # decorate(surface, vmin, vmax)
            # mlab.points3d(points[0], points[1], points[2])
            # a = update_animation(Z, surface, writer,  DDD)
            # mlab.show()

def main(argv):
    parser = OptionParser()
    parser.add_option("-o", "--output", type="str", dest="output", help="output animation name")
    parser.add_option("-m", "--min", type="float", default=None, dest="min", help="min value in color scale")
    parser.add_option("-M", "--max", type="float", default=None, dest="max", help="max value in color scale")
    parser.add_option("-g", "--gbif", type="string", default=None, dest="gbif", help="Occurence file gotten from get_gbif")
    parser.add_option("-w", "--warp-scale", type="float", default=1.0, dest="warp_scale", help="Warp scale for the vertical axis.")
    parser.add_option("--DDD", dest="DDD", default = False, action = 'store_true', help="Plot a 3 dimensional version of the data")
    parser.add_option("--no-DDD", dest="DDD", action = 'store_false', help="Normal 2 dimension plot.")
    (options, args) = parser.parse_args(argv)
    return animate(args[0],
     vmin=options.min,
     vmax=options.max,
     output=options.output,
     gbif_occurrences=options.gbif,
     DDD=options.DDD,
     warp_scale=options.warp_scale)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
