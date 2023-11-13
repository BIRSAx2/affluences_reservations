import logging

import requests
import random
import json

import time
from datetime import date
import datetime
import sys

from enum import Enum

class ReservationType(Enum):
    FULL_DAY = 1
    ONLY_MORNING = 2
    ONLY_AFTERNOON = 3


logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")


def get_info(site_id: str, headers: dict) -> dict:
    """
    Retrieve information about a site from the Affluences API.

    Args:
        site_id (str): The ID of the site to get information about.
        headers (dict): A dictionary of headers to include in the request.

    Returns:
        dict: A dictionary containing information about the site.
    """
    url = "https://reservation.affluences.com/api/sites/" + site_id + "/infos"
    response = requests.get(url, headers=headers, timeout=5)
    return json.loads(response.text)


def get_resources(info_json: dict) -> list:
    """
    Extract a list of resources from the given info_json dictionary.

    Args:
        info_json (dict): A dictionary containing information about resources.

    Returns:
        list: A list of dictionaries, where each dictionary contains the name and ID of a resource.
    """
    resources_list = []

    for resource in info_json["types"]:
        resources_list.append(
            {
                "resource_name": resource["localized_description"],
                "resource_id": resource["resource_type"],
            }
        )
    return resources_list


def get_available_slots(site_id: str, resourse_type: str, date: date, headers: dict) -> dict:
    """
    Get available slots for a given site, resource type, and date.

    Args:
        site_id (str): The ID of the site to check availability for.
        resourse_type (str): The type of resource to check availability for.
        date (date): The date to check availability for.
        headers (dict): The headers to use for the HTTP request.

    Returns:
        dict: A dictionary containing the available slots for the given site, resource type, and date.
    """
    logging.debug("Getting available slots for " + str(date))

    url = (
        "https://reservation.affluences.com/api/resources/"
        + str(site_id)
        + "/available?date="
        + str(date)
        + "&type="
        + str(resourse_type)
        + "&capacity=1"
    )

    logging.debug("Making a call to URL: " + url)
    response = requests.get(url, headers=headers, timeout=5)

    return json.loads(response.text)


def compress_availabilities(available_slots: json) -> dict:
    """
    Compress the available time slots for each resource in the given list of available slots.

    Args:
        available_slots (json): A list of available time slots for each resource.

    Returns:
        dict: A dictionary containing the compressed time slots for each resource.
    """
    slots = {}

    for resource in available_slots:
        resource_id = resource["resource_id"]
        resource_name = resource["resource_name"]

        hours = resource["hours"]

        available_slots = filter(lambda x: x["state"] == "available", hours)
        available_slots = map(lambda x: x["hour"], available_slots)
        available_slots = map(
            lambda x: datetime.datetime.strptime(x, "%H:%M"), available_slots
        )

        # split into consecutive slots separated by 30 minutes

        consecutive_slots = []
        for slot in available_slots:
            if len(consecutive_slots) == 0:
                consecutive_slots.append([slot])
            else:
                if slot == consecutive_slots[-1][-1] + datetime.timedelta(minutes=30):
                    consecutive_slots[-1].append(slot)
                else:
                    consecutive_slots.append([slot])

        consecutive_slots = map(
            lambda x: {
                "slot": [x[0].time(), x[-1].time()],
                "length": (x[-1] - x[0]).total_seconds() / 60 / 60,
                "resource_name": resource_name,
            },
            consecutive_slots,
        )

        slots[resource_id] = list(consecutive_slots)
    return slots


def find_ideal_slot(slots: dict, length: int, start_time: datetime.time) -> list or None:
    """
    Find an available time slot of a given length starting at a given time.

    Args:
        slots (dict): A dictionary of available time slots for each resource.
        length (int): The length of the desired time slot in hours.
        start_time (datetime.time): The desired start time for the time slot.

    Returns:
        A list containing the name of the resource and the time slot if one is found,
        otherwise returns None.
    """
    
    start_time = datetime.datetime.combine(datetime.datetime.today(), start_time)
    logging.debug(
        "Looking for a slot of " + str(length) + " hours starting at " + str(start_time)
    )
    for resource in slots:
        for slot in slots[resource]:
            slot_start_time = datetime.datetime.combine(
                datetime.datetime.today(), slot["slot"][0]
            )
            if(length >= slot["length"]-0.5):
                continue
            
            if( abs(slot_start_time - start_time) > datetime.timedelta(minutes=30)):
                continue
            
            logging.debug("Found a slot of " + str(slot["length"]) + " hours " + str(slot["slot"]) + " starting at " + str(slot_start_time))
            return [resource, slot]
    
    return None



def get_header() -> dict:
    """
    Return a dictionary containing a random User-Agent header.

    Returns:
        dict: A dictionary containing a User-Agent header.
    """
    user_agent_list = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    ]
    return {"User-Agent": random.choice(user_agent_list)}


def construct_reservations(library_id: str, resourse_preference: list, slots: list) -> list:
    """
    Construct reservations for the given library, resource preferences, and time slots.

    Args:
        library_id (str): The ID of the library to make reservations for.
        resourse_preference (list): A list of resource names in order of preference.
        slots (list): A list of dictionaries representing time slots to make reservations for.

    Returns:
        list: A list of dictionaries representing the reservations made.
    """

    resourses = get_resources(get_info(library_id, get_header()))
    resource_ids = []
    for resource in resourse_preference:
        for res in resourses:
            if res["resource_name"] == resource:
                resource_ids.append((res["resource_id"], res["resource_name"]))

    reservations = []
    for resource, name in resource_ids:
        for slot in slots:
            avalable_slots = get_available_slots(
                library_id, resource, slot["date"], get_header()
            )
            compressed_slots = compress_availabilities(avalable_slots)
            ideal = find_ideal_slot(compressed_slots, slot["slot"][1], slot["slot"][0])

            if ideal != None:
                reservation = {
                    "resource_id": ideal[0],
                    "resource_type": name,
                    "resource_name": ideal[1]["resource_name"],
                    "start_time": slot["slot"][0],
                    "duration": slot["slot"][1],
                    "date": slot["date"],
                }
                reservations.append(reservation)
                slots.remove(slot)
        if len(slots) == 0:
            break

    if len(slots) > 0:
        logging.warning("Could not find all slots")
        logging.warning("Missing slots: " + str(slots))
    logging.debug("Found the following available slots: " + str(reservations))
    return reservations


def make_reservations(email: str, reservations: list, first_name: str = None, last_name:str = None, phone_number: str = None)-> None:
    """
    Given an email, a library_id, and the list of reservations, make the reservation.

    Args:
        email (str): The user's email.
        reservations (list): A list of reservations to be made.
    """
    logging.debug("Making reservations")

    base_url = "https://reservation.affluences.com/api/reserve/"

    for reservation in reservations:
        end_time = datetime.datetime.combine(
            reservation["date"], reservation["start_time"]
        ) + datetime.timedelta(hours=reservation["duration"])
        payload = {
            "auth_type": None,
            "date": str(reservation["date"]),
            "email": email,
            "start_time": str(reservation["start_time"]),
            "end_time": str(end_time.time()),
            "note": None,
            "user_firstname": first_name,
            "user_lastname": last_name,
            "user_phone": phone_number,
            "person_count": 1,
        }
        logging.info(
            f"Making a reservation in {reservation["resource_type"]} for seat {reservation['resource_name']} ({reservation['resource_id']}) on {reservation['date']} at "
            f"{reservation['start_time']} for {reservation['duration']} hours ending at {end_time.time()}"
        )
        response = requests.post(
            base_url + str(reservation["resource_id"]),
            json=payload,
            headers=get_header(),
            timeout=5,
        )

        if response.status_code == 200:
            logging.debug("Reservation successful")
        else:
            logging.error("Reservation failed: " + str(response.json()))

        time.sleep(5)



def generate_slots(start_date: date = datetime.datetime.now().date(), end_date: date =  datetime.datetime.now().date() + datetime.timedelta(weeks=1), reservation_type: ReservationType = ReservationType.FULL_DAY, slot_duration: int = 4) -> list:
    one_week_from_now = datetime.datetime.now().date() + datetime.timedelta(weeks=1)
    if end_date > one_week_from_now:
        end_date = one_week_from_now

    slots = []
    delta = end_date - start_date

    for i in range(delta.days + 1):
        day = start_date + datetime.timedelta(days=i)
        
        if(reservation_type == ReservationType.FULL_DAY or reservation_type == ReservationType.ONLY_MORNING):
            slots.append({
                "slot": [datetime.time(9, 0), slot_duration],
                "date": day,
            })
        
        if(reservation_type == ReservationType.FULL_DAY or reservation_type == ReservationType.ONLY_AFTERNOON):
            slots.append({
                "slot": [datetime.time(14, 0), slot_duration],
                "date": day,
            })

    return slots


def main():
    """
    Orchestrate the reservation process.

    Makes reservations based on resource preferences and available time slots.
    """
    email = "your_email@here.domain"
    # you can find the library id in the Network tab of the developer tools in your browser
    metelli = "93c5673e-1b0b-4286-ac4c-4c3bb286785b"
    
    
    resources_by_preference = [
        "BALLATOIO RIVISTE",
        "BALLATOIO LFA",
        "SALA LETTURA",
        "SALA PC",
    ]
    # slots = [
    #     {
    #         "slot": [datetime.time(9, 0), 4],
    #         "date": datetime.date(2023, 11, 20),
    #     },
    #     {
    #         "slot": [datetime.time(14, 0), 4],
    #         "date": datetime.date(2023, 11, 20),
    #     },
    # ]
    
    slots = generate_slots(start_date=datetime.date(2023,11,14),slot_duration=4)

    reservations_to_book = construct_reservations(
        library_id=metelli, resourse_preference=resources_by_preference, slots=slots
    )

    make_reservations(
        email=email,
        reservations=reservations_to_book,
    )
    logging.info("Done")


if __name__ == "__main__":    
    main()
