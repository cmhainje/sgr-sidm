"""
ic.py
Author: Connor Hainje (cmhainje@gmail.com)

One stop shop for creating a new scan's initial conditions files.

Two subcommands, to be run IN THIS ORDER:
- make: makes the directories and paramfiles for all the relevant jobs
- submit: submits the GalIC jobs to the job queue
"""

import subprocess
from glob import glob
from argparse import ArgumentParser
from os import makedirs
from os.path import join

from gtools.models import dutton_maccio, Virial, NFW


def parse():
    ap = ArgumentParser()
    subparsers = ap.add_subparsers(dest="subcommand", required=True)

    maker = subparsers.add_parser("make", help="make directories and paramfiles")
    maker.add_argument(
        "--scan_dir",
        type=str,
        required=True,
        help="base directory to write initial conditions to",
    )
    maker.add_argument(
        "--N_MW",
        type=int,
        default=1_000_000,
        help="total number of MW particles (used to set the mass resolution)",
    )
    maker.add_argument(
        "--star_dm_ratio",
        type=float,
        default=10.0,
        help="ratio of (star/dark matter) particle masses",
    )
    maker.add_argument(
        "--sgr_halo_bulge_ratio",
        type=float,
        default=18.0,
        help="ratio of Sgr (halo/bulge) mass",
    )

    submitter = subparsers.add_parser("submit", help="submit GalIC jobs to SLURM queue")
    submitter.add_argument(
        "--scan_dir",
        type=str,
        required=True,
        help="base directory to submit GalIC jobs from",
    )

    args = ap.parse_args()
    return args


def make(args):
    import pandas as pd
    from itertools import product

    velocities = [50, 70, 90, 110, 130, 150]
    thetas = [40, 50, 60, 70, 80, 90]
    masses = [1e9, 10**9.5, 1e10, 10**10.5, 1e11]

    N_total = args.N_MW
    star_dm_ratio = args.star_dm_ratio

    # Sagittarius halo/bulge mass ratio
    halo_bulge_ratio = args.sgr_halo_bulge_ratio

    # Milky Way parameters: only modify these if you know what you're doing
    MW_halo = 1e12
    MW_disk = 6.5e10
    MW_bulge = 1e10

    # Helpful constants for later
    MW_total = MW_halo + star_dm_ratio * (MW_disk + MW_bulge)
    mass_per_particle = MW_total / N_total

    # Logging
    print(f"N total (MW): {N_total}")
    print(f"Star/DM ratio: {star_dm_ratio}")
    print(f"Mass per DM particle:   {mass_per_particle:.4e} M_sun")
    print(f"Mass per star particle: {mass_per_particle / star_dm_ratio:.4e} M_sun")
    print(f"Sgr halo/bulge mass ratio: {halo_bulge_ratio}")
    print()

    # *** Saving the specified parameters to a CSV ***

    data = dict(
        (i, {"v": float(v), "theta": float(theta), "M": masses.index(M), "M_real": M})
        for i, (v, theta, M) in enumerate(product(velocities, thetas, masses))
    )
    df = pd.DataFrame.from_dict(data, orient="index")
    df.to_csv("params.csv")
    print(f"Parameters saved to params.csv")
    print()

    # *** Making the Milky Way ***

    N_disk = int(star_dm_ratio * MW_disk / mass_per_particle)
    N_bulge = int(star_dm_ratio * MW_bulge / mass_per_particle)
    N_halo = N_total - N_disk - N_bulge

    # Write out the GalIC paramfile for the MW
    mw_folder = join(args.scan_dir, "mw")
    makedirs(mw_folder, exist_ok=True)
    fname = join(mw_folder, "make.sh")
    with open(fname, "w") as f:
        cmd = " \\\n \t".join(
            [
                f"python -m cpg.galic",
                f"--jobtime 6:00:00",
                f'--name "mw"',
                f"--redshift 0",
                f"--n_halo {N_halo}",
                f"--M_halo {MW_halo:.3e}",
                f"--c 10",
                f"--n_disk {N_disk}",
                f"--M_disk {MW_disk:.3e}",
                f"--disk_scale 3.5",
                f"--disk_height 0.53",
                f"--n_bulge {N_bulge}",
                f"--M_bulge {MW_bulge:.3e}",
                f"--bulge_scale 0.70",
            ]
        )
        f.write(f"#!/bin/bash\n\n{cmd}")

    print("Host galaxy:")
    print(f"  N halo:  {N_halo}")
    print(f"  N disk:  {N_disk}")
    print(f"  N bulge: {N_bulge}")
    print(f"  N total: {N_halo + N_disk + N_bulge}")
    print(f"  make script written to {mw_folder}/make.sh")
    print()

    # *** Making the Sagittarii ***

    v = Virial(redshift=1)

    for i, M_halo in enumerate(masses):

        N_halo = int(M_halo / mass_per_particle)
        M_bulge = M_halo / halo_bulge_ratio
        N_bulge = int(star_dm_ratio * M_bulge / mass_per_particle)
        c_halo = dutton_maccio(M_halo, v=v)

        bulge_scale = NFW.from_M200_c200(M_halo, c_halo, redshift=1).r_s / 6

        sgr_folder = join(args.scan_dir, "sgr", f"{i}")
        makedirs(sgr_folder, exist_ok=True)
        fname = join(sgr_folder, "make.sh")
        with open(fname, "w") as f:
            cmd = " \\\n \t".join(
                [
                    "python -m cpg.galic",
                    f"--jobtime 2:00:00",
                    f'--name "sgr_{i}"',
                    "--redshift 0",
                    f"--n_halo {N_halo}",
                    f"--M_halo {M_halo:.3e}",
                    f"--c {c_halo:.3f}",
                    f"--n_bulge {N_bulge}",
                    f"--M_bulge {M_bulge:.3e}",
                    f"--bulge_scale {bulge_scale:.3f}",
                    "--n_disk 0",
                ]
            )
            f.write(f"#!/bin/bash\n\n{cmd}")

        print("Satellite galaxy:")
        print(f"  N halo:  {N_halo}")
        print(f"  N bulge: {N_bulge}")
        print(f"  N total: {N_halo + N_bulge}")
        print(f"  M halo:  {M_halo}")
        print(f"  M bulge: {M_bulge}")
        print(f"  M_total: {M_halo + M_bulge}")
        print(f"  c_halo:  {c_halo}")
        print(f"  make script written to {sgr_folder}/make.sh")
        print()

    # *** Run all those 'make.sh' scripts we just made ***
    print("Running the `make.sh` scripts we just made.")

    def run_script(folder):
        """Runs the make.sh script in `folder`."""
        subprocess.run(["sh", join(folder, "make.sh")], check=True)

    run_script(join(args.scan_dir, "mw"))
    for sgr in sorted(glob(join(args.scan_dir, "sgr", "*"))):
        run_script(sgr)


def submit(args):
    def run_script(folder):
        """Submits the run_galic.sh script in `folder` to the job queue."""
        subprocess.run(["sbatch", join(folder, "run_galic.sh")], check=True)

    run_script(join(args.scan_dir, "mw"))
    for sgr in sorted(glob(join(args.scan_dir, "sgr", "*"))):
        run_script(sgr)


if __name__ == "__main__":
    args = parse()

    if args.subcommand == "make":
        make(args)
    elif args.subcommand == "submit":
        submit(args)
