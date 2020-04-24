import numpy as np
import pandas as pd
#import xarray as xr
#import defopt
#import seawater
import os
import glob
import data.observational
from data.observational import Platform, Sample, Station, DataType
import datetime

#downloading datasets
station_IDs = pd.read_csv("https://www.smartatlantic.ca/erddap/tabledap/allDatasets.csv?datasetID",skiprows=[0])

if len(os.listdir("stationFiles") ) == 0:
    print("dowloading the data")
    #only downloads smart atlantic datasets
    for i in range(24):
        df = pd.read_csv("https://www.smartatlantic.ca/erddap/tabledap/"+ station_IDs.iloc[i,0]+".csv?station_name%2Ctime%2Clatitude%2Clongitude%2Cwind_spd_avg",skiprows=[1])   
        df=df.dropna(axis=0)
        #reformating the date and time 
    #    for j in range(len(df['time'])):
    #        date_time_str = df.iloc[j,1]
    #        date_time_str=date_time_str[0:10] + " " + date_time_str[11:19]
    #        date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
    #        df.iloc[j,1]=date_time_obj
        df.to_csv("stationFiles/"+station_IDs.iloc[i,0]+".csv", index=False)

VARIABLES = [ 'TEMP', 'PSAL' ]

META_FIELDS = {
    'PLATFORM_NUMBER': None,
    'PROJECT_NAME': None,
    'PI_NAME': None,
    'DATA_CENTRE': None,
    'PLATFORM_TYPE': None,
    'FLOAT_SERIAL_NO': None,
    'FIRMWARE_VERSION': None,
    'WMO_INST_TYPE': None
}

datatype_map = {}



def main(uri: str, filename: str):
    """Import Seal Profiles
    :param str uri: Database URI
    :param str filename: CIOOS csv Filename, or directory of files
    """
    data.observational.init_db(uri, echo=False)
    data.observational.create_tables()

    if os.path.isdir(filename):
        filenames = sorted(glob.glob(os.path.join(filename, "*.csv")))
    else:
        filenames = [filename]

    for fname in filenames:
        print(fname)
        ds=pd.read_csv(fname)
        
        print(ds)
        # we'll just make sure the DataTypes are in the db now.
        if DataType.query.get('wind_speed') is None:
            dt = DataType(
                key='wind_speed',
                name='Wind Speed',
                unit='m s-1'
            )
            data.observational.db.session.add(dt)

        data.observational.db.session.commit()

   

        # This is a single platform, so we can construct it here.
        p = Platform(
            type=Platform.Type.animal,
            unique_id=fname
        )
        p.attrs = {
#            'Principle Investigator': ds.pi_name,
#            'Platform Code': ds.platform_code,
#            'Species': ds.species,
        }

        data.observational.db.session.add(p)
        data.observational.db.session.commit()

         #Generate Stations
        
        df = ds[['latitude', 'longitude', 'time']]
        
        stations = [
            Station(
                platform_id=p.id,
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                time=row.time,
                )
            for idx, row in df.iterrows()
        ]

            # Using return_defaults=True here so that the stations will get
            # updated with id's. It's slower, but it means that we can just
            # put all the station ids into a pandas series to use when
            # constructing the samples.
        data.observational.db.session.bulk_save_objects(
            stations,
            return_defaults=True
        )
        df['station_name'] = [s.id for s in stations]

        # Generate Samples
#        df_samp = ds[
#            ['TEMP_ADJUSTED', 'PSAL_ADJUSTED', 'DEPTH']
#        ].to_dataframe().reorder_levels(['N_PROF', 'N_LEVELS'])
#
        samples = [
            [
                Sample(
                    station_id=df.STATION_ID[idx[0]],
                    datatype_key='wind_speed',
                    value=row.wind_spd_avg,
                    depth=0,
                ),
#                Sample(
#                    station_id=df.STATION_ID[idx[0]],
#                    datatype_key='sea_water_salinity',
#                    value=row.PSAL_ADJUSTED,
#                    depth=row.DEPTH,
#                )
         ]
#
            for idx, row in df_samp.iterrows()
        ]
        samples = [item for sublist in samples for item in sublist]
        samples = [s for s in samples if not pd.isna(s.value)]

        data.observational.db.session.bulk_save_objects(samples)
        data.observational.db.session.commit()


if __name__ == '__main__':
#    defopt.run(main)
    main("sqlite:///C:\sqlite/stationdbs.db", "stationFiles")