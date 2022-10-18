def load():
    import pandas as pd

    data = pd.read_csv(
        "/home/chainje/sgr/stream_data/catalogue.txt", delim_whitespace=True
    )
    data = data.loc[data["g_mag"].values <= 18.5]
    return data


def to_cartesian(data, as_torch=True):
    import astropy.coordinates as coord
    import astropy.units as units

    sf = coord.SkyCoord(
        ra=data["ra"].values * units.deg,
        dec=data["dec"].values * units.deg,
        distance=data["dist"].values * units.kpc,
        frame=coord.ICRS,
    )
    sf_gal = sf.transform_to(coord.Galactocentric)

    if as_torch:
        import torch

        return torch.stack(
            (
                torch.tensor(sf_gal.x),
                torch.tensor(sf_gal.y),
                torch.tensor(sf_gal.z),
            ),
            dim=-1,
        )
    else:
        import numpy as np

        return np.stack(
            (
                np.array(sf_gal.x),
                np.array(sf_gal.y),
                np.array(sf_gal.z),
            ),
            axis=-1,
        )
