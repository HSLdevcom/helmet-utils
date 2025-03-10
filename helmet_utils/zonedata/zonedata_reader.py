import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional, Dict
from .zonedata import ZoneData

class ZoneDataReader:
    def __init__(self, zonedata_directory: str, zones_filepath: str=None, landcover_filepath: str=None):
        if not Path(zonedata_directory).exists():
            raise FileNotFoundError(f"Directory {zonedata_directory} does not exist.")
        if zones_filepath and not Path(zones_filepath).exists():
            raise FileNotFoundError(f"File {zones_filepath} does not exist.")
        elif not zones_filepath:
            default_zones = Path(__file__).resolve().parent.parent / 'data' / 'SIJ2023_aluejako.gpkg'
            self.zones = gpd.read_file(default_zones)
        else:
            self.zones = gpd.read_file(zones_filepath)

        if landcover_filepath and not Path(landcover_filepath).exists():
            raise FileNotFoundError(f"File {landcover_filepath} does not exist.")
        elif not landcover_filepath:
            self.landcover_file = Path(__file__).resolve().parent.parent / 'data' / 'landcover.tif'
        else:
            self.landcover_file = landcover_filepath
        
        self.landuse = self._extract_df_from_zonedata(zonedata_directory, '*.lnd')
        self.population = self._extract_df_from_zonedata(zonedata_directory, '*.pop')
        self.work = self._extract_df_from_zonedata(zonedata_directory, '*.wrk')
        self.edu = self._extract_df_from_zonedata(zonedata_directory, '*.edu')
        self.bks = self._extract_df_from_zonedata(zonedata_directory, '*.bks')


    def zonedata(self) -> ZoneData:
        return ZoneData(self.landuse, self.population, self.work, self.edu, self.bks, self.zones, self.landcover_file)
    
    def _extract_df_from_zonedata(self, directory: str, pattern: str) -> pd.DataFrame:
        file = next(Path(directory).glob(pattern), None)
        if file:
            return pd.read_csv(file, sep="\t", comment="#", index_col=0)
        else:
            raise FileNotFoundError(f"No file matching pattern {pattern} found in {directory}")
    
    def _calculate_detach_share_for_region(self, df: pd.DataFrame, area_changes_mapped: Dict[int, int], original_lnd: pd.DataFrame) -> pd.DataFrame:
        for i in area_changes_mapped.keys():
            df.loc[i, 'detach'] = original_lnd.loc[area_changes_mapped[i], 'detach']
        return df
    

def get_helmet_zonedata(zonedata_directory: str, zones_filepath: str=None, landcover_filepath: str=None) -> ZoneData:
    zondedata_reader = ZoneDataReader(zonedata_directory, zones_filepath=zones_filepath, landcover_filepath=landcover_filepath)
    return zondedata_reader.zonedata()