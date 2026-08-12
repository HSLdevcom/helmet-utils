import rasterstats
import geopandas as gpd
import pandas as pd

from pathlib import Path

class BuiltArea:
    """
    A class to recalculate the built area of assignment zones based on landcover data and zone borders.

    ...

    Attributes
    ----------
    landuse_filepath : str
        Filepath of the original .lnd file as a string.
    landcover_filepath : str
        Filepath of the landcover file to be used in calculating the built area as a string. 
        In projects with new land use development, the landcover file can be modified.
        CRS is expected to be EPSG 3067.
    zones_filepath : str
        Filepath of the shapefile representing the zones as a string, modified according to
        the needs of the project.
        CRS is expected to be EPSG 3879.
    area_changes : dict
        A dictionary describing zone area changes, where keys are original zone IDs,
        and values are lists of new zone IDs.

        E.g., {292: [292, 295]} indicates that zone 292 has been split into two, 
        with one half retaining the original ID and the other assigned a new ID
        that corresponds to a new centroid in EMME, following the numbering conventions 
        described in helmet-docs.

    Methods
    -------
    calculate(year, output_path=""):
        Calculates the share of built area for each assignment zone.
    
        Parameters:
            year : int
                Year of the examination in question. Used in naming the output .lnd file.
            output_path : str, optional
                Path of the output .lnd file as a string. If not provided, a default path is used.

    """
    
    def __init__(self, landuse, landcover, zones, year, area_changes):
        self.landuse = Path(landuse)
        self.landcover = Path(landcover)
        self.zones = Path(zones)
        self.year = year
        self.area_changes = area_changes
    
    def calculate(self, output_path=""):
        # Check if file paths exist
        if not self.landuse.exists() or not self.landcover.exists() or not self.zones.exists():
            print("One or more file paths do not exist.")
            return

        print(f"Landuse filepath: {self.landuse}")
        print(f"Landcover filepath: {self.landcover}")
        print(f"Zones filepath: {self.zones}")
        print(f"Target year: {self.year}")
        print(f"Area changes received: {self.area_changes}")


        output = output_path + str(self.year) + ".lnd"

        original_lnd = pd.read_csv(self.landuse, sep="\t", comment="#", index_col=0)

        sijoittelualueet = gpd.read_file(self.zones)
        sijoittelualueet.crs = 'EPSG:3879'
        sijoittelualueet = sijoittelualueet.to_crs('EPSG:3067')
        stats = rasterstats.zonal_stats(sijoittelualueet.geometry, self.landcover, categorical=True)

        df = pd.DataFrame(data=stats)

        df = df.fillna(0)
        df.index = sijoittelualueet['SIJ2019'].astype(int)
        df.index.name = None

        # Corine ids representing built area, then convert squares to km^2
        df['builtar'] = (df[1] + df[2] + df[3] + df[4]+ df[5] + df[6] + df[7] + df[8] + df[9] + df[10] + df[11] + df[12] + df[13] + df[14] + df[15] + df[16])*0.0004
        df['detach'] = original_lnd['detach']
        df = df.sort_index()

        area_changes_mapped = {}
        area_changes_mapped = {i: int(original) for original, new in self.area_changes.items() for i in new}

        df = self._calculate_detach_share_for_region(df, area_changes_mapped, original_lnd)
        df = df[['builtar','detach']]

        f = open(output, 'a')
        f.write('# Land use 2023\n#\n# builtar: area of built environment\n# detach: detached houses as share of total number of houses\n#\n')

        df.to_csv(f, float_format='%.4g', sep="\t", line_terminator="\n")
        f.close()
        return
    
    def _calculate_detach_share_for_region(self, df, area_changes_mapped, original_lnd):
        for i in area_changes_mapped.keys():
            df.loc[i]['detach'] = original_lnd.loc[area_changes_mapped[i]]['detach']
        return df