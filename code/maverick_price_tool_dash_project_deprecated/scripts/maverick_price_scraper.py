# %%
#imports for logfile
import os
import inspect 
import logging

from bs4 import BeautifulSoup
import requests
import pandas as pd
import datetime
import time
import random
import re #for pulling integers out of strings
import math #for the ceil rounding function
import proxy_config #private proxy

# %%
#format date for filename as per ISO spec
todays_date_fn = datetime.datetime.today().strftime('%Y-%-m-%dT%H%M%S')

todays_date = str(datetime.datetime.now().date()) #date for the data in the parsed_date column

# %%
#if in a script in an actual basepath, can use the autogenerating script_name, otherwise must use an explicitly called out script name
'''
#create a logfile
script_name = os.path.splitext(
    os.path.basename(
        inspect.getfile(inspect.currentframe())
    )
)[0]
'''
script_name = 'maverick_price_scraper'
log_path = '/Users/jonathanduberman/maverick_price_tool/log'
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=f'{log_path}//{todays_date_fn}-{script_name}.log', level=logging.DEBUG, format=log_format)


# %%
headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'}

# %%
#initial url is just to see how many matches there are to get how many pages to set up
first_url = 'https://www.cars.com/shopping/results/?dealer_id=&keyword=&list_price_max=&list_price_min=&makes[]=ford&maximum_distance=all&mileage_max=&models[]=ford-maverick&page=1&page_size=100&sort=distance&stock_type=used&year_max=&year_min=&zip=28533'

# %%

proxies = proxy_config.proxy_info #private proxy information
response=requests.get(first_url,headers=headers, proxies=proxies) # http response code 200 is ok
soup=BeautifulSoup(response.content, 'html.parser') # soup is the large body of text to search for all of the information

#see how many matches there are in your nationwide search for ford mavericks
matches = soup.find_all("span", class_='total-filter-count')[0].get_text().strip()
matches = re.findall(r'\d+',matches)
matches = [int(x) for x in matches][0]
pages = math.ceil(matches/100) #this is how many pages are needed based on matches of our search result

# %%
#generates a list of all of the urls that we will then parse for listing links
search_urls = []
for page_num in range(1,pages+1):
    search_url = f'https://www.cars.com/shopping/results/?dealer_id=&keyword=&list_price_max=&list_price_min=&makes[]=ford&maximum_distance=all&mileage_max=&models[]=ford-maverick&page={page_num}&page_size=100&sort=distance&stock_type=used&year_max=&year_min=&zip=28533'
    search_urls.append(search_url)

# %%
########################
#now that we have the page links where we will get the urls for the individual listings, we can grab the listing links
#put the data grabbing loop inside of this eventually, but for now you could do it one page at a time?  no...you dont even ned to do that once you have the master list of listing links
mav_links = []
for search_url_iterator in range(len(search_urls)):
    #search_url_iterator = 0
    response=requests.get(search_urls[search_url_iterator],headers=headers, proxies=proxies)
    soup=BeautifulSoup(response.content, 'html.parser')

    #named raw because further processing is required to get just the links.  These links will be used to get the pricing data for each car
    mav_links_raw = soup.find_all('a', class_='image-gallery-link vehicle-card-visited-tracking-link')
    #loop through the text of html "a" class's to get just the isolated listing links
    for i in range(len(mav_links_raw)):
        mav_links.append(mav_links_raw[i].get('href'))
    time.sleep(2)


################################################################################################################
#now that we have the links, we can begin with pricing info, which we will do in a completely separate loop

# %%
#len(mav_links)

# %%
def carsdotcom_datagrabber(proxies):
    try:
        #format date for filename as per ISO spec
        todays_date_fn = str(datetime.datetime.now())[:19]
        todays_date_fn = todays_date_fn.replace(' ','T')
        todays_date_fn = todays_date_fn.replace(':','')

        #loop
        #create the df for the vehicle data
        columns = ['condition','model_year','make','model','trim_level','list_price', 'exterior_color','interior_color','fwd_or_awd','hybrid_or_eco','mileage','dealer_address','date_parsed','url','data_source_name']
        carsdotcom_for_sale = pd.DataFrame(columns=columns)
        for i in range(len(mav_links)):
            base_path = 'http://cars.com'
            url = f'{base_path}//{mav_links[i]}'
            data_source_name = 'cars.com'

            response=requests.get(url,headers=headers, proxies=proxies)
            soup=BeautifulSoup(response.content, 'html.parser') #html parser because when inspected source, top of page said html, but can always try xml to see if it works better

            # Grab items fom the title.  this is where the bulk of the information is stored
            # if theres no title there is no point in continnuing to try to get anything from this article
            try:    
                title = soup.findAll('title')[0].get_text().strip() #title format = used/new, make, model, trim, "for sale", price
                logging.debug(f'title : {title} iteration: {i}')
                logging.info(f'URL: {url}')
            except Exception as TitleError:
                title = None
                logging.exception(TitleError) 
                continue

            title = title.upper() #make everything uppercase in order to make filtering easier later for NLP
            title_split = title.rsplit() #split into a list to be able to separate components and begin storage [condition, year, make, model, trim, "for", "sale", prices, "|", "CARS.COM"]
            if len(title_split) >= 5:
                title_split_new = title_split[:5] #remove for sale from title/just get first 5 items
            if len(title_split) < 5:
                logging.info('Title too short to continue collecting data')
                continue
            try: 
                car_price_int = title_split[7].replace(',','') #make price an int so we can do math on it later
            except Exception as car_price_int_indexerror:
                car_price_int = None
                logging.exception(car_price_int_indexerror)
            try:
                car_price_int = int(car_price_int.replace('$','')) #make price an int so we can do math on it later
            except Exception as car_price_int_exception:
                car_price_int = None
                logging.exception(car_price_int_exception)
            title_split_new.append(car_price_int) #add price back into list

            #get seller info
            meta = soup.findAll('meta') #seller info in a meta tag
            try:
                seller_info_section = soup.find_all('section', class_='seller-info')[0] #seller info in a seller info class (very creative naming scheme)
            except Exception as seller_info_section_error:
                seller_info_section = None
                logging.exception(seller_info_section_error)
            #try to find the dealer or sellers address by first looking at the dealer's address location, and if index error, look at sellers address, and if index error, no address returned
            try:
                dealer_address = seller_info_section.find_all('div',class_='dealer-address')[0].get_text().strip() # dealer adress in a sub class called dealer-address or seller-address
            except Exception as dealer_address_index_error:
                dealer_address = None
                logging.exception(dealer_address_index_error)
            if dealer_address == None:
                try:
                    dealer_address = seller_info_section.find_all('div',class_='seller-address')[0].get_text().strip() # private seller               
                except Exception as seller_address_exception:
                    dealer_address = None 
                    logging.exception(seller_address_exception)

            #now move on to the car description
            try: 
                car_description = soup.find_all('dl', class_="fancy-description-list")[0] #find certain specifics of vehicle description
            except Exception as CarDescrptionError:
                car_description = None
                logging.exception(CarDescrptionError)

            if car_description is not None:
                try:
                    exterior_color = car_description.findAll('dd')[0].get_text().strip() #dd is the characteristic
                except Exception as ExteriorColorException:
                    exterior_color = None
                    logging.exception(ExteriorColorException)
                try:
                    interior_color = car_description.findAll('dd')[1].get_text().strip()
                except Exception as InteriorColorException:
                    interior_color = None
                    logging.exception(InteriorColorException)
                try:
                    fwd_or_awd = car_description.findAll('dd')[2].get_text().strip()
                except Exception as FwdOrAwdException:
                    fwd_or_awd = None
                    logging.exception(FwdOrAwdException)
                try:
                    hybrid_or_eco = car_description.findAll('dd')[4].get_text().strip()
                except Exception as HybridOrEcoException:
                    hybrid_or_eco = None
                    logging.exception(HybridOrEcoException)
                    #finds out which position in the car description the mileage is in as to prevent errors

                for k in range(len(car_description.findAll('dt'))):
                    desc_str = car_description.findAll('dt')[k].get_text().strip().upper()
                    if desc_str == 'MILEAGE':
                        mileage = car_description.findAll('dd')[k].get_text().strip()
                    else:
                        pass
                try:
                    mileage_int = mileage.replace(',','') #remove comma
                    mileage_int = int(mileage_int.replace(' mi.', '')) #Need to turn mileage into integer to do math on it
                except Exception as mileage_int_exception:
                    mileage_int = None
                    logging.exception(mileage_int_exception)
            if car_description is None:
                exterior_color,interior_color,fwd_or_awd,hybrid_or_eco,mileage_int = None, None, None, None, None

            fancy_description = [exterior_color,interior_color,fwd_or_awd,hybrid_or_eco,mileage_int]
            carsdotcom_output = title_split_new + fancy_description + [dealer_address] + [todays_date] + [url] + [data_source_name] #combine the lists before entering into the dataframe

            carsdotcom_for_sale.loc[i] = carsdotcom_output #add the new data to the df
            #time.sleep(10)
            logging.debug(f'Iteration Number: {i}' + ' successful')
            time.sleep(2+random.randint(0,3))


        carsdotcom_for_sale.to_csv(f'/Users/jonathanduberman/maverick_price_tool/data/scraper-output/{todays_date_fn}-carsdotcom_for_sale.csv')
        logging.info('Scraping complete.  All available data has been scraped.')
        return carsdotcom_for_sale, print('Done')

    except Exception as master_exception:
        carsdotcom_for_sale.to_csv(f'/Users/jonathanduberman/maverick_price_tool/data/scraper-output/{todays_date_fn}-carsdotcom_for_sale-incomplete.csv')
        print('error occurred')
        logging.exception(master_exception,'scraping incomplete and with errors')
        return carsdotcom_for_sale, print('Done with errors')

# %%
def main():
    odf = carsdotcom_datagrabber(proxies)
    print(f'Time Completed: {str(datetime.datetime.now())}')
    
if __name__ == '__main__':
    main()


