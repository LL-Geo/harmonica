"""
Define a layer of prisms
"""
import numpy as np
import xarray as xr
import verde as vd

from .prism import prism_gravity


def prisms_layer(
    region,
    shape=None,
    spacing=None,
    adjust="spacing",
    pixel_register=False,
    bottom=None,
    top=None,
    properties=None,
):
    """
    Create a layer of prisms of equal size

    Build a regular grid of prisms of equal size on the horizontal directions
    with variable top and bottom boundaries and properties like density,
    magnetization, etc. The function returns a :class:`xarray.Dataset`
    containing ``easting``, ``northing``, ``top`` and ``bottom`` coordinates,
    and all physical properties as ``data_var`` s. The ``easting`` and
    ``northing`` coordinates correspond to the location of the center of each
    prism.

    The ``prisms_layer`` dataset accessor can be used to access special methods
    and attributes for the layer of prisms, like the horizontal dimensions of
    the prisms, getting the boundaries of each prisms, computing the
    gravitational fields generated by the prisms, etc. See :class:`PrismLayer`
    for the definition of these methods and attributes.

    Parameters
    ----------
    region : list = [W, E, S, N]
        The boundaries of the region for the layer of prisms in Cartesian
        coordinates and meters. Use ``pixel_register`` to choose if the region
        should be interpreted as the boundaries of the layer or the boundaries
        of the centers of the prisms.
    shape : tuple = (n_north, n_east) or None
        The number of prisms in the South-North and West-East directions,
        respectively.
    spacing : float, tuple = (s_north, s_east), or None
        The horizontal dimensions of the prisms in the South-North and
        West-East directions, respectively. The dimensions of the prisms are
        equivalent to the grid spacing on the same directions. A single value
        means that the spacing is equal in both directions. Spacing must be in
        meters.
    adjust : {'spacing', 'region'}
        Whether to adjust the spacing or the region if required. Ignored if
        *shape* is given instead of *spacing*. Defaults to adjusting the
        spacing.
    pixel_register : bool
        If True, the ``region`` will be interpreted as the boundaries of the
        layer, so there will be no mass outside the passed region. If False,
        the center of the prisms will be bounded to the passed ``region``,
        therefore the layer of prisms will be slightly padded outside the
        ``region``, more precisely by half of the horizontal dimensions of each
        prism. Default is False.
    bottom : float or None
        Upward coordinate of the bottom boundary of the prisms (in meters). If
        None, the bottom boundaries will be set to ``np.nan``.
    top : float or None
        Upward coordinate of the top boundary of the prisms (in meters). If
        None, the top boundaries will be set to ``np.nan``.
    properties : dict or None
        Dictionary containing the physical properties of the prisms. The keys
        must be strings that will be use to name the corresponding ``data_var``
        inside the :class:`xarray.Dataset`, while the values must be floats.
        All physical properties must be passed in SI units. If None, no
        ``data_var`` will be added to the :class:`xarray.Dataset`. Default is
        None.

    Returns
    -------
    dataset : :class:`xarray.Dataset`
        Dataset containing the coordinates of the center of each prism, the
        height of its top and bottom boundaries and its corresponding physical
        properties.

    See also
    --------
    harmonica.PrismsLayer

    Examples
    --------

    >>> # Define a layer of prisms
    >>> prisms = prisms_layer(
    ...     region=(0, 3, -2, 2),
    ...     spacing=1,
    ...     bottom=0,
    ...     top=2,
    ...     properties={"density": 2670},
    ... )
    >>> print(prisms)
    <xarray.Dataset>
    Dimensions:   (easting: 4, northing: 5)
    Coordinates:
      * easting   (easting) float64 0.0 1.0 2.0 3.0
      * northing  (northing) float64 -2.0 -1.0 0.0 1.0 2.0
        bottom    (northing, easting) float64 0.0 0.0 0.0 0.0 ... 0.0 0.0 0.0 0.0
        top       (northing, easting) float64 2.0 2.0 2.0 2.0 ... 2.0 2.0 2.0 2.0
    Data variables:
        density   (northing, easting) float64 2.67e+03 2.67e+03 ... 2.67e+03
    Attributes:
        coords_units:      meters
        properties_units:  SI
    >>> # Get the boundaries of the layer (will exceed the region)
    >>> print(prisms.prisms_layer.boundaries)
    (-0.5, 3.5, -2.5, 2.5)
    >>> # Get the boundaries of one of the prisms
    >>> prisms.prisms_layer.get_prism((0, 2))
    (1.5, 2.5, -2.5, -1.5, 0.0, 2.0)
    >>> # Compute gravity above the layer
    >>> g_z = prisms.prisms_layer.gravity((2.5, 0, 10), field="g_z")
    >>> print("{:.6f}".format(g_z))
    0.008231
    """  # noqa: W505
    dims = ("northing", "easting")
    if top is None:
        top = np.nan
    if bottom is None:
        bottom = np.nan
    coordinates = vd.grid_coordinates(
        region,
        shape=shape,
        spacing=spacing,
        adjust=adjust,
        pixel_register=pixel_register,
        extra_coords=[bottom, top],
    )
    # Generate xr.Dataset.
    # Would use vd.build_grid, but for now I copy paste the code:
    coords = {dims[1]: coordinates[0][0, :], dims[0]: coordinates[1][:, 0]}
    coords["bottom"] = (dims, coordinates[2])
    coords["top"] = (dims, coordinates[3])
    data_vars = None
    if properties:
        data_vars = {
            prop: (dims, value * np.ones_like(coordinates[0]))
            for prop, value in properties.items()
        }
    attrs = {"coords_units": "meters", "properties_units": "SI"}
    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


@xr.register_dataset_accessor("prisms_layer")
class PrismsLayer:
    """
    Defines dataset accessor for layer of prisms

    .. warning::

        This class is not intended to be initialized.
        Use the :func:`prisms_layer` accessor for accessing the methods and
        attributes of this class.

    See also
    --------
    harmonica.prisms_layer
    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        self._spacing = None
        self._size = None

    @property
    def spacing(self):
        """
        Spacing between center of prisms

        Returns
        -------
        s_north : float
            Spacing between center of prisms on the South-North direction.
        s_east : float
            Spacing between center of prisms on the West-East direction.
        """
        if self._spacing is None:
            self._spacing = (
                self._obj.northing.values[1] - self._obj.northing.values[0],
                self._obj.easting.values[1] - self._obj.easting.values[0],
            )
        return self._spacing

    @property
    def boundaries(self):
        """
        Boundaries of the layer

        Returns
        -------
        boundaries : tuple
            Boundaries of the layer of prisms in the following order: ``west``,
            ``east``, ``south``, ``north``.
        """
        s_north, s_east = self.spacing
        west = self._obj.easting.values.min() - s_east / 2
        east = self._obj.easting.values.max() + s_east / 2
        south = self._obj.northing.values.min() - s_north / 2
        north = self._obj.northing.values.max() + s_north / 2
        return west, east, south, north

    @property
    def size(self):
        """
        Return the total number of prisms on the layer

        Returns
        -------
        size : int
            Total number of prisms in the layer.
        """
        if self._size is None:
            self._size = self._obj.northing.size * self._obj.easting.size
        return self._size

    @property
    def shape(self):
        """
        Return the number of prisms on each direction

        Returns
        -------
        n_north : int
            Number of prisms on the South-North direction.
        n_east : int
            Number of prisms on the West-East direction.
        """
        return (self._obj.northing.size, self._obj.easting.size)

    def _get_prism_horizontal_boundaries(self, easting, northing):
        """
        Compute the horizontal boundaries of the prism

        Parameters
        ----------
        easting : float or array
            Easting coordinate of the center of the prism
        northing : float or array
            Northing coordinate of the center of the prism
        """
        west = easting - self.spacing[1] / 2
        east = easting + self.spacing[1] / 2
        south = northing - self.spacing[0] / 2
        north = northing + self.spacing[0] / 2
        return west, east, south, north

    def gravity(self, coordinates, field, **kwargs):
        """
        Computes the gravity generated by the layer

        All ``kwargs`` will be passed to :func:`harmonica.prism_gravity`.

        Parameters
        ----------
        coordinates : list or 1d-array
            List or array containing ``easting``, ``northing`` and ``upward``
            of the computation points defined on a Cartesian coordinate system.
            All coordinates should be in meters.
        field : str
            Gravitational field that wants to be computed.
            The available fields are:

            - Gravitational potential: ``potential``
            - Downward acceleration: ``g_z``

        Returns
        -------
        result : array
            Gravitational field generated by the prisms on the computation
            points.

        See also
        --------
        harmonica.prism_gravity
        """
        return prism_gravity(
            coordinates, self.get_prisms(), self._obj.density, field=field, **kwargs
        )

    def get_prisms(self):
        """
        Return the boundaries of each prism of the layer

        Returns
        -------
        prisms : 2d-array
            Array containing the boundaries of each prism of the layer.
            Each row contains the boundaries of each prism in the following
            order: ``west``, ``east``, ``south``, ``north``, ``bottom``,
            ``top``.
        """
        # The meshgrid must be done on this order (northing and then easting)
        # to follow the same index ordering as the data_vars
        northing, easting = np.meshgrid(
            self._obj.northing.values, self._obj.easting.values
        )
        west, east, south, north = self._get_prism_horizontal_boundaries(
            easting.ravel(), northing.ravel()
        )
        bottom = self._obj.bottom.values.ravel()
        top = self._obj.top.values.ravel()
        prisms = np.vstack((west, east, south, north, bottom, top)).T
        return prisms

    def get_prism(self, indices):
        """
        Return the boundaries of the chosen prism

        Parameters
        ----------
        indices : tuple
            Indices of the desired prism of the layer in  the following order:
            ``(index_northing, index_easting)``.

        Returns
        -------
        prism : tuple
           Boundaries of the prisms in the following order:
           ``west``, ``east``, ``south``, ``north``, ``bottom``, ``top``.
        """
        # Get the center of the prism
        center_easting = self._obj.easting.values[indices[1]]
        center_northing = self._obj.northing.values[indices[0]]
        # Calculate the boundaries of the prism
        west, east, south, north = self._get_prism_horizontal_boundaries(
            center_easting, center_northing
        )
        bottom = self._obj.bottom.values[indices]
        top = self._obj.top.values[indices]
        return west, east, south, north, bottom, top

    def __iter__(self):
        """
        Initialize iteration by setting counter to zero
        """
        self._n = 0
        return self

    def __next__(self):
        """
        Iterate over the prisms of the layer
        """
        if self._n >= self.size:
            raise StopIteration
        indices = np.unravel_index(self._n, shape=self.shape)
        prism = self.get_prism(indices)
        self._n += 1
        return prism
