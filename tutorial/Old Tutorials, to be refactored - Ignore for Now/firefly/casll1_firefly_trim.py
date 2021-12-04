import copy

from aerosandbox import *

opti = cas.Opti()  # Initialize an optimization environment


def variable(init_val, lb=None, ub=None):
    """
    Initialize attrib_name scalar design variable.
    :param init_val: Initial guess
    :param lb: Optional lower bound
    :param ub: Optional upper bound
    :return: The created variable
    """
    var = opti.variable()
    opti.set_initial(var, init_val)
    if lb is not None:
        opti.subject_to(var >= lb)
    if ub is not None:
        opti.subject_to(var <= ub)
    return var


def quasi_variable(val):
    """
    Initialize attrib_name scalar design variable.
    :param init_val: Initial guess
    :param lb: Optional lower bound
    :param ub: Optional upper bound
    :return: The created variable
    """
    var = opti.variable()
    opti.set_initial(var, val)
    opti.subject_to(var == val)
    return var


# Airfoils
generic_cambered_airfoil = Airfoil(
    CL_function=lambda alpha, Re, mach, deflection,: (  # Lift coefficient function
            (alpha * np.pi / 180) * (2 * np.pi) + 0.4550
    ),
    CDp_function=lambda alpha, Re, mach, deflection: (  # Profile drag coefficient function
            (1 + (alpha / 5) ** 2) * 2 * (0.074 / Re ** 0.2)
    ),
    Cm_function=lambda alpha, Re, mach, deflection: (  # Moment coefficient function
        0
    )
)
generic_airfoil = Airfoil(
    CL_function=lambda alpha, Re, mach, deflection,: (  # Lift coefficient function
            (alpha * np.pi / 180) * (2 * np.pi)
    ),
    CDp_function=lambda alpha, Re, mach, deflection: (  # Profile drag coefficient function
            (1 + (alpha / 5) ** 2) * 2 * (0.074 / Re ** 0.2)
    ),
    Cm_function=lambda alpha, Re, mach, deflection: (  # Moment coefficient function
        0
    )
)

# Fuselage sections
fuse_xsecs = []
x = cosspace(0, 0.480, 21)
c = np.max(x) - np.min(x)
x0 = np.min(x)
y = 0.065 / 2 * 10 * (
        + 0.2969 * ((x - x0) / c) ** 0.5
        - 0.1260 * ((x - x0) / c)
        - 0.3516 * ((x - x0) / c) ** 2
        + 0.2843 * ((x - x0) / c) ** 3
        - 0.1036 * ((x - x0) / c) ** 4
) + 0.024 / 2 * ((x - x0) / c)

airplane = Airplane(
    name="Firefly",
    x_ref=0.24,  # CG location
    y_ref=0,  # CG location
    z_ref=0,  # CG location
    fuselages=[
        Fuselage(
            name="Fuselage",
            x_le=0,
            y_le=0,
            z_le=0,
            symmetric=False,
            xsecs=[
                FuselageXSec(
                    x_c=x[i],
                    y_c=0,
                    z_c=0,
                    radius=y[i]
                ) for i in range(x.shape[0])
            ]
        )
    ],
    wings=[
        Wing(
            name="Main Wing",
            x_le=0.22,  # Coordinates of the wing's leading edge
            y_le=0,  # Coordinates of the wing's leading edge
            z_le=0.0325,  # Coordinates of the wing's leading edge
            symmetric=True,
            xsecs=[  # The wing's cross ("X") sections
                WingXSec(  # Root
                    x_le=0,  # Coordinates of the XSec's leading edge, relative to the wing's leading edge.
                    y_le=0,  # Coordinates of the XSec's leading edge, relative to the wing's leading edge.
                    z_le=0,  # Coordinates of the XSec's leading edge, relative to the wing's leading edge.
                    chord=0.07,
                    twist_angle=0,  # degrees
                    airfoil=generic_cambered_airfoil,  # Airfoils are blended between a given XSec and the next one.
                    control_surface_type='symmetric',
                    # Flap # Control surfaces are applied between a given XSec and the next one.
                    control_surface_deflection=0,  # degrees
                ),
                WingXSec(  # Mid
                    x_le=0.0602,
                    y_le=0.220,
                    z_le=0,
                    chord=0.0198,
                    twist_angle=0,
                    airfoil=generic_cambered_airfoil,
                ),
            ]
        ),
        Wing(
            name="Canard",
            x_le=0.0375,
            y_le=0.031,
            z_le=0,
            symmetric=True,
            xsecs=[
                WingXSec(  # tip
                    x_le=0.0,
                    y_le=0.0,
                    z_le=0.0,
                    chord=0.012,
                    twist_angle=variable(0, -30, 30),
                    airfoil=generic_airfoil,
                    control_surface_type='symmetric',  # Elevator
                    control_surface_deflection=0,
                ),
                WingXSec(  # root
                    x_le=0.00804,
                    y_le=0.06081,
                    z_le=0,
                    chord=0.012,
                    twist_angle=variable(0, -30, 30),
                    airfoil=generic_airfoil,
                ),
            ]
        ),
        Wing(
            name="Vtail",
            x_le=0,
            y_le=0,
            z_le=0,
            symmetric=True,
            xsecs=[
                WingXSec(
                    x_le=0.429,
                    y_le=0.0177,
                    z_le=0.0177,
                    chord=0.012,
                    twist_angle=0,
                    airfoil=generic_airfoil,
                    control_surface_type='symmetric',  # Rudder
                    control_surface_deflection=0,
                ),
                WingXSec(
                    x_le=0.439,
                    y_le=0.0518,
                    z_le=0.0518,
                    chord=0.012,
                    twist_angle=0,
                    airfoil=generic_airfoil
                )
            ]
        )
    ]
)
airplane.set_paneling_everywhere(1, 20)
ap = Casll1(  # Set up the AeroProblem
    airplane=airplane,
    op_point=OperatingPoint(
        velocity=100,
        alpha=5,
        beta=0,
        p=0,
        q=0,  # quasi_variable(0),
        r=0,
    ),
    opti=opti
)
# Set up the VLM optimization submatrix
ap._setup(run_symmetric_if_possible=True)

### Extra constraints
# Joint movements
opti.subject_to(airplane.wings[1].xsecs[0].twist == airplane.wings[1].xsecs[1].twist)
# Trim constraint
opti.subject_to(ap.Cm == 0)
# Stability constraint
# opti.subject_to(cas.gradient(ap.Cm, ap.op_point.alpha) == 0)

# Objective
# opti.minimize(-ap.CL_over_CDi)

# Solver options
p_opts = {}
s_opts = {}
s_opts["max_iter"] = 1e6  # If you need to interrupt, just use ctrl+c
s_opts["mu_strategy"] = "adaptive"
# s_opts["start_with_resto"] = "yes"
# s_opts["required_infeasibility_reduction"] = 0.1
opti.solver('ipopt', p_opts, s_opts)

# Solve
try:
    sol = opti.solve()
except RuntimeError:
    sol = opti.debug

# Create solved object
ap_sol = copy.deepcopy(ap)
ap_sol.substitute_solution(sol)

# Postprocess

ap_sol.draw()

print("CL:", ap_sol.CL)
print("CD:", ap_sol.CD)
print("CY:", ap_sol.CY)
print("Cl:", ap_sol.Cl)
print("Cm:", ap_sol.Cm)
print("Cn:", ap_sol.Cn)

# Answer you should get: (XFLR5)
# CL = 0.797
# CDi = 0.017
# CL/CDi = 47.211
