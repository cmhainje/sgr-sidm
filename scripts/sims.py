"""
sims.py
Author: Connor Hainje (cmhainje@gmail.com)

One stop shop for running a scan's simulations.

Two subcommands, to be run IN THIS ORDER:
- make: makes the directories and paramfiles for all the relevant jobs
- submit: submits the GIZMO jobs to the job queue
"""

import subprocess
from argparse import ArgumentParser
from glob import glob
from os.path import join


def parse():
    ap = ArgumentParser()
    subparsers = ap.add_subparsers(dest="subcommand", required=True)

    maker = subparsers.add_parser("make", help="make directories and paramfiles")
    maker.add_argument(
        "--scan_dir", type=str, required=True, help="base directory for this new scan"
    )
    maker.add_argument(
        "--ic_dir", type=str, help="base directory containing IC files (GalIC jobs)"
    )
    maker.add_argument("--params", type=str, help="params.csv file created by ic.py")
    maker.add_argument(
        "--dm_cross_section",
        type=float,
        default=0,
        help="cross section for DM self-interactions (default: 0)",
    )
    maker.add_argument(
        "--dm_velocity_scale",
        type=float,
        default=0,
        help="velocity scale for DM self-interactions (default: 0)",
    )
    maker.add_argument(
        "--jobtime",
        type=str,
        default="1-12:00:00",
        help="amount of time to ask for on SLURM queue",
    )

    submitter = subparsers.add_parser("submit", help="submit GIZMO jobs")
    submitter.add_argument(
        "--scan_dir", type=str, required=True, help="base directory for this scan"
    )

    args = ap.parse_args()
    return args


def make(args):
    import pandas as pd
    from numpy import cos, sin, radians
    from os import makedirs

    params = pd.read_csv(args.params, index_col=0)

    for i, row in params.iterrows():

        # make the directory
        folder = join(args.scan_dir, f"{i:03d}")
        makedirs(folder, exist_ok=True)

        # compute the initial velocity
        vx = -row["v"] * cos(radians(row["theta"]))
        vz = row["v"] * sin(radians(row["theta"]))

        make_filename = join(folder, "make.sh")
        cmd1 = "\\\n\t".join(
            [
                f"python ~/gtools/scripts/combine.py",
                f"{args.ic_dir}/mw.hdf5",
                f"{args.ic_dir}/sgr_{int(row.M)}.hdf5",
                f"-o {folder}/ic.hdf5",
                f"--pos 0 0 0 125 0 0",
                f"--vel 0 0 0 {vx:.3f} 0 {vz:.3f}",
                f"--r_trunc 500 50",
            ]
        )

        cmd2_lines = [
            "python -m cpg.gizmo",
            f'--name "{i:03d}"',
            f"--location {folder}",
            f"--icpath {folder}/ic",
            f"--output {folder}/output",
            f'--jobtime "{args.jobtime}"',
            "--ntasks 10",
        ]

        if args.dm_cross_section != 0:
            cmd2_lines += [
                "--gizmo /home/chainje/gizmo-sidm/GIZMO",
                f"--dm_cross_section {args.dm_cross_section}",
                f"--dm_velocity_scale {args.dm_velocity_scale}",
            ]

        cmd2 = "\\\n\t".join(cmd2_lines)

        with open(make_filename, "w") as f:
            f.write("#!/bin/bash")
            f.write("\n")
            f.write(cmd1)
            f.write("\n")
            f.write(cmd2)

    def run_script(folder):
        """Runs the make.sh script in folder."""
        subprocess.run(["sh", join(folder, "make.sh")], check=True)

    print("Running the `make.sh` scripts we just made.")
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
