import rasterstats
import geopandas as gpd
import pandas as pd
import numpy as np
import webbrowser
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score

from sklearn.linear_model import LinearRegression, SGDRegressor


from sklearn import metrics
from rasterio.plot import show

# Turns 20m * 20m squares into km^2 (20m*20m = 400m^2 -> 0.0004 km^2)
AREA_MULTIPLIER = 400*0.000001

def read_and_process_data(pop_file, wrk_file):
    # Read population data
    pop_df = pd.read_csv(pop_file, sep='\t', index_col=0, comment="#", header=0)
    
    # Calculate age groups and total population
    pop_df[['pop_7-17', 'pop_18-29', 'pop_30-49', 'pop_50-64', 'pop_65-']] = np.around(pop_df[['sh_7-17', 'sh_1829', 'sh_3049', 'sh_5064', 'sh_65-']].multiply(pop_df['total'], axis=0)).fillna(0).astype('int')
    pop_df['pop_0-6'] = pop_df['total'] - pop_df[['pop_7-17', 'pop_18-29', 'pop_30-49', 'pop_50-64', 'pop_65-']].sum(axis=1)
    pop_df['pop_total'] = pop_df['total']
    
    # Read workplace data
    wrk_df = pd.read_csv(wrk_file, sep='\t', index_col=0, comment="#", header=0)
    
    # Calculate workplace categories and total workplaces
    wrk_df[['wrk_serv', 'wrk_shop', 'wrk_logi', 'wrk_indu']] = np.around(wrk_df[['sh_serv', 'sh_shop', 'sh_logi', 'sh_indu']].multiply(wrk_df['total'], axis=0)).fillna(0).astype('int')
    wrk_df['wrk_other'] = wrk_df['total'] - wrk_df[['wrk_serv', 'wrk_shop', 'wrk_logi', 'wrk_indu']].sum(axis=1)
    wrk_df['wrk_total'] = wrk_df['total']
    
    # Merge population and workplace data on index
    X = pd.merge(pop_df[['pop_total', 'pop_0-6', 'pop_7-17', 'pop_18-29', 'pop_30-49', 'pop_50-64', 'pop_65-']],
                 wrk_df[['wrk_total', 'wrk_serv', 'wrk_shop', 'wrk_logi', 'wrk_indu', 'wrk_other']],
                 left_index=True, right_index=True)
    X = X[['pop_total', 'wrk_total']]
    
    return X


def get_distance_to_center(row, centers):
    center_geom = gdf_2018[gdf_2018['SIJ2019'].isin(centers)]['geometry_centroid']
    return row['geometry_centroid'].distance(center_geom).min()

def get_distance_to_station(row, stations):
    return row['geometry_centroid'].distance(stations['geometry']).min()

# def remove_large_fluctuations(row):
#     if row['wrk_total_2']-row['wrk_total_1'] > 580:
#         wrk_total_2 = row['wrk_total_1'] + 580
#     elif row['wrk_total_2']-row['wrk_total_1'] < -400:
#         wrk_total_2 = row['wrk_total_1'] - 400
#     else:
#         wrk_total_2 = row['wrk_total_2']
#     return wrk_total_2


# 2012 data is in a slightly different format
pop_2012 = pd.read_csv('2012/wrk_pop_2012.tsv', sep='\t', index_col=0, comment="#", header=0)

pop_2012['pop_total'] = pop_2012['v_yht']
pop_2012['wrk_total'] = pop_2012['tp_yht']

X_2012 = pop_2012[['pop_total', 'wrk_total']]
X_2012.index.name = None


# Read 2018 and 2040 zone data
pop_2018_file = '2018/2017.pop'
wrk_2018_file = '2018/2018_v2.wrk'
pop_2040_file = '2040_MAL2023_ve2/2040_ve2.pop'
wrk_2040_file = '2040_MAL2023_ve2/2040_ve2.wrk'

X_2018 = read_and_process_data(pop_2018_file, wrk_2018_file)
X_2040 = read_and_process_data(pop_2040_file, wrk_2040_file)
X_merged_12_18 = pd.merge(X_2018, X_2012, how='inner', left_index=True, right_index=True, suffixes=('_2', '_1'))
X_merged_18_40 = pd.merge(X_2040, X_2018, how='inner', left_index=True, right_index=True, suffixes=('_2', '_1'))

# Smooth data. Not used.
# X_merged_12_18['wrk_total_2'] = X_merged_12_18.apply(remove_large_fluctuations, axis=1)
# X_merged_18_40['wrk_total_2'] = X_merged_12_18.apply(remove_large_fluctuations, axis=1)

# Read station location data, used with distance metrics
train_stations_2018 = pd.read_csv('stations/train_stations_2018.txt', sep=',', index_col=0, header=0)
metro_stations_2018 = pd.read_csv('stations/metro_stations_2018.txt', sep=',', index_col=0, header=0)
train_stations_2040 = pd.read_csv('stations/train_stations_2040.txt', sep=',', index_col=0, header=0)
metro_stations_2040 = pd.read_csv('stations/metro_stations_2040_ve2.txt', sep=',', index_col=0, header=0, comment='#')
train_2018 = gpd.GeoDataFrame(train_stations_2018, geometry=gpd.points_from_xy(train_stations_2018['X-coord'], train_stations_2018['Y-coord']), crs='EPSG:3879')
metro_2018 = gpd.GeoDataFrame(metro_stations_2018, geometry=gpd.points_from_xy(metro_stations_2018['X-coord'], metro_stations_2018['Y-coord']), crs='EPSG:3879')
train_2040 = gpd.GeoDataFrame(train_stations_2040, geometry=gpd.points_from_xy(train_stations_2040['X-coord'], train_stations_2040['Y-coord']), crs='EPSG:3879')
metro_2040 = gpd.GeoDataFrame(metro_stations_2040, geometry=gpd.points_from_xy(metro_stations_2040['X-coord'], metro_stations_2040['Y-coord']), crs='EPSG:3879')

# Read zone centroid location data, used with distance metrics
centroids_df = pd.read_csv("centroids.tsv", sep="\s+")
centroids = gpd.GeoDataFrame(centroids_df, geometry=gpd.points_from_xy(centroids_df['X-coord'], centroids_df['Y-coord']), crs='EPSG:3879')[['SIJ2019', 'geometry']]

# Read zone data and augment it with landcover raster data
zones = gpd.read_file("sijoittelualueet/sijoittelualueet2019.shp")
zones.crs = 'EPSG:3879'
zones = zones.to_crs('EPSG:3067')  # CORINE uses the national crs
stats_2018 = rasterstats.zonal_stats(zones.geometry, 'corine_data/landcover.tif', categorical=True)
stats_2012 = rasterstats.zonal_stats(zones.geometry, 'corine_data/landcover_2012.tif', categorical=True)
df_2018 = pd.DataFrame(data=stats_2018)
df_2012 = pd.DataFrame(data=stats_2012)
gdf_2012 = zones.join(df_2012)
gdf_2018 = zones.join(df_2018)
gdf_2012 = gdf_2012.to_crs('EPSG:3879')
gdf_2018 = gdf_2018.to_crs('EPSG:3879')


# Helsinki
region_center = [102]
# High density local centers from centers.tsv, as well as salo, lahti, porvoo, riihimäki, hämeenlinna
local_centers = [102, 271, 1401, 1423, 1225, 2370, 2282, 2151, 2691, 4075, 4333, 4492, 6061, 7232, 8315, 9301, 10205, 12263, 11043, 14004, 13031, 16012, 20007, 23016, 26003, 27047]


def calculate_landuse_metrics(gdf, year):
    gdf['kokonaispinta-ala'] = gdf['geometry'].area*0.000001
    gdf = gdf.fillna(0)
    gdf['id'] = gdf.index
    if year == 2012:  
        gdf['rakennettu pinta-ala'] = (gdf[1] + gdf[2] + gdf[3] + gdf[4] + gdf[5] + gdf[6] + gdf[7] + gdf[8] + gdf[9] + gdf[10] + gdf[11] + gdf[12] + gdf[13] + gdf[14] + gdf[15])*AREA_MULTIPLIER
        gdf['vesi'] = (gdf[46] + gdf[47] + gdf[48]) * AREA_MULTIPLIER
        gdf['kosteikko'] = (gdf[40] + gdf[41] + gdf[42] + gdf[43] + gdf[44] + gdf[45]) * AREA_MULTIPLIER
    elif year == 2018:  # Corine has changed slightly
        gdf['rakennettu pinta-ala'] = (gdf[1] + gdf[2] + gdf[3] + gdf[4]+ gdf[5] + gdf[6] + gdf[7] + gdf[8] + gdf[9] + gdf[10] + gdf[11] + gdf[12] + gdf[13] + gdf[14] + gdf[15] + gdf[16])*AREA_MULTIPLIER
        gdf['vesi'] = (gdf[47] + gdf[48] + gdf[49]) * AREA_MULTIPLIER
        gdf['kosteikko'] = (gdf[41] + gdf[42] + gdf[43] + gdf[44] + gdf[45] + gdf[46]) * AREA_MULTIPLIER
    gdf['kokonaispinta-ala'] = gdf.apply(lambda row: row['rakennettu pinta-ala'] if row['rakennettu pinta-ala'] > row['kokonaispinta-ala'] else row['kokonaispinta-ala'], axis=1)

    gdf = gdf[['SIJ2019', 'geometry', 'kokonaispinta-ala', 'rakennettu pinta-ala','vesi','kosteikko']]

    gdf['suhteellinen_kosteikko'] = gdf['kosteikko'] / (gdf['kokonaispinta-ala'] - gdf['vesi'])
    gdf['suhteellinen_rakennettu'] = gdf['rakennettu pinta-ala'] / (gdf['kokonaispinta-ala'] - gdf['vesi'])

    return gdf

gdf_2018 = calculate_landuse_metrics(gdf_2018, 2018)

gdf_2018_centroids = pd.merge(gdf_2018, centroids, how='inner', on='SIJ2019', suffixes=(None, '_centroid'))
gdf_2018 = gpd.GeoDataFrame(gdf_2018_centroids, geometry='geometry')


gdf_2018['dist_region_center'] = gdf_2018.apply(lambda row: get_distance_to_center(row, region_center), axis=1)
gdf_2018['dist_local_center'] = gdf_2018.apply(lambda row: get_distance_to_center(row, local_centers), axis=1)
df_2018_copy = gdf_2018.copy()
df_2040 = X_merged_40 = pd.merge(X_merged_18_40, df_2018_copy, how='inner', left_index=True, right_on="SIJ2019")
gdf_2040 = gpd.GeoDataFrame(df_2040, geometry='geometry')
gdf_2018 = gdf_2018[['SIJ2019', 'geometry', 'geometry_centroid', 'kokonaispinta-ala','vesi', 'suhteellinen_rakennettu', 'suhteellinen_kosteikko', 'dist_region_center', 'dist_local_center']]
X_merged_40 = pd.merge(X_merged_18_40, gdf_2018, how='inner', left_index=True, right_on="SIJ2019")
gdf_40 = gpd.GeoDataFrame(X_merged_40, geometry='geometry')

gdf_2012 = calculate_landuse_metrics(gdf_2012, 2012)


gdf_2012 = gdf_2012[['SIJ2019', 'suhteellinen_rakennettu','suhteellinen_kosteikko']]

# gdf_2018 = gdf_2018[['SIJ2019', 'geometry', 'geometry_centroid', 'suhteellinen_rakennettu', 'suhteellinen_kosteikko', 'dist_region_center', 'dist_local_center']]


merged = pd.merge(gdf_2018, gdf_2012, how='inner', on='SIJ2019', suffixes=('_2018', '_2012'))
# merged = merged.drop(['kokonaispinta-ala_2012', 'vesi_2018', 'kosteikko_2018'], axis=1)
# merged = merged.rename(columns={'kokonaispinta-ala_2018':'kokonaispinta-ala', 'vesi_2012':'vesi', 'kosteikko_2012':'kosteikko'})

X_merged_18 = pd.merge(X_merged_12_18, merged, how='inner', left_index=True, right_on="SIJ2019")
gdf_18 = gpd.GeoDataFrame(X_merged_18, geometry='geometry')


gdf_18 = gdf_18.rename(columns={'suhteellinen_rakennettu_2012': 'suhteellinen_rakennettu','suhteellinen_kosteikko_2012':'suhteellinen_kosteikko', 'suhteellinen_rakennettu_2018':'Y'})
gdf_18 = gdf_18.drop('suhteellinen_kosteikko_2018', axis=1)

cols = gdf_18.columns.tolist()
# print(cols)
cols = cols[:9] + cols[10:] + [cols[9]]
gdf_18 = gdf_18[cols]
cols = gdf_40.columns.tolist()
# print(cols)
cols = cols[:9] + cols[11:] + cols[9:11]
gdf_40 = gdf_40[cols]


y = np.ravel(gdf_18.iloc[:,-1:])
gdf_18 = gdf_18.iloc[:,:-1]

# print(gdf_18.columns)
# print(gdf_40.columns)

gdf_18['wrk_change'] = (gdf_18['wrk_total_2'] - gdf_18['wrk_total_1']) / (gdf_18['kokonaispinta-ala'] - gdf_18['vesi'])
gdf_18['pop_change'] = (gdf_18['pop_total_2'] - gdf_18['pop_total_1']) / (gdf_18['kokonaispinta-ala'] - gdf_18['vesi'])
gdf_40['wrk_change'] = (gdf_40['wrk_total_2'] - gdf_40['wrk_total_1']) / (gdf_40['kokonaispinta-ala'] - gdf_40['vesi'])
gdf_40['pop_change'] = (gdf_40['pop_total_2'] - gdf_40['pop_total_1']) / (gdf_40['kokonaispinta-ala'] - gdf_40['vesi'])

gdf_18['dist_closest_railway_station'] = gdf_18.apply(lambda row: get_distance_to_station(row, train_2018), axis=1)
gdf_18['dist_closest_metro_station'] = gdf_18.apply(lambda row: get_distance_to_station(row, metro_2018), axis=1)

gdf_40['dist_closest_railway_station'] = gdf_40.apply(lambda row: get_distance_to_station(row, train_2040), axis=1)
gdf_40['dist_closest_metro_station'] = gdf_40.apply(lambda row: get_distance_to_station(row, metro_2018), axis=1)


X_train, X_test, y_train, y_test = train_test_split(gdf_18.drop(['geometry', 'geometry_centroid', 'kokonaispinta-ala','vesi','wrk_total_1','wrk_total_2','pop_total_1','pop_total_2','suhteellinen_kosteikko'], axis=1), y, test_size=0.2, random_state=1)

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score

degree = 2
# Create a list of regression models
models = [
    # ("Linear Regression", LinearRegression()),
    # ("Ridge Regression", Ridge(alpha=1.0)),
    # ("Lasso Regression", Lasso(alpha=1.0)),
    # ("Polynomial Regression", make_pipeline(PolynomialFeatures(degree), LinearRegression())),
    ("Gradient Boosting Regression", GradientBoostingRegressor())
]
from sklearn.model_selection import GridSearchCV

# Define hyperparameter grids for each model
param_grid = {
    # "Linear Regression": {},
    # "Ridge Regression": {"alpha": [0.01, 0.1, 1.0, 10.0], "solver": ["auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga"], "max_iter": [10000]},
    # "Lasso Regression": {"alpha": [0.01, 0.1, 1.0, 10.0]},
    # "Polynomial Regression": {"polynomialfeatures__degree": [2, 3, 4]},
    "Gradient Boosting Regression": {"n_estimators": [200], "learning_rate": [0.05],
                                    "max_depth": [3], "min_samples_split": [32]}}

best_model_name = None
best_model = None
best_rmse = float('inf')
best_mape = float('inf')
def mean_absolute_percentage_error(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100



for name, model in models:
    # print(f"Model: {name}")
    
    # Get the corresponding hyperparameters from the param_grid
    hyperparameters = param_grid[name]
    
    # Initialize GridSearchCV for hyperparameter tuning
    grid_search = GridSearchCV(model, hyperparameters, scoring='neg_mean_squared_error', cv=5)
    
    # Fit the GridSearchCV object
    grid_search.fit(X_train, y_train)
    
    # Get the best estimator with tuned hyperparameters
    current_best_model = grid_search.best_estimator_
    
    # Predict using the best model
    y_pred = current_best_model.predict(X_test)
    y_pred_restricted = np.maximum(X_test['suhteellinen_rakennettu'], np.minimum(y_pred, 1))

    
    # Calculate Mean Squared Error
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_restricted))
    r2 = r2_score(y_test, y_pred_restricted)
    # Calculate MAPE for your predictions
    mape = mean_absolute_percentage_error(y_test, y_pred_restricted)

    # print(f"Best Hyperparameters: {grid_search.best_params_}")
    print(f"Root Mean Squared Error: {rmse:.2f}")
    print(f"MAPE: {mape:.2f}%")
    print(f"R-squared: {r2:.2f}")

    
    # Update the best model if this model has a lower RMSE
    if mape < best_mape:
        best_mape = mape
        best_model_name = name
        best_model = current_best_model
    
    print("\n--------------------------\n")

print(f"Best Model: {best_model_name}")
print("Best Hyperparameters:", best_model.get_params())

# Using the best-selected model to predict unseen data

    
# Calculate Mean Squared Error
# mse_fix = metrics.mean_squared_error(y_test, np.maximum(0, np.minimum(1, y_pred)))
# mse = metrics.mean_squared_error(y_test, y_pred)

# print(f"Root Mean Squared Error (potential fix): {np.sqrt(mse_fix)}")


# fig, ax = plt.subplots(nrows=2, ncols=1)
# ax[0].plot(np.arange(0, len(y_pred)), y_pred)
# ax[1].plot(np.arange(0, len(y_test)), y_test)
# plt.show()


prediction_2040 = best_model.predict(gdf_40.drop(['geometry', 'geometry_centroid', 'kokonaispinta-ala','vesi','wrk_total_1','wrk_total_2','pop_total_1','pop_total_2','suhteellinen_kosteikko'], axis=1))

# gdf_40['prediction'] = np.minimum(prediction_2040, (gdf_40['kokonaispinta-ala']-gdf_40['vesi']))
gdf_2040['y'] = prediction_2040
gdf_2040['prediction'] = np.maximum(gdf_2040['rakennettu pinta-ala'], np.minimum(prediction_2040*(gdf_2040['kokonaispinta-ala']-gdf_2040['vesi']), (gdf_2040['kokonaispinta-ala']-gdf_2040['vesi'])))

# gdf_2040['prediction'] = gdf_2040.apply(lambda row: row['kokonaispinta-ala']-row['vesi'] if row['y'] > 0.97 else row['prediction'], axis=1)
gdf_2040['muutos'] = ((gdf_2040['prediction'] - gdf_2040['rakennettu pinta-ala']) / gdf_2040['kokonaispinta-ala']) * 100

print("2018 rakennettu pinta ala km^2: ", np.around(gdf_2040['rakennettu pinta-ala'].sum(), 2))
print("2040 ennustettu rakennettu pinta ala km^2: ", np.around(gdf_2040['prediction'].sum(), 2))
print(f"Rakennetun alueen muutos: +{np.around(100*(gdf_2040['prediction'].sum() / gdf_2040['rakennettu pinta-ala'].sum())-100, 2)} %")
print(f"Työpaikkojen muutos: +{np.around(100*(gdf_2040['wrk_total_2'].sum() / gdf_2040['wrk_total_1'].sum())-100, 2)} %")
print(f"Asukasmäärän muutos: +{np.around(100*(gdf_2040['pop_total_2'].sum() / gdf_2040['pop_total_1'].sum())-100, 2)} %")

preds = gdf_2040[['prediction', 'SIJ2019']].set_index('SIJ2019').sort_index()
preds.index = preds.index.astype(int)
preds.to_csv('ennuste.tsv', sep='\t')

map = gdf_2040.explore(column='muutos',)

map.save('map.html')
webbrowser.open('map.html')