import os
from collections import deque
import numpy as np
import pandas as pd

base_path = '/Users/jonathanduberman/maverick_price_tool/data'

def add_csv_paths_to_deque_from_bp(base_path):
    #items on left are oldest, incomplete data has "incomplete" in filename and should be discarded
    for root, dirs, files in os.walk(base_path):
        csv_list = sorted(files)
    q = deque()
    for csv in csv_list:
        q.append(csv)
    return q

#data loading goes in here
def read_csvs_from_dequelinks(q):
    mavericks = pd.DataFrame()
    for file_name in list(q):
        #this is so you don't get incomplete data
        if file_name.find('incomplete') == -1:
            #move to next link in queue
            file_name = q.pop()
            carsdotcom_data = pd.read_csv(f'{base_path}//{file_name}')
            mavericks = pd.concat([mavericks, carsdotcom_data])
        else:
            q.pop()
            continue
    return mavericks

#all data cleaning operations should go in here
#note that there is a possibility for duplicates where price has been lowered the next day but all other data is the same
def process_maverick_data(mavericks):
    mavericks = mavericks.sort_values(by='date_parsed')
    mavericks = mavericks.drop_duplicates(subset=['model_year','make','model',
                                                    'trim_level','list_price','exterior_color',
                                                    'interior_color','hybrid_or_eco',
                                                    'mileage','dealer_address'], keep='last')
    acceptable_trim_levels = ['XL','XLT','LARIAT']
    mavericks = mavericks.drop('Unnamed: 0', axis=1)
    mavericks = mavericks[mavericks.trim_level.isin(acceptable_trim_levels)]
    #this is an important line of code, do not delete it
    mavericks = mavericks.dropna(subset='list_price') # drop na because we are about to do statistics on price

    #important cell, do not delete
    #calculate upper and lower quartile so you can get the interquartile range to eliminate outliers
    q75,q25 = np.percentile(np.array(mavericks.list_price),[75,25])
    intr_qr = q75 - q25
    q75,q25,intr_qr

    #max_ex = max value for extreme outliers, min_ex = min value for extreme outliers
    max_ex = q75+(3*intr_qr)
    min_ex = q25-(3*intr_qr)

    #this is an important cell of code, do not delete
    #only removing low outliers for now because high outliers DNE, and slightly "extreme" outliers should be evaluated on a case by case basis in this market
    mavericks_outliers_removed = mavericks.copy() #make copy to do stats work on
    mavericks_outliers_removed.loc[:,'list_price'] = mavericks.list_price.mask(mavericks.list_price < min_ex, other=np.nan) # set extreme prices to nan 
    #mavericks_outliers_removed.loc[:,'list_price'] = mavericks.list_price.mask(mavericks.list_price > max_ex, other=np.nan) # set extreme high prices to nan
    maverick_data_processed = mavericks_outliers_removed.reset_index(drop=True)

    #dropna, grab index of non-NaN and hit iloc with them, set as int
    maverick_data_processed.list_price.iloc[maverick_data_processed.loc[:,'list_price'].dropna().index] = maverick_data_processed.list_price.dropna().astype(int)
    maverick_data_processed.mileage.iloc[maverick_data_processed.loc[:,'mileage'].dropna().index] = maverick_data_processed.mileage.dropna().astype(int)

    return maverick_data_processed

def main():
    q = add_csv_paths_to_deque_from_bp(base_path) # first create the queue of csv paths to parse for data
    mavericks = read_csvs_from_dequelinks(q) # create a df of all of the maverick data in the filepath
    maverick_data_processed = process_maverick_data(mavericks) # process the data in the fp (dedupe, remove extrema)
    maverick_data_processed.to_csv(f'{base_path}//'+'maverick_data_processed.csv') # export result to a csv for trending

if __name__ == '__main__':
    main()

