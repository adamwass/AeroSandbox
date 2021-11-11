from aerosandbox import AeroSandboxObject
from aerosandbox.geometry.common import *
from typing import List, Dict, Any, Union
from numpy import pi
from textwrap import dedent
from pathlib import Path
import aerosandbox.geometry.mesh_utilities as mesh_utils


class Airplane(AeroSandboxObject):
    """
    Definition for an airplane.
    """

    def __init__(self,
                 name: str = "Untitled",  # A sensible name for your airplane.
                 xyz_ref: np.ndarray = np.array([0, 0, 0]),  # Ref. point for moments; should be the center of gravity.
                 wings: List['Wing'] = None,  # A list of Wing objects.
                 fuselages: List['Fuselage'] = None,  # A list of Fuselage objects.
                 s_ref: float = None,  # If not set, populates from first wing object.
                 c_ref: float = None,  # See above
                 b_ref: float = None,  # See above
                 analysis_specific_options: Dict[type, Dict[type, Dict[str, Any]]] = {}
                 # dict of analysis-specific options dicts in form {analysis: {"option": value}}, e.g. {AeroSandbox.AVL: {"component": 1}}
                 ):
        ### Initialize
        self.name = name

        self.xyz_ref = np.array(xyz_ref)

        ## Add the wing objects
        if wings is not None:
            self.wings = wings
        else:
            self.wings: List['Wing'] = []

        ## Add the fuselage objects
        if fuselages is not None:
            self.fuselages = fuselages
        else:
            self.fuselages: List['Fuselage'] = []

        ## Assign reference values
        try:
            main_wing = self.wings[0]
            if s_ref is None:
                s_ref = main_wing.area()
            if c_ref is None:
                c_ref = main_wing.mean_aerodynamic_chord()
            if b_ref is None:
                b_ref = main_wing.span()
        except IndexError:
            pass
        self.s_ref = s_ref
        self.c_ref = c_ref
        self.b_ref = b_ref

        self.analysis_specific_options = __class__.parse_analysis_specific_options(analysis_specific_options)

    def __repr__(self):
        n_wings = len(self.wings)
        n_fuselages = len(self.fuselages)
        return f"Airplane '{self.name}' " \
               f"({n_wings} {'wing' if n_wings == 1 else 'wings'}, " \
               f"{n_fuselages} {'fuselage' if n_fuselages == 1 else 'fuselages'})"

    def mesh_body(self,
                  method="quad",
                  thin_wings=False,
                  stack_meshes=True,
                  ):
        """
        Returns a surface mesh of the Airplane, in (points, faces) format. For reference on this format,
        see the documentation in `aerosandbox.geometry.mesh_utilities`.

        Args:

            method:

            thin_wings: Controls whether wings should be meshed as thin surfaces, rather than full 3D bodies.

            stack_meshes: Controls whether the meshes should be merged into a single mesh or not.

                * If True, returns a (points, faces) tuple in standard mesh format.

                * If False, returns a list of (points, faces) tuples in standard mesh format.

        Returns:

        """
        if thin_wings:
            wing_meshes = [
                wing.mesh_thin_surface(
                    method=method,
                )
                for wing in self.wings
            ]
        else:
            wing_meshes = [
                wing.mesh_body(
                    method=method,
                )
                for wing in self.wings
            ]

        fuse_meshes = [
            fuse.mesh_body(
                method=method
            )
            for fuse in self.fuselages
        ]

        meshes = wing_meshes + fuse_meshes

        if stack_meshes:
            points, faces = mesh_utils.stack_meshes(*meshes)
            return points, faces
        else:
            return meshes

    def draw(self,
             backend: str = "pyvista",
             thin_wings: bool = False,
             show: bool = True,
             show_kwargs=None,
             ):
        """

        Args:

            backend: One of:
                * "plotly" for a Plot.ly backend
                * "pyvista" for a PyVista backend
                * "trimesh" for a trimesh backend

            thin_wings: A boolean that determines whether to draw the full airplane (i.e. thickened, 3D bodies), or to use a
            thin-surface representation for any Wing objects.

            show: Should we show the visualization, or just return it?

        Returns: The plotted object, in its associated backend format. Also displays the object if `show` is True.

        """
        if show_kwargs is None:
            show_kwargs = {}

        if backend == "plotly":

            points, faces = self.mesh_body(method="quad", thin_wings=thin_wings)

            from aerosandbox.visualization.plotly_Figure3D import Figure3D
            fig = Figure3D()
            for f in faces:
                fig.add_quad((
                    points[f[0]],
                    points[f[1]],
                    points[f[2]],
                    points[f[3]],
                ), outline=True)
                show_kwargs = {
                    "show": show,
                    **show_kwargs
                }
            return fig.draw(**show_kwargs)
        elif backend == "pyvista":

            points, faces = self.mesh_body(method="quad")

            import pyvista as pv
            fig = pv.PolyData(
                *mesh_utils.convert_mesh_to_polydata_format(points, faces)
            )
            show_kwargs = {
                "show_edges": True,
                "show_grid" : True,
                **show_kwargs,
            }
            if show:
                fig.plot(**show_kwargs)
            return fig
        elif backend == "trimesh":

            points, faces = self.mesh_body(method="tri")

            import trimesh as tri
            fig = tri.Trimesh(points, faces)
            if show:
                fig.show(**show_kwargs)
            return fig
        else:
            raise ValueError("Bad value of `backend`!")

    def is_entirely_symmetric(self):
        """
        Returns a boolean describing whether the airplane is geometrically entirely symmetric across the XZ-plane.
        :return: [boolean]
        """
        for wing in self.wings:
            if not wing.is_entirely_symmetric():
                return False
            for xsec in wing.xsecs:
                if not (xsec.control_surface_is_symmetric or xsec.control_surface_deflection == 0):
                    return False
                if not wing.symmetric:
                    if not xsec.xyz_le[1] == 0:
                        return False
                    if not xsec.twist == 0:
                        if not (xsec.twist_axis[0] == 0 and xsec.twist_axis[2] == 0):
                            return False
                    if not xsec.airfoil.CL_function(0, 1e6, 0, 0) == 0:
                        return False
                    if not xsec.airfoil.Cm_function(0, 1e6, 0, 0) == 0:
                        return False

        return True

    def aerodynamic_center(self, chord_fraction: float = 0.25):
        """
        Computes the location of the aerodynamic center of the wing.
        Uses the generalized methodology described here:
            https://core.ac.uk/download/pdf/79175663.pdf

        Args:
            chord_fraction: The position of the aerodynamic center along the MAC, as a fraction of MAC length.
                Typically, this value (denoted `h_0` in the literature) is 0.25 for a subsonic wing.
                However, wing-fuselage interactions can cause a forward shift to a value more like 0.1 or less.
                Citing Cook, Michael V., "Flight Dynamics Principles", 3rd Ed., Sect. 3.5.3 "Controls-fixed static stability".
                PDF: https://www.sciencedirect.com/science/article/pii/B9780080982427000031

        Returns: The (x, y, z) coordinates of the aerodynamic center of the airplane.
        """
        wing_areas = [wing.area(type="projected") for wing in self.wings]
        ACs = [wing.aerodynamic_center() for wing in self.wings]

        wing_AC_area_products = [
            AC * area
            for AC, area in zip(
                ACs,
                wing_areas
            )
        ]

        aerodynamic_center = sum(wing_AC_area_products) / sum(wing_areas)

        return aerodynamic_center
