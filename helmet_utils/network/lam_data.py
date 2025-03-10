import webbrowser
import pandas as pd
import datetime as dt
import geopandas as gpd
from pathlib import Path
import time
import requests
import re
import numpy as np
import io

from shapely.geometry import Point

class LamData:
    def __init__(self):
        self.lam_links = {
            23117: [[310376,300054], [222576,222575]],  # Vt1 - Turunväylä
            23103: [[300054,280061], [280062,222578]],
            20018: [[280061,197051], [197048,280062]],
            20016: [[197004,197005], [None, None]],
            23144: [[50073,40222], [40224,50074]],
            20010: [[40222,50070], [40225,50069]],
            20011: [[40223,197014], [196994,40225]], # 20013 dropped, perhaps average over 20011 and 20013
            20009: [[196922,198911], [198925,197043]],
            23167: [[198911,197033], [197094,198925]],
            20005: [[197033,300162], [300163,197094]],  # Same here with 20006
            20007: [[236329,196999], [185295,236152]],  # And here with 20004
            23175: [[196999,197024], [197037,185295]],
            20002: [[185283,239284], [185289,239319]],
            23139: [[43076,239286], [50068,43075]],
            23191: [[310493,183601], [181260,310494]],
            23192: [[50055,50083], [50084,50058]],
            23104: [[172605,131903], [161384,173149]],
            23193: [[50385,161396], [161406,50386]],
            23194: [[50391,300004], [300003,163134]],
            24607: [[181015,300006], [50394,166156]],
            24606: [[321809,300013], [300012,321810]],
            24605: [[300010,300017], [300016,300011]],
            24604: [[184858,321090], [321090,184840]],
            24603: [[321808,321091], [321091,321808]],
            24602: [[321091,321092], [321092,321091]],
            24601: [[321092,321807], [321807,321092]],
            23248: [[321093,321465], [321465,321093]],
            23247: [[321094,321095], [321095,321094]],
            23245: [[321095,34102], [34102,321095]],  # Connector to ext, perhaps add a node 
            23106: [[174525,174608], [174608,174525]],  # Vt2
            23122: [[140526,140429], [140429,140526]],
            23164: [[240756,42048], [40486,202909]],  # Vt3 - Hämeenlinnanväylä
            23152: [[199663,240759], [221802,204863]],
            23165: [[310225,310202], [218703,310203]],
            23107: [[220796,220797], [42020,220727]],
            23013: [[227517,227518], [41921,228919]],
            23004: [[280105,50343], [50342,50341]],
            23137: [[310339,50438], [50437,310340]],
            23005: [[210064,50347], [50346,208831]],  # Skipping old counters 20021 and 20027
            20024: [[50370,306080], [306082,50371]],
            20025: [[306079,50351], [50350,306081]],
            20026: [[None, None], [170337,50360]],
            23108: [[163166,150522], [150360,171417]],
            23429: [[50381,83958], [83974,50380]],
            23432: [[92275,321162], [321162,92853]],
            23465: [[321164,321165], [321165,321164]],
            23466: [[321165,322283], [322283,321165]],
            23437: [[321166,322292], [322292,321166]],
            23154: [[225892,50161], [50160,50153]],  # Vt4 - Lahdenväylä
            23109: [[310574,50285], [50284,310573]],
            23007: [[226186,310589], [310590,226100]],
            23008: [[205947,190887], [42608,205617]],
            23099: [[321811,229571], [222768,321812]],
            23110: [[321814,231846], [208158,321813]],
            23998: [[231732,230962], [50297,50296]],
            23142: [[321292,50325], [50326,208152]],
            23424: [[321399,321396], [321396,321399]],
            23470: [[322174,322176], [322175,322173]],
            23111: [[47875,47867], [47867,47875]],  # Vt6
            23015: [[46983,47039], [47039,46983]],  # Skipping 23014, model needs a couple of links to reach it
            23179: [[50136,227772], [227266,50137]],  # Vt7 - Porvoonväylä
            23119: [[227461,65574], [50169,227267]],
            23172: [[50211,50212], [65756,50210]],
            23176: [[66829,50023], [66031,65757]],
            23177: [[67684,67055], [66950,64303]],
            23141: [[50110,280010], [280009,50109]],
            23178: [[280014,62989], [63112,280015]],
            23112: [[50112,50118], [50117,50111]],
            23190: [[58157,58142], [60762,58149]],
            23198: [[50237,60760], [58163,50236]],
            23001: [[60760,59936], [58156,58163]],
            23184: [[58167,58165], [58159,60831]],
            23185: [[50194,50221], [50220,50193]],
            23186: [[47965,50279], [50278,49310]],
            23187: [[40429,50244], [50245,49854]],
            23188: [[40431,40433], [40432,44151]],
            23189: [[50235,50227], [50224,50226]],
            23425: [[322084,322088], [322088,322084]],  # Vt10
            23405: [[321253,321255], [321255,321253]],
            23426: [[321262,321261], [321261,321262]],  # Vt12
            23407: [[321288,321289], [321289,321288]],  # Lahden eteläinen kehätie 
            23468: [[322150,322153], [322157,322151]],
            23469: [[322156,322161], [322162,322160]],
            23124: [[159110,159114], [159114,159110]],  # Vt25
            23114: [[132585,42931], [42931,132585]],
            23129: [[163020,164313], [164313,163020]],
            23133: [[127722,130240], [130240,127722]],
            23130: [[231642,231643], [231643,231642]],
            23153: [[239362,239363], [239374,205330]],  # Kt45 - Tuusulanväylä
            23131: [[239370,50207], [50208,306155]],
            23009: [[205935,205964], [205976,205499]],
            23127: [[235233,233782], [233782,235233]],
            23125: [[210816,40302], [238032,40303]],  # Kt50 - Kehä III
            23012: [[238788,185280], [185288,198437]],
            23140: [[217821,217544], [217174,218169]],
            23183: [[217544,217554], [218158,217174]],
            23168: [[310267,220342], [220178,310263]],
            23159: [[310274,310276], [226140,310279]],
            23128: [[228903,50358], [50357,226155]],
            23169: [[228528,228529], [208400,228190]],
            23150: [[210104,210106], [210098,208812]],
            23160: [[185980,42815], [42816,185981]],
            23182: [[228887,40214], [227221,227222]],            
            23134: [[174823,174829], [174829,174823]],  # Kt51
            23156: [[183995,280133], [40311,40312]],
            23143: [[181748,183986], [40324,40325]],
            23102: [[238478,280134], [197062,300025]],
            23003: [[238836,280211], [238589,238609]],
            23098: [[195722,197029], [239895,198822]],
            23101: [[50444,195620], [198301,50443]],
            23115: [[400682,61298], [61298,400682]],  # Kt55 - Mäntsäläntie
            23197: [[205214,300032], [300032,205214]],  # St100 - Hakamäentie
            23118: [[198834,40340], [40484,196175]],  # St101 - Kehä I
            23010: [[198841,198842], [198921,198920]],
            23116: [[198824,198817], [210405,197026]],
            23126: [[50429,239387], [221915,50428]],
            23145: [[239390,212271], [213674,42043]],
            23146: [[239401,213563], [213723,221928]],
            23147: [[50433,50435], [50434,50432]],
            23148: [[214166,213240], [213893,213115]],
            23149: [[42473,214168], [214258,213997]],
            23011: [[222671,222672], [222691,222690]],
            23162: [[217719,197594], [41724,217418]],  # St102 - Kehä II
            23163: [[41720,280174], [280175,41721]],
            23006: [[197090,187155], [243058,198868]],
            23195: [[227970,225931], [225717,227028]],  # St103 - Satamatie (Kehä III)
            23105: [[181269,181283], [181283,181269]],  # St110 - Turuntie
            23201: [[321087,321088], [321088,321087]],
            23151: [[225726,310515], [310517,225690]],  # St120 - Vihdintie
            23123: [[310133,310124], [310233,310135]],
            20028: [[50228,50191], [50229,204905]],  # St170 - Itäväylä
            23121: [[400970,400972], [400972,400970]],  # Yt11888
            23196: [[205181,300048], [300048,205181]],  # Niinisaarentie
            23447: [[321372,322271], [322271,321372]],  # Mannerheiminkatu, Lahti
        }

        self.bike_lam_links = {
            1010: [43565,40211],
            1020: [204233,212408],
            1030: [40205,40206],
            1040: [200708,203644],
            1041: [203644,200708],
            1050: [208143,199943],
            1051: [204905,321825],
            1060: [202841,221129],
            1070: [240853,40350],
            1080: [40350,240853],
            1090: [199597,40538],
            1100: [221036,204952],
            1110: [204952,221036],
            1120: [201013,50507],
            1150: [50018,50016],
            1160: [202841,243006],
            1170: [50021,50022],
            1190: [199549,40466],
            1140: [200208,212933],
            1180: [208191,208192],
            2010: [801041,237662],
            2020: [236397,236395],
            2030: [300054,280061],
            2040: [280062,222578],
            2050: [239323,223875],
            2060: [40477,198921],
            2070: [321962,321963],
            2080: [237673,238138],
            2090: [321932,810051],
            2100: [321838,280057],
            2110: [195626,50095],
            2120: [340068,321510],
            2130: [195663,195664],
            2140: [217214,217213],
            2150: [40950,195639],
            2160: [40950,195639],
            2170: [228477,223984],
            2180: [801037,50011],
            2190: [195675,310360],
            2200: [195639,40950],
            2210: [320336,217837],
            2220: [310133,310124],
            2230: [198848,197671],
            4010: [219312,280024],
            4020: [218995,42414],
            4030: [42251,219609],
            4040: [219597,42389],
            4050: [226232,226289],
            4060: [239508,42740],
            4070: [226257,41056],
            4080: [205960,42667],
            4090: [42389,219597],
        }


        self.hel_link_map = {
            'HEL409 - Hämeentien silta': [[213936, 205306], [205306, 213936]],   
            'HEL411 - Kaivokatu': [[202841, 221129], [221129, 202841]],
            'HEL412 - Paciuksenkatu': [[240853, 40350], [40350, 240853]],      # Ei dataa
            'HEL501 - Ruskeasuo': [[221796, 40347], [40347, 221796]],
            'HEL504 - Hämeenlinnanväylä': [[213313, 240766], [221811, 212958]],  
            'HEL507 - Helsinginkatu': [[40410, 199549], [199549, 40410]],      
            'HEL508 - Hakaniemen silta': [[40420, 204685], [204685, 40420]],   
            'HEL509 - Lauttasaarensilta': [[203644, 200708], [200708, 203644]],  
            'HEL510 - Mäkelänkatu': [[201316, 280346], [280346, 201316]],      # Ei dataa 
            'HEL513 - Koskelantie': [[199915, 211689], [211689, 199915]],        
            'HEL516 - Metsäläntie': [[200943, 203855], [203855, 200943]],        
            'HEL528 - Kallvikintie': [[225505, 225504], [225504, 22505]],      # Ei dataa 
            'HEL529 - Ratapihantie': [[213397, 200219], [200219, 213397]],       
            'HEL533 - Siltasaarenkatu': [[222164, 222163], [222163, 222164]],    
            'HEL537 - Runeberginkatu': [[201739, 199101], [199101, 201739]],   # Ei dataa 
            'HEL539 - Ilmalankatu': [[42063, 42064], [42064, 42063]],        
            'HEL542 - Meilahdentie': [[199552, 201859], [201859, 199552]],       
            'HEL543 - Vanha Suutarilantie': [[211244, 42397], [42397, 211244]],
            'HEL545 - Veturitie': [[203175, 199020], [199020, 203175]],
            'HEL601 - Itäväylä': [[228197, 225504], [225504, 228197]],
            'HEL608 - Vanha Turuntie': [[218435, 217837], [217837, 218435]],   # Ei dataa 
            'HEL609 - Lapinlahdensilta': [[205059, 199920], [199880, 199913]],
            'HEL612 - Vanha Porvoontie': [[42814, 42839], [42839, 42814]],
            'HEL614 - Otaniemensilta': [[200018, 197763], [197763, 200018]],
            'Kalasataman tunneli, LML02/Itään': [[208143, 199943], [None, None]],
            'Kalasataman tunneli, LML01/Länteen': [[204905, 200231], [None, None]]
        }

    def parse_date(self, date):
        match = re.search(r'(\d+)\. (\w+) (\d+) (\d+)\.(\d+)', date)
        if match:
            day, month, year, hour, minute = match.groups()
            month_dict = {'tammikuuta': 1, 'helmikuuta': 2, 'maaliskuuta': 3, 'huhtikuuta': 4, 'toukokuuta': 5, 'kesäkuuta': 6, 'heinäkuuta': 7, 'elokuuta': 8, 'syyskuuta': 9, 'lokakuuta': 10, 'marraskuuta': 11, 'joulukuuta': 12}
            month_num = month_dict.get(month, 0)
            return dt.datetime(int(year), month_num, int(day), int(hour), int(minute))
        else:
            return None
        
    def fintraffic_lam_data(self, year=2023, all_vehicles=False):
        if year == 2023:
            start_date = "2023-09-01"
            end_date = "2023-11-01"
        if all_vehicles:
            url_volumes = f"https://tie.digitraffic.fi/api/tms/v1/history?api=liikennemaara&tyyppi=h&pvm={start_date}&loppu={end_date}&lam_type=option2&pistejoukko=284,287,286,281,282&luokka=kaikki&suunta=1,2"
            # url_speeds= f"https://tie.digitraffic.fi/api/tms/v1/history?api=keskinopeus&tyyppi=h&pvm={start_date}&loppu={end_date}&lam_type=option2&pistejoukko=284,287,286,281,282&luokka=kaikki&suunta=1,2"
        else:
            url_volumes = f"https://tie.digitraffic.fi/api/tms/v1/history?api=liikennemaara&tyyppi=h&pvm={start_date}&loppu={end_date}&lam_type=option2&pistejoukko=284,287,286,281,282&luokka=kevyet&suunta=1,2"
            # url_speeds = f"https://tie.digitraffic.fi/api/tms/v1/history?api=keskinopeus&tyyppi=h&pvm={start_date}&loppu={end_date}&lam_type=option2&pistejoukko=284,287,286,281,282&luokka=kevyet&suunta=1&sisallytakaistat=0"
                                                    # "/api/tms/v1/history?api=keskinopeus&tyyppi=h&pvm=2025-02-13&loppu=2025-02-13&lam_type=option1&piste=5&luokka=kevyet&suunta=1&suunta=2&sisallytakaistat=0"
        response_volumes = requests.get(url_volumes)
        # response_speeds = requests.get(url_speeds)
        # print(response_speeds)
        if response_volumes.status_code == 200:
            data_volumes = response_volumes.content.decode('utf-8')
            # data_speeds = response_speeds.content.decode('utf-8')
            df = pd.read_csv(io.StringIO(data_volumes), sep=';')
            # df_speeds = pd.read_csv(io.StringIO(data_speeds), sep=';')
            # print(df_speeds.head())
            
            # Calculate average aht, pt, iht, and daily counts
            df['datetime'] = pd.to_datetime(df['pvm'], format="%Y%m%d")
            df.set_index('datetime', inplace=True)

            df['week_number'] = df.index.strftime('%U').astype(int)
            df = df[df['week_number'] != 42]
            df['formatted_date'] = df.index.strftime('%m-%d')
            df_weekdays = df[df.index.dayofweek < 5].copy()

            df_weekdays['aht'] = df_weekdays.loc[:, '07_08':'08_09'].max(axis=1)*1.2
            df_weekdays['pt'] = df_weekdays.loc[:, '09_10':'14_15'].mean(axis=1)
            df_weekdays['iht'] = df_weekdays.loc[:, '15_16':'16_17'].max(axis=1)*1.2
            df_weekdays['vrk'] = df_weekdays.loc[:, '00_01':'23_24'].sum(axis=1)
            
            grouped_df = df_weekdays.groupby(['pistetunnus', 'suunta']).agg({
                'aht': 'mean',
                'pt': 'mean',
                'iht': 'mean',
                'vrk': 'mean'
            }).reset_index()
            
            # Transform the dataframe to have both directions in the same row
            pivot_df = grouped_df.pivot(index='pistetunnus', columns='suunta', values=['aht', 'pt', 'iht', 'vrk'])
            pivot_df.columns = [f'{col[0]}_{col[1]}' for col in pivot_df.columns]
            pivot_df.reset_index(inplace=True)
            
            # Add back the "suuntaselite" column
            suuntaselite_df = df_weekdays[['pistetunnus', 'suunta', 'suuntaselite']].drop_duplicates()
            suuntaselite_pivot = suuntaselite_df.pivot(index='pistetunnus', columns='suunta', values='suuntaselite')
            suuntaselite_pivot.columns = [f'suuntaselite_{col}' for col in suuntaselite_pivot.columns]
            suuntaselite_pivot.reset_index(inplace=True)
            
            pivot_df = pivot_df.merge(suuntaselite_pivot, on='pistetunnus', how='left')
            
            # Convert values to integers
            pivot_df = pivot_df.fillna(0)
            pivot_df = pivot_df.astype({col: int for col in pivot_df.columns if col.startswith(('aht', 'pt', 'iht', 'vrk'))})
            
            return pivot_df
        else:
            print("Failed to fetch the fintraffic lam data")
            return None

    def fintraffic_lam_stations(self, zones=None):
        if zones is None:
            zones = Path(__file__).resolve().parent.parent / 'data' / 'SIJ2023_aluejako.gpkg'

        url = "https://tie.digitraffic.fi/api/tms/v1/stations"
        response = requests.get(url)
        trans_table = str.maketrans({'ä': 'a', 'å': 'a', 'ö': 'o'})
        if response.status_code == 200:
            stations_data = response.json()
            df = self.fintraffic_lam_data()
            if df is not None:
                matched_stations = []
                for station in stations_data['features']:
                    tms_number = station['properties']['tmsNumber']
                    station_data = df[df['pistetunnus'] == tms_number]
                    if not station_data.empty:
                        coordinates = station['geometry']['coordinates']
                        matched_stations.append({
                            'id': station['properties']['id'],
                            'name': station['properties']['name'],
                            'longitude': coordinates[0],
                            'latitude': coordinates[1],
                            'geometry': Point(coordinates[0], coordinates[1]),
                            'suuntaselite_1': station_data['suuntaselite_1'].values[0],
                            'suuntaselite_2': station_data['suuntaselite_2'].values[0],
                            'aht_1': station_data['aht_1'].values[0],
                            'pt_1': station_data['pt_1'].values[0],
                            'iht_1': station_data['iht_1'].values[0],
                            'vrk_1': station_data['vrk_1'].values[0],
                            'aht_2': station_data['aht_2'].values[0],
                            'pt_2': station_data['pt_2'].values[0],
                            'iht_2': station_data['iht_2'].values[0],
                            'vrk_2': station_data['vrk_2'].values[0],
                            'source': "FinTraffic LAM"
                        })
                
                gdf = gpd.GeoDataFrame(matched_stations, crs="EPSG:4326")
                gdf = gdf.to_crs(epsg=3879)
                
                zones_gdf = gpd.read_file(zones)
                gdf = gdf[gdf.geometry.within(zones_gdf.unary_union)]
                gdf['name'] = gdf['name'].apply(lambda name: name.translate(trans_table))
                return gdf
            else:
                print("No fintraffic lam data to display")
        else:
            print("Failed to fetch the stations data")

    def display_fintraffic_lam_locations(self):
        gdf = self.fintraffic_lam_stations()
        map = gdf.explore(marker_kwds={'radius': 5})
        map.save('fintraffic_map.html')
        webbrowser.open('fintraffic_map.html')

    def bike_lams(self):
        """
        Requesting data straight from an API would be ideal, but currently not possible for day specific data
        """

        espoo_cols = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]
        espoo = pd.read_csv("bikers/Espoon_pyorailijamaarat 2024.csv", sep=";", decimal=",", usecols=espoo_cols, parse_dates=[['Päivämäärä', 'Aika']]).fillna(0)
        espoo = espoo.rename(columns={'Päivämäärä_Aika': 'datetime', 'Espoon portti (Eco-Counter)':2010,'Espoonlahdenraitti (Eco-Counter)':2020,'Gallen-Kallela (Eco-Counter)':2030,'Gallen-Kallelan tie (DSL10)':2040,'Kalevalantien alikulku (DSL10)':2050,'Kehä I, Laajalahti (DSL10)':2060,'Kehä I, Laajalahti (Eco-counter)':2070,'Kirkkojärventie (DSL10)':2080,'Leppävaarankäytävä (Eco-counter)':2090,'Länsiväylä (Eco-counter)':2100,'Länsiväylä, Karhusaari (DSL10)':2110,'Martinsillantie (DSL10)':2120,'Merituulentie (DSL10)':2130,'Olarinkatu (Eco-Counter)':2140,'Pohjantien ylikulku (DSL10)':2150,'Pohjantien ylikulku (Eco-Counter)':2160,'Pitkäjärventie (DSL10)':2170,'Päivänkestämänpolku, Kera (Eco-Counter)':2180,'Suomenlahdentie (Eco-Counter)':2190,'Tapiola, Länsituulenkuja (Eco-Counter)':2200,'Turuntie, Rantaradanraitti (Eco-Counter)':2210,'Vihdintie, Uusmäki (DSL10)':2220,'Ylismäentie, Suurpelto (Eco-Counter)':2230}).drop(columns=["Päivä"])
        # espoo = espoo.drop(columns=['Laajalahdenbaana'])
        espoo['datetime'] = espoo['datetime'].astype('datetime64[ns]')
        helsinki = pd.read_excel("bikers/Helsingin_pyorailijamaarat.xlsx").fillna(0)
        helsinki = helsinki.rename(columns={'Päivämäärä_aika': 'datetime','Kaisaniemi/Eläintarhanlahti':1010,'Eteläesplanadi':1020,'Baana':1030,'Lauttasaaren silta eteläpuoli':1040,'Lauttasaaren silta pohjoispuoli':1041,'Kulosaaren silta et.':1050,'Kuusisaarentie':1060,'Munkkiniemi silta pohjoispuoli':1070,'Munkkiniemen silta eteläpuoli':1080,'Hesperian puisto/Ooppera':1090,'Pitkäsilta länsipuoli':1100,'Pitkäsilta itäpuoli':1110,'Merikannontie':1120,'Kulosaaren silta po. ':1051,'Ratapihantie':1140,'Huopalahti (asema)':1150,'Kaivokatu':1160,'Käpylä - Pohjoisbaana':1170,'Viikintie':1180,'Auroransilta':1190})
        vantaa = pd.read_csv("bikers/Vantaan_pyorailijamaarat_2017_alkaen.csv", sep=";",decimal=",", parse_dates=['Päivämäärä'], date_parser=self.parse_date).fillna(0)
        vantaa = vantaa.rename(columns={'Päivämäärä': 'datetime', 'Kytöpuisto':4010,'Talvikkitie-Lummetie':4020,'Ylästöntie itä':4030,'Kielotie länsi':4040,'Pellas':4050,'Kuusijärvi':4060,'Kyytitie':4070,'Urpiaisentie':4080,'Kielotie_ita':4090})

        loc_helsinki = pd.read_csv('bikers/pyoralaskentapisteiden_sijainnit_helsinki.csv', sep=';', index_col='id')
        loc_espoo = pd.read_csv('bikers/pyoralaskentapisteiden_sijainnit_espoo.csv', sep=';', index_col='id')
        loc_vantaa = pd.read_csv('bikers/pyoralaskentapisteiden_sijainnit_vantaa.csv', sep=';', index_col='id')

        locations = pd.concat([loc_helsinki, loc_espoo, loc_vantaa], axis=0)
        # print(locations.head())
        holidays = ['1-6','5-1','12-6','12-25','12-26']

        hel_esp = pd.merge(helsinki, espoo, on=['datetime', 'datetime'], how='outer').set_index('datetime')
        hel_esp_van = pd.merge(hel_esp, vantaa, on=['datetime', 'datetime'], how='outer').set_index('datetime')

        df = hel_esp_van.loc['2023-09-01':'2023-10-31'].drop(columns=['Päivämäärä', 'Aika']).sort_index()
        df['week_number'] = df.index.strftime('%U').astype(int)
        df = df[df['week_number'] != 42]
        df['formatted_date'] = df.index.strftime('%m-%d')
        df = df[~df['formatted_date'].isin(holidays)]
        df = df.drop(columns=['formatted_date'])
        # Create a dictionary from the 'locations' dataframe
        id_to_name = locations['name'].to_dict()

        # Rename the columns in the 'df' dataframe using the dictionary
        df_test = df.copy()
        df_test.rename(columns=id_to_name, inplace=True)
        # df_test.to_excel("pyorat_esp_hel_van.xlsx")

        df_weekdays = df[df.index.dayofweek < 5]
        daily_df = df_weekdays.resample('D').sum()
        df_weekdays = df_weekdays.replace(0, np.nan)
        daily_df = daily_df.replace(0, np.nan)

        df_07_09 = df_weekdays.between_time('07:00', '08:59').max()*1.2   
        # df_mornings = df_07_09.resample('D').sum()
        df_aht = df_07_09.mean()    
        df_pt = df_weekdays.between_time('09:00', '14:59').mean()
        df_15_17 = df_weekdays.between_time('15:00', '16:59').max()*1.2
        # df_evenings = df_15_17.resample('D').sum()
        df_iht = df_15_17.mean()

        avg_df = pd.DataFrame(data=daily_df.mean(), columns=['vrk'])

        new_df = locations.join(avg_df, on='id')
        new_df['geometry'] = new_df.apply(lambda row: Point([row['x'], row['y']]), axis=1)

        gdf = gpd.GeoDataFrame(new_df,geometry=new_df['geometry'], crs='EPSG:3879')
        gdf = gdf.loc[gdf['vrk']>0]

        # Add the nodes column using the map method
        gdf['nodes'] = gdf.index.map(self.bike_lam_links)
        gdf['aht'] = df_aht
        gdf['pt'] = df_pt
        gdf['iht'] = df_iht

        # Add the inode and jnode columns
        gdf['inode'] = gdf['nodes'].apply(lambda x: (x[0]))
        gdf['jnode'] = gdf['nodes'].apply(lambda x: (x[1]))

        gdf = gdf.drop('nodes', axis=1)
        gdf['source'] = gdf.apply(lambda row: 'Helsinki bike LAM' if row.name < 2000 else 'Espoo bike LAM' if row.name < 4000 else 'Vantaa bike LAM', axis=1)
        return gdf

    def read_hel_lam_data(self, year=2023):
        if year == 2023:
            start = "2023-09-01T00:00:00"
            end = "2023-11-01T00:00:00"
        elif year == 2024:
            start = "2024-09-01T00:00:00"
            end = "2024-11-01T00:00:00"

        start_period = dt.datetime.fromisoformat(start)
        end_period = dt.datetime.fromisoformat(end)

        one_day = dt.timedelta(days=1)

        data = []
        columns_dict = {}

        while start_period + one_day <= end_period:
            # Get the week number and weekday
            week_num = start_period.isocalendar()[1]  # ISO week number
            weekday = start_period.weekday()  # Monday=0, Sunday=6

            # Skip week 42 and weekends
            if week_num == 42 or weekday in {5, 6}:  
                start_period += one_day
                continue

            start_str = start_period.isoformat()
            end_str = (start_period + dt.timedelta(hours=1)).isoformat()
            response = requests.get(f"https://lamapi.azurewebsites.net/api/Public/getTotalCount?start={start_str}&end={end_str}")
            period_data = {'datetime': start_period}
            if response.status_code == 200:
                response_data = response.json()
                
                seen_entries_period = set()
                for entry in response_data:
                    if entry['name'] not in columns_dict:
                        columns_dict[entry['name']] = []
                    
                    if (entry['name'] not in seen_entries_period) or (entry['name'] in seen_entries_period and entry['count'] > 0):
                        seen_entries_period.add(entry['name'])
                        period_data[entry['name']] = entry['count']
                seen_entries_period.clear()
            data.append(period_data)
            start_period += one_day
        
            time.sleep(0.01)

        df = pd.DataFrame(data)
        df = df.replace(0, np.nan)
        df = df.set_index("datetime")
        daily_avg = df.mean(axis=0)
        daily_avg.dropna(inplace=True)


        return daily_avg

    def hel_lam_stations(self, year=2023):
        response = requests.get("https://lamapi.azurewebsites.net/api/Public/getAllPoints")
        matched_stations = []
        if response.status_code == 200:
            stations_data = response.json()
            df = self.read_hel_lam_data(year)
            for station in stations_data:
                vrk =  df[station['name']] if station['name'] in df.index else 0
                if vrk:
                    matched_stations.append({
                        'id': station['id'],
                        'name': station['name'],
                        'longitude': float(station['longitude']),
                        'latitude': float(station['latitude']),
                        'geometry': Point(float(station['longitude']), float(station['latitude'])),
                        'vrk_1': int(vrk/2 if "Kalasataman tunneli" not in station['name'] else vrk),
                        'vrk_2': int(vrk/2 if "Kalasataman tunneli" not in station['name'] else 0),
                        'source': "Helsinki LAM"
                    })
            
            gdf = gpd.GeoDataFrame(matched_stations, crs="EPSG:4326")
            return gdf       
        else:
            print("Failed to fetch the Helsinki lam data")

    def display_hel_lam_locations(self, year=2023):
        gdf = self.hel_lam_stations(year)
        map = gdf.explore(marker_kwds={'radius':5})
        map.save('hel_lam_map.html')
        webbrowser.open('hel_lam_map.html')



    def fintraffic_lam_to_network(self, network):
        lam_data = self.fintraffic_lam_stations()
        lam_cols = ['@lam_counts_vrk', '@lam_counts_aht', '@lam_counts_pt', '@lam_counts_iht', '#lam_name', '#lam_source']        
        for lamid, linkpair in self.lam_links.items():
            for i, link in enumerate(linkpair):
                if link[0]:
                    link_data = lam_data[lam_data['id'] == lamid][[f"vrk_{i+1}", f"aht_{i+1}", f"pt_{i+1}", f"iht_{i+1}", "name", "source"]]
                    network.loc[(network['From']==link[0]) & (network['To']==link[1]), lam_cols] = link_data.values
        network[['#lam_name','#lam_source']] = network[['#lam_name','#lam_source']].fillna("")
        return network
    

    def hel_lam_to_network(self, network):
        lam_data = self.hel_lam_stations()
        lam_cols = ['@lam_counts_vrk', '#lam_name', '#lam_source']        
        for lamname, linkpair in self.hel_link_map.items():
            for i, link in enumerate(linkpair):
                if link[0]:
                    link_data = lam_data[lam_data['name'] == lamname][[f"vrk_{i+1}", "name", "source"]]
                    if not link_data.empty:
                        network.loc[(network['From']==link[0]) & (network['To']==link[1]), lam_cols] = link_data.values
        network[['#lam_name','#lam_source']] = network[['#lam_name','#lam_source']].fillna("")
        return network

    def bike_lam_to_network(self, network):
        lam_data = self.bike_lams()
        print(lam_data.columns)
        print(lam_data.head())
        lam_cols = ['@bike_lam_counts_vrk', '@bike_lam_counts_aht', '@bike_lam_counts_pt', '@bike_lam_counts_iht', '#lam_name', '#lam_source']       
        for lamid, link in self.bike_lam_links.items():
            if lamid in lam_data.index:
                link_data = lam_data.loc[lamid, [f"vrk", "aht", "pt", "iht", "name", "source"]]
                network.loc[(network['From']==link[0]) & (network['To']==link[1]), lam_cols] = link_data.values
        network[['#lam_name','#lam_source']] = network[['#lam_name','#lam_source']].fillna("")
        return network

