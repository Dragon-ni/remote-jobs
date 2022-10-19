import http.client
import io
import json

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.files import File

# from .base import BaseScrapingEngine, state_lookup_dict
# from .keywordselector import KeywordDrivenCandidate

# import time
# from urllib.request import Request, urlopen


# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait
# from webdriver_manager.chrome import ChromeDriverManager
urls = [
    "https://www.autumnridgewaukee.com",
    "https://www.hgliving.com/apartments/fl/miami/parkline-miami",
    "https://www.hgliving.com/apartments/wa/kent/chandlers-bay",
    "https://www.livetheivy.com",
    "https://dakotaaptsolympia.com",
    "https://deltamanorapts.com",
    "https://dovehollowapts.com",
    # "https://www.liveatsocial28.com",
    "https://www.delpradoapts.com",
    "https://www.deerhavenapts.com",
]

for main_url in urls:
    

    def test_link(main_url, link_group):
        key_list = list(link_group.keys())
        exist_link_type_list = [
            "floorplans_link",
            "amenities_link",
            "gallery_link",
            "tour_link",
            "contact_link",
        ]
        for link_type in exist_link_type_list:
            if link_type not in key_list:
                link_group[link_type] = main_url
        return link_group

    def get_links(main_url):
        # main_url_change = main_url.split(".com")
        url_container = BeautifulSoup(requests.get(main_url).content, "html.parser")
        href_link = url_container.find(attrs={"id": "drop-target-nav"})
        a_tag_container = href_link.find_all("a")
        link_group = {}
        exist_link_type_dict = {
            "amenit": "amenities_link",
            "property": "amenities_link",
            "floor": "floorplans_link",
            "feature": "floorplans_link",
            "gallery": "gallery_link",
            "photo": "gallery_link",
            "contact": "contact_link",
            "tour": "tour_link",
        }

        for idx in range(len(a_tag_container)):
            temp = a_tag_container[idx]["href"]
            for key in list(exist_link_type_dict.keys()):
                if key in str(temp.lower()):
                    link_group[exist_link_type_dict[key]] = main_url + temp
        link_group = test_link(main_url, link_group)
        return link_group

    def get_photos(gallery_link, name):
        photo_set = {}
        propertyphoto_set = []
        photo_container = BeautifulSoup(
            requests.get(gallery_link).content, "html.parser"
        )
        photo_detector = ["photo-cards-mosaic", "full-gallery"]
        for detector_key in photo_detector:
            photo_info = photo_container.find(attrs={"class": detector_key})
            if photo_info is not None:
                break
        photo_urls = []
        if photo_info is None:
            raise ValidationError("The URL cannot be scraped (unable to get photos)")
        img_tag_container = photo_info.find_all("img")
        for item in img_tag_container:
            photo_urls.append(item["src"])
        index = 0
        for item in photo_urls:
            index += 1
            url = item
            idx = url.rfind(".")
            extension_item = url[idx:]
            extension = extension_item.replace(".", "")
            res = requests.get(url, stream=True)
            if res.status_code == 200:
                propertyphoto_set.append(
                    {
                        "name": name + "{}".format(index),
                        "photo": File(
                            io.BytesIO(res.content),
                            name + "{}.".format(index) + extension,
                        ),
                        "category": "*-*",
                    }
                )
        #         if index == 0:
        #             photo_set["highlight_photo"] = File(
        #                 io.BytesIO(res.content), name + "." + extension
        #             )
        photo_set["propertyphoto_set"] = propertyphoto_set
        return photo_set

    def get_cominfo(main_url, link_group):
        def phone_format(n):
            return format(int(n[:-1]), ",").replace(",", "-") + n[-1]

        url_pet_friendly = main_url
        pet_info_container = BeautifulSoup(
            requests.get(url_pet_friendly).content, "html.parser"
        )
        pet_info_text = str(pet_info_container)
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False
        phone_container = BeautifulSoup(requests.get(main_url).content, "html.parser")
        phone_a_href = phone_container.find_all("a")
        for href_item in phone_a_href:
            if "href" in str(href_item):
                phone_info = href_item["href"]
                if "tel:" in phone_info:
                    phone_info = (
                        phone_info.replace("tel:", "")
                        .replace("-", " ")
                        .replace("%20", " ")
                        .replace("(", "")
                        .replace(")", "")
                        .replace(" ", "")
                    )
                    break
        phone_info = phone_format(phone_info)
        cominfo_container = BeautifulSoup(requests.get(main_url).content, "html.parser")
        com_info = cominfo_container.find("script", {"type": "application/ld+json"})
        com_info_json = json.loads(com_info.contents[0])
        property = {
            "name": com_info_json["name"],
            "homepage_link": main_url,
            "amenities_link": link_group["amenities_link"],
            "floorplans_link": link_group["floorplans_link"],
            "gallery_link": link_group["gallery_link"],
            "contact_link": link_group["contact_link"],
            "tour_link": link_group["tour_link"],
            "address": com_info_json["address"]["streetAddress"],
            "city": com_info_json["address"]["addressLocality"],
            "state": com_info_json["address"]["addressRegion"],
            "country_code": "US",
            "postal_code": com_info_json["address"]["postalCode"],
            "phone": phone_info,
            "pet_friendly": pet_allowed,
            "latitude": float(com_info_json["geo"]["latitude"]),
            "longitude": float(com_info_json["geo"]["longitude"]),
        }
        return property

    def get_amenity(amenities_link):
        propertyamenity_set = []
        propertyunitamenity_set = []
        amenity_group = {}
        amenity_container = BeautifulSoup(
            requests.get(amenities_link).content, "html.parser"
        )
        amenity_groups = amenity_container.find_all(attrs={"class": "html-content"})
        index = -1
        for amenity_dector in amenity_groups:
            index += 1
            if amenity_dector.find("h2") is not None:
                community_keys = [
                    "community",
                ]
                for key in community_keys:
                    if key in amenity_dector.find("h2").text.lower():
                        community_amenity_info = amenity_dector.find_all("li")
                        if community_amenity_info is None:
                            community_amenity_info = amenity_dector.find_all("p")

                        propertyamenity_set = []
                        for community_text in community_amenity_info:
                            temp = {"name": community_text.text}
                            propertyamenity_set.append(temp)
                unit_keys = ["inside", "in-home", "aparment"]
                for key in unit_keys:
                    if key in amenity_dector.find("h2").text.lower():
                        unit_amenity_info = amenity_dector.find_all("li")
                        if unit_amenity_info is None:
                            unit_amenity_info = amenity_dector.find_all("p")
                        propertyunitamenity_set = []
                        for unit_text in unit_amenity_info:
                            temp = {"name": unit_text.text}
                            propertyunitamenity_set.append(temp)
            else:
                if amenity_dector.find_all("li") is not None:
                    community_amenity_info = amenity_dector.find_all("li")
        amenity_group["propertyamenity_set"] = propertyamenity_set
        amenity_group["propertyunitamenity_set"] = propertyunitamenity_set
        return amenity_group

    def get_floorplan(floorplans_link):
        propertyunit_set = []
        floorplan_container = BeautifulSoup(
            requests.get(floorplans_link).content, "html.parser"
        )
        floorplan_scripts_container = floorplan_container.find("script")
        floorplan_scripts_container_str = str(floorplan_scripts_container)
        for item in floorplan_scripts_container_str.splitlines():
            if "G5_STORE_ID" in item:
                store_id = (
                    item.replace('"G5_STORE_ID": ', "")
                    .replace('"', "")
                    .replace(" ", "")
                    .replace(",", "")
                )
                conn = http.client.HTTPSConnection("inventory.g5marketingcloud.com")
                payload = ""
                headers = {}
                store_id_text = (
                    "/api/v1/apartment_complexes/" + store_id + "/floorplans"
                )
                conn.request("GET", store_id_text, payload, headers)
                res = conn.getresponse()
                data = res.read()
                data_text = str(data)
                if len(data_text) < 5:
                    if "deer" in floorplans_link:
                        return propertyunit_set
                    return get_api_liveatsocial()
                data_test = data_text.replace("b'", "").replace("'", "")
                data_json = json.loads(data_test)
                for item in data_json["floorplans"]:
                    temp = {
                        "bedrooms": item["beds"],
                        "bathrooms": item["baths"],
                        "floor_area": item["sqft"],
                        "starting_rate": item["starting_rate"],
                    }
                    propertyunit_set.append(temp)
        return propertyunit_set

    def get_api_liveatsocial(self):
        url = (
            "https://entrata.liveatsocial28.com/gainesville/social28/student?"
            + "&amp;is_responsive_snippet=1&amp;snippet_type=website"
            + "&amp;occupancy_type=10&amp;locale_code=en_US&amp;is_collapsed=1&amp;include_paragraph_content=1&amp"
        )
        url_container = BeautifulSoup(requests.get(url).content, "html.parser")
        url_container_analysing = url_container.find_all("span")
        floor_plan_total = ""
        propertyunit_set = []
        for item in url_container_analysing:
            floor_plan_total += " : " + item.text
        floor_plan_total.replace("\xa0\xa0/", "").replace("\n665\n+\n", "")
        floor_plan_tatic = floor_plan_total.split("Bed / Bath")
        for item in floor_plan_tatic:
            item = item.replace("\xa0\xa0/", "").replace("\n665\n+\n", "")
            if "Deposit" in item:
                starting_rate = 0
                if "Student" in item:
                    item_cut = item.split("Student")
                    item = item_cut[0]
                item_cut_again = item.split("Sq. Ft")
                item_cut_bdba = item_cut_again[0].split(":")
                for item_index in item_cut_bdba:
                    if item_index == "":
                        continue
                    else:
                        if "bd" in item_index and "ba" in item_index:
                            bd_ba = item_index.split(" ")
                            bedrooms = bd_ba[1].replace("bd", "")
                            bathrooms = bd_ba[2].replace("ba", "")
                item_cut_sqft = item_cut_again[1].split(":")
                sqft = 0
                item_index_result = ""
                for item_index in item_cut_sqft:
                    if item_index == "":
                        continue
                    else:
                        for x in range(len(item_index)):

                            if item_index[x] in "1234567890":
                                item_index_result += item_index[x]
                if item_index_result == "":
                    sqft = 0
                else:
                    sqft = int(item_index_result)
                temp = {
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "floor_area": sqft,
                    "starting_rate": starting_rate,
                }
                propertyunit_set.append(temp)
        return propertyunit_set

    def run(main_url):

        property = {}
        link_group = get_links(main_url)
        photo_set = {}
        property = get_cominfo(main_url, link_group)
        photo_set = get_photos(link_group["gallery_link"], property["name"])
        property = get_cominfo(main_url, link_group)
        amenity_group = get_amenity(link_group["amenities_link"])
        property["propertyamenity_set"] = amenity_group["propertyamenity_set"]
        property["propertyunitamenity_set"] = amenity_group["propertyunitamenity_set"]
        property["propertyunit_set"] = get_floorplan(link_group["floorplans_link"])
        property["propertyphoto_set"] = photo_set["propertyphoto_set"]
        # property["highlight_photo"] = photo_set["highlight_photo"]
        filename = "g5" + main_url + ".txt"
        f = open(filename, "a")
        f.write(property)
        f.close()
        return property

    
    result = run(main_url)
