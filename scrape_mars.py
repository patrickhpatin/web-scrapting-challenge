
# Dependencies
import pandas as pd
import time as time
from splinter import Browser
from bs4 import BeautifulSoup
import numpy as np
import requests
import pymongo
from flask import Flask, jsonify

# Initialize the chrome browser
# @NOTE: Replace the path with your actual path to the chromedriver
executable_path = {"executable_path": "chrome_driver\chromedriver"}
browser = Browser("chrome", **executable_path, headless=False)

# This delay varies based on the user's internet speed and how fast the JavaScript loads on the destination page
# 5 seems to work every time.  3 doesn't work at GT consistently.
sleep_delay = 5

# Function for navigating to a web page (we'll reuse this several times)
def init_page(url):
    # url = "https://mars.nasa.gov/news/"
    browser.visit(url)
    time.sleep(sleep_delay)

    html = browser.html
    ret_soup = BeautifulSoup(html, "html.parser")
    return ret_soup

# Function for following links on pages
def click_link(button_text):
    browser.click_link_by_partial_text(button_text)
    time.sleep(sleep_delay)
    
    html = browser.html
    ret_soup = BeautifulSoup(html, "html.parser")
    return ret_soup

# Function cleans up text by removing "\", removing " Enhanced" and replacing " with '
def clean_text(text_to_clean):
    cleaned_text = text_to_clean.replace("\'", "'")
    cleaned_text = cleaned_text.replace('"', "'")
    cleaned_text = cleaned_text.replace(' Enhanced', "")
    return cleaned_text


def populate_mars_db():
    try:
        # Nasa News
        soup = init_page("https://mars.nasa.gov/news/")
        news_title = clean_text(soup.find_all("div", class_="content_title")[1].find("a").text)
        news_p = clean_text(soup.find_all("div", class_="image_and_description_container")[0].find("div", class_="article_teaser_body").text)

        # Nasa's JPL Page
        base_url = "https://www.jpl.nasa.gov"
        url = base_url + "/spaceimages/?search=&category=Mars"
        soup = init_page(url)
        soup = click_link("FULL IMAGE")
        soup = click_link("more info")
        featured_image_url = soup.find("figure", class_="lede").find("a")["href"]
        featured_image_url = base_url + featured_image_url

        # Mars Weather Report
        soup = init_page("https://twitter.com/marswxreport?lang=en")
        mars_weather = soup.find_all("span", class_="css-901oao css-16my406 r-1qd0xha r-ad9z0x r-bcqeeo r-qvutc0")[27].text

        # Mars Facts In Table Format
        soup = init_page("https://space-facts.com/mars/")
        mars_table = soup.find("table", class_="tablepress tablepress-id-p-mars")

        # Mars Hemisphere Photos
        hemisphere_image_urls = []
        base_url = "https://astrogeology.usgs.gov"

        for i in range(4):
            soup = init_page("https://astrogeology.usgs.gov/search/results?q=hemisphere+enhanced&k1=target&v1=Mars")
            title = soup.find("div", class_="collapsible results").find_all("h3")[i].text
            
            soup = click_link(title)
            img_url = base_url + soup.find("img", class_="wide-image")["src"]
            title = clean_text(title)
            
            hemisphere_image_urls.append({"title": title, "img_url": img_url})

        # Create a dictionary that contains all of our return values
        dict_mars = [{
            "news_title": news_title,
            "news_p": news_p,
            "featured_image_url": featured_image_url,
            "hemisphere_image_urls": hemisphere_image_urls,
            "mars_table": mars_table}]

        # Initialize PyMongo to work with MongoDBs
        conn = 'mongodb://localhost:27017'
        client = pymongo.MongoClient(conn)

        # Define database and collection
        db = client.mars_db

        # Refresh database (i.e. drop table/collection)
        db.mars_data.drop()

        # Re-create the collection
        mars_collection = db.mars_data
        mars_collection.insert_one(dict_mars)
        
        return 200
# end def populate_mars_db()

def get_mars_data_from_db():
    conn = 'mongodb://localhost:27017'
    client = pymongo.MongoClient(conn)
    # Define database and collection
    db = client.mars_db

    # Re-create the collection
    mars_collection = db.mars_data

    return mars_collection
# end def get_mars_data_from_db()



#################################################
# Flask Setup
#################################################
app = Flask(__name__)



@app.route('/')
def index():
    return scrape()
# end def index()

#################################################
# Flask Routes
#################################################
# Display routes
@app.route('/routes')
def routes():
    """List of all available api routes."""
    return (
        f"Available Routes:<br/>"
        f"/routes"<br>
        f"/scrape"
    )
# end def routes()

@app.route("/scrape")
def scrape():
    try:
        if populate_mars_db() == 200:
            mars_data = get_mars_data_from_db()
        else:
            print("There was a problem scraping data from NASA. Please try again later.")
        # end if

        # Return the template with the teams list passed in
        return render_template('index.html', 
                news_title=mars_data.news_title, 
                news_p=mars_data.news_p, 
                featured_mars_image=mars_data.featured_mars_image, 
                mars_weather=mars_data.mars_weather, 
                mars_table=mars_data.mars_table,
                hem1_url=mars_data.hemisphere_image_urls[0].img_url,
                hem1_name=mars_data.hemisphere_image_urls[0].title,
                hem1_url=mars_data.hemisphere_image_urls[1].img_url,
                hem1_name=mars_data.hemisphere_image_urls[1].title,
                hem1_url=mars_data.hemisphere_image_urls[2].img_url,
                hem1_name=mars_data.hemisphere_image_urls[2].title,
                hem1_url=mars_data.hemisphere_image_urls[3].img_url,
                hem1_name=mars_data.hemisphere_image_urls[3].title)

    except Exception as e:
        print(e)
# end def scrape()



if __name__ == '__main__':
    app.run(debug=False)
