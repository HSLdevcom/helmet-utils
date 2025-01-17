import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional, Dict

class ZoneDataReader:
    def __init__(self, zones_filepath: str, zonedata_directory: str):
        self.zones = gpd.read_file(zones_filepath)
        self.landuse = self._extract_df_from_zonedata(zonedata_directory, '*.lnd')
        self.population = self._extract_df_from_zonedata(zonedata_directory, '*.pop')
        self.work = self._extract_df_from_zonedata(zonedata_directory, '*.wrk')
        self.car_cost = self._extract_df_from_zonedata(zonedata_directory, '*.cco')
        self.transit_cost = self._extract_df_from_zonedata(zonedata_directory, '*.tco')

    def _extract_df_from_zonedata(self, directory: str, pattern: str) -> pd.DataFrame:
        file = next(Path(directory).glob(pattern), None)
        if file:
            return pd.read_csv(file, sep="\t", comment="#", index_col=0)
        else:
            raise FileNotFoundError(f"No file matching pattern {pattern} found in {directory}")

    def calculate_built_area(self, corine_raster: str, year: int, area_changes: Optional[Dict[int, int]] = None, output_path: str = ''):
        try:
            import rasterstats
        except ImportError:
            raise ImportError("The 'rasterstats' library is required to calculate built area.")

        if not self.landuse.exists() or not Path(corine_raster).exists() or not self.zones.exists():
            raise FileNotFoundError("One or more file paths do not exist.")

        print(f"Corine landcover filepath: {corine_raster}")
        print(f"Target year: {year}")
        if area_changes:
            print(f"Area changes received: {area_changes}")

        output = Path(output_path) / f"{year}.lnd"

        sijoittelualueet = self.zones.to_crs('EPSG:3067')
        stats = rasterstats.zonal_stats(sijoittelualueet.geometry, corine_raster, categorical=True)

        df = pd.DataFrame(data=stats).fillna(0)
        df.index = sijoittelualueet['SIJ2019'].astype(int)
        df.index.name = None

        # Corine ids representing built area, then convert squares to km^2
        df['builtar'] = df.loc[:, 1:16].sum(axis=1) * 0.0004
        df['detach'] = self.landuse['detach']
        df = df.sort_index()

        area_changes_mapped = {i: int(original) for original, new in area_changes.items() for i in new}
        df = self._calculate_detach_share_for_region(df, area_changes_mapped, self.landuse)
        df = df[['builtar', 'detach']]

        with open(output, 'a') as f:
            f.write('# Land use 2023\n#\n# builtar: area of built environment\n# detach: detached houses as share of total number of houses\n#\n')
            df.to_csv(f, float_format='%.4g', sep="\t", line_terminator="\n")

    def _calculate_detach_share_for_region(self, df: pd.DataFrame, area_changes_mapped: Dict[int, int], original_lnd: pd.DataFrame) -> pd.DataFrame:
        for i in area_changes_mapped.keys():
            df.loc[i, 'detach'] = original_lnd.loc[area_changes_mapped[i], 'detach']
        return df