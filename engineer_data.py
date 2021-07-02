import pandas as pd 
import numpy as np
import datetime
import math
import numpy as np

## Data
df_population = pd.read_csv('Population Data.csv')
df_temperature = pd.read_csv('Temperature Data.csv')





def interpolate_temperature(dt, df_station, field='temp_mean_c'):
    # From the new datetime, get the temperature from previous and following day.
    dt = pd.to_datetime(dt).to_pydatetime()
    next_day = dt + datetime.timedelta(days=1)
    prev_day = dt - datetime.timedelta(days=1)
    #return next_day, prev_day, dt
    #print(next_day, prev_day, dt)
    prev_temps = df_station[df_station.datetime == prev_day][field].values
    next_temps = df_station[df_station.datetime == next_day][field].values
    
    # Handle the case where one is missing
    prev_temp = prev_temps[0] if prev_temps.size > 0 else float("nan")
    next_temp = next_temps[0] if next_temps.size > 0 else float("nan")


    return np.nanmean([prev_temp, next_temp])



def create_new_date_row(row, dt, df_station):
    """Use an old row and new datetime to create a new row, to be interpolated on."""
    new_row = row.copy()
    # Change fields... (temp_mean_c, temp_min_c, temp_max_c, datetime, date)
    #print(new_row)
    
    #print(dt)
    # Replace dates...
    new_row['datetime'] = dt
    new_row['location_date'] = pd.to_datetime(dt).to_pydatetime().strftime("%-m/%-d/%Y")
    # Make temps nan
    new_row['temp_mean_c'] = interpolate_temperature(dt, df_station, field='temp_mean_c')
    new_row['temp_min_c'] = interpolate_temperature(dt, df_station, field='temp_min_c')
    new_row['temp_max_c'] = interpolate_temperature(dt, df_station, field='temp_max_c')

    #print(new_row)
    return new_row


# Create all missing rows
def build_interpolated_df(station_name, df_temperature):
# Station data
    df_station = df_temperature[df_temperature['name'] == station_name]

    station_dates = df_station.datetime.unique()
    missing_dts = missing_datetimes_of_station(station_name, df_temperature)

    # This row is just for a template
    matching_row = df_temperature[df_temperature.name==station_name].iloc[0]

    rows = []

    for missing_dt in missing_dts:
        rows.append(create_new_date_row(matching_row, missing_dt, df_station))
    return pd.DataFrame(rows)

def missing_datetimes_of_station(station_name, df_temperature):
    ref_dates = df_temperature.datetime.unique()
    df_station = df_temperature[df_temperature['name'] == station_name]

    station_dates = df_station.datetime.unique()
    missing_dts = []
    for d in ref_dates:
        if d not in station_dates:
            missing_dts.append(d)
            
    return missing_dts


def build_missing(df_temperature):
    dfs_interp = []
    for station_u in df_temperature.name.unique():
        dfs_interp.append(build_interpolated_df(station_u, df_temperature))
    
    # Contains the interpolations for all missing day-stations
    df_interp_full = pd.concat(dfs_interp, ignore_index=True)

    return df_interp_full

def build_full_temp(df_temperature):
    """Does interpolation and returns a dataframe with missing days
    filled in, for every place. """
    df_interp_full = build_missing(df_temperature)
    df_full = pd.concat([df_interp_full, df_temperature], ignore_index=True)
    df_full = df_full.sort_values(by=['datetime'])
    return df_full



def closest_stations(latlong, df):
    """Stations and their distances, ranked descending."""
    names = df['name'].values
    station_dists = {}
    for (lat, lon, name) in list(df[['Lat', 'Lon', 'name']].value_counts().index):
        if not(np.isnan(lat) or np.isnan(lon)):
            station_dists[name] = haversine(latlong, (lat, lon))     
            
    return sorted(station_dists.items(), key=lambda x: x[1])

def haversine(origin, destination):
    # Lat/Long
    # Returns distance in km
    lat1, lon1 = origin
    lat2, lon2 = destination
    if np.isnan(lat2) or np.isnan(lon2):
        return float("nan")
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def idw_temperature_avg_min_max(origin, df_subset):
    # Interpolate avg temperature using inverse-distance-weighting,
    # using the stations data from df_subset

    latlongs = df_subset[['Lat','Lon']].values
    mean_temps = df_subset['temp_mean_c'].values
    min_temps = df_subset['temp_min_c'].values
    max_temps = df_subset['temp_max_c'].values


    # Compute distances
    dists = [haversine(origin, latlong) for latlong in latlongs]
    if not dists:
        print(f"Not dists...{dists}, {origin}, {latlongs}")
    # Compute inverse-distance-weighted temperature, from stations in df_subset
    idw_means = [(t)*((1/(d+1))**2) for t,d in zip(mean_temps, dists)]
    idw_maxs = [(t)*((1/(d+1))**2) for t,d in zip(max_temps, dists)]
    idw_mins = [(t)*((1/(d+1))**2) for t,d in zip(min_temps, dists)]

    sqdist_sum = sum([((1/(d+1))**2) for d in dists])
    if sqdist_sum != 0:
        interpolated_mean = sum(idw_means)/sqdist_sum
        interpolated_min = sum(idw_mins)/sqdist_sum
        interpolated_max = sum(idw_maxs)/sqdist_sum
    else:
        (interpolated_mean, interpolated_min, interpolated_max) = (float("nan"), float('nan'), float('nan'))

    return (interpolated_mean, interpolated_min, interpolated_max)






def make_list_of_dicts_of_temps(df_population, df_temperature):
    # For each unique date, each city. 
    # Compute temperature (using 3 neighbors, idw)
    # And save a tuple (t_mean, t_min, t_max)
    list_of_dicttemps = []
    map_to_stations = {}
    for (lat, lon, city) in df_population[['Lat', 'Lon','City']].values:
        map_to_stations[city] = closest_stations((lat,lon), df_temperature)

    for datetime in df_temperature.datetime.unique():
        dicttemp = {}
        dicttemp['datetime'] = datetime
        # And each unique city
        for i in range(len(df_population)):
            series = df_population.iloc[i]
            loc = (series.Lat, series.Lon)
            close_stations = map_to_stations[series.City]

            # Use only 3 closest stations, on the date
            df_sub = df_temperature[df_temperature.datetime == datetime]
            df_sub = df_sub[df_sub.name.isin([s[0] for s in close_stations[:3]])]
            if df_sub.empty:
                continue
            mean_temp, min_temp, max_temp = idw_temperature_avg_min_max(loc, df_sub)
            dicttemp[f"{series.City}, {series.State}"] = (mean_temp, min_temp, max_temp)
        # Append the dictionary of many city: (mean, min, max)
        list_of_dicttemps.append(dicttemp)
    return list_of_dicttemps