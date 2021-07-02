import pandas as pd
import math

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

def interpolate_missing_signal(series):
    return

def closest_stations(latlong, date, df):
    """Stations and their distances, ranked descending."""
    df_of_day = df[df['datetime']  == datetime.datetime.strptime(date, "%m/%d/%Y")]
    names = df_of_day['name'].values
    #df_of_day = df_of_day['Lat']
    station_dists = {}
    for i,latlong_station in enumerate(df_of_day[['Lat', 'Lon']].values):
        if not (np.isnan(latlong_station[0]) or np.isnan(latlong_station[1])):
            station_dists[names[i]] = haversine(latlong, latlong_station)
        
    return station_dists


def idw_temperature_avg_min_max(origin, df_subset):
    """Interpolate avg temperature at a location using inverse-distance-weighting,
    and the stations data from df_subset"""

    latlongs = df_subset[['Lat','Lon']].values
    mean_temps = df_subset['temp_mean_c'].values
    min_temps = df_subset['temp_min_c'].values
    max_temps = df_subset['temp_max_c'].values


    # Compute distances
    dists = [haversine(origin, latlong) for latlong in latlongs]
    # Compute inverse-distance-weighted temperature, from stations in df_subset
    idw_means = [(t)*((1/(d+1))**2) for t,d in zip(mean_temps, dists)]
    idw_maxs = [(t)*((1/(d+1))**2) for t,d in zip(max_temps, dists)]
    idw_mins = [(t)*((1/(d+1))**2) for t,d in zip(min_temps, dists)]

    sqdist_sum = sum([((1/(d+1))**2) for d in dists])
    interpolated_mean = sum(idw_means)/sqdist_sum
    interpolated_min = sum(idw_mins)/sqdist_sum
    interpolated_max = sum(idw_maxs)/sqdist_sum

    return (interpolated_mean, interpolated_min, interpolated_max)



# Functions to join the two tables, and get lat/long from the population table
# when possible
abbrev_map = {'Wash DC': 'Washington', 'NYC': 'New York', 'St Louis': 'St. Louis'}

def match_cityname(city, df):
    """ 1) Try to match exactly, and check abbrevaiation map.
        2) Split by / if there is one
        3) Repeat """
    if len(df[df.City == city]) == 1:
        return df[df.City == city]
    elif city in abbrev_map:
        return df[df.City == abbrev_map[city]]
    else:
        for piece in city.split("/"):
            split_name = piece.split(" ")
            if piece in abbrev_map:
                return df[df.City == abbrev_map[piece]]
            beginning = split_name[0]
            
            if len(df[df.City == beginning]) == 1:
                return df[df.City == beginning]
            
            if not df[df.City.str.contains(beginning)].empty:
                return df[df.City.str.contains(beginning)]
            
            elif (len(split_name) > 1) and not df[df.City.str.contains(piece.split(" ")[1])].empty:
                return df[df.City.str.contains(piece.split(" ")[1])]
            else:
                continue
                
                
def find_city(city, df):
    """Match the state based on strings, if there are multiple matches then pick the first."""
    matched_rows = match_cityname(city, df)
    if matched_rows is not None and len(matched_rows) == 1:
        return matched_rows.City.values[0]
    else:
        return None
    
    

def find_state(city, df):
    """Match the state based on strings"""
    matched_rows = match_cityname(city, df)
    if matched_rows is not None and len(matched_rows) == 1:
        return matched_rows.State.values[0]
    else:
        return None
    
def find_longlat(city, df):
    """Find Long, Lat..."""
    matched_rows = match_cityname(city, df)
    if matched_rows is not None and len(matched_rows) == 1:
        return matched_rows.Lon.values[0], matched_rows.Lat.values[0]
    else:
        return float("nan"), float("nan")