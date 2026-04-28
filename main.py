import os
import requests
from google.transit import gtfs_realtime_pb2
import discord
import asyncio

API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("DISCORD_TOKEN")
MY_USER_ID = int(os.getenv("DISCORD_USER_ID"))

# URLs for NSW Trains v1
POSITIONS_URL = "https://api.transport.nsw.gov.au/v1/gtfs/vehiclepos/nswtrains"
UPDATES_URL = "https://api.transport.nsw.gov.au/v1/gtfs/realtime/nswtrains"
HEADERS = {"Authorization": f"apikey {API_KEY}", "Accept": "application/x-google-protobuf"}


target_set = "XP2013"
target_route = "4T.T.ST21"


async def send_discord_dm(message_text):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        user = await client.fetch_user(MY_USER_ID)
        await user.send(message_text)
        await client.close()

    await client.start(TOKEN)

def get_feed(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed

def main():
    try:
        # 1. Get Vehicle Positions and map trip_id -> vehicle_id (Physical Set)
        pos_feed = get_feed(POSITIONS_URL)
        vehicle_lookup = {}
        for entity in pos_feed.entity:
            if entity.HasField('vehicle'):
                t_id = entity.vehicle.trip.trip_id
                v_set = entity.vehicle.vehicle.id # This is where 'XP2012' lives
                vehicle_lookup[t_id] = v_set

        # 2. Get Trip Updates (Delays)
        upd_feed = get_feed(UPDATES_URL)

        print(f"{'SET ID':<10} | {'ROUTE':<12} | {'STATUS/DELAY'}")
        print("-" * 45)

        for entity in upd_feed.entity:
            if entity.HasField('trip_update'):
                t_id = entity.trip_update.trip.trip_id
                route = entity.trip_update.trip.route_id
                
                # Link the vehicle set ID using the trip_id
                physical_set = vehicle_lookup.get(t_id, "Unknown")
                
                # Get the delay (if available)
                delay = "On Time"
                updates = entity.trip_update.stop_time_update
                if updates and updates[0].arrival.delay:
                    delay = f"{updates[0].arrival.delay // 60}m late"

                if physical_set != "Unknown":
                    print(f"{physical_set:<10} | {route:<12} | {delay}")

                if physical_set == target_set and route.strip() == target_route:
                    print(f"ROUTE IS RUNNING WITH {physical_set}")
                    msg = f"ALERT: {physical_set} found on {route}!"
                    print(msg)
                    # Trigger the DM
                    asyncio.run(send_discord_dm(msg))



    except Exception as e:
        print(f"Error linking feeds: {e}")

if __name__ == "__main__":
    main()