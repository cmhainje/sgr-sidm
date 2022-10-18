import gtools as gt
import numpy as np


def make_part_types(sim_dir):
    import json
    from os.path import join

    json_file = join(sim_dir, "ic.hdf5_summary.json")
    with open(json_file, "r") as f:
        counts = json.load(f)
    gizptypes = {"halo": "PartType1", "disk": "PartType2", "bulge": "PartType3"}
    ptypes = dict()
    for g, d in zip(["mw", "sgr"], counts.values()):
        for pt, n in d.items():
            if n == 0:
                continue
            ptypes[f"{g}_{pt}"] = {"type": gizptypes[pt], "number": n}
    return ptypes


def load_times_array():
    with open("/scratch/gpfs/chainje/scans/low/times.txt", "r") as f:
        times = np.array([float(line.strip()) for line in f.readlines()])
    return times


def open_reader(sim_dir):
    return gt.Reader(sim_dir, make_part_types(sim_dir), load_times_array())


def to_ICRS(*args):
    import astropy.coordinates as coord
    import astropy.units as u

    if len(args) == 3:
        x, y, z = args
        s = coord.CartesianRepresentation(x=x, y=y, z=z, unit=u.kpc)
    elif len(args) == 6:
        x, y, z, vx, vy, vz = args
        s = coord.CartesianRepresentation(x=x, y=y, z=z, unit=u.kpc)
        ds = coord.CartesianDifferential(d_x=vx, d_y=vy, d_z=vz, unit=u.km / u.s)
        s = s.with_differentials(ds)
    else:
        raise ValueError(
            "bad number of arguments. "
            "provide either `x, y, z` or `x, y, z, vx, vy, vz`."
        )

    galcen = coord.SkyCoord(s, frame=coord.Galactocentric)
    return galcen.transform_to(coord.ICRS)
