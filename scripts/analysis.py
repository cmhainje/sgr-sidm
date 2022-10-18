"""
analysis.py
Author: Connor Hainje (cmhainje@gmail.com)

Creates and submits jobs to the queue that compute a number
of useful metrics for analysis.
"""

import numpy as np
import torch
import h5py
import sgrana

from argparse import ArgumentParser
from glob import glob
from tqdm.auto import tqdm


def parse():
    ap = ArgumentParser()
    subparsers = ap.add_subparsers(dest="subcommand", required=True)

    cp = subparsers.add_parser("compute", help="make directories and paramfiles")
    cp.add_argument("scan_dir", type=str, required=True, help="scan directory")
    cp.add_argument("start", default=0, type=int)
    cp.add_argument("end", default=0, type=int)
    cp.add_argument("--params", type=str, required=True, help="params.csv filepath")

    sp = subparsers.add_parser("submit", help="submit compute job(s) to SLURM queue")
    sp.add_argument("scan_dir", type=str, required=True, help="scan directory")
    sp.add_argument("--n_jobs", type=int, default=10, help="number of array jobs")
    sp.add_argument("--scriptname", type=str, default="./temp.sh")
    sp.add_argument("--jobtime", type=str, default="1-00:00:00")
    sp.add_argument("--jobmem", type=str, default="12G")

    args = ap.parse_args()
    return args


def submit(args):
    import subprocess
    from jinja2 import FileSystemLoader, Environment
    from math import ceil

    job_size = ceil(180 / args.n_jobs)
    n_jobs = ceil(180 / job_size)

    # Make the slurm script
    file_loader = FileSystemLoader("/home/chainje/sgr/scripts")
    env = Environment(loader=file_loader)
    template = env.get_template("analysis_template.sh")
    output = template.render(
        job_t=args.jobtime,
        job_m=args.jobmem,
        n_jobs=n_jobs,
        scan_dir=args.scan_dir,
        job_size=job_size,
    )
    with open(args.scriptname, "w") as f:
        f.write(output)

    # Run it
    subprocess.run(["sbatch", args.scriptname])


def compute(args):
    data_tens = sgrana.sf.to_cartesian(sgrana.sf.load())

    sim_dirs = sorted(glob(f"{args.scan_dir}/[0-9][0-9][0-9]/output"))
    sim_dirs = [d.replace("/output", "") for d in sim_dirs]
    print(f"Found {len(sim_dirs)} simulations.")

    if args.end != 0:
        sim_dirs = sim_dirs[args.start : args.end]
        print(f"  Using sims from {args.start} to {args.end}")
    else:
        sim_dirs = sim_dirs[args.start :]
        print(f"  Using sims from {args.start} to end")

    outfile = h5py.File(f"./rdKS_{args.start}_{args.end}.h5", "w")

    for sim_dir in sim_dirs:
        sim = sgrana.open_reader(sim_dir)
        sim_num = sim_dir.replace(f"{args.scan_dir}/", "")
        iterator = range(len(sim.times))
        iterator = tqdm(iterator, desc=sim_dir, unit="snap")

        rdks_values = []
        bootstrap_trials = []

        for j in iterator:
            sim_tens = torch.tensor(sim.get_pos(j, "sgr_bulge"))
            rdks_values.append(sgrana.rdks(sim_tens, data_tens))
            bootstrap_trials.append(
                sgrana.bootstrap(
                    sim_tens, data_tens, n_trials=100, m=2000, use_tqdm=False
                )
            )

        rdks_values = np.array(rdks_values)
        bootstrap_trials = np.stack(bootstrap_trials, axis=0)

        outfile.create_dataset(f"{sim_num}/rdKS_bulge", data=rdks_values)
        outfile.create_dataset(f"{sim_num}/bootstraps_bulge", data=bootstrap_trials)

    outfile.close()


if __name__ == "__main__":
    args = parse()

    if args.subcommand == "compute":
        compute(args)
    elif args.subcommand == "submit":
        submit(args)
